import numpy as np
from sklearn.metrics import f1_score, balanced_accuracy_score, accuracy_score, confusion_matrix

def summarize(y_true, y_pred, labels):
    return {"macro_f1": float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)),
            "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "confusion": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
            "support": {l: int((np.asarray(y_true) == l).sum()) for l in labels}, "labels": list(labels)}

def bootstrap_ci(df, labels, n=1000, seed=0, group="base_id"):
    """95% percentile CI of macro-F1, resampling whole base circuits (groups)."""
    rng = np.random.default_rng(seed); g = {k: v for k, v in df.groupby(group)}; keys = list(g); out = []
    for _ in range(n):
        s = [g[keys[i]] for i in rng.integers(0, len(keys), len(keys))]
        d = np.concatenate([x[["y_true", "y_pred"]].to_numpy() for x in s])
        out.append(f1_score(d[:, 0], d[:, 1], labels=labels, average="macro", zero_division=0))
    return [float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))]

def relative_reduction(f1_base, f1_prot):
    """Descriptive only; undefined (None) when baseline F1 <= 0. Always report absolute values alongside."""
    return None if f1_base <= 0 else float((f1_base - f1_prot) / f1_base)
