"""Paper-aligned intent-recovery benchmark (Buesser & Kurmus, QCE 2026) -- OUR independent implementation.

Stage 1  build_dataset : Table I sources -> FakeNighthawk transpile -> Table II features (+ sensitivity variant).
Stage 2  evaluate      : source-disjoint splits, RF + 5-fold CV grid search, Table-III/IV style transfer matrices,
                         plus controls (shuffled labels, metadata-only) and a stricter generator-disjoint split.
Paper numbers are never read here; see paper_compare.py for the separate side-by-side."""
import json, time, pathlib, itertools, warnings
import numpy as np, pandas as pd, yaml
from concurrent.futures import ProcessPoolExecutor
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV, GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from . import compilation, paper_circuits as PC
from .paper_features import extract_paper_features, PAPER_FEATURE_NAMES
from .metrics import summarize
warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[2]
FEAT = list(PAPER_FEATURE_NAMES); FEAT_USED = [f + "__used" for f in FEAT]
META = ["n_gates", "depth", "n2q", "n_qubits_logical"]            # unnormalised size/complexity control

def load_cfg(profile="quick"):
    d = yaml.safe_load(open(ROOT / "config" / "paper.yaml")); d.update(d.pop("profiles", {}).get(profile, {})); d["profile"] = profile; return d

def out_dir(cfg, sub):
    p = ROOT / "artifacts" / f"paper_{cfg['profile']}" / sub; p.mkdir(parents=True, exist_ok=True); return p

def jdump(o, path):
    def _j(x):
        if isinstance(x, (np.integer,)): return int(x)
        if isinstance(x, (np.floating,)): return float(x)
        if isinstance(x, np.ndarray): return x.tolist()
        raise TypeError(type(x))
    open(path, "w").write(json.dumps(o, indent=2, default=_j))

_EDGES = {}
def coupling_edges(name):
    if name not in _EDGES: _EDGES[name] = sorted({tuple(sorted(e)) for e in compilation.get_backend(name).coupling_map.get_edges()})
    return _EDGES[name]

# --------------------------------------------------------------------------- stage 1
def physical_row(tc, backend):
    e = coupling_edges(backend); f = extract_paper_features(tc, e); g = extract_paper_features(tc, e, gini_population="used")
    ops = [i for i in tc.data if i.operation.name not in ("barrier", "delay")]
    touched = {tc.find_bit(q).index for i in ops for q in i.qubits}
    r = dict(f); r.update({k + "__used": g[k] for k in FEAT})
    r.update(n_gates=len(ops), depth=tc.depth(), n2q=sum(1 for i in ops if len(i.qubits) == 2), active=len(touched)); return r

def _job(job):
    gen, var, n, opt, seed, backend = job
    base = dict(generator=gen, intent=PC.GENERATORS[gen], variant=var, source_id=PC.source_id(gen, var), n_qubits=n, opt=opt)
    try:
        qc = PC.make_source(gen, n, var); t = time.perf_counter()
        tc, _ = compilation.compile_circuit(qc, opt, seed, None, backend)
        r = physical_row(tc, backend); r.update(base, n_qubits_logical=n, logical_gates=qc.size(), compile_s=time.perf_counter() - t, status="OK"); return r
    except Exception as ex:
        return dict(base, status="ERROR", error=repr(ex)[:300])

def build_dataset(cfg, workers=2, log=print):
    jobs = [(g, v, n, o, cfg["transpile_seed"], cfg["backend"]) for n in cfg["sizes"] for v in range(cfg["variants"])
            for g in PC.GENERATORS for o in cfg["opt_levels"]]
    path = out_dir(cfg, "features") / "dataset.csv"; done = pd.read_csv(path) if path.exists() else pd.DataFrame()
    have = set(zip(done.generator, done.variant, done.n_qubits, done.opt)) if len(done) else set()
    todo = [j for j in jobs if (j[0], j[1], j[2], j[3]) not in have]
    log(f"[paper-dataset] {len(jobs)} transpiles total, {len(todo)} to do (resume), workers={workers}")
    t0 = time.perf_counter(); rows = [done] if len(done) else []; buf = []
    with ProcessPoolExecutor(workers) as ex:
        for i, r in enumerate(ex.map(_job, todo, chunksize=1)):
            buf.append(r)
            if (i + 1) % 25 == 0 or i + 1 == len(todo):
                part = pd.concat(rows + [pd.DataFrame(buf)], ignore_index=True); part.to_csv(path, index=False)
                log(f"  {i + 1}/{len(todo)}  ({time.perf_counter() - t0:.0f}s)")
    df = pd.read_csv(path); bad = df[df.status != "OK"]
    if len(bad): bad.to_csv(out_dir(cfg, "features") / "dataset_errors.csv", index=False)
    return df[df.status == "OK"].reset_index(drop=True)

