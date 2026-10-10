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


def test_dag_identity_shortcut_checks_parameters_operands_and_order():
    from qiskit import QuantumCircuit
    from qpf import verification
    a = QuantumCircuit(3); a.rz(0.3, 0); a.cx(0, 1); a.x(2); a.cx(1, 2)
    same = QuantumCircuit(3); same.x(2); same.rz(0.3, 0); same.cx(0, 1); same.cx(1, 2)   # independent ops interleaved: identical DAG
    assert verification.verify(a, same).method == "dag_identity"
    diff_param = QuantumCircuit(3); diff_param.rz(0.31, 0); diff_param.cx(0, 1); diff_param.x(2); diff_param.cx(1, 2)
    diff_operand = QuantumCircuit(3); diff_operand.rz(0.3, 0); diff_operand.cx(1, 0); diff_operand.x(2); diff_operand.cx(1, 2)
    diff_order = QuantumCircuit(3); diff_order.rz(0.3, 0); diff_order.x(2); diff_order.cx(1, 2); diff_order.cx(0, 1)   # non-commuting swap (shares qubit 1)
    diff_gate = QuantumCircuit(3); diff_gate.rz(0.3, 0); diff_gate.cz(0, 1); diff_gate.x(2); diff_gate.cx(1, 2)
    for bad in (diff_param, diff_operand, diff_order, diff_gate):
        v = verification.verify(a, bad, qcec_timeout_s=10); assert v.status != "PASS" and v.method != "dag_identity"


def test_unverified_candidates_are_rejected_by_selection():
    import pandas as pd
    from qpf import selection
    for st in ("UNKNOWN", "FAIL", "ERROR"):
        r = pd.Series(dict(strategy="decomp", verify_status=st, depth=5, d_depth=0, d_n2q=0, d_active=0)); assert "verification" in selection.reject_reason(r, 1.0)
