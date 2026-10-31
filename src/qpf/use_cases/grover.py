"""Synthetic defensive-cryptanalysis case: a Grover search for a secret predicate (toy width). NOT AES. The secret is
held locally for evaluation only; it must never be written to the outbound artifact or to default logs."""
import math
from qiskit import QuantumCircuit, ClassicalRegister

def grover_kernel(secret: str, iterations=None):
    """Bound, static, unitary kernel on len(secret) qubits (no measurements). secret is little-endian-agnostic:
    bit i of `secret` (left to right) is the marked value of qubit i."""
    n = len(secret); k = iterations or max(1, round(math.pi / 4 * math.sqrt(2 ** n)))
    qc = QuantumCircuit(n, name="grover_kernel"); qc.h(range(n))
    def mcz():
        qc.h(n - 1); qc.mcx(list(range(n - 1)), n - 1); qc.h(n - 1)
    for _ in range(k):
        for i, b in enumerate(secret):
            if b == "0": qc.x(i)
        mcz()
        for i, b in enumerate(secret):
            if b == "0": qc.x(i)
        qc.h(range(n)); qc.x(range(n)); mcz(); qc.x(range(n)); qc.h(range(n))
    return qc

def with_measurements(kernel):
    """Reattach terminal measurements to a (possibly rewritten) kernel: qubit i -> clbit i."""
    n = kernel.num_qubits; qc = kernel.copy(); qc.add_register(ClassicalRegister(n, "c")); qc.measure(range(n), range(n)); return qc
