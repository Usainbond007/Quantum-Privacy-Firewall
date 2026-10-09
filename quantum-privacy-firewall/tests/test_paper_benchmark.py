import numpy as np, pandas as pd
from qpf import paper_benchmark as PB, paper_circuits as PC, paper_features as PF

CFG = {"seed": 7, "variants": 6, "test_variants": 2}

def test_splits_are_source_disjoint_and_cover_every_generator():
    for s in range(5):
        part = PB.make_splits(CFG, s); tr = {k for k, v in part.items() if v == "train"}; te = {k for k, v in part.items() if v == "test"}
        assert tr.isdisjoint(te) and len(tr | te) == 47 * 6
        for g in PC.GENERATORS: assert sum(1 for v in range(6) if part[PC.source_id(g, v)] == "test") == 2

def test_generator_disjoint_split_never_shares_a_generator():
    for s in range(5):
        part = PB.make_generator_splits(CFG, s); gt = {k.rsplit("-v", 1)[0] for k, v in part.items() if v == "test"}
        gr = {k.rsplit("-v", 1)[0] for k, v in part.items() if v == "train"}
        assert gt.isdisjoint(gr) and len(gt) == 14        # two held-out generators for each of the seven classes
        assert all(any(PC.GENERATORS[g] == c for g in gt) for c in PC.CLASS_LABELS)

def test_real_transpiled_circuit_features_are_finite_and_in_range():
    qc = PC.make_source("qft_swaps", 8, 0); from qpf import compilation
    tc, _ = compilation.compile_circuit(qc, 2, 11); r = PB.physical_row(tc, "FakeNighthawk")
    for f in PF.PAPER_FEATURE_NAMES: assert np.isfinite(r[f]) and r[f] >= 0
    for f in ("two_qubit_fraction", "phase_rotation_fraction", "two_qubit_layer_fraction", "used_hardware_edge_fraction", "max_edge_load_fraction"): assert r[f] <= 1 + 1e-9
    assert 0 <= r["edge_two_qubit_gini"] <= 1 and 0 <= r["qubit_two_qubit_gini"] <= 1
    assert r["edge_two_qubit_gini__used"] <= r["edge_two_qubit_gini"] + 1e-9        # excluding zeros can only lower inequality

def test_job_returns_status_ok_for_a_real_source():
    r = PB._job(("ghz", 0, 8, 0, 11, "FakeNighthawk")); assert r["status"] == "OK" and r["intent"] == "entanglement_generation"
