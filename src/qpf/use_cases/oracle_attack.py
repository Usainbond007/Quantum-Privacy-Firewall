"""Exact marked-state recovery from a circuit AS RECEIVED (logical or compiled). Lower-bound attacker: if this recovers the
secret, no ML score can justify release. Works on physical circuits by keeping only touched qubits and following the
measurement map, so layout changes and re-ordering do not matter to it."""
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

MAX_ACTIVE = 22

def _active_core(qc):
    """-> (unitary-only circuit on touched qubits, [(local_qubit, clbit_index), ...])"""
    qidx = {q: i for i, q in enumerate(qc.qubits)}; cidx = {c: i for i, c in enumerate(qc.clbits)}
    touched = sorted({qidx[q] for i in qc.data if i.operation.name not in ("barrier", "delay") for q in i.qubits})
    loc = {p: k for k, p in enumerate(touched)}; core = QuantumCircuit(len(touched)); meas = []
    for inst in qc.data:
        nm = inst.operation.name
        if nm in ("barrier", "delay"): continue
        qs = [loc[qidx[q]] for q in inst.qubits]
        if nm == "measure": meas.append((qs[0], cidx[inst.clbits[0]])); continue
        core.append(inst.operation, qs)
    core.global_phase = qc.global_phase
    return core, meas

def recover(qc, top=3):
    """-> dict(status, best, p_best, top=[(bitstring, p)...], n_active). Bitstring is clbit0..clbitN-1 left to right."""
    core, meas = _active_core(qc)
    if not meas: return {"status": "NO_MEASUREMENTS", "n_active": core.num_qubits}
    if core.num_qubits > MAX_ACTIVE: return {"status": "TOO_WIDE_FOR_EXACT", "n_active": core.num_qubits}
    probs = Statevector.from_instruction(core).probabilities(); nq = core.num_qubits
    meas = sorted(meas, key=lambda m: m[1]); order = [q for q, _ in meas]
    dist = {}
    for idx, p in enumerate(probs):
        if p < 1e-12: continue
        key = "".join(str((idx >> q) & 1) for q in order); dist[key] = dist.get(key, 0.0) + float(p)
    t = sorted(dist.items(), key=lambda kv: -kv[1])[:top]
    return {"status": "OK", "best": t[0][0], "p_best": t[0][1], "top": t, "n_active": nq}
