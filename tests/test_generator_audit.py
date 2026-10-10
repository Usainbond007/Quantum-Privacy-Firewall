"""Semantic / structural audit of the 47 Table I generators. The tier of each generator is declared in paper_circuits.AUDIT;
`test_every_generator_has_an_audit_tier` fails if a generator is added without one."""
import numpy as np, pytest
from qiskit.quantum_info import Statevector, Operator, Pauli
from qpf import paper_circuits as PC

R = lambda s=0: np.random.default_rng(s)
sv = lambda qc: Statevector(qc)
ops = lambda qc: [(i.operation.name, tuple(qc.find_bit(q).index for q in i.qubits)) for i in qc.data]
bits_int = lambda n, s: sum(b << i for i, b in enumerate(PC._bits(R(s), n)))
def out_bits(qc):
    p = Statevector(qc).probabilities(); i = int(np.argmax(p)); assert p[i] > 0.999; return [(i >> k) & 1 for k in range(qc.num_qubits)]

def test_every_generator_has_an_audit_tier():
    assert set(PC.AUDIT) == set(PC.GENERATORS) and set(PC.AUDIT.values()) <= {"semantic", "structural", "analogue"}

# ---- entanglement
def test_ghz_state():
    p = sv(PC.ghz(8, R())).probabilities(); assert np.isclose(p[0], .5) and np.isclose(p[-1], .5)

@pytest.mark.parametrize("gen", ["graph_line", "graph_ring", "graph_star", "cluster_grid"])
def test_graph_states_satisfy_their_stabilizers(gen):
    n = 8; qc = PC._FN[gen](n, R()); E = [tuple(qc.find_bit(q).index for q in i.qubits) for i in qc.data if i.operation.name == "cz"]; s = sv(qc)
    for v in range(n):
        lab = ["I"] * n; lab[v] = "X"
        for a, b in E:
            if a == v: lab[b] = "Z"
            if b == v: lab[a] = "Z"
        assert abs(s.expectation_value(Pauli("".join(reversed(lab)))) - 1) < 1e-9

def test_bell_chain_structure():
    n = 8; o = ops(PC.bell_chain(n, R())); assert o.count(("h", (0,))) == 1 and sum(1 for g, _ in o if g == "cx") == n // 2 + (n // 2 - 1)

# ---- Fourier-like
def _dft(n, k, inverse): N = 2 ** n; return np.exp((-1 if inverse else 1) * 2j * np.pi * k * np.arange(N) / N) / np.sqrt(N)
def _rev(n, v): return np.array([v[int(format(x, f"0{n}b")[::-1], 2)] for x in range(2 ** n)])

def test_qft_variants_match_analytic_dft():
    n = 6; k = bits_int(n, 3)
    f = lambda g: sv(PC._FN[g](n, R(3))).data
    assert abs(np.vdot(_dft(n, k, False), f("qft_swaps"))) ** 2 > 1 - 1e-9
    assert abs(np.vdot(_dft(n, k, True), f("iqft_swaps"))) ** 2 > 1 - 1e-9
    assert abs(np.vdot(_rev(n, _dft(n, k, False)), f("qft_no_swaps"))) ** 2 > 1 - 1e-9

def test_iqft_no_swaps_is_the_inverse_of_qft_no_swaps():
    n = 5; q = PC.qft_no_swaps(n, R()); iq = PC.iqft_no_swaps(n, R())
    def core(qc):                                                    # strip the random X input preparation
        c = qc.copy_empty_like(); [c.append(i.operation, i.qubits) for i in qc.data if i.operation.name != "x"]; return c
    assert np.allclose(Operator(core(iq)).data @ Operator(core(q)).data, np.eye(2 ** n), atol=1e-9)

def test_phase_estimation_peaks_at_the_true_phase():
    n = 10; t = n - 1; theta = float(R(2).uniform(0.1, 2 * np.pi - 0.1)); p = sv(PC.phase_estimation(n, R(2))).probabilities()
    cnt = np.zeros(2 ** t)
    for i, pp in enumerate(p): cnt[i & (2 ** t - 1)] += pp
    assert abs(cnt.argmax() - theta / (2 * np.pi) * 2 ** t) < 1 and cnt.max() > 0.4

