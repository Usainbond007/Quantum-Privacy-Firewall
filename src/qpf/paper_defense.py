"""Defense evaluated ON TOP of the paper-aligned benchmark (Buesser & Kurmus, Section V direction).

Question: can verified, semantics-preserving rewrites of the *source* circuit lower the intent recoverability of the final
transpiled circuit at bounded depth / two-qubit / width overhead, when the attacker is the paper's Table II + Random Forest
pipeline RETRAINED on protected circuits?

Partitions (grouped by source circuit, per generator): 3 train / 1 validation / 2 test variants. Candidate search, the frozen
surrogate and every classifier hyper-parameter use TRAIN only (grouped CV); validation is reported separately; the test split
is never used to select anything.
Arms: guided (label-free frozen-surrogate selection) vs random eligible candidate.
Attackers: static (trained on unprotected), adaptive RF / GBoost / LogReg (retrained on protected), normalization-aware RF
(re-optimises every observed circuit at optimization level 3), metadata-only RF (size/complexity confound control)."""
import time, warnings
import numpy as np, pandas as pd
from concurrent.futures import ProcessPoolExecutor
from qiskit import transpile
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from . import compilation, defenses, verification, selection, paper_circuits as PC, paper_benchmark as PB
warnings.filterwarnings("ignore")
FEAT = PB.FEAT; NFEAT = ["n_" + f for f in FEAT]; META = ["n_gates", "depth", "n2q"]; LAB = PC.CLASS_LABELS

def _tseed(strategy, cseed, base):
    """Transpiler-seed diversification: the 'seed' strategy compiles the unchanged circuit with a candidate-specific seed."""
    return int(cseed % 100000) + 1 if "seed" in strategy.split("+") else int(base)

def _cand_job(job):
    gen, var, n, strat, cseed, opts, tseed, backend, qto = job
    sid = PC.source_id(gen, var); meta = dict(generator=gen, intent=PC.GENERATORS[gen], variant=var, source_id=sid, strategy=strat, cand_seed=cseed, n_qubits=n, cid=f"{sid}|{strat}|{cseed}")
    try:
        base = PC.make_source(gen, n, var); cand, layout = defenses.apply_strategy(base, strat, cseed, backend)
        t = time.perf_counter(); v = verification.verify(base, cand, operator_max_qubits=10, qcec_timeout_s=qto); vt = time.perf_counter() - t
        rows = []
        for o in opts:
            r = dict(meta, opt=o, verify_status=v.status, verify_method=v.method, verify_note=v.note, verify_s=vt)
            if v.status == "PASS":
                tc, dt = compilation.compile_circuit(cand, o, _tseed(strat, cseed, tseed), layout, backend); r.update(PB.physical_row(tc, backend)); r["compile_s"] = dt
            rows.append(r)
        return rows
    except Exception as ex:
        return [dict(meta, opt=-1, verify_status="ERROR", verify_note=repr(ex)[:200])]

def _norm_job(job):
    """Normalization-aware attacker's view: re-optimise the observed physical circuit at level 3, then featurize."""
    cid, gen, var, n, strat, cseed, opt, tseed, backend = job
    try:
        base = PC.make_source(gen, n, var); cand, layout = defenses.apply_strategy(base, strat, cseed, backend) if strat != "baseline" else (base, None)
        tc, _ = compilation.compile_circuit(cand, opt, _tseed(strat, cseed, tseed), layout, backend)
        tn = transpile(tc, backend=compilation.get_backend(backend), optimization_level=3, seed_transpiler=0)
        r = PB.physical_row(tn, backend); return dict(cid=cid, opt=opt, **{"n_" + f: r[f] for f in FEAT})
    except Exception as ex:
        return dict(cid=cid, opt=opt, error=repr(ex)[:200])

