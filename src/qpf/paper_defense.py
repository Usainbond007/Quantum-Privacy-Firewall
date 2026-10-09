"""Defense evaluated ON TOP of the paper-aligned benchmark.

Question (the paper's Section V direction): can verified, semantics-preserving rewrites of the *source* circuit
lower the intent recoverability of the final transpiled circuit, at bounded depth / two-qubit / width overhead,
when the attacker is the paper's own Table II + Random Forest pipeline RETRAINED on protected circuits?

Arms compared on identical candidates:  guided (label-free frozen-surrogate selection)  vs  random eligible candidate.
Attackers: static (paper-style RF trained on unprotected), adaptive (retrained on protected train split),
normalization-aware (retrained, and re-optimises every observed circuit at optimization level 3 before featurizing)."""
import time, itertools, warnings
import numpy as np, pandas as pd
from concurrent.futures import ProcessPoolExecutor
from qiskit import transpile
from . import compilation, defenses, verification, selection, paper_circuits as PC, paper_benchmark as PB
from .artifact_integrity import provenance, require_matching_cache, write_json_atomic
from .metrics import summarize
warnings.filterwarnings("ignore")
FEAT = PB.FEAT; NFEAT = ["n_" + f for f in FEAT]

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
                tc, dt = compilation.compile_circuit(cand, o, tseed, layout, backend); r.update(PB.physical_row(tc, backend)); r["compile_s"] = dt
            rows.append(r)
        return rows
    except Exception as ex:
        return [dict(meta, opt=-1, verify_status="ERROR", verify_note=repr(ex)[:200])]

def _norm_job(job):
    """Normalization-aware attacker's view: re-optimise the observed physical circuit at level 3, then featurize."""
    cid, gen, var, n, strat, cseed, opt, tseed, backend = job
    try:
        base = PC.make_source(gen, n, var); cand, layout = defenses.apply_strategy(base, strat, cseed, backend) if strat != "baseline" else (base, None)
        tc, _ = compilation.compile_circuit(cand, opt, tseed, layout, backend)
        tn = transpile(tc, backend=compilation.get_backend(backend), optimization_level=3, seed_transpiler=0)
        r = PB.physical_row(tn, backend); return dict(cid=cid, opt=opt, **{"n_" + f: r[f] for f in FEAT})
    except Exception as ex:
        return dict(cid=cid, opt=opt, error=repr(ex)[:200])

def build_candidates(cfg, workers=2, log=print):
    d = cfg["defense"]; n = d["n_qubits"]; path = PB.out_dir(cfg, "defense") / "candidates.csv"
    jobs = []
    for gi, gen in enumerate(PC.GENERATORS):
        for v in range(cfg["variants"]):
            for k, st in enumerate(d["strategies"]): jobs.append((gen, v, n, st, (gi * 100 + v) * 1000 + k + 1, d["opt_levels"], cfg["transpile_seed"], cfg["backend"], d["qcec_timeout_s"]))
    manifest = path.with_suffix(".provenance.json")
    expected = provenance(cfg, [__file__, PC.__file__, defenses.__file__, verification.__file__, compilation.__file__], {"kind": "defense_candidates"})
    if path.exists():
        require_matching_cache(manifest, expected)
    else:
        write_json_atomic(manifest, expected)
    prev = pd.read_csv(path) if path.exists() else pd.DataFrame()
    if len(prev):
        required = {"cid", "opt", "verify_status"}
        if not required.issubset(prev.columns):
            raise ValueError("Candidate cache missing required columns")
        if prev.duplicated(["cid", "opt"]).any():
            raise ValueError("Candidate cache has duplicate candidate/opt keys")
    done = set()
    if len(prev):
        for cid, group in prev.groupby("cid"):
            if set(group.opt.astype(int)) == set(map(int, d["opt_levels"])):
                done.add(cid)
    todo = [j for j in jobs if f"{PC.source_id(j[0], j[1])}|{j[3]}|{j[4]}" not in done]
    log(f"[defense] {len(jobs)} candidate circuits x {len(d['opt_levels'])} opt levels; {len(todo)} to do (resume), workers={workers}")
    t0 = time.perf_counter(); rows = [prev] if len(prev) else []; buf = []
    with ProcessPoolExecutor(workers) as ex:
        for i, r in enumerate(ex.map(_cand_job, todo, chunksize=1)):
            buf += r
            if (i + 1) % 50 == 0 or i + 1 == len(todo):
                merged = pd.concat(rows + [pd.DataFrame(buf)], ignore_index=True).drop_duplicates(["cid", "opt"], keep="last")
                tmp = path.with_suffix(".partial.csv")
                merged.to_csv(tmp, index=False)
                tmp.replace(path)
                log(f"  {i + 1}/{len(todo)} ({time.perf_counter() - t0:.0f}s)")
    df = pd.read_csv(path); return df

