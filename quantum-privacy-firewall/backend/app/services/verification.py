"""Exact, layout-aware clean-ancilla isometry verification; never sample a proof.

For every logical basis input, compare the compiled output with the logical
unitary embedded at the final layout. Unused physical qubits start and must
finish in |0>. Idle hardware wires need not inflate the simulation dimension.
"""
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
from qpf.verification import Verdict

MAX_ACTIVE_QUBITS = 10


def layout_indices(compiled, width):
    if compiled.layout is None:
        if compiled.num_qubits != width:
            raise ValueError("Missing layout for a circuit with additional physical qubits")
        return {"initial": list(range(width)), "final": list(range(width))}
    initial = compiled.layout.initial_index_layout(filter_ancillas=True)
    final = compiled.layout.final_index_layout(filter_ancillas=True)
    for mapping in (initial, final):
        if len(mapping) != width or len(set(mapping)) != width or any(q < 0 or q >= compiled.num_qubits for q in mapping):
            raise ValueError("Incomplete or invalid transpiler layout")
    return {"initial": list(initial), "final": list(final)}


def verify_compiled(logical, compiled, max_active_qubits=MAX_ACTIVE_QUBITS):
    method = "exact_layout_isometry"
    try:
        mappings = layout_indices(compiled, logical.num_qubits)
        active = set(mappings["initial"] + mappings["final"])
        for inst in compiled.data:
            if inst.operation.name in ("measure", "reset", "delay") or inst.clbits or inst.operation.num_clbits:
                return Verdict("UNKNOWN", method, "Non-unitary or classical instruction is unsupported")
            active.update(compiled.find_bit(q).index for q in inst.qubits)
        if len(active) > max_active_qubits:
            return Verdict("UNKNOWN", method, f"{len(active)} active physical wires exceed the exact-check limit of {max_active_qubits}")
        wire = {physical: compact for compact, physical in enumerate(sorted(active))}
        compact = QuantumCircuit(len(active))
        compact.global_phase = compiled.global_phase
        for inst in compiled.data:
            if inst.operation.name != "barrier":
                compact.append(inst.operation, [wire[compiled.find_bit(q).index] for q in inst.qubits])
        def embed(mapping):
            return [sum(((basis >> logical_q) & 1) << wire[physical_q]
                        for logical_q, physical_q in enumerate(mapping))
                    for basis in range(2**logical.num_qubits)]
        actual = Operator(compact).data[:, embed(mappings["initial"])]
        expected = np.zeros_like(actual)
        expected[embed(mappings["final"]), :] = Operator(logical).data
        pivot = np.unravel_index(np.argmax(np.abs(expected)), expected.shape)
        phase = actual[pivot] / expected[pivot]
        ok = np.isclose(abs(phase), 1, atol=1e-8, rtol=1e-7) and np.allclose(actual, phase * expected, atol=1e-8, rtol=1e-7)
        return Verdict("PASS" if ok else "FAIL", method,
                       f"All {2**logical.num_qubits} basis inputs; {len(active)} active wires; initial/final layout and clean ancillas; global phase allowed")
    except Exception as exc:
        return Verdict("UNKNOWN", method, f"{type(exc).__name__}: {str(exc)[:200]}")
