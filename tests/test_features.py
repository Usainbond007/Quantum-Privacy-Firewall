import numpy as np
from qpf import circuits, compilation, features as F

def test_feature_vector_shape_range_and_determinism():
    qc = circuits.make_circuit("qaoa", 6, 3); tc, _ = compilation.compile_circuit(qc, 1, 11)
    m, f = F.analyze(tc); m2, f2 = F.analyze(tc)
    assert list(f) == F.FEATURE_NAMES and f == f2 and m == m2
    assert all(0 <= v <= 1 + 1e-9 for k, v in f.items() if k != "burstiness")

def test_all_two_qubit_ops_counted():
    qc = circuits.make_circuit("graph_ghz", 6, 5); tc, _ = compilation.compile_circuit(qc, 0, 11)
    m, _ = F.analyze(tc)
    assert m["n2q"] == sum(1 for i in tc.data if len(i.qubits) == 2 and i.operation.name != "barrier")
    assert m["size"] == sum(1 for i in tc.data if i.operation.name not in ("barrier", "delay"))
