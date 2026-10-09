"""End-to-end stages (plan M0-M5). Every number reported is computed here from saved artifacts."""
import json, sys, time, subprocess, platform, importlib.metadata as im
import numpy as np, pandas as pd, joblib
from concurrent.futures import ProcessPoolExecutor
from qiskit import transpile
from . import circuits, compilation, features as FT, verification, defenses, attacks, metrics, selection, report
from .circuits import FAMILIES, CONTROL
from .config import art, ROOT

LABELS = list(FAMILIES); FEAT = FT.FEATURE_NAMES; NFEAT = ["n_" + f for f in FEAT]
META = ["width", "depth", "size", "n2q"]      # logical width + physical complexity (trivial-confound control)

def log(*a): print(*a, flush=True)
def _j(o):
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.floating,)): return float(o)
    if isinstance(o, np.ndarray): return o.tolist()
    raise TypeError(type(o))
def jdump(obj, path): open(path, "w").write(json.dumps(obj, indent=2, default=_j))
def jload(path): return json.load(open(path))

# ---------------------------------------------------------------- M0 environment
def environment_snapshot(cfg):
    pk = ["qiskit", "qiskit-ibm-runtime", "scikit-learn", "numpy", "pandas", "networkx", "mqt.qcec", "pyyaml"]
    ver = {}
    for p in pk:
        try: ver[p] = im.version(p)
        except Exception: ver[p] = None
    try: commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL).decode().strip()
    except Exception: commit = None
    snap = {"python": platform.python_version(), "packages": ver, "git_commit": commit, "profile": cfg["profile"],
            "seeds": {"dataset": cfg["dataset"]["seed"], "transpile": cfg["backend"]["transpile_seed"],
                      "attacker": cfg["experiment"]["attacker"]["seed"]},
            "backend": compilation.backend_info(cfg["backend"]["name"]), "feature_version": FT.FEATURE_VERSION,
            "config": {k: cfg[k] for k in ("dataset", "backend", "experiment", "budgets")}}
    jdump(snap, art(cfg, "manifests") / "environment.json"); return snap

# ---------------------------------------------------------------- M1 dataset
def assign_splits(man, frac, seed):
    rng = np.random.default_rng(seed); out = {}
    for _, g in man.groupby("family", sort=True):
        ids = sorted(g.base_id); rng.shuffle(ids); n = len(ids)
        nv, nt = max(1, round(n * frac["val"])), max(1, round(n * frac["test"]))
        for i, b in enumerate(ids): out[b] = "train" if i < n - nv - nt else ("val" if i < n - nt else "test")
    return pd.Series(out)

def build_manifest(cfg):
    d = cfg["dataset"]; rows = []; k = 0
    for fam in list(d["families"]) + [d["control_family"]]:
        for w in d["widths"]:
            for i in range(d["bases_per_cell"]):
                k += 1
                rows.append(dict(base_id=f"{fam}-w{w}-{i:03d}", family=fam, width=int(w), gen_seed=int(d["seed"]) * 100000 + k))
    man = pd.DataFrame(rows); man["split"] = man.base_id.map(assign_splits(man, d["split"], d["seed"]))
    check_disjoint(man)
    p = art(cfg, "manifests"); man.to_csv(p / "dataset.csv", index=False)
    jdump({"test_base_ids": sorted(man[man.split == "test"].base_id)}, p / "frozen_test_ids.json")
    return man

def check_disjoint(df):
    assert df.groupby("base_id")["split"].nunique().max() == 1, "a base_id occurs in more than one partition"

def load_manifest(cfg): return pd.read_csv(art(cfg, "manifests") / "dataset.csv")