def baseline_rows(cfg, ds):
    d = cfg["defense"]; b = ds[(ds.n_qubits == d["n_qubits"]) & (ds.opt.isin(d["opt_levels"])) & (ds.status == "OK")].copy()
    b["strategy"] = "baseline"; b["cand_seed"] = 0; b["cid"] = b.source_id + "|baseline|0"; b["verify_status"] = "PASS"; b["verify_method"] = "baseline"; return b

def _fit(tr, cols, cfg, seed):
    c = dict(cfg); c["rf_grid"] = cfg["defense"]["rf_grid"]; return PB.fit_attacker(tr, cols, c, seed)

def _acc(model, te, cols):
    te = te.dropna(subset=cols)
    if not len(te): return None
    return PB._score(model, te, cols)

def _select(cands, surrogates, rng, budget, mode):
    """Per (source, opt): choose a candidate among baseline + eligible ones. guided = least surrogate confidence; random = uniform."""
    c = cands.copy(); c["reason"] = c.apply(lambda r: selection.reject_reason(r, budget), axis=1); e = c[c.reason == ""].copy()
    conf = np.zeros(len(e))
    for o, sur in surrogates.items():
        m = (e.opt == o).to_numpy()
        if m.any(): conf[m] = sur.predict_proba(e.loc[m, FEAT].to_numpy(float)).max(axis=1)
    e["conf"] = conf
    if mode == "random": e["conf"] = rng.random(len(e))
    e = e.sort_values(["source_id", "opt", "conf", "cost", "cid"])
    return e.groupby(["source_id", "opt"], as_index=False).head(1).copy()