# --------------------------------------------------------------------------- stage 2
def make_splits(cfg, seed, val_variants=0):
    """Source-disjoint split: per generator, `test_variants` of its variants are held out as test and `val_variants` as
    validation (all sizes / opt levels of one source stay together). val_variants=0 reproduces the paper-style train/test split."""
    rng = np.random.default_rng([cfg["seed"], seed]); part = {}
    for g in PC.GENERATORS:
        vs = list(rng.permutation(cfg["variants"]))
        for k, v in enumerate(vs):
            part[PC.source_id(g, int(v))] = "test" if k < cfg["test_variants"] else ("val" if k < cfg["test_variants"] + val_variants else "train")
    return part

def make_generator_splits(cfg, seed, hold=2):
    """Stricter: hold out whole generators (>= `hold` per class), so no generator appears in both partitions."""
    rng = np.random.default_rng([cfg["seed"], 99, seed]); test = set()
    for c, gs in PC.CLASSES.items(): test |= set(rng.choice(gs, hold, replace=False))
    return {PC.source_id(g, v): ("test" if g in test else "train") for g in PC.GENERATORS for v in range(cfg["variants"])}

def fit_attacker(tr, cols, cfg, seed=0, shuffle=False):
    """RF with 5-fold CV grid search on the training split only (folds grouped by source circuit); scaler fit on train."""
    y = tr.intent.to_numpy()
    if shuffle: y = np.random.default_rng(seed).permutation(y)
    grid = {"rf__" + k: v for k, v in cfg["rf_grid"].items()}
    pipe = make_pipeline(StandardScaler(), RandomForestClassifier(random_state=seed, n_jobs=1)); pipe.steps[-1] = ("rf", pipe.steps[-1][1])
    k = min(cfg["cv_folds"], tr.source_id.nunique())
    gs = GridSearchCV(pipe, grid, cv=GroupKFold(k), scoring="f1_macro", n_jobs=1)
    gs.fit(tr[cols].to_numpy(float), y, groups=tr.source_id.to_numpy()); return gs

def per_class(cm):
    cm = np.asarray(cm, float); tp = np.diag(cm); pr = tp / np.maximum(cm.sum(0), 1); rc = tp / np.maximum(cm.sum(1), 1)
    f1 = 2 * pr * rc / np.maximum(pr + rc, 1e-12)
    return {c: {"precision": float(pr[i]), "recall": float(rc[i]), "f1": float(f1[i]), "support": int(cm.sum(1)[i])} for i, c in enumerate(PC.CLASS_LABELS)}

def _score(model, te, cols):
    p = model.predict(te[cols].to_numpy(float)); s = summarize(te.intent.to_numpy(), p, PC.CLASS_LABELS)
    return {"accuracy": s["accuracy"], "macro_f1": s["macro_f1"], "n": int(len(te)), "confusion": s["confusion"], "per_class": per_class(s["confusion"])}

def _regimes(df, kind):
    if kind == "opt": return {f"L{o}": df[df.opt == o] for o in sorted(df.opt.unique())}
    r = {f"{n}q": df[df.n_qubits == n] for n in sorted(df.n_qubits.unique())}
    if len(r) > 1: r["24+48"] = df
    return r

def transfer_matrix(tr, te, kind, cols, cfg, seed):
    R_tr, R_te = _regimes(tr, kind), _regimes(te, kind); M = {}
    for a, t in R_tr.items():
        m = fit_attacker(t, cols, cfg, seed)
        for b, e in R_te.items(): M[f"{a}->{b}"] = _score(m, e, cols)
    return M

