import pandas as pd, numpy as np
from qpf import selection

def _row(**k):
    d = dict(strategy="x", verify_status="PASS", depth=10, d_depth=0.0, d_n2q=0.0, d_active=0.0); d.update(k); return pd.Series(d)

def test_budget_boundaries():
    assert selection.reject_reason(_row(d_depth=0.10), 0.10) == ""
    assert "over budget" in selection.reject_reason(_row(d_depth=0.101), 0.10)
    assert "over budget" in selection.reject_reason(_row(d_n2q=0.01), 0.0)
    assert selection.reject_reason(_row(d_depth=-0.2), 0.0) == ""            # cheaper than baseline is fine

def test_unverified_never_eligible():
    for s in ("UNKNOWN", "FAIL", "ERROR"): assert "verification" in selection.reject_reason(_row(verify_status=s), 9.0)

def test_selection_is_label_free_and_deterministic():
    class S:   # surrogate stub: only sees features
        def predict_proba(self, X): return np.c_[X[:, 0], 1 - X[:, 0]]
    mk = lambda cid, f, st: dict(base_id="b", opt=0, cid=cid, strategy=st, verify_status="PASS", depth=5, d_depth=0.0, d_n2q=0.0, d_active=0.0, cost=0.0, f0=f, family="SECRET")
    df = pd.DataFrame([mk("a", 0.9, "baseline"), mk("b", 0.55, "decomp"), mk("c", 0.7, "reorder")])
    s1, _ = selection.choose(df, S(), ["f0"], 0.1); s2, _ = selection.choose(df.sample(frac=1, random_state=1), S(), ["f0"], 0.1)
    assert s1.cid.iloc[0] == s2.cid.iloc[0] == "b"       # least confident for the attacker; row order irrelevant
