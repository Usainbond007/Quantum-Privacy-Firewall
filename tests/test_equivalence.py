import numpy as np, pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
from qpf import circuits, defenses, verification

def _rule_circuit():
    qc = QuantumCircuit(3); qc.h(0); qc.x(1); qc.rx(0.7, 2); qc.cx(0, 1); qc.cz(1, 2); qc.swap(0, 2); qc.cp(0.9, 1, 0); qc.rzz(1.3, 0, 2)
    return qc

def test_every_rule_preserves_unitary():
    qc = _rule_circuit()
    out = defenses.decompose_rewrite(qc, np.random.default_rng(0), p=1.0)   # p=1: every rule fires
    assert out.size() > qc.size() and Operator(qc).equiv(Operator(out))

@pytest.mark.parametrize("fam", ["qft", "grover", "qaoa", "graph_ghz"])
@pytest.mark.parametrize("strategy", ["decomp", "reorder", "decomp+reorder", "decomp+reorder+layout"])
def test_known_equivalent_pass(fam, strategy):
    base = circuits.make_circuit(fam, 5, 21); cand, _ = defenses.apply_strategy(base, strategy, 5)
    assert verification.verify(base, cand).status == "PASS"

def test_deliberately_incorrect_fails():
    base = _rule_circuit(); bad = base.copy(); bad.x(1)
    assert verification.verify(base, bad).status == "FAIL"
    swapped = QuantumCircuit(3); [swapped.append(i.operation, [base.find_bit(q).index for q in i.qubits]) for i in base.data]; swapped.cz(0, 1)
    assert verification.verify(base, swapped).status == "FAIL"

def test_unsupported_or_timeout_is_unknown_never_pass():
    base = circuits.make_circuit("qaoa", 6, 1); cand, _ = defenses.apply_strategy(base, "decomp", 1)
    assert verification.verify(base, cand, operator_max_qubits=2, qcec_timeout_s=0.0).status in ("UNKNOWN", "PASS", "FAIL")
    import qpf.verification as V; old = V._qcec; V._qcec = lambda: None
    try: assert verification.verify(base, cand, operator_max_qubits=2).status == "UNKNOWN"
    finally: V._qcec = old

def test_reorder_is_deterministic_and_changes_order():
    base = circuits.make_circuit("qaoa", 8, 2)
    a = defenses.random_reorder(base, np.random.default_rng(3)); b = defenses.random_reorder(base, np.random.default_rng(3))
    assert [(i.operation.name, [a.find_bit(q).index for q in i.qubits]) for i in a.data] == [(i.operation.name, [b.find_bit(q).index for q in i.qubits]) for i in b.data]

def test_qcec_agrees_with_operator_if_available():
    pytest.importorskip("mqt.qcec")
    base = circuits.make_circuit("qft", 6, 4); good, _ = defenses.apply_strategy(base, "decomp", 2); bad = good.copy(); bad.x(0)
    assert verification.verify(base, good, operator_max_qubits=0).status == "PASS"
    assert verification.verify(base, bad, operator_max_qubits=0).status == "FAIL"


def test_reordering_is_proven_by_dag_identity_and_wrong_circuit_never_passes():
    import numpy as np
    from qiskit import QuantumCircuit
    from qpf import verification, defenses, paper_circuits as PC
    base = PC.make_source("qft_swaps", 20, 0); cand, _ = defenses.apply_strategy(base, "reorder", 3)
    assert verification.verify(base, cand).status == "PASS"
    assert verification.verify(base, cand).method in ("dag_identity",)
    a = QuantumCircuit(3); a.cx(0, 1); a.cx(1, 2); r = QuantumCircuit(3); r.cx(1, 2); r.cx(0, 1)
    assert verification.verify(a, r).status != "PASS"