def build_candidates(cfg, workers=2, log=print):
    d = cfg["defense"]; n = d["n_qubits"]; path = PB.out_dir(cfg, "defense") / "candidates.csv"; jobs = []
    for gi, gen in enumerate(PC.GENERATORS):
        for v in range(cfg["variants"]):
            for k, st in enumerate(d["strategies"]): jobs.append((gen, v, n, st, (gi * 100 + v) * 1000 + k + 1, d["opt_levels"], cfg["transpile_seed"], cfg["backend"], d["qcec_timeout_s"]))
    prev = pd.read_csv(path) if path.exists() else pd.DataFrame(); done = set(prev.cid) if len(prev) else set()       # resume
    todo = [j for j in jobs if f"{PC.source_id(j[0], j[1])}|{j[3]}|{j[4]}" not in done]
    log(f"[defense] {len(jobs)} candidate circuits x {len(d['opt_levels'])} opt levels; {len(todo)} to do (resume), workers={workers}")
    t0 = time.perf_counter(); rows = [prev] if len(prev) else []; buf = []
    with ProcessPoolExecutor(workers) as ex:
        for i, r in enumerate(ex.map(_cand_job, todo, chunksize=1)):
            buf += r
            if (i + 1) % 50 == 0 or i + 1 == len(todo):
                pd.concat(rows + [pd.DataFrame(buf)], ignore_index=True).to_csv(path, index=False); log(f"  {i + 1}/{len(todo)} ({time.perf_counter() - t0:.0f}s)")
    return pd.read_csv(path)

def baseline_rows(cfg, ds):
    d = cfg["defense"]; b = ds[(ds.n_qubits == d["n_qubits"]) & (ds.opt.isin(d["opt_levels"])) & (ds.status == "OK")].copy()
    b["strategy"] = "baseline"; b["cand_seed"] = 0; b["cid"] = b.source_id + "|baseline|0"; b["verify_status"] = "PASS"; b["verify_method"] = "baseline"; return b

def _cfgd(cfg): return {**cfg, "rf_grid": cfg["defense"]["rf_grid"]}
def _fit(tr, cols, cfg, seed): return PB.fit_attacker(tr, cols, _cfgd(cfg), seed)

def _simple(kind, tr, cols, seed):
    y = tr.intent.to_numpy(); X = tr[cols].to_numpy(float)
    m = GradientBoostingClassifier(random_state=seed) if kind == "gboost" else make_pipeline(StandardScaler(), LogisticRegression(max_iter=5000, random_state=seed))
    return m.fit(X, y)

def _acc(model, te, cols):
    te = te.dropna(subset=cols)
    return PB._score(model, te, cols) if len(te) else None

def _select(cands, surrogates, rng, budget, mode):
    """Per (source, opt): pick among baseline + eligible candidates. guided = least frozen-surrogate confidence (label-free); random = uniform."""
    c = cands.copy(); c["reason"] = c.apply(lambda r: selection.reject_reason(r, budget), axis=1); e = c[c.reason == ""].copy(); conf = np.zeros(len(e))
    for o, sur in surrogates.items():
        m = (e.opt == o).to_numpy()
        if m.any(): conf[m] = sur.predict_proba(e.loc[m, FEAT].to_numpy(float)).max(axis=1)
    e["conf"] = rng.random(len(e)) if mode == "random" else conf
    return e.sort_values(["source_id", "opt", "conf", "cost", "cid"]).groupby(["source_id", "opt"], as_index=False).head(1).copy()

def rejection_table(allc, budgets):
    """Every non-baseline candidate x opt level with the reason it was rejected (or 'accepted') at each budget."""
    c = allc[allc.strategy != "baseline"].copy(); out = {}
    for b in budgets:
        r = c.apply(lambda x: selection.reject_reason(x, b), axis=1).replace("", "accepted")
        r = r.str.replace(r"\(.*\)", "", regex=True).str.replace(r"[\d.]+%", "X%", regex=True).str.strip()
        out[str(b)] = r.value_counts().to_dict()
    return out