def evaluate_defense(cfg, ds, cands, log=print, workers=2):
    d = cfg["defense"]; base = baseline_rows(cfg, ds); allc = pd.concat([base, cands[cands.verify_status.notna()]], ignore_index=True)
    allc = selection.add_overheads(allc.rename(columns={"source_id": "base_id"}), base.rename(columns={"source_id": "base_id"})[["base_id", "opt", "depth", "n2q", "active"]]).rename(columns={"base_id": "source_id"})
    pas = allc[(allc.verify_status == "PASS") & allc.depth.notna()].copy()
    # survival: did the rewrite change the observable Table II features at all?
    bf = base.set_index(["source_id", "opt"])[FEAT]; c = pas[pas.strategy != "baseline"]
    diff = np.abs(c[FEAT].to_numpy(float) - bf.loc[list(zip(c.source_id, c.opt))].to_numpy(float)).max(axis=1); pas.loc[c.index, "changed"] = diff > 1e-9
    stats = {"verification": cands.drop_duplicates("cid").groupby("verify_status").size().to_dict(),
             "verification_methods": cands.drop_duplicates("cid").groupby("verify_method").size().to_dict(),
             "survival_by_strategy_opt": {f"{s}|L{o}": float(g.changed.mean()) for (s, o), g in pas[pas.strategy != "baseline"].groupby(["strategy", "opt"])}}
    # normalization-aware features for every candidate that could ever be selected (verified, within the largest budget)
    elig = pas[(pas.cost <= max(d["budgets"]) + 1e-12)]
    parse = lambda r: (r.cid, r.generator, int(r.variant), d["n_qubits"], r.strategy, int(r.cand_seed), int(r.opt), cfg["transpile_seed"], cfg["backend"])
    jobs = [parse(r) for r in elig.itertuples()]; npath = PB.out_dir(cfg, "defense") / "norm_features.csv"
    nmanifest = npath.with_suffix(".provenance.json")
    expected_norm = provenance(cfg, [__file__, compilation.__file__, defenses.__file__, (PB.ROOT / "src/qpf/paper_features.py")], {"kind": "normalized_features", "eligible_keys": sorted([f"{j[0]}|{j[6]}" for j in jobs])})
    if npath.exists():
        require_matching_cache(nmanifest, expected_norm)
        nd = pd.read_csv(npath)
        if nd.duplicated(["cid", "opt"]).any():
            raise ValueError("Normalization cache contains duplicate candidate/opt keys")
        if set(zip(nd.cid, nd.opt.astype(int))) != set((j[0], j[6]) for j in jobs):
            raise ValueError("Normalization cache keyset does not match current eligible candidates")
        log(f"[defense] reusing {len(nd)} cached normalization-aware features")
    else:
        log(f"[defense] normalization-aware features for {len(jobs)} circuits")
        with ProcessPoolExecutor(workers) as ex: nd = pd.DataFrame(list(ex.map(_norm_job, jobs, chunksize=4)))
        tmp = npath.with_suffix(".partial.csv")
        nd.to_csv(tmp, index=False)
        tmp.replace(npath)
        write_json_atomic(nmanifest, expected_norm)
    nd = nd.dropna(subset=NFEAT); pas = pas.merge(nd, on=["cid", "opt"], how="left")
    pas.to_csv(PB.out_dir(cfg, "defense") / "all_candidates_with_overheads.csv", index=False)
    res = {"stats": stats, "n_sources": int(pas.source_id.nunique()), "budgets": {}, "baseline": []}; R = {str(b): {"guided": [], "random": []} for b in d["budgets"]}
    for s in range(cfg["n_splits"]):
        part = PB.make_splits(cfg, s); pas["_p"] = pas.source_id.map(part)
        btr, bte = pas[(pas.strategy == "baseline") & (pas._p == "train")], pas[(pas.strategy == "baseline") & (pas._p == "test")]
        surr = {o: _fit(btr[btr.opt == o], FEAT, cfg, s).best_estimator_ for o in d["opt_levels"]}        # frozen, train split only
        stat = _fit(btr, FEAT, cfg, s)                                                                       # static attacker (paper-style)
        bm = {"pooled": _acc(stat, bte, FEAT)}
        for o in d["opt_levels"]: bm[f"L{o}"] = _acc(_fit(btr[btr.opt == o], FEAT, cfg, s), bte[bte.opt == o], FEAT)
        res["baseline"].append(bm); log(f"  split {s}: unprotected pooled F1 = {bm['pooled']['macro_f1']:.3f}")
        for b in d["budgets"]:
            for mode in ("guided", "random"):
                sel = _select(pas, surr, np.random.default_rng([cfg["seed"], s, int(b * 100)]), b, mode); sel["_p"] = sel.source_id.map(part)
                tr, te = sel[sel._p == "train"], sel[sel._p == "test"]; one = {"split": s, "arm": mode}
                one["static"] = _acc(stat, te, FEAT); one["adaptive_pooled"] = _acc(_fit(tr, FEAT, cfg, s), te, FEAT)
                for o in d["opt_levels"]: one[f"adaptive_L{o}"] = _acc(_fit(tr[tr.opt == o], FEAT, cfg, s), te[te.opt == o], FEAT)
                tn, en = tr.dropna(subset=NFEAT), te.dropna(subset=NFEAT)
                if len(tn) and len(en): one["norm_aware_pooled"] = _acc(PB.fit_attacker(tn, NFEAT, {**cfg, "rf_grid": d["rf_grid"]}, s), en, NFEAT)
                one["cost"] = {k: float(te[k].mean()) for k in ("d_depth", "d_n2q", "d_active")}
                one["fraction_changed"] = float(((te.strategy != "baseline") & te.changed.fillna(False).astype(bool)).mean())
                one["fraction_baseline_kept"] = float((te.strategy == "baseline").mean()); R[str(b)][mode].append(one)
    for b, arms in R.items(): res["budgets"][b] = arms
    res["summary"] = summarize_defense(res, d); return res

