import pytest
from qiskit import QuantumCircuit, transpile
from qiskit.transpiler import CouplingMap
from backend.app.services.serialization import serialize_circuit
from backend.app.services.verification import verify_compiled, layout_indices


@pytest.fixture
def routed():
    logical = QuantumCircuit(3)
    logical.h(0)
    logical.cx(0, 2)
    logical.rx(.37, 1)
    logical.cx(2, 1)
    logical.cx(0, 2)
    physical = transpile(logical, basis_gates=["rz", "sx", "x", "cx"],
                         coupling_map=CouplingMap.from_line(5), initial_layout=[4, 0, 2],
                         optimization_level=0, seed_transpiler=7)
    return logical, physical


def test_layout_routing_and_clean_ancillas(routed):
    logical, physical = routed
    mapping = layout_indices(physical, 3)
    assert mapping["initial"] == [4, 0, 2]
    assert mapping["final"] != mapping["initial"]
    assert verify_compiled(logical, physical).status == "PASS"
    physical.global_phase += .43
    assert verify_compiled(logical, physical).status == "PASS"


def test_corrupted_gate_and_output_permutation_fail(routed):
    logical, physical = routed
    bad = physical.copy()
    final = layout_indices(bad, 3)["final"]
    bad.x(final[0])
    assert verify_compiled(logical, bad).status == "FAIL"
    swapped = physical.copy()
    swapped.swap(final[0], final[1])
    assert verify_compiled(logical, swapped).status == "FAIL"


def test_dirty_ancilla_fails():
    logical = QuantumCircuit(2)
    logical.h(0)
    physical = transpile(logical, basis_gates=["rz", "sx", "x", "cx"],
                         coupling_map=CouplingMap.from_line(4), initial_layout=[1, 2])
    physical.x(0)
    assert verify_compiled(logical, physical).status == "FAIL"


def test_limits_missing_layout_and_nonunitary_are_unknown(routed):
    logical, physical = routed
    assert verify_compiled(logical, physical, max_active_qubits=2).status == "UNKNOWN"
    assert verify_compiled(logical, QuantumCircuit(5)).status == "UNKNOWN"
    measured = logical.copy()
    measured.measure_all()
    assert verify_compiled(logical, measured).status == "UNKNOWN"


def test_serialization_preserves_wire_indices_and_mappings(routed):
    logical, physical = routed
    data = serialize_circuit(physical, logical.num_qubits)
    assert data["layout"] == layout_indices(physical, 3)
    assert all(set(g["qubits"]) <= set(data["qubits"]) for g in data["gates"])
    assert data["num_qubits"] == 5
    assert data["logical_width"] == 3
    assert all(g["layer"] >= 1 for g in data["gates"])