def evaluate(cfg, df, log=print, feat_cols=None, tag="main"):
    cols = feat_cols or FEAT; res = {"cfg": {k: cfg[k] for k in ("sizes", "opt_levels", "variants", "test_variants", "n_splits", "rf_grid", "cv_folds")},
                                     "features": cols, "n_rows": int(len(df)), "n_sources": int(df.source_id.nunique()), "splits": []}
    chance = 1 / len(PC.CLASS_LABELS); res["chance"] = chance
    pdir = out_dir(cfg, "results") / "partial"; pdir.mkdir(exist_ok=True)
    for s in range(cfg["n_splits"]):
        ck = pdir / f"{tag}_split{s}.json"                      # resume: a finished split is never recomputed
        if ck.exists():
            res["splits"].append(json.load(open(ck))); log(f"  [{tag}] split {s}: loaded checkpoint"); continue
        part = make_splits(cfg, s); df["_p"] = df.source_id.map(part); tr, te = df[df._p == "train"], df[df._p == "test"]
        assert set(tr.source_id).isdisjoint(set(te.source_id))
        t0 = time.perf_counter(); one = {"split": s, "n_train": len(tr), "n_test": len(te)}
        one["opt_transfer"] = transfer_matrix(tr, te, "opt", cols, cfg, s)
        one["size_transfer"] = transfer_matrix(tr, te, "size", cols, cfg, s) if tr.n_qubits.nunique() > 1 else {}
        full = fit_attacker(tr, cols, cfg, s); one["pooled"] = _score(full, te, cols); one["best_params"] = full.best_params_
        one["control_shuffled_labels"] = _score(fit_attacker(tr, cols, cfg, s, shuffle=True), te, cols)
        one["control_metadata_only"] = _score(fit_attacker(tr, META, cfg, s), te, META)
        res["splits"].append(one); log(f"  [{tag}] split {s}: pooled acc={one['pooled']['accuracy']:.3f} f1={one['pooled']['macro_f1']:.3f} ({time.perf_counter() - t0:.0f}s)")
        # stricter generator-disjoint check
        gp = make_generator_splits(cfg, s); df["_p"] = df.source_id.map(gp); gtr, gte = df[df._p == "train"], df[df._p == "test"]
        assert set(gtr.generator).isdisjoint(set(gte.generator))
        gm = fit_attacker(gtr, cols, cfg, s); one["generator_disjoint"] = {"pooled": _score(gm, gte, cols), "by_opt": {k: _score(gm, v, cols) for k, v in _regimes(gte, "opt").items()}}
        jdump(one, ck)
    df.drop(columns="_p", inplace=True, errors="ignore")
    res["summary"] = aggregate(res); return res

def aggregate(res):
    def agg(getter):
        v = [getter(s) for s in res["splits"]]; v = [x for x in v if x is not None]
        return {"mean": float(np.mean(v)), "std": float(np.std(v)), "n_splits": len(v)} if v else None
    out = {"opt_transfer": {}, "size_transfer": {}}
    for kind in ("opt_transfer", "size_transfer"):
        keys = res["splits"][0][kind].keys() if res["splits"][0][kind] else []
        for k in keys: out[kind][k] = {m: agg(lambda s, k=k, m=m: s[kind][k][m]) for m in ("accuracy", "macro_f1")}
    for name in ("pooled", "control_shuffled_labels", "control_metadata_only"):
        out[name] = {m: agg(lambda s, name=name, m=m: s[name][m]) for m in ("accuracy", "macro_f1")}
    out["generator_disjoint_pooled"] = {m: agg(lambda s, m=m: s["generator_disjoint"]["pooled"][m]) for m in ("accuracy", "macro_f1")}
    out["pooled_confusion_sum"] = np.sum([s["pooled"]["confusion"] for s in res["splits"]], axis=0).tolist()
    out["pooled_per_class"] = {c: {m: agg(lambda s, c=c, m=m: s["pooled"]["per_class"][c][m]) for m in ("precision", "recall", "f1")} for c in PC.CLASS_LABELS}
    out["generator_disjoint_per_class"] = {c: {"recall": agg(lambda s, c=c: s["generator_disjoint"]["pooled"]["per_class"][c]["recall"])} for c in PC.CLASS_LABELS}
    return out