# ---- phase / oracle
@pytest.mark.parametrize("gen,sel", [("parity", lambda n: range(n - 1)), ("parity_odd", lambda n: range(1, n - 1, 2)), ("parity_even", lambda n: range(0, n - 1, 2))])
def test_parity_oracles_recover_their_subset_by_bernstein_vazirani(gen, sel):
    n = 10; i = int(np.argmax(sv(PC._FN[gen](n, R())).probabilities())); chosen = set(sel(n))
    assert [(i >> k) & 1 for k in range(n - 1)] == [1 if k in chosen else 0 for k in range(n - 1)]

def test_phase_oracle_is_a_stabilizer_circuit_with_only_clifford_gates():
    assert {g for g, _ in ops(PC.phase_oracle(8, R()))} <= {"h", "z", "cz"}

@pytest.mark.parametrize("gen", ["phase_ladder", "controlled_phase_ladder", "diagonal_phase_pattern"])
def test_diagonal_phase_generators_only_add_phases_after_hadamards(gen):
    qc = PC._FN[gen](8, R(1)); assert {g for g, _ in ops(qc)} <= {"h", "rz", "p", "cz", "cp"}
    a = np.abs(sv(qc).data); assert np.allclose(a, a[0])

# ---- amplitude amplification
def _marked_prob(qc, m, marked):
    return sum(pp for i, pp in enumerate(Statevector(qc).probabilities()) if (i & (2 ** m - 1)) == marked)
def _anc_zero(qc, m): return sum(pp for i, pp in enumerate(Statevector(qc).probabilities()) if (i >> m) == 0)

@pytest.mark.parametrize("gen,it", [("grover", 1), ("grover_zero", 1), ("grover_two_iterations", 2)])
def test_grover_success_probability_matches_theory_and_ancillas_are_restored(gen, it):
    n, m = 12, 6; qc = PC._FN[gen](n, R(4)); bits = [0] * m if gen == "grover_zero" else PC._bits(R(4), m)
    th = np.arcsin(2 ** -(m / 2))
    assert np.isclose(_marked_prob(qc, m, sum(b << i for i, b in enumerate(bits))), np.sin((2 * it + 1) * th) ** 2, atol=1e-9)
    assert _anc_zero(qc, m) > 1 - 1e-9

def test_parity_phase_oracle_applies_minus_one_to_odd_parity_and_restores_ancilla():
    from qiskit import QuantumCircuit
    m = 4; qc = QuantumCircuit(m + 1); qc.h(range(m)); PC._parity_phase_oracle(qc, list(range(m)), m); d = sv(qc).data
    for x in range(2 ** m): assert np.isclose(d[x], (-1) ** bin(x).count("1") / 4)          # ancilla index bit m is 0 -> index x
    assert np.allclose(d[2 ** m:], 0)

def test_parity_amplitude_amplification_matches_two_iteration_theory_and_restores_ancillas():
    n, m = 12, 6; qc = PC.parity_amplitude_amplification(n, R(4)); p = Statevector(qc).probabilities()
    assert np.isclose(sum(pp for i, pp in enumerate(p) if bin(i & (2 ** m - 1)).count("1") % 2), np.sin(5 * np.pi / 4) ** 2) and _anc_zero(qc, m) > 1 - 1e-9

def test_fixed_point_aa_restores_all_ancillas():
    assert _anc_zero(PC.fixed_point_amplitude_amplification(12, R(4)), 6) > 1 - 1e-9

# ---- variational / Hamiltonian simulation: gate content and topology
def _pairs(qc, name): return {tuple(sorted(q)) for g, q in ops(qc) if g == name}
LINE = lambda n: {(i, i + 1) for i in range(n - 1)}
RING = lambda n: LINE(n) | {(0, n - 1)}

