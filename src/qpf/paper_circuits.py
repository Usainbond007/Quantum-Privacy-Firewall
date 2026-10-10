"""Table I of Buesser & Kurmus (QCE 2026): seven intent classes and their 47 circuit generators.

The paper names the generators but does not publish their definitions. Every generator below is OUR interpretation
of its name, written to use exactly ``n`` qubits and to stay polynomial in size at n = 24 and 48.
A source circuit is a pure function of (generator, n, variant). Variants differ in random angles, marked bit
strings, input bits and (odd variants) a random relabeling of logical qubits, so several distinct source circuits
exist per generator.  ``source_id = "<generator>-v<variant>"`` is size independent: the 24- and 48-qubit versions of
one source always fall in the same train/test partition.
"""
import numpy as np
from qiskit import QuantumCircuit
from qiskit.synthesis.qft import synth_qft_full

CLASSES = {
    "entanglement_generation": ["ghz", "bell_chain", "graph_line", "graph_ring", "graph_star", "w_state_ladder", "cluster_grid"],
    "fourier_like": ["qft_swaps", "qft_no_swaps", "iqft_swaps", "iqft_no_swaps", "approx_qft", "phase_estimation", "qft_phase_gradient"],
    "phase_oracle_like": ["parity", "parity_odd", "parity_even", "phase_oracle", "phase_ladder", "controlled_phase_ladder", "diagonal_phase_pattern"],
    "amplitude_amplification": ["grover", "grover_zero", "grover_two_iterations", "parity_amplitude_amplification",
                                "fixed_point_amplitude_amplification", "amplitude_estimation_style"],
    "variational_ansatz": ["hea_linear", "hea_ring", "hea_brickwork", "real_amplitudes", "twolocal_rx_rz", "qaoa_line", "qaoa_ring"],
    "hamiltonian_simulation": ["trotter_zz_xx", "trotter_zz_xx_ring", "trotter_tfim", "trotter_xxz", "trotter_heisenberg", "trotter_longitudinal_ising"],
    "arithmetic_permutation": ["ripple_adder", "incrementer", "permutation_swaps", "controlled_swap_network", "comparator", "majority_logic", "toffoli"],
}
CLASS_LABELS = list(CLASSES)

# Verification tier of each generator, backed by tests/test_generator_audit.py:
#   semantic   - mathematical invariant checked (statevector / truth table / stabilizers / analytic result)
#   structural - gate content and qubit topology checked against the named construction; dynamics NOT checked
#   analogue   - only unitarity/width/determinism tested; the circuit is a structural stand-in for its name
AUDIT = {
 "ghz": "semantic", "bell_chain": "structural", "graph_line": "semantic", "graph_ring": "semantic", "graph_star": "semantic",
 "w_state_ladder": "semantic", "cluster_grid": "semantic",
 "qft_swaps": "semantic", "qft_no_swaps": "semantic", "iqft_swaps": "semantic", "iqft_no_swaps": "semantic",
 "approx_qft": "analogue", "phase_estimation": "semantic", "qft_phase_gradient": "analogue",
 "parity": "semantic", "parity_odd": "semantic", "parity_even": "semantic", "phase_oracle": "structural",
 "phase_ladder": "structural", "controlled_phase_ladder": "structural", "diagonal_phase_pattern": "structural",
 "grover": "semantic", "grover_zero": "semantic", "grover_two_iterations": "semantic", "parity_amplitude_amplification": "semantic",
 "fixed_point_amplitude_amplification": "structural", "amplitude_estimation_style": "analogue",
 "hea_linear": "structural", "hea_ring": "structural", "hea_brickwork": "structural", "real_amplitudes": "structural",
 "twolocal_rx_rz": "structural", "qaoa_line": "structural", "qaoa_ring": "structural",
 "trotter_zz_xx": "structural", "trotter_zz_xx_ring": "structural", "trotter_tfim": "structural", "trotter_xxz": "structural",
 "trotter_heisenberg": "structural", "trotter_longitudinal_ising": "structural",
 "ripple_adder": "semantic", "incrementer": "semantic", "permutation_swaps": "semantic", "controlled_swap_network": "structural",
 "comparator": "semantic", "majority_logic": "semantic", "toffoli": "semantic",
}
GENERATORS = {g: c for c, gs in CLASSES.items() for g in gs}
assert len(GENERATORS) == 47 and sum(len(v) for v in CLASSES.values()) == 47