def paired_bootstrap(rows, n_boot, seed=0):
    """rows: DataFrame[source_id, y_true, p_base, p_prot]. Resample source circuits; returns CI of macro-F1(base)-macro-F1(prot)."""
    rng = np.random.default_rng(seed); g = {k: v for k, v in rows.groupby("source_id")}; keys = list(g); deltas = []
    for _ in range(n_boot):
        d = pd.concat([g[keys[i]] for i in rng.integers(0, len(keys), len(keys))])
        deltas.append(f1_score(d.y_true, d.p_base, labels=LAB, average="macro", zero_division=0) - f1_score(d.y_true, d.p_prot, labels=LAB, average="macro", zero_division=0))
    return [float(np.percentile(deltas, 2.5)), float(np.percentile(deltas, 97.5))]

def evaluate_defense(cfg, ds, cands, log=print, workers=2):
    d = cfg["defense"]; base = baseline_rows(cfg, ds); cands = cands.copy(); cands["n_qubits_logical"] = d["n_qubits"]; base["n_qubits_logical"] = d["n_qubits"]
    allc = pd.concat([base, cands[cands.verify_status.notna()]], ignore_index=True)
    allc = selection.add_overheads(allc.rename(columns={"source_id": "base_id"}), base.rename(columns={"source_id": "base_id"})[["base_id", "opt", "depth", "n2q", "active"]]).rename(columns={"base_id": "source_id"})
    cand_u = cands.drop_duplicates("cid")
    stats = {"verification": cand_u.groupby("verify_status").size().to_dict(), "verification_methods": cand_u.groupby("verify_method").size().to_dict(),
             "verification_by_strategy": {s: g.verify_status.value_counts().to_dict() for s, g in cand_u.groupby("strategy")},
             "verification_failure_reasons": cand_u[cand_u.verify_status != "PASS"].groupby(["verify_status", "verify_method", "verify_note"]).size().rename("n").reset_index().to_dict("records"),
             "rejections_by_budget": rejection_table(allc[allc.verify_status.notna()], d["budgets"])}
    pas = allc[(allc.verify_status == "PASS") & allc.depth.notna()].copy()
    bf = base.set_index(["source_id", "opt"])[FEAT]; c = pas[pas.strategy != "baseline"]
    diff = np.abs(c[FEAT].to_numpy(float) - bf.loc[list(zip(c.source_id, c.opt))].to_numpy(float)).max(axis=1); pas.loc[c.index, "changed"] = diff > 1e-9
    stats["survival_by_strategy_opt"] = {f"{s}|L{o}": float(g.changed.mean()) for (s, o), g in pas[pas.strategy != "baseline"].groupby(["strategy", "opt"])}
    elig = pas[(pas.strategy != "baseline") & (pas.cost <= max(d["budgets"]) + 1e-12)]
    parse = lambda r: (r.cid, r.generator, int(r.variant), d["n_qubits"], r.strategy, int(r.cand_seed), int(r.opt), cfg["transpile_seed"], cfg["backend"])
    jobs = [parse(r) for r in pas[pas.strategy == "baseline"].itertuples()] + [parse(r) for r in elig.itertuples()]; npath = PB.out_dir(cfg, "defense") / "norm_features.csv"
    if npath.exists(): nd = pd.read_csv(npath); log(f"[defense] reusing {len(nd)} cached normalization-aware features")
    else:
        log(f"[defense] normalization-aware features for {len(jobs)} circuits"); done = []
        with ProcessPoolExecutor(workers) as ex: nd = pd.DataFrame(list(ex.map(_norm_job, jobs, chunksize=4)))
        nd.to_csv(npath, index=False)
    nd = nd.dropna(subset=NFEAT).drop_duplicates(["cid", "opt"]); pas = pas.merge(nd, on=["cid", "opt"], how="left")
    pas.to_csv(PB.out_dir(cfg, "defense") / "all_candidates_with_overheads.csv", index=False)
    res = {"stats": stats, "n_sources": int(pas.source_id.nunique()), "baseline": [], "budgets": {str(b): {"guided": [], "random": []} for b in d["budgets"]}}; pairs = {}
    for s in range(cfg["n_splits"]):
        part = PB.make_splits(cfg, s, d["val_variants"]); pas["_p"] = pas.source_id.map(part)
        assert set(pas[pas._p == "train"].source_id).isdisjoint(set(pas[pas._p == "test"].source_id)) and set(pas[pas._p == "train"].source_id).isdisjoint(set(pas[pas._p == "val"].source_id))
        B = pas[pas.strategy == "baseline"]; btr, bva, bte = B[B._p == "train"], B[B._p == "val"], B[B._p == "test"]
        surr = {o: _fit(btr[btr.opt == o], FEAT, cfg, s).best_estimator_ for o in d["opt_levels"]}        # frozen surrogate: train split only
        stat = _fit(btr, FEAT, cfg, s); bm = {"pooled": _acc(stat, bte, FEAT), "pooled_val": _acc(stat, bva, FEAT)}
        for o in d["opt_levels"]: bm[f"L{o}"] = _acc(_fit(btr[btr.opt == o], FEAT, cfg, s), bte[bte.opt == o], FEAT)
        bm["gboost_pooled"] = _acc(_simple("gboost", btr, FEAT, s), bte, FEAT); bm["logreg_pooled"] = _acc(_simple("logreg", btr, FEAT, s), bte, FEAT)
        bm["metadata_only"] = _acc(_fit(btr, META, cfg, s), bte, META); res["baseline"].append(bm)
        pb = pd.Series(stat.predict(bte[FEAT].to_numpy(float)), index=pd.MultiIndex.from_arrays([bte.source_id, bte.opt]))
        log(f"  split {s}: unprotected pooled F1 test={bm['pooled']['macro_f1']:.3f} val={bm['pooled_val']['macro_f1']:.3f} (metadata-only {bm['metadata_only']['macro_f1']:.3f})")
        for b in d["budgets"]:
            for mode in ("guided", "random"):
                sel = _select(pas, surr, np.random.default_rng([cfg["seed"], s, int(b * 100)]), b, mode); sel["_p"] = sel.source_id.map(part)
                tr, va, te = (sel[sel._p == k] for k in ("train", "val", "test")); one = {"split": s, "arm": mode}
                m_ad = _fit(tr, FEAT, cfg, s); one["static"] = _acc(stat, te, FEAT); one["adaptive_pooled"] = _acc(m_ad, te, FEAT); one["adaptive_pooled_val"] = _acc(m_ad, va, FEAT)
                for o in d["opt_levels"]: one[f"adaptive_L{o}"] = _acc(_fit(tr[tr.opt == o], FEAT, cfg, s), te[te.opt == o], FEAT)
                one["adaptive_gboost"] = _acc(_simple("gboost", tr, FEAT, s), te, FEAT); one["adaptive_logreg"] = _acc(_simple("logreg", tr, FEAT, s), te, FEAT)
                one["metadata_only"] = _acc(_fit(tr, META, cfg, s), te, META)
                tn, en = tr.dropna(subset=NFEAT), te.dropna(subset=NFEAT)
                if len(tn) and len(en): one["norm_aware_pooled"] = _acc(PB.fit_attacker(tn, NFEAT, _cfgd(cfg), s), en, NFEAT)
                one["cost"] = {k: float(te[k].mean()) for k in ("d_depth", "d_n2q", "d_active")}
                one["fraction_changed"] = float(((te.strategy != "baseline") & te.changed.fillna(False).astype(bool)).mean()); one["fraction_baseline_kept"] = float((te.strategy == "baseline").mean())
                one["strategy_mix"] = te.strategy.value_counts(normalize=True).to_dict(); res["budgets"][str(b)][mode].append(one)
                pp = pd.Series(m_ad.predict(te[FEAT].to_numpy(float)), index=pd.MultiIndex.from_arrays([te.source_id, te.opt]))
                j = pd.DataFrame({"p_prot": pp}).join(pd.DataFrame({"p_base": pb})).dropna(); j["y_true"] = [PC.GENERATORS[sid.rsplit("-v", 1)[0]] for sid, _ in j.index]
                j["source_id"] = [sid for sid, _ in j.index]; j["split"] = s; pairs.setdefault((str(b), mode), []).append(j.reset_index(drop=True))
    res["paired_ci"] = {f"{b}|{m}": paired_bootstrap(pd.concat(v), d["n_boot"]) for (b, m), v in pairs.items()}
    res["summary"] = summarize_defense(res, d); return res

