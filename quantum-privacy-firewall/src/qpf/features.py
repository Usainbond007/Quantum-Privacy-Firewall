"""Observable-structure features of a physical circuit. Counts ALL 2-qubit operations (plan M2)."""
from collections import Counter, defaultdict
import numpy as np
FEATURE_VERSION = "v1"
FEATURE_NAMES = ["frac_2q", "frac_rz", "frac_sx", "frac_x", "mean_2q_per_layer", "burstiness",
                 "early_2q_mass", "mid_2q_mass", "late_2q_mass", "active_qubit_frac",
                 "qubit_load_gini", "edge_entropy", "max_edge_share"]
META_NAMES = ["logical_width", "depth", "size", "n2q"]   # trivial-complexity control features

def gini(x):
    x = np.sort(np.asarray(x, float))
    if len(x) == 0 or x.sum() == 0: return 0.0
    n = len(x); return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum()))

def analyze(tc):
    """-> (metrics dict, feature dict). One ASAP-scheduling pass over the physical circuit."""
    idx = {q: i for i, q in enumerate(tc.qubits)}; n = tc.num_qubits
    clock = np.zeros(n, int); per_layer = defaultdict(int); qload = np.zeros(n)
    eload = defaultdict(int); names = Counter(); touched = set(); total = n2q = 0
    for inst in tc.data:
        nm = inst.operation.name
        if nm in ("barrier", "delay"): continue
        qs = [idx[q] for q in inst.qubits]
        t = int(max(clock[qs])) + 1; clock[qs] = t
        total += 1; names[nm] += 1; touched.update(qs)
        if len(qs) == 2:
            n2q += 1; per_layer[t] += 1
            for q in qs: qload[q] += 1
            eload[tuple(sorted(qs))] += 1
    depth = int(clock.max()) if total else 0; active = len(touched)
    L = np.array([per_layer.get(t, 0) for t in range(1, depth + 1)], float)
    ev = np.array(list(eload.values()), float)
    thirds = [c.sum() for c in np.array_split(L, 3)] if len(L) else [0, 0, 0]
    p = ev / ev.sum() if ev.sum() else ev; pp = p[p > 0]
    d = max(1, total)
    f = {"frac_2q": n2q / d, "frac_rz": names["rz"] / d, "frac_sx": names["sx"] / d, "frac_x": names["x"] / d,
         "mean_2q_per_layer": float(L.mean() / max(1, active)) if len(L) else 0.0,
         "burstiness": float(L.std() / (L.mean() + 1e-9)) if len(L) else 0.0,
         "early_2q_mass": thirds[0] / max(1, n2q), "mid_2q_mass": thirds[1] / max(1, n2q),
         "late_2q_mass": thirds[2] / max(1, n2q), "active_qubit_frac": active / n,
         "qubit_load_gini": gini(qload[qload > 0]),
         "edge_entropy": float(-(pp * np.log(pp)).sum() / np.log(max(2, len(p)))) if len(pp) else 0.0,
         "max_edge_share": float(ev.max() / ev.sum()) if ev.sum() else 0.0}
    return {"depth": depth, "size": total, "n2q": n2q, "active": active}, f