# ------------------------------------------------------------------ small helpers
def _line(n): return [(i, i + 1) for i in range(n - 1)]
def _ring(n): return _line(n) + [(n - 1, 0)]
def _brick(n, par): return [(i, i + 1) for i in range(par, n - 1, 2)]
def _ang(rng, k=None): return rng.uniform(0.1, 2 * np.pi - 0.1) if k is None else rng.uniform(0.1, 2 * np.pi - 0.1, k)
def _bits(rng, n): return [int(b) for b in rng.integers(0, 2, n)]

def _mcz(qc, controls, target, anc):
    """Multi-controlled Z on `controls`+`target`, using the spare qubits `anc` as V-chain ancillas (linear size)."""
    qc.h(target)
    if len(controls) == 1: qc.cx(controls[0], target)
    elif len(controls) == 2: qc.ccx(controls[0], controls[1], target)
    else: qc.mcx(list(controls), target, ancilla_qubits=list(anc[:len(controls) - 2]), mode="v-chain")
    qc.h(target)

def _qft(qc, qs, swaps=True, inverse=False, approx=0):
    sub = synth_qft_full(len(qs), do_swaps=swaps, approximation_degree=approx, inverse=inverse)
    qc.compose(sub, qubits=list(qs), inplace=True)


# ------------------------------------------------------------------ entanglement generation
def ghz(n, r):
    qc = QuantumCircuit(n); qc.h(0)
    for a, b in _line(n): qc.cx(a, b)
    return qc

def bell_chain(n, r):
    qc = QuantumCircuit(n)
    for i in range(0, n - 1, 2): qc.h(i); qc.cx(i, i + 1)
    for i in range(1, n - 1, 2): qc.cx(i, i + 1)       # link neighbouring pairs
    return qc

def _graph_state(n, edges):
    qc = QuantumCircuit(n); qc.h(range(n))
    for a, b in edges: qc.cz(a, b)
    return qc

def graph_line(n, r): return _graph_state(n, _line(n))
def graph_ring(n, r): return _graph_state(n, _ring(n))
def graph_star(n, r): return _graph_state(n, [(0, i) for i in range(1, n)])

def w_state_ladder(n, r):
    qc = QuantumCircuit(n); qc.x(0)
    for i in range(n - 1):                              # move one excitation along the chain with weight 1/(n-i)
        th = 2 * np.arccos(np.sqrt(1.0 / (n - i)))
        qc.cry(th, i, i + 1); qc.cx(i + 1, i)
    return qc

def cluster_grid(n, r):
    rows = max(d for d in range(1, int(np.sqrt(n)) + 1) if n % d == 0); cols = n // rows
    e = [(i * cols + j, i * cols + j + 1) for i in range(rows) for j in range(cols - 1)]
    e += [(i * cols + j, (i + 1) * cols + j) for i in range(rows - 1) for j in range(cols)]
    return _graph_state(n, e)


# ------------------------------------------------------------------ Fourier-like
def _prep(qc, r, only=None):
    """Random classical input bits (always draws n bits so rng streams are stable); `only` limits which qubits get set."""
    for i, b in enumerate(_bits(r, qc.num_qubits)):
        if b and (only is None or i in only): qc.x(i)

def qft_swaps(n, r): qc = QuantumCircuit(n); _prep(qc, r); _qft(qc, range(n), True); return qc
def qft_no_swaps(n, r): qc = QuantumCircuit(n); _prep(qc, r); _qft(qc, range(n), False); return qc
def iqft_swaps(n, r): qc = QuantumCircuit(n); _prep(qc, r); _qft(qc, range(n), True, True); return qc
def iqft_no_swaps(n, r): qc = QuantumCircuit(n); _prep(qc, r); _qft(qc, range(n), False, True); return qc