def _ms(v):
    v = [x for x in v if x is not None]; return {"mean": float(np.mean(v)), "std": float(np.std(v)), "n": len(v)} if v else None

def _agg_scores(runs, key):
    xs = [r[key] for r in runs if r.get(key)]
    if not xs: return None
    return {"accuracy": _ms([x["accuracy"] for x in xs]), "macro_f1": _ms([x["macro_f1"] for x in xs]),
            "per_class_f1": {c: _ms([x["per_class"][c]["f1"] for x in xs]) for c in LAB}, "confusion_sum": np.sum([x["confusion"] for x in xs], axis=0).tolist()}

def summarize_defense(res, d):
    base_keys = [k for k in res["baseline"][0] if res["baseline"][0][k]]
    S = {"unprotected": {k: _agg_scores(res["baseline"], k) for k in base_keys}, "budgets": {}}; f0 = [b["pooled"]["macro_f1"] for b in res["baseline"]]
    for b, arms in res["budgets"].items():
        S["budgets"][b] = {}
        for arm, runs in arms.items():
            keys = [k for k in runs[0] if k not in ("split", "arm", "cost", "fraction_changed", "fraction_baseline_kept", "strategy_mix")]; v = {k: _agg_scores(runs, k) for k in keys}
            fp = [r["adaptive_pooled"]["macro_f1"] for r in runs]; dl = [a - c for a, c in zip(f0, fp)]
            v["delta_macro_f1_abs"] = _ms(dl); v["delta_macro_f1_rel"] = _ms([(a - c) / a for a, c in zip(f0, fp)]); v["paired_ci95_source_bootstrap"] = res["paired_ci"][f"{b}|{arm}"]
            v["cost"] = {k: _ms([r["cost"][k] for r in runs]) for k in ("d_depth", "d_n2q", "d_active")}
            v["fraction_changed"] = _ms([r["fraction_changed"] for r in runs]); v["fraction_baseline_kept"] = _ms([r["fraction_baseline_kept"] for r in runs])
            mix = pd.DataFrame([r["strategy_mix"] for r in runs]).fillna(0).mean().to_dict(); v["strategy_mix"] = mix; S["budgets"][b][arm] = v
    return S

