#!/usr/bin/env python
"""Terminal demo: attack an unprotected circuit, protect it with QPF, verify equivalence, attack again.

Usage:  python scripts/demo_attack.py [--generator qft_swaps] [--variant 5] [--budget 0.2]

Attacker here is a fixed Random Forest trained on the saved final dataset (chosen opt level, 24 qubits) with the
victim's source circuit EXCLUDED. It illustrates the pipeline; the measured evaluation (adaptive attackers, CIs)
is in artifacts/paper_full.
"""
import argparse
import os
import sys
import time
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from qpf import compilation, defenses, verification, paper_circuits as PC, paper_benchmark as PB


GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


ap = argparse.ArgumentParser()
ap.add_argument("--generator", default="qft_swaps")
ap.add_argument("--variant", type=int, default=5)
ap.add_argument("--budget", type=float, default=0.2)
ap.add_argument("--opt", type=int, default=3)
ap.add_argument("--n", type=int, default=24)
ap.add_argument("--out", default=str(ROOT / "artifacts" / "demo_attack"), help="directory for demo plots/tables")
ap.add_argument("--no-plots", action="store_true", help="skip PNG plot export")
a = ap.parse_args()

cfg = PB.load_cfg("full")
BE = cfg["backend"]
FEAT = PB.FEAT
LAB = {c: c.replace("_", " ") for c in PC.CLASS_LABELS}
out_dir = Path(a.out)
out_dir.mkdir(parents=True, exist_ok=True)


def hdr(t):
    print("\n" + "=" * 86 + f"\n {BOLD}{t}{RESET}\n" + "=" * 86)


def pct(x, digits=0):
    if pd.isna(x):
        return "-"
    return f"{x:.{digits}%}"


def signed_pct(x, digits=1):
    if pd.isna(x):
        return "-"
    return f"{x:+.{digits}%}"


def bar(x, width=24):
    x = 0.0 if pd.isna(x) else float(max(0, min(1, x)))
    n = int(round(x * width))
    return "█" * n + "░" * (width - n)


def print_table(df, columns=None, title=None):
    if title:
        print(f"\n{BOLD}{title}{RESET}")
    if columns:
        df = df[columns]
    print(df.to_string(index=False))


def predict(row, atk):
    p = atk.predict_proba(np.array([[row[f] for f in FEAT]], float))[0]
    order = np.argsort(-p)
    cl = atk.classes_
    return cl[order[0]], p[order[0]], dict(zip(cl, p))


def save_demo_plots(T, probs_before, probs_after, selected, conf_before):
    if a.no_plots:
        return []
    mpl_cache = out_dir / ".mplconfig"
    mpl_cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(mpl_cache))
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:
        print(f"\n(plot export skipped: matplotlib unavailable: {exc})")
        return []

    paths = []
    labels = [LAB.get(k, k) for k in probs_before]
    before = np.array([probs_before[k] for k in probs_before])
    after = np.array([probs_after.get(k, 0.0) for k in probs_before]) if probs_after else None

    fig, ax = plt.subplots(figsize=(11, 5))
    y = np.arange(len(labels))
    ax.barh(y + 0.18, before, height=0.34, label="unprotected", color="#ef4444")
    if after is not None:
        ax.barh(y - 0.18, after, height=0.34, label="protected", color="#14b8a6")
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 1)
    ax.set_xlabel("attacker confidence")
    ax.set_title("Intent prediction confidence before vs after QPF")
    ax.legend()
    ax.grid(axis="x", alpha=0.25)
    p = out_dir / "attack_confidence_before_after.png"
    fig.tight_layout()
    fig.savefig(p, dpi=180)
    plt.close(fig)
    paths.append(p)

    good = T[T.verify.str.startswith("PASS")].copy()
    if len(good):
        fig, ax = plt.subplots(figsize=(10, 5))
        colors = np.where(good.ok, "#22c55e", "#94a3b8")
        ax.scatter(good["d_depth"] * 100, good["conf"] * 100, c=colors, s=75, edgecolor="white", linewidth=0.8)
        ax.axvline(a.budget * 100, color="#f59e0b", linestyle="--", linewidth=1.5, label="depth budget")
        ax.axhline(conf_before * 100, color="#ef4444", linestyle=":", linewidth=1.5, label="unprotected confidence")
        if selected is not None:
            ax.scatter([selected.d_depth * 100], [selected.conf * 100], c="#0f172a", s=170, marker="*", label="selected")
        ax.set_xlabel("depth overhead (%)")
        ax.set_ylabel("confidence in original guess (%)")
        ax.set_title("Verified rewrite candidates: lower is better")
        ax.grid(alpha=0.25)
        ax.legend()
        p = out_dir / "candidate_confidence_vs_depth.png"
        fig.tight_layout()
        fig.savefig(p, dpi=180)
        plt.close(fig)
        paths.append(p)
    return paths


