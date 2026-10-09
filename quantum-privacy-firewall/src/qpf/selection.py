"""Budgeted, label-free candidate selection (plan M4). Uses ONLY features + a frozen surrogate; never any label."""
import numpy as np, pandas as pd

TOL = 1e-12

def add_overheads(cands, baseline):
    b = baseline[["base_id", "opt", "depth", "n2q", "active"]].rename(columns={"depth": "b_depth", "n2q": "b_n2q", "active": "b_active"})
    d = cands.merge(b, on=["base_id", "opt"], how="left")
    for k in ("depth", "n2q", "active"): d["d_" + k] = d[k] / d["b_" + k].clip(lower=1) - 1
    d["cost"] = d[["d_depth", "d_n2q", "d_active"]].max(axis=1).clip(lower=0)
    return d

def reject_reason(row, budget):
    if row["strategy"] == "baseline": return ""
    if row["verify_status"] != "PASS": return f"verification {row['verify_status']}"
    if pd.isna(row.get("depth")): return "compile failed"
    over = [f"{k} +{row['d_' + k] * 100:.1f}%" for k in ("depth", "n2q", "active") if row["d_" + k] > budget + TOL]
    return ("over budget (" + ", ".join(over) + f" > {budget * 100:.0f}%)") if over else ""

def choose(cands, surrogate, feat_cols, budget):
    """Per (base_id, opt): among baseline + eligible candidates, pick the one the surrogate is LEAST confident about;
    tie-break by lower cost then id. Returns selected rows with n_eligible and a pareto flag."""
    c = cands.copy(); c["reason"] = c.apply(lambda r: reject_reason(r, budget), axis=1)
    e = c[c["reason"] == ""].copy()
    e["surrogate_conf"] = surrogate.predict_proba(e[feat_cols].to_numpy(float)).max(axis=1)
    e["n_eligible"] = e.groupby(["base_id", "opt"])["cid"].transform("count")
    e = e.sort_values(["base_id", "opt", "surrogate_conf", "cost", "cid"])
    sel = e.groupby(["base_id", "opt"], as_index=False).head(1).copy()
    pf = pd.Series(False, index=e.index)           # pareto-valid: not dominated in (surrogate_conf, cost)
    for _, g in e.groupby(["base_id", "opt"]):
        for r in g.itertuples():
            dom = ((g.surrogate_conf <= r.surrogate_conf) & (g.cost <= r.cost) &
                   ((g.surrogate_conf < r.surrogate_conf) | (g.cost < r.cost))).any()
            pf.loc[r.Index] = not dom
    sel["pareto_valid"] = pf.loc[sel.index]
    return sel, c