def test_hea_and_ansatz_topologies():
    n = 8
    assert _pairs(PC.hea_linear(n, R()), "cx") == LINE(n) and _pairs(PC.hea_ring(n, R()), "cx") == RING(n)
    assert _pairs(PC.hea_brickwork(n, R()), "cx") == LINE(n) and _pairs(PC.real_amplitudes(n, R()), "cx") == LINE(n)
    assert _pairs(PC.twolocal_rx_rz(n, R()), "cz") == LINE(n)
    assert {g for g, _ in ops(PC.real_amplitudes(n, R()))} == {"ry", "cx"} and {g for g, _ in ops(PC.twolocal_rx_rz(n, R()))} == {"rx", "rz", "cz"}

def test_qaoa_structure():
    n = 8
    for gen, E in (("qaoa_line", LINE(n)), ("qaoa_ring", RING(n))):
        qc = PC._FN[gen](n, R()); assert _pairs(qc, "rzz") == E and {g for g, _ in ops(qc)} == {"h", "rzz", "rx"}
        assert sum(1 for g, _ in ops(qc) if g == "rzz") == 2 * len(E)             # p = 2 layers

@pytest.mark.parametrize("gen,terms,E,fields", [
    ("trotter_zz_xx", {"rzz", "rxx"}, LINE, set()), ("trotter_zz_xx_ring", {"rzz", "rxx"}, RING, set()), ("trotter_tfim", {"rzz"}, LINE, {"rx"}),
    ("trotter_xxz", {"rxx", "ryy", "rzz"}, LINE, set()), ("trotter_heisenberg", {"rxx", "ryy", "rzz"}, RING, set()), ("trotter_longitudinal_ising", {"rzz"}, LINE, {"rx", "rz"})])
def test_trotter_generators_use_the_named_hamiltonian_terms_on_the_named_graph(gen, terms, E, fields):
    n = 8; qc = PC._FN[gen](n, R()); names = {g for g, _ in ops(qc)}
    assert terms <= names and names <= terms | fields | {"x"}
    for t in terms: assert _pairs(qc, t) == E(n)

# ---- arithmetic / permutation (classical reversible logic, checked against a classical reference)
def test_permutation_swaps_applies_the_permutation_sequence():
    n = 8
    for s in range(5):
        r = R(s); bits = PC._bits(r, n); perm = r.permutation(n)
        for i, p in enumerate(perm):
            if i != p: bits[i], bits[int(p)] = bits[int(p)], bits[i]
        assert out_bits(PC.permutation_swaps(n, R(s))) == bits

def test_toffoli_ladder_matches_classical_reference():
    n = 9
    for s in range(5):
        bits = PC._bits(R(s), n)
        for _ in range(2):
            for i in range(n - 2): bits[i + 2] ^= bits[i] & bits[i + 1]
        assert out_bits(PC.toffoli(n, R(s))) == bits

def test_majority_logic_matches_classical_reference():
    n = 9; k = (2 * n) // 3
    for s in range(5):
        bits = PC._bits(R(s), n); ref = list(bits)
        for j, i in enumerate(range(0, k - 2)):
            a, b, c = bits[i], bits[i + 1], bits[i + 2]; ref[k + (j % (n - k))] ^= (a & b) ^ (b & c) ^ (a & c)
        assert out_bits(PC.majority_logic(n, R(s))) == ref

def test_controlled_swap_network_structure():
    n = 9; o = ops(PC.controlled_swap_network(n, R())); k = (n - 1) // 2
    assert [g for g in o if g[0] == "cswap"] == [("cswap", (0, 1 + i, 1 + k + i)) for i in range(k)]

# ---- analogues: honest minimal checks
@pytest.mark.parametrize("gen", ["qft_phase_gradient", "amplitude_estimation_style", "approx_qft"])
def test_analogue_generators_are_normalised_states(gen):
    assert np.isclose(np.linalg.norm(sv(PC._FN[gen](10, R())).data), 1)