ds = pd.read_csv(ROOT / "artifacts" / "paper_full" / "features" / "dataset.csv")
ds = ds[(ds.status == "OK") & (ds.n_qubits == a.n) & (ds.opt == a.opt)]
gen = a.generator
if gen not in PC.GENERATORS:
    sys.exit(f"unknown generator. choose from: {sorted(PC.GENERATORS)}")
truth = PC.GENERATORS[gen]
sid = PC.source_id(gen, a.variant)

hdr("0. THE ATTACKER (trained WITHOUT ever seeing the victim's source circuit)")
tr = ds[ds.source_id != sid]
atk = make_pipeline(StandardScaler(), RandomForestClassifier(n_estimators=300, random_state=0, n_jobs=-1)).fit(
    tr[FEAT].to_numpy(float), tr.intent
)
attacker_summary = pd.DataFrame(
    [
        ["saved final paper dataset", f"{a.n} qubits, opt level {a.opt}"],
        ["training circuits", f"{len(tr)} compiled circuits"],
        ["training sources", f"{tr.source_id.nunique()} source circuits"],
        ["held-out victim source", sid],
        ["algorithm classes", f"{tr.intent.nunique()} classes"],
        ["features", "10 paper Table II physical-circuit features"],
    ],
    columns=["item", "value"],
)
print_table(attacker_summary)

hdr(f"1. THE VICTIM: '{gen}' ({a.n} qubits) - the developer's private workload")
base = PC.make_source(gen, a.n, a.variant)
tc0, _ = compilation.compile_circuit(base, a.opt, cfg["transpile_seed"], None, BE)
r0 = PB.physical_row(tc0, BE)
pred, conf, probs = predict(r0, atk)
top_before = pd.DataFrame(
    [
        {"rank": i + 1, "class": LAB.get(k, k), "confidence": pct(v), "bar": bar(v)}
        for i, (k, v) in enumerate(sorted(probs.items(), key=lambda kv: -kv[1])[:5])
    ]
)
victim_summary = pd.DataFrame(
    [
        ["secret true class", LAB.get(truth, truth)],
        ["cloud-visible object", "transpiled physical circuit"],
        ["compiled depth", r0["depth"]],
        ["two-qubit gates", r0["n2q"]],
        ["active qubits", r0["active"]],
        ["attacker prediction", LAB.get(pred, pred)],
        ["attacker confidence", pct(conf)],
        ["verdict", "INTENT LEAKED" if pred == truth else "attack missed"],
    ],
    columns=["metric", "value"],
)
print_table(victim_summary)
print_table(top_before, title="Top attacker confidences before QPF")

hdr(f"2. QPF DEFENSE: generate rewrites, VERIFY equivalence, enforce overhead budget <= {a.budget:.0%}")
rows = []
strategies = cfg["defense"]["strategies"]
t0 = time.perf_counter()
for si, st in enumerate(strategies):
    for k in range(3):
        cseed = 1000 * (si + 1) + k + 1
        cand, layout = defenses.apply_strategy(base, st, cseed, BE)
        v = verification.verify(base, cand, operator_max_qubits=10, qcec_timeout_s=cfg["defense"]["qcec_timeout_s"])
        if v.status != "PASS":
            rows.append(
                dict(
                    strategy=st,
                    seed=k,
                    verify=f"REJECT ({v.status})",
                    verify_method=v.method,
                    d_depth=np.nan,
                    d_2q=np.nan,
                    conf=np.nan,
                    pred=None,
                    ok=False,
                )
            )
            continue
        tc, _ = compilation.compile_circuit(
            cand,
            a.opt,
            cfg["transpile_seed"] if "seed" not in st.split("+") else int(cseed % 100000) + 1,
            layout,
            BE,
        )
        r = PB.physical_row(tc, BE)
        dd = r["depth"] / r0["depth"] - 1
        d2 = r["n2q"] / r0["n2q"] - 1
        p = atk.predict_proba(np.array([[r[f] for f in FEAT]], float))[0]
        pc = dict(zip(atk.classes_, p))
        rows.append(
            dict(
                strategy=st,
                seed=k,
                verify=f"PASS ({v.method})",
                verify_method=v.method,
                d_depth=dd,
                d_2q=d2,
                conf=pc[pred],
                pred=atk.classes_[int(np.argmax(p))],
                ok=max(dd, d2) <= a.budget,
            )
        )