def approx_qft(n, r):
    qc = QuantumCircuit(n); _prep(qc, r); _qft(qc, range(n), True, False, approx=int(r.integers(3, max(4, n // 3)))); return qc

def phase_estimation(n, r):
    """n-1 counting qubits, 1 eigenstate qubit; controlled-U^(2^k) with U = phase(theta)."""
    qc = QuantumCircuit(n); t = n - 1; theta = float(r.uniform(0.1, 2 * np.pi - 0.1))
    qc.x(t); qc.h(range(t))
    for k in range(t): qc.cp((theta * 2 ** (k % 20)) % (2 * np.pi), k, t)
    _qft(qc, range(t), True, True)
    return qc

def qft_phase_gradient(n, r):
    qc = QuantumCircuit(n); qc.h(range(n)); _qft(qc, range(n), True)
    for i in range(n): qc.p(2 * np.pi * (i + 1) / 2 ** min(i + 1, 12), i)    # phase-gradient layer
    return qc


# ------------------------------------------------------------------ phase / oracle-like
def _parity(n, qs, r):
    qc = QuantumCircuit(n); t = n - 1; qc.x(t); qc.h(t); qc.h(range(n - 1))
    for q in qs:
        if q != t: qc.cx(q, t)
    qc.h(range(n - 1)); return qc

def parity(n, r): return _parity(n, range(n - 1), r)
def parity_odd(n, r): return _parity(n, range(1, n - 1, 2), r)
def parity_even(n, r): return _parity(n, range(0, n - 1, 2), r)

def phase_oracle(n, r):
    """Random degree-2 phase polynomial: Z on a random subset, CZ on random pairs, sandwiched by Hadamards."""
    qc = QuantumCircuit(n); qc.h(range(n))
    for i in np.flatnonzero(r.integers(0, 2, n)): qc.z(int(i))
    for _ in range(2 * n):
        a, b = r.choice(n, 2, replace=False); qc.cz(int(a), int(b))
    qc.h(range(n)); return qc

def phase_ladder(n, r):
    qc = QuantumCircuit(n); qc.h(range(n)); th = _ang(r, n)
    for i in range(n): qc.rz(float(th[i]), i)
    for a, b in _line(n): qc.cz(a, b)
    for i in range(n): qc.p(float(th[(i + 1) % n]), i)
    return qc

def controlled_phase_ladder(n, r):
    qc = QuantumCircuit(n); qc.h(range(n))
    for a, b in _line(n): qc.cp(float(_ang(r)), a, b)
    for a, b in reversed(_line(n)): qc.cp(float(_ang(r)), a, b)
    return qc

def diagonal_phase_pattern(n, r):
    qc = QuantumCircuit(n); qc.h(range(n)); stride = int(r.integers(2, 5)); pat = _ang(r, stride)
    for i in range(n): qc.rz(float(pat[i % stride]), i)
    for i in range(0, n - stride, stride): qc.cz(i, i + stride)
    for i in range(n): qc.rz(float(pat[(i + 1) % stride]), i)
    return qc


# ------------------------------------------------------------------ amplitude amplification
def _search_regs(n): m = n // 2; return list(range(m)), list(range(m, n))     # search register, ancillas

def _parity_phase_oracle(qc, S, anc):
    """Phase (-1)^{parity(x)} on register S via phase kickback from a clean ancilla (prepared in |-> and restored)."""
    qc.x(anc); qc.h(anc)
    for q in S: qc.cx(q, anc)
    qc.h(anc); qc.x(anc)

def _grover(n, r, marked, iters, parity_oracle=False, fixed_point=False):
    S, A = _search_regs(n); m = len(S); qc = QuantumCircuit(n); qc.h(S)
    for it in range(iters):
        if parity_oracle: _parity_phase_oracle(qc, S, A[0])
        else:
            for q, b in zip(S, marked):
                if b == 0: qc.x(q)
            _mcz(qc, S[:-1], S[-1], A)
            for q, b in zip(S, marked):
                if b == 0: qc.x(q)
        qc.h(S); qc.x(S)
        if fixed_point:                                # partial-phase reflection with a decreasing angle
            phi = np.pi / (2 + it)
            ctl = S[:-1]; out = A[-1]; w = A[:-1]                 # AND of controls -> out (V-chain), phase, uncompute
            qc.mcx(ctl, out, ancilla_qubits=w[:len(ctl) - 2], mode="v-chain"); qc.cp(phi, out, S[-1])
            qc.mcx(ctl, out, ancilla_qubits=w[:len(ctl) - 2], mode="v-chain")
        else: _mcz(qc, S[:-1], S[-1], A)
        qc.x(S); qc.h(S)
    return qc

def grover(n, r): return _grover(n, r, _bits(r, n // 2), 1)
def grover_zero(n, r): return _grover(n, r, [0] * (n // 2), 1)
def grover_two_iterations(n, r): return _grover(n, r, _bits(r, n // 2), 2)
def parity_amplitude_amplification(n, r): return _grover(n, r, None, 2, parity_oracle=True)
def fixed_point_amplitude_amplification(n, r): return _grover(n, r, _bits(r, n // 2), 3, fixed_point=True)

def amplitude_estimation_style(n, r):
    """Counting register (n//3) + state register: state prep, controlled-rotation 'Grover powers', inverse QFT."""
    c = n // 3; S = list(range(c, n)); qc = QuantumCircuit(n); th = float(r.uniform(0.2, 1.2))
    for q in S: qc.ry(float(r.uniform(0.2, 1.2)), q)
    qc.h(range(c))
    for k in range(c):
        for q in S[::2]: qc.cry((2 * th * 2 ** (k % 10)) % (2 * np.pi), k, q)
    _qft(qc, range(c), True, True)
    return qc


# ------------------------------------------------------------------ variational ansatz
def _hea(n, r, ent, reps=3):
    qc = QuantumCircuit(n)
    for _ in range(reps):
        for q in range(n): qc.ry(float(_ang(r)), q); qc.rz(float(_ang(r)), q)
        for a, b in ent: qc.cx(a, b)
    for q in range(n): qc.ry(float(_ang(r)), q)
    return qc

def hea_linear(n, r): return _hea(n, r, _line(n))
def hea_ring(n, r): return _hea(n, r, _ring(n))
def hea_brickwork(n, r):
    qc = QuantumCircuit(n)
    for rep in range(4):
        for q in range(n): qc.ry(float(_ang(r)), q); qc.rz(float(_ang(r)), q)
        for a, b in _brick(n, rep % 2): qc.cx(a, b)
    for q in range(n): qc.ry(float(_ang(r)), q)
    return qc

def real_amplitudes(n, r):                              # RY layers + reverse-linear CX entanglement
    qc = QuantumCircuit(n)
    for _ in range(3):
        for q in range(n): qc.ry(float(_ang(r)), q)
        for i in range(n - 2, -1, -1): qc.cx(i, i + 1)
    for q in range(n): qc.ry(float(_ang(r)), q)
    return qc

def twolocal_rx_rz(n, r):                               # RX, RZ rotation layers + linear CZ entanglement
    qc = QuantumCircuit(n)
    for _ in range(3):
        for q in range(n): qc.rx(float(_ang(r)), q); qc.rz(float(_ang(r)), q)
        for a, b in _line(n): qc.cz(a, b)
    for q in range(n): qc.rx(float(_ang(r)), q); qc.rz(float(_ang(r)), q)
    return qc

def _qaoa(n, r, edges, p=2):
    qc = QuantumCircuit(n); qc.h(range(n))
    for _ in range(p):
        g, b = _ang(r, 2)
        for u, v in edges: qc.rzz(float(g), u, v)
        for q in range(n): qc.rx(float(b), q)
    return qc

def qaoa_line(n, r): return _qaoa(n, r, _line(n))
def qaoa_ring(n, r): return _qaoa(n, r, _ring(n))


# ------------------------------------------------------------------ Hamiltonian simulation (Trotter)
def _trotter(n, r, edges, terms, steps=3, field=None):
    qc = QuantumCircuit(n); dt = float(r.uniform(0.05, 0.4)); J = r.uniform(0.5, 1.5, 3)
    for q in range(n):
        if r.random() < 0.5: qc.x(q)
    for _ in range(steps):
        for a, b in edges:
            if "xx" in terms: qc.rxx(float(2 * J[0] * dt), a, b)
            if "yy" in terms: qc.ryy(float(2 * J[1] * dt), a, b)
            if "zz" in terms: qc.rzz(float(2 * J[2] * dt), a, b)
        if field == "x":
            for q in range(n): qc.rx(float(2 * dt), q)
        if field == "zx":
            for q in range(n): qc.rz(float(dt), q); qc.rx(float(2 * dt), q)
    return qc

def trotter_zz_xx(n, r): return _trotter(n, r, _line(n), ("zz", "xx"))
def trotter_zz_xx_ring(n, r): return _trotter(n, r, _ring(n), ("zz", "xx"))
def trotter_tfim(n, r): return _trotter(n, r, _line(n), ("zz",), field="x")
def trotter_xxz(n, r): return _trotter(n, r, _line(n), ("xx", "yy", "zz"))
def trotter_heisenberg(n, r): return _trotter(n, r, _ring(n), ("xx", "yy", "zz"))
def trotter_longitudinal_ising(n, r): return _trotter(n, r, _line(n), ("zz",), field="zx")


# ------------------------------------------------------------------ arithmetic / permutation
def _maj(qc, a, b, c): qc.cx(c, b); qc.cx(c, a); qc.ccx(a, b, c)
def _uma(qc, a, b, c): qc.ccx(a, b, c); qc.cx(c, a); qc.cx(a, b)
def _unmaj(qc, a, b, c): qc.ccx(a, b, c); qc.cx(c, a); qc.cx(c, b)      # exact inverse of _maj

def ripple_adder(n, r):                                  # Cuccaro adder: cin, a[k], b[k], cout with n = 2k + 2
    k = (n - 2) // 2; qc = QuantumCircuit(n); _prep(qc, r)
    cin, a, b, cout = 0, list(range(1, k + 1)), list(range(k + 1, 2 * k + 1)), 2 * k + 1
    _maj(qc, cin, b[0], a[0])
    for i in range(1, k): _maj(qc, a[i - 1], b[i], a[i])
    qc.cx(a[k - 1], cout)
    for i in range(k - 1, 0, -1): _uma(qc, a[i - 1], b[i], a[i])
    _uma(qc, cin, b[0], a[0]); return qc

def incrementer(n, r):                                   # +1 on the first m bits, clean-ancilla Toffoli carry ladder
    m = n // 2; qc = QuantumCircuit(n); _prep(qc, r, only=range(m)); c = list(range(m, n))
    qc.cx(0, c[0])                                       # carry into bit 1
    for i in range(1, m - 1): qc.ccx(i, c[i - 1], c[i])
    qc.cx(c[m - 2], m - 1)
    for i in range(m - 2, 0, -1): qc.ccx(i, c[i - 1], c[i]); qc.cx(c[i - 1], i)
    qc.cx(0, c[0]); qc.x(0); return qc

def permutation_swaps(n, r):
    qc = QuantumCircuit(n); _prep(qc, r); perm = r.permutation(n)
    for i, p in enumerate(perm):
        if i != p: qc.swap(int(i), int(p))
    return qc

def controlled_swap_network(n, r):                       # swap-test-like fredkin network from control qubit 0
    qc = QuantumCircuit(n); _prep(qc, r); qc.h(0); k = (n - 1) // 2
    for i in range(k): qc.cswap(0, 1 + i, 1 + k + i)
    qc.h(0); return qc

def comparator(n, r):                                    # carry-only Cuccaro half: computes (a > b) into the last qubit
    k = (n - 2) // 2; qc = QuantumCircuit(n); _prep(qc, r)
    a, b, cout = list(range(1, k + 1)), list(range(k + 1, 2 * k + 1)), n - 1
    for q in b: qc.x(q)
    _maj(qc, 0, b[0], a[0])
    for i in range(1, k): _maj(qc, a[i - 1], b[i], a[i])
    qc.cx(a[k - 1], cout)
    for i in range(k - 1, 0, -1): _unmaj(qc, a[i - 1], b[i], a[i])   # uncompute carries
    _unmaj(qc, 0, b[0], a[0])
    for q in b: qc.x(q)
    return qc

def majority_logic(n, r):                                # majority of sliding triples written into ancilla qubits
    qc = QuantumCircuit(n); k = (2 * n) // 3; _prep(qc, r)
    for j, i in enumerate(range(0, k - 2)):
        t = k + (j % (n - k))
        qc.ccx(i, i + 1, t); qc.ccx(i + 1, i + 2, t); qc.ccx(i, i + 2, t)
    return qc

def toffoli(n, r):
    qc = QuantumCircuit(n); _prep(qc, r)
    for _ in range(2):
        for i in range(n - 2): qc.ccx(i, i + 1, i + 2)
    return qc


# ------------------------------------------------------------------ public API
_FN = {g: globals()[g] for g in GENERATORS}

def source_id(generator, variant): return f"{generator}-v{int(variant)}"

def make_source(generator, n, variant, base_seed=2026):
    """Deterministic in (generator, n, variant).  Parameters depend on (generator, variant) but NOT on n beyond shape.
    Odd variants relabel the logical qubits by a random permutation (same circuit up to renaming)."""
    gid = list(GENERATORS).index(generator)
    rng = np.random.default_rng([base_seed, gid, int(variant), int(n)])
    qc = _FN[generator](int(n), rng)
    assert qc.num_qubits == n
    if variant % 2 == 1:
        perm = [int(x) for x in rng.permutation(n)]
        out = QuantumCircuit(n); out.global_phase = qc.global_phase
        for inst in qc.data: out.append(inst.operation, [perm[qc.find_bit(q).index] for q in inst.qubits])
        qc = out
    qc.name = source_id(generator, variant)
    return qc