# ---------------------------------------------------------------- jobs
def run_job(job):
    meta = dict(base_id=job["base_id"], family=job["family"], width=job["width"], strategy=job["strategy"],
                cand_seed=job["cand_seed"], tseed=job["tseed"], cid=f"{job['base_id']}|{job['strategy']}|{job['cand_seed']}")
    try:
        base = circuits.make_circuit(job["family"], job["width"], job["gen_seed"])
        if job["strategy"] == "baseline": cand, layout = base, None
        else: cand, layout = defenses.apply_strategy(base, job["strategy"], job["cand_seed"])
        t0 = time.perf_counter(); v = verification.verify(base, cand, **job["ver"]); vt = time.perf_counter() - t0
        rows = []
        for opt in job["opts"]:
            r = dict(meta, opt=opt, verify_status=v.status, verify_method=v.method, verify_note=v.note, verify_time_s=vt)
            if v.status == "PASS":
                tc, dt = compilation.compile_circuit(cand, opt, job["tseed"], layout, job["backend"])
                m, f = FT.analyze(tc); r.update(m); r.update(f); r["compile_time_s"] = dt
                if job.get("normalize"):   # normalization-aware attacker re-optimises what it observes
                    tn = transpile(tc, backend=compilation.get_backend(job["backend"]), optimization_level=3, seed_transpiler=0)
                    mn, fn = FT.analyze(tn); r.update({"n_" + k: x for k, x in fn.items()})
            rows.append(r)
        return rows
    except Exception as e:
        return [dict(meta, opt=-1, verify_status="ERROR", error=repr(e)[:300])]

