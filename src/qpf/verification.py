"""Semantic verification. PASS / FAIL / UNKNOWN. Timeout or unsupported => UNKNOWN, never PASS (plan M3)."""
from dataclasses import dataclass
from qiskit.quantum_info import Operator

@dataclass
class Verdict:
    status: str; method: str; note: str = ""

def _qcec():
    try:
        from mqt import qcec; return qcec
    except Exception:
        return None

def verify(orig, cand, operator_max_qubits=10, qcec_timeout_s=60):
    if cand is orig:
        return Verdict("PASS", "identical_logical_circuit", "candidate differs only at compile time")
    if orig.num_qubits != cand.num_qubits:
        return Verdict("FAIL", "width_mismatch")
    n = orig.num_qubits
    try:
        if n <= operator_max_qubits:
            ok = Operator(orig).equiv(Operator(cand))
            return Verdict("PASS" if ok else "FAIL", "operator_equiv", "unitary equal up to global phase")
        q = _qcec()
        if q is None: return Verdict("UNKNOWN", "none", "no checker available for this width")
        res = q.verify(orig, cand, timeout=float(qcec_timeout_s))
        e = str(res.equivalence).split(".")[-1].lower()
        if e.startswith("equivalent"): return Verdict("PASS", "mqt_qcec", e)
        if e == "not_equivalent": return Verdict("FAIL", "mqt_qcec", e)
        return Verdict("UNKNOWN", "mqt_qcec", e)       # probably_equivalent / no_information are NOT proofs
    except Exception as ex:
        return Verdict("UNKNOWN", "error", repr(ex)[:200])