def write_defense_report(cfg, res, path=None):
    import csv, json
    S = res["summary"]; d = cfg["defense"]; rd = PB.out_dir(cfg, "results"); f = lambda x: "n/a" if not x else f"{x['mean']:.3f}±{x['std']:.3f}"
    g = lambda v, k: f(v[k]["macro_f1"]) if v.get(k) else "n/a"; U = S["unprotected"]
    L = ["# Defense evaluation on the paper-aligned benchmark", "",
         f"{res['n_sources']} source circuits at {d['n_qubits']} qubits, FakeNighthawk, optimization levels {d['opt_levels']}, {cfg['n_splits']} repeated source-disjoint splits "
         f"(3 train / {d['val_variants']} validation / {cfg['test_variants']} test variants per generator), mean±std over splits. Metric: macro-F1 on held-out circuits (lower = less intent recoverable; chance 0.143). "
         "Only candidates whose logical rewrite passed equivalence verification (QCEC / DAG identity / identical circuit) and the overhead budget were eligible.", "",
         f"**Unprotected** (paper-style RF, pooled test): {g(U, 'pooled')} (validation {g(U, 'pooled_val')}); per level: " + ", ".join(f"L{o} {g(U, f'L{o}')}" for o in d["opt_levels"]) +
         f"; GBoost {g(U, 'gboost_pooled')}, LogReg {g(U, 'logreg_pooled')}; metadata-only control {g(U, 'metadata_only')}.", "",
         "| budget | arm | static RF | adaptive RF | Δ abs | Δ rel | paired 95% CI of Δ | norm-aware RF | adaptive GBoost | adaptive LogReg | metadata-only | Δdepth | Δ2Q | rewritten |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    csvrows = []
    for b, arms in S["budgets"].items():
        for arm, v in arms.items():
            ci = v["paired_ci95_source_bootstrap"]
            L.append(f"| {float(b) * 100:.0f}% | {arm} | {g(v, 'static')} | {g(v, 'adaptive_pooled')} | {f(v['delta_macro_f1_abs'])} | {f(v['delta_macro_f1_rel'])} | [{ci[0]:+.3f}, {ci[1]:+.3f}] | {g(v, 'norm_aware_pooled')} | {g(v, 'adaptive_gboost')} | {g(v, 'adaptive_logreg')} | {g(v, 'metadata_only')} | "
                     f"{v['cost']['d_depth']['mean'] * 100:+.1f}% | {v['cost']['d_n2q']['mean'] * 100:+.1f}% | {v['fraction_changed']['mean'] * 100:.0f}% |")
            for k, x in v.items():
                if isinstance(x, dict) and "macro_f1" in x: csvrows.append(dict(budget=b, arm=arm, attacker=k, macro_f1_mean=x["macro_f1"]["mean"], macro_f1_std=x["macro_f1"]["std"], accuracy_mean=x["accuracy"]["mean"], accuracy_std=x["accuracy"]["std"]))
            csvrows.append(dict(budget=b, arm=arm, attacker="DELTA_adaptive_vs_unprotected_abs", macro_f1_mean=v["delta_macro_f1_abs"]["mean"], macro_f1_std=v["delta_macro_f1_abs"]["std"], ci_lo=ci[0], ci_hi=ci[1]))
    L += ["", "Δ = unprotected macro-F1 − adaptive macro-F1 on the same splits (positive = defense helped). The paired CI resamples source circuits and pairs each protected circuit with its own unprotected version.", "",
          "### Per-class F1 of the adaptive RF (pooled test)", "", "| budget | arm | " + " | ".join(LAB) + " |", "|---|---|" + "---|" * len(LAB)]
    L.append("| unprotected | - | " + " | ".join(f(U["pooled"]["per_class_f1"][c]) for c in LAB) + " |")
    for b, arms in S["budgets"].items():
        for arm, v in arms.items(): L.append(f"| {float(b) * 100:.0f}% | {arm} | " + " | ".join(f(v["adaptive_pooled"]["per_class_f1"][c]) for c in LAB) + " |")
    L += ["", "### Verification (all generated candidates)", "", f"Status: {res['stats']['verification']}; methods: {res['stats']['verification_methods']}", "", "By strategy:", ""]
    L += [f"- {k}: {v}" for k, v in res["stats"]["verification_by_strategy"].items()]
    fr = res["stats"]["verification_failure_reasons"]; L += ["", "Non-PASS reasons: " + (str(fr) if fr else "none (every candidate verified)"), "", "### Candidate rejections by budget (candidate x optimization level)", ""]
    L += [f"- budget {float(b) * 100:.0f}%: {v}" for b, v in res["stats"]["rejections_by_budget"].items()]
    L += ["", "### Share of verified rewrites that changed the attacker-visible Table II features", ""] + [f"- {k}: {v * 100:.0f}%" for k, v in sorted(res["stats"]["survival_by_strategy_opt"].items())]
    p = path or rd / "defense_summary.md"; p.write_text("\n".join(L) + "\n")
    with open(rd / "defense_summary.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["budget", "arm", "attacker", "macro_f1_mean", "macro_f1_std", "accuracy_mean", "accuracy_std", "ci_lo", "ci_hi"]); w.writeheader(); w.writerows(csvrows)
    return p