def run_jobs(jobs, workers, label):
    t0 = time.perf_counter(); out = []; step = max(1, len(jobs) // 10)
    if workers > 1:
        with ProcessPoolExecutor(workers) as ex: it = ex.map(run_job, jobs, chunksize=2)
        res = list(it)
    else: res = None
    for i, j in enumerate(jobs):
        out += res[i] if res else run_job(j)
        if (i + 1) % step == 0 or i + 1 == len(jobs): log(f"  [{label}] {i + 1}/{len(jobs)} jobs  ({time.perf_counter() - t0:.0f}s)")
    return pd.DataFrame(out)

def _job(cfg, b, strategy, cand_seed, opts, normalize=False):
    return dict(base_id=b.base_id, family=b.family, width=int(b.width), gen_seed=int(b.gen_seed), strategy=strategy,
                cand_seed=int(cand_seed), tseed=cfg["backend"]["transpile_seed"], opts=list(opts), backend=cfg["backend"]["name"],
                ver=cfg["budgets"]["verification"] and dict(operator_max_qubits=cfg["budgets"]["verification"]["operator_max_qubits"],
                                                            qcec_timeout_s=cfg["budgets"]["verification"]["qcec_timeout_s"]), normalize=normalize)

def _failures(cfg, df, stage):
    bad = df[df.verify_status.isin(["ERROR", "FAIL", "UNKNOWN"])]
    with open(art(cfg, "") / "failure_log.jsonl", "a") as f:
        for r in bad.to_dict("records"): f.write(json.dumps(dict(stage=stage, **r), default=_j) + "\n")
    return len(bad)

# ---------------------------------------------------------------- M2 baseline
def _fit_eval(name, tr, te, cols, cfg, shuffle=False, seed=0):
    ex = cfg["experiment"]["attacker"]; ytr = tr.family.to_numpy()
    if shuffle: ytr = np.random.default_rng(seed).permutation(ytr)
    m, pred, proba = attacks.fit_predict(name, tr[cols].to_numpy(float), ytr, te[cols].to_numpy(float), ex["seed"], ex["rf_trees"])
    return m, pred, proba

def _pred_df(te, pred, attacker, **extra):
    d = pd.DataFrame({"base_id": te.base_id.to_numpy(), "opt": te.opt.to_numpy(), "y_true": te.family.to_numpy(), "y_pred": pred, "attacker": attacker})
    for k, v in extra.items(): d[k] = v
    return d

def train_baseline(cfg):
    man = load_manifest(cfg); workers = cfg["experiment"]["workers"]
    jobs = [_job(cfg, b, "baseline", 0, cfg["backend"]["opt_levels"]) for b in man.itertuples()]
    log(f"[baseline] compiling {len(jobs)} base circuits x {len(cfg['backend']['opt_levels'])} opt levels")
    df = run_jobs(jobs, workers, "baseline"); _failures(cfg, df, "baseline")
    df = df.merge(man[["base_id", "split"]], on="base_id"); check_disjoint(df)
    df.to_csv(art(cfg, "features") / "baseline.csv", index=False)
    lab = LABELS; chance = 1 / len(lab); df = df.dropna(subset=FEAT); fam = df[df.family.isin(lab)]
    tr, va, te = (fam[fam.split == s] for s in ("train", "val", "test"))
    rf, pred_te, _ = _fit_eval("rf", tr, te, FEAT, cfg); _, pred_va, _ = _fit_eval("rf", tr, va, FEAT, cfg)
    _, pred_sh, _ = _fit_eval("rf", tr, te, FEAT, cfg, shuffle=True, seed=1)
    _, pred_me, _ = _fit_eval("rf", tr, te, META, cfg)
    joblib.dump(rf, art(cfg, "models") / "baseline_rf.joblib")
    P = pd.concat([_pred_df(te, pred_te, "rf_full", split="test"), _pred_df(va, pred_va, "rf_full", split="val"),
                   _pred_df(te, pred_sh, "rf_shuffled_labels", split="test"), _pred_df(te, pred_me, "rf_metadata_only", split="test")])
    ctl = df[df.family == CONTROL]; cp = rf.predict(ctl[FEAT].to_numpy(float))
    P = pd.concat([P, _pred_df(ctl, cp, "rf_full_on_random_control", split="all")])
    P.to_csv(art(cfg, "predictions") / "baseline_predictions.csv", index=False)
    S = lambda p: metrics.summarize(te.family.to_numpy(), p, lab)
    full, shuf, meta = S(pred_te), S(pred_sh), S(pred_me)
    ci = metrics.bootstrap_ci(P[(P.attacker == "rf_full") & (P.split == "test")], lab, cfg["experiment"]["bootstrap"])
    # transfer (disjoint logical circuits: train-split bases -> test-split bases)
    opts, widths = sorted(fam.opt.unique()), sorted(fam.width.unique()); xfer = {"opt": {}, "size": {}}
    for a in opts:
        for b in opts:
            t, e = tr[tr.opt == a], te[te.opt == b]
            xfer["opt"][f"train{a}->test{b}"] = metrics.summarize(e.family.to_numpy(), _fit_eval("rf", t, e, FEAT, cfg)[1], lab)["macro_f1"]
    for a in widths:
        for b in widths:
            t, e = tr[tr.width == a], te[te.width == b]
            if len(t) and len(e): xfer["size"][f"train_w{a}->test_w{b}"] = metrics.summarize(e.family.to_numpy(), _fit_eval("rf", t, e, FEAT, cfg)[1], lab)["macro_f1"]
    reps = []
    for r in range(cfg["experiment"]["repeats"]):
        sp = fam.base_id.map(assign_splits(man, cfg["dataset"]["split"], 1000 + r)); a, b = fam[sp == "train"], fam[sp == "test"]
        f = lambda cols, sh=False: metrics.summarize(b.family.to_numpy(), _fit_eval("rf", a, b, cols, cfg, sh, r)[1], lab)["macro_f1"]
        reps.append({"full": f(FEAT), "metadata_only": f(META), "shuffled": f(FEAT, True)})
    R = pd.DataFrame(reps)
    gate_pass = full["macro_f1"] > max(chance, shuf["macro_f1"]) + cfg["experiment"]["gate_margin"]
    confound = bool(meta["macro_f1"] >= full["macro_f1"] - 0.02 or R["metadata_only"].mean() >= R["full"].mean() - 0.02)
    res = {"chance": chance, "full": full, "shuffled": shuf, "metadata_only": meta, "full_macro_f1_ci95": ci,
           "transfer": xfer, "repeated_grouped": {k: {"mean": R[k].mean(), "std": R[k].std(ddof=0), "values": R[k].tolist()} for k in R},
           "random_control_predictions": pd.Series(cp).value_counts().to_dict(),
           "n_rows": {"train": len(tr), "val": len(va), "test": len(te)}, "class_support_test": full["support"],
           "surrogate_train_base_ids": sorted(tr.base_id.unique()),
           "exit_gate": {"passed": bool(gate_pass), "metadata_confound_warning": confound,
                         "rule": f"full macro-F1 > max(chance, shuffled) + {cfg['experiment']['gate_margin']}; confound warning if metadata-only is within 0.02 of full (frozen split or repeated-split mean)"}}
    jdump(res, art(cfg, "results") / "baseline.json")
    report.confusion(full["confusion"], lab, "Baseline attacker (RF) - frozen test split", art(cfg, "figures") / "confusion_baseline.png")
    return res

# ---------------------------------------------------------------- M3/M4 defense
def run_defense(cfg):
    man = load_manifest(cfg); ex = cfg["experiment"]; workers = ex["workers"]
    bl = pd.read_csv(art(cfg, "features") / "baseline.csv"); rf = joblib.load(art(cfg, "models") / "baseline_rf.joblib")
    jobs = []
    for b in man.itertuples():
        for k in range(ex["n_candidates"]):
            jobs.append(_job(cfg, b, ex["strategies"][k % len(ex["strategies"])], b.gen_seed * 1000 + k + 1, cfg["backend"]["opt_levels"]))
    log(f"[defense] generating+verifying+compiling {len(jobs)} candidate circuits (x{len(cfg['backend']['opt_levels'])} opt levels)")
    cd = run_jobs(jobs, workers, "candidates"); nbad = _failures(cfg, cd, "candidates")
    cd = cd.merge(man[["base_id", "split"]], on="base_id")
    allc = pd.concat([bl, cd], ignore_index=True)
    bl_only = bl.dropna(subset=["depth"])
    allc = selection.add_overheads(allc, bl_only)
    # survival: did the transformation change the observable features vs the baseline circuit?
    b = bl_only.set_index(["base_id", "opt"])[FEAT]
    c = allc[(allc.strategy != "baseline") & (allc.verify_status == "PASS")].dropna(subset=["depth"])
    diff = np.abs(c[FEAT].to_numpy(float) - b.loc[list(zip(c.base_id, c.opt))].to_numpy(float)).max(axis=1)
    c = c.assign(changed=diff > 1e-9); surv = c.groupby("strategy")["changed"].agg(["mean", "count"]).to_dict("index")
    stats = {"n_candidate_circuits": len(jobs), "verification_counts": cd.groupby("verify_status").size().to_dict(),
             "verification_method_counts": cd.groupby("verify_method").size().to_dict(),
             "survival_rate_by_strategy": surv, "n_failures_logged": nbad}
    allc.to_csv(art(cfg, "features") / "candidates.csv", index=False)
    sel_rows = {}
    for bud in cfg["budgets"]["budgets"]:
        sel, annotated = selection.choose(allc, rf, FEAT, bud)
        sel.to_csv(art(cfg, "features") / f"selected_b{bud}.csv", index=False); sel_rows[bud] = sel
        stats.setdefault("rejections", {})[str(bud)] = annotated[annotated.reason != ""].reason.str.replace(r"[\d.]+%", "X%", regex=True).value_counts().head(8).to_dict()
        stats.setdefault("selection", {})[str(bud)] = {"groups": len(sel), "non_baseline_selected": int((sel.strategy != "baseline").sum()),
                                                        "all_selected_verified_PASS": bool((sel.verify_status == "PASS").all())}
    # normalization-aware attacker features for selected protected circuits
    need = pd.concat(sel_rows.values())[["base_id", "strategy", "cand_seed", "opt"]].drop_duplicates()
    mi = man.set_index("base_id"); njobs = []
    for (bid, st, cs), g in need.groupby(["base_id", "strategy", "cand_seed"]):
        r = mi.loc[bid]; bb = type("B", (), dict(base_id=bid, family=r.family, width=r.width, gen_seed=r.gen_seed))
        njobs.append(_job(cfg, bb, st, cs, sorted(g.opt), normalize=True))
    log(f"[defense] normalization-aware features for {len(njobs)} selected circuits")
    nd = run_jobs(njobs, workers, "normalize"); nd.to_csv(art(cfg, "features") / "selected_norm.csv", index=False)
    jdump(stats, art(cfg, "results") / "defense.json"); return stats

# ---------------------------------------------------------------- M5 adaptive evaluation
def evaluate_adaptive(cfg):
    man = load_manifest(cfg); ex = cfg["experiment"]; lab = LABELS
    bl = pd.read_csv(art(cfg, "features") / "baseline.csv").dropna(subset=["depth"]); rf0 = joblib.load(art(cfg, "models") / "baseline_rf.joblib")
    base_res = jload(art(cfg, "results") / "baseline.json"); cand = pd.read_csv(art(cfg, "features") / "candidates.csv")
    nrm = pd.read_csv(art(cfg, "features") / "selected_norm.csv"); key = ["base_id", "strategy", "cand_seed", "opt"]
    nrm = nrm[key + NFEAT].dropna()
    blf = bl[bl.family.isin(lab)]; bte = blf[blf.split == "test"]
    out = {"baseline_test_macro_f1": base_res["full"]["macro_f1"], "chance": base_res["chance"], "budgets": {}}; allp = []
    ngroups = cand.groupby(["base_id", "opt"]).ngroups
    search_time = cand[cand.strategy != "baseline"].groupby(["base_id", "opt"]).apply(lambda g: g.compile_time_s.sum() + g.verify_time_s.sum()).mean()
    for bud in cfg["budgets"]["budgets"]:
        sel = pd.read_csv(art(cfg, "features") / f"selected_b{bud}.csv").merge(nrm, on=key, how="left")
        P = sel[sel.family.isin(lab)]; tr, te = P[P.split == "train"], P[P.split == "test"]
        R = {}
        p_static = rf0.predict(te[FEAT].to_numpy(float)); allp.append(_pred_df(te, p_static, "static_baseline_rf", budget=bud))
        R["static_baseline_rf"] = metrics.summarize(te.family.to_numpy(), p_static, lab)
        for name in ("rf", "logreg", "gboost"):
            _, p, _ = _fit_eval(name, tr, te, FEAT, cfg); allp.append(_pred_df(te, p, f"adaptive_{name}", budget=bud))
            R[f"adaptive_{name}"] = metrics.summarize(te.family.to_numpy(), p, lab)
        tn, en = tr.dropna(subset=NFEAT), te.dropna(subset=NFEAT)
        if len(tn) and len(en):
            m, p, _ = attacks.fit_predict("rf", tn[NFEAT].to_numpy(float), tn.family.to_numpy(), en[NFEAT].to_numpy(float), ex["attacker"]["seed"], ex["attacker"]["rf_trees"])
            allp.append(_pred_df(en, p, "adaptive_rf_normalization_aware", budget=bud))
            R["adaptive_rf_normalization_aware"] = metrics.summarize(en.family.to_numpy(), p, lab)
        ap = pd.concat(allp); ap = ap[(ap.budget == bud) & (ap.attacker == "adaptive_rf")]
        ci = metrics.bootstrap_ci(ap, lab, ex["bootstrap"]); diffs = []
        for r in range(ex["repeats"]):   # paired baseline vs protected on the SAME repeated grouped splits
            sp = assign_splits(man, cfg["dataset"]["split"], 1000 + r)
            a, b = blf[blf.base_id.map(sp) == "train"], blf[blf.base_id.map(sp) == "test"]
            pa, pb = P[P.base_id.map(sp) == "train"], P[P.base_id.map(sp) == "test"]
            fb = metrics.summarize(b.family.to_numpy(), _fit_eval("rf", a, b, FEAT, cfg, seed=r)[1], lab)["macro_f1"]
            fp = metrics.summarize(pb.family.to_numpy(), _fit_eval("rf", pa, pb, FEAT, cfg, seed=r)[1], lab)["macro_f1"]
            diffs.append({"baseline": fb, "protected_adaptive": fp, "delta": fb - fp})
        D = pd.DataFrame(diffs); fb0, fp0 = out["baseline_test_macro_f1"], R["adaptive_rf"]["macro_f1"]
        out["budgets"][str(bud)] = {"attackers": R, "adaptive_rf_macro_f1_ci95": ci, "relative_reduction_descriptive": metrics.relative_reduction(fb0, fp0),
            "paired_repeated_grouped": {"baseline_mean": D.baseline.mean(), "protected_mean": D.protected_adaptive.mean(), "delta_mean": D.delta.mean(), "delta_std": D.delta.std(ddof=0), "rows": diffs},
            "cost_mean_rel_change_vs_baseline": {"depth": sel.d_depth.mean(), "n2q": sel.d_n2q.mean(), "active_qubits": sel.d_active.mean()},
            "fraction_protected_non_baseline": float((sel.strategy != "baseline").mean()), "candidate_search_time_s_per_circuit": float(search_time)}
        report.confusion(R["adaptive_rf"]["confusion"], lab, f"Adaptive RF on protected test (budget {bud * 100:.0f}%)", art(cfg, "figures") / f"confusion_adaptive_b{bud}.png")
    pd.concat(allp).to_csv(art(cfg, "predictions") / "adaptive_predictions.csv", index=False)
    report.frontier(out, art(cfg, "figures") / "privacy_cost_frontier.png")
    jdump(out, art(cfg, "results") / "adaptive.json"); return out

# ---------------------------------------------------------------- release gate
def release_gate(cfg):
    g = {}; man = load_manifest(cfg)
    try: check_disjoint(man); [check_disjoint(pd.read_csv(art(cfg, "features") / f)) for f in ("baseline.csv", "candidates.csv")]; g["split_disjoint"] = True
    except AssertionError: g["split_disjoint"] = False
    sels = [pd.read_csv(art(cfg, "features") / f"selected_b{b}.csv") for b in cfg["budgets"]["budgets"]]
    g["all_selected_verified"] = all((s.verify_status == "PASS").all() for s in sels)
    base = jload(art(cfg, "results") / "baseline.json"); tr_ids = set(man[man.split == "train"].base_id)
    g["surrogate_trained_on_train_only"] = set(base["surrogate_train_base_ids"]) <= tr_ids
    P = pd.read_csv(art(cfg, "predictions") / "baseline_predictions.csv"); q = P[(P.attacker == "rf_full") & (P.split == "test")]
    g["baseline_numbers_trace_to_predictions"] = abs(metrics.summarize(q.y_true, q.y_pred, LABELS)["macro_f1"] - base["full"]["macro_f1"]) < 1e-9
    A = pd.read_csv(art(cfg, "predictions") / "adaptive_predictions.csv"); ad = jload(art(cfg, "results") / "adaptive.json"); ok = True
    for b, v in ad["budgets"].items():
        q = A[(A.budget == float(b)) & (A.attacker == "adaptive_rf")]
        ok &= abs(metrics.summarize(q.y_true, q.y_pred, LABELS)["macro_f1"] - v["attackers"]["adaptive_rf"]["macro_f1"]) < 1e-9
    g["adaptive_numbers_trace_to_predictions"] = bool(ok)
    g["no_nan_features_in_selected"] = all(not s[FEAT].isna().any().any() for s in sels)
    jdump(g, art(cfg, "results") / "release_gate.json"); return g

def summary_text(cfg):
    b = jload(art(cfg, "results") / "baseline.json"); a = jload(art(cfg, "results") / "adaptive.json"); L = []
    L.append(f"BASELINE (frozen test split, K={len(LABELS)} classes, chance={b['chance']:.2f})")
    L.append(f"  full-feature RF macro-F1 = {b['full']['macro_f1']:.3f}  CI95 {b['full_macro_f1_ci95'][0]:.3f}-{b['full_macro_f1_ci95'][1]:.3f}")
    L.append(f"  shuffled-label control  = {b['shuffled']['macro_f1']:.3f}   metadata-only control = {b['metadata_only']['macro_f1']:.3f}")
    L.append(f"  exit gate passed = {b['exit_gate']['passed']}   metadata confound warning = {b['exit_gate']['metadata_confound_warning']}")
    L.append("PROTECTED (adaptive attackers retrained on protected training groups; frozen test split)")
    L.append("  budget | adaptive RF | logreg | gboost | norm-aware | d.depth | d.2Q | protected%")
    for k, v in a["budgets"].items():
        R = v["attackers"]; g = lambda n: f"{R[n]['macro_f1']:.3f}" if n in R else "  n/a"
        L.append(f"  {float(k) * 100:5.0f}% | {g('adaptive_rf'):>11} | {g('adaptive_logreg'):>6} | {g('adaptive_gboost'):>6} | {g('adaptive_rf_normalization_aware'):>10} | "
                 f"{v['cost_mean_rel_change_vs_baseline']['depth'] * 100:8.1f}% | {v['cost_mean_rel_change_vs_baseline']['n2q'] * 100:5.1f}% | {v['fraction_protected_non_baseline'] * 100:6.0f}%")
    return "\n".join(L)