T = pd.DataFrame(rows)
show = T.copy()
show["depth overhead"] = show.d_depth.map(signed_pct)
show["2Q overhead"] = show.d_2q.map(signed_pct)
show["confidence"] = show.conf.map(pct)
show["in budget"] = show.ok.map({True: f"{GREEN}yes{RESET}", False: f"{RED}NO{RESET}"})
show["prediction"] = show.pred.map(lambda x: LAB.get(x, x) if isinstance(x, str) else "-")
print_table(show, ["strategy", "seed", "verify", "depth overhead", "2Q overhead", "confidence", "prediction", "in budget"])

verified = int((T.verify.str.startswith("PASS")).sum())
rejected = int((~T.verify.str.startswith("PASS")).sum())
elapsed = time.perf_counter() - t0
summary = pd.DataFrame(
    [
        ["candidates generated", len(T)],
        ["verified equivalent", verified],
        ["verification rejected", rejected],
        ["inside budget", int((T.verify.str.startswith("PASS") & T.ok).sum())],
        ["generation + verification time", f"{elapsed:.1f}s"],
    ],
    columns=["metric", "value"],
)
print_table(summary, title="Candidate pool summary")
method_summary = (
    T[T.verify.str.startswith("PASS")]
    .groupby("verify_method")
    .size()
    .rename("count")
    .reset_index()
    .sort_values("count", ascending=False)
)
print_table(method_summary, title="Equivalence evidence")

hdr("3. SELECT (label-free: lowest attacker confidence in its own original guess, among verified candidates within budget)")
elig = T[T.verify.str.startswith("PASS") & T.ok]
selected = None
probs_after = {}
if elig.empty:
    print("no verified candidate fits the budget -> QPF returns the unprotected circuit (never trades correctness for privacy)")
else:
    b = elig.sort_values("conf").iloc[0]
    selected = b
    same = b["pred"] == truth
    chosen = pd.DataFrame(
        [
            ["selected strategy", b.strategy],
            ["selected seed", int(b.seed)],
            ["equivalence", b.verify],
            ["depth overhead", signed_pct(b.d_depth)],
            ["two-qubit overhead", signed_pct(b.d_2q)],
            ["original attacker confidence", pct(conf)],
            ["protected confidence in original guess", pct(b.conf)],
            ["absolute confidence drop", f"{(conf - b.conf) * 100:.1f} percentage points"],
            ["relative confidence drop", pct((conf - b.conf) / conf if conf else np.nan, 1)],
            ["protected prediction", LAB.get(b["pred"], b["pred"])],
            ["result", "attacker still identifies the algorithm" if same else "attacker FOOLED (this one static attacker)"],
        ],
        columns=["metric", "value"],
    )
    print_table(chosen)
    chosen_path = out_dir / "selected_candidate.csv"
    pd.DataFrame([b]).to_csv(chosen_path, index=False)

    # Reconstruct the selected row's full probability vector for plotting/reporting.
    best_mask = (T.index == b.name)
    best_row = T.loc[best_mask].iloc[0]
    for si, st in enumerate(strategies):
        for k in range(3):
            if st == best_row.strategy and k == int(best_row.seed):
                cseed = 1000 * (si + 1) + k + 1
                cand, layout = defenses.apply_strategy(base, st, cseed, BE)
                tc, _ = compilation.compile_circuit(
                    cand,
                    a.opt,
                    cfg["transpile_seed"] if "seed" not in st.split("+") else int(cseed % 100000) + 1,
                    layout,
                    BE,
                )
                r = PB.physical_row(tc, BE)
                _, _, probs_after = predict(r, atk)
                break
    if probs_after:
        after_df = pd.DataFrame(
            [
                {
                    "rank": i + 1,
                    "class": LAB.get(k, k),
                    "confidence": pct(v),
                    "bar": bar(v),
                }
                for i, (k, v) in enumerate(sorted(probs_after.items(), key=lambda kv: -kv[1])[:5])
            ]
        )
        print_table(after_df, title="Top attacker confidences after QPF")

plot_paths = save_demo_plots(T, probs, probs_after, selected, conf)
if plot_paths:
    print(f"\n{BOLD}Saved demo visuals{RESET}")
    for p in plot_paths:
        print(f" - {p}")

T_export = T.copy()
T_export.to_csv(out_dir / "candidate_table.csv", index=False)

hdr("HONEST NOTE")
print(
    "This is ONE victim and ONE fixed attacker. Across all 282 source circuits and an attacker RETRAINED on protected circuits,\n"
    "macro-F1 falls only 0.916 -> 0.865 at a 50% budget (artifacts/paper_full/results/defense_summary.md)."
)