def _ms(v):
    v = [x for x in v if x is not None]
    return {"mean": float(np.mean(v)), "std": float(np.std(v)), "n": len(v)} if v else None

def summarize_defense(res, d):
    S = {"unprotected": {k: {m: _ms([b[k][m] for b in res["baseline"] if b.get(k)]) for m in ("accuracy", "macro_f1")} for k in res["baseline"][0]}, "budgets": {}}
    for b, arms in res["budgets"].items():
        S["budgets"][b] = {}
        for arm, runs in arms.items():
            keys = [k for k in runs[0] if k not in ("split", "arm", "cost", "fraction_changed", "fraction_baseline_kept")]
            S["budgets"][b][arm] = {k: {m: _ms([r[k][m] for r in runs if r.get(k)]) for m in ("accuracy", "macro_f1")} for k in keys}
            S["budgets"][b][arm]["cost"] = {k: _ms([r["cost"][k] for r in runs]) for k in ("d_depth", "d_n2q", "d_active")}
            S["budgets"][b][arm]["fraction_changed"] = _ms([r["fraction_changed"] for r in runs]); S["budgets"][b][arm]["fraction_baseline_kept"] = _ms([r["fraction_baseline_kept"] for r in runs])
    return S

def write_defense_report(cfg, res, path=None):
    S = res["summary"]; d = cfg["defense"]; f = lambda x: "n/a" if not x else f"{x['mean']:.3f}±{x['std']:.3f}"
    L = ["# Defense evaluation on the paper-aligned benchmark", "",
         f"{res['n_sources']} source circuits at {d['n_qubits']} qubits, FakeNighthawk, optimization levels {d['opt_levels']}, {cfg['n_splits']} repeated source-disjoint splits (mean±std). "
         "Macro-F1 of the attacker on held-out protected circuits; lower = less intent recoverable; chance = 0.143. "
         "Every protected candidate passed exact logical-equivalence checking (MQT QCEC) against its source circuit; UNKNOWN/FAIL candidates were excluded.", "",
         f"Unprotected, paper-style RF (pooled): **{f(S['unprotected']['pooled']['macro_f1'])}**; per level: " + ", ".join(f"L{o} {f(S['unprotected'][f'L{o}']['macro_f1'])}" for o in d["opt_levels"]), "",
         "| budget | arm | static RF | adaptive RF (pooled) | " + " | ".join(f"adaptive L{o}" for o in d["opt_levels"]) + " | norm-aware RF | Δdepth | Δ2Q | rewritten |", "|---|---|---|---|" + "---|" * len(d["opt_levels"]) + "---|---|---|---|"]
    for b, arms in S["budgets"].items():
        for arm, v in arms.items():
            L.append(f"| {float(b) * 100:.0f}% | {arm} | {f(v['static']['macro_f1'])} | {f(v['adaptive_pooled']['macro_f1'])} | " + " | ".join(f(v[f'adaptive_L{o}']['macro_f1']) for o in d["opt_levels"]) +
                     f" | {f(v.get('norm_aware_pooled', {}).get('macro_f1') if v.get('norm_aware_pooled') else None)} | {v['cost']['d_depth']['mean'] * 100:+.1f}% | {v['cost']['d_n2q']['mean'] * 100:+.1f}% | {v['fraction_changed']['mean'] * 100:.0f}% |")
    L += ["", "### Verification", "", f"{res['stats']['verification']} via {res['stats']['verification_methods']}", "",
          "### Fraction of verified rewrites that changed the attacker-visible Table II features", ""]
    L += [f"- {k}: {v * 100:.0f}%" for k, v in sorted(res["stats"]["survival_by_strategy_opt"].items())]
    p = path or PB.out_dir(cfg, "results") / "defense_summary.md"; p.write_text("\n".join(L) + "\n"); return p
