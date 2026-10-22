#!/usr/bin/env python
"""Terminal demo: attack an unprotected circuit, protect it with QPF, verify equivalence, attack again."""
import argparse, sys, time, warnings
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "src")); warnings.filterwarnings("ignore")
import pandas as pd, numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from qpf import compilation, defenses, verification, paper_circuits as PC, paper_benchmark as PB

ap = argparse.ArgumentParser(); ap.add_argument("--generator", default="qft_swaps"); ap.add_argument("--variant", type=int, default=5)
ap.add_argument("--budget", type=float, default=0.2); ap.add_argument("--opt", type=int, default=3); ap.add_argument("--n", type=int, default=24)
a = ap.parse_args(); cfg = PB.load_cfg("full"); BE = cfg["backend"]; FEAT = PB.FEAT
LAB = {c: c.replace("_", " ") for c in PC.CLASS_LABELS}
def hdr(t): print("\n" + "=" * 78 + f"\n {t}\n" + "=" * 78)

ds = pd.read_csv(ROOT / "artifacts" / "paper_full" / "features" / "dataset.csv"); ds = ds[(ds.status == "OK") & (ds.n_qubits == a.n) & (ds.opt == a.opt)]
gen = a.generator
if gen not in PC.GENERATORS: sys.exit(f"unknown generator. choose from: {sorted(PC.GENERATORS)}")
truth = PC.GENERATORS[gen]; sid = PC.source_id(gen, a.variant)

hdr("0. THE ATTACKER (trained WITHOUT ever seeing the victim's source circuit)")
tr = ds[ds.source_id != sid]
atk = make_pipeline(StandardScaler(), RandomForestClassifier(n_estimators=300, random_state=0, n_jobs=-1)).fit(tr[FEAT].to_numpy(float), tr.intent)
print(f"trained on {len(tr)} compiled circuits from {tr.source_id.nunique()} source circuits, {tr.intent.nunique()} algorithm classes, features = 10 paper Table II features")
def predict(row):
    p = atk.predict_proba(np.array([[row[f] for f in FEAT]], float))[0]; order = np.argsort(-p); cl = atk.classes_
    return cl[order[0]], p[order[0]], dict(zip(cl, p))

hdr(f"1. THE VICTIM: '{gen}' ({a.n} qubits) - the developer's private workload")
base = PC.make_source(gen, a.n, a.variant); tc0, _ = compilation.compile_circuit(base, a.opt, cfg["transpile_seed"], None, BE)
r0 = PB.physical_row(tc0, BE); pred, conf, probs = predict(r0)
print(f"true class (secret)      : {LAB.get(truth, truth)}")
print(f"what the cloud backend sees: transpiled circuit, depth={r0['depth']}, two-qubit gates={r0['n2q']}, active qubits={r0['active']}")
print(f"\nATTACK on unprotected circuit -> predicted: {LAB.get(pred, pred)}   (confidence {conf:.0%})   {'*** INTENT LEAKED ***' if pred == truth else 'attack missed'}")
print("   confidence by class:", {LAB.get(k, k): f"{v:.0%}" for k, v in sorted(probs.items(), key=lambda kv: -kv[1])[:3]})

hdr(f"2. QPF DEFENSE: generate rewrites, VERIFY equivalence, enforce overhead budget <= {a.budget:.0%}")
rows = []; strategies = cfg["defense"]["strategies"]; t0 = time.perf_counter()
for si, st in enumerate(strategies):
    for k in range(3):
        cseed = 1000 * (si + 1) + k + 1
        cand, layout = defenses.apply_strategy(base, st, cseed, BE)
        v = verification.verify(base, cand, operator_max_qubits=10, qcec_timeout_s=cfg["defense"]["qcec_timeout_s"])
        if v.status != "PASS": rows.append(dict(strategy=st, seed=k, verify=f"REJECT ({v.status})", d_depth=np.nan, d_2q=np.nan, conf=np.nan, ok=False)); continue
        tc, _ = compilation.compile_circuit(cand, a.opt, cfg["transpile_seed"] if "seed" not in st.split("+") else int(cseed % 100000) + 1, layout, BE)
        r = PB.physical_row(tc, BE); dd = r["depth"] / r0["depth"] - 1; d2 = r["n2q"] / r0["n2q"] - 1
        p = atk.predict_proba(np.array([[r[f] for f in FEAT]], float))[0]; pc = dict(zip(atk.classes_, p))
        rows.append(dict(strategy=st, seed=k, verify=f"PASS ({v.method})", d_depth=dd, d_2q=d2, conf=pc[pred], pred=atk.classes_[int(np.argmax(p))], ok=max(dd, d2) <= a.budget))
T = pd.DataFrame(rows)
with pd.option_context("display.width", 200, "display.max_columns", 20):
    show = T.copy(); show["d_depth"] = show.d_depth.map(lambda x: f"{x:+.1%}" if x == x else "-"); show["d_2q"] = show.d_2q.map(lambda x: f"{x:+.1%}" if x == x else "-")
    show["conf"] = show.conf.map(lambda x: f"{x:.0%}" if x == x else "-"); show["in budget"] = show.ok.map({True: "yes", False: "NO"})
    print(show[["strategy", "seed", "verify", "d_depth", "d_2q", "conf", "in budget"]].to_string(index=False))
print(f"\n{len(T)} candidates generated in {time.perf_counter() - t0:.0f}s; {int((T.verify.str.startswith('PASS')).sum())} verified equivalent, {int((~T.verify.str.startswith('PASS')).sum())} rejected")

hdr("3. SELECT (label-free: lowest attacker confidence in its own original guess, among verified candidates within budget)")
elig = T[T.verify.str.startswith("PASS") & T.ok]
if elig.empty: print("no verified candidate fits the budget -> QPF returns the unprotected circuit (never trades correctness for privacy)")
else:
    b = elig.sort_values("conf").iloc[0]; same = b["pred"] == truth
    print(f"selected: {b.strategy} (seed {int(b.seed)}), depth {b.d_depth:+.1%}, two-qubit gates {b.d_2q:+.1%}, equivalence {b.verify}")
    print(f"\nATTACK on protected circuit  -> predicted: {LAB.get(b['pred'], b['pred'])}   (confidence in original guess: {conf:.0%} -> {b.conf:.0%})")
    print("   RESULT:", "attacker still identifies the algorithm" if same else "attacker FOOLED (this one static attacker)")
hdr("HONEST NOTE")
print("This is ONE victim and ONE fixed attacker. Across all 282 source circuits and an attacker RETRAINED on protected circuits,\n"
      "macro-F1 falls only 0.916 -> 0.865 at a 50% budget (artifacts/paper_full/results/defense_summary.md).")