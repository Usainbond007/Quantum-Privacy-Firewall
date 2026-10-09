import numpy as np, pytest
from qiskit.quantum_info import Statevector
from qpf import paper_circuits as PC

def test_table1_structure():
    assert PC.CLASS_LABELS == ["entanglement_generation", "fourier_like", "phase_oracle_like", "amplitude_amplification",
                               "variational_ansatz", "hamiltonian_simulation", "arithmetic_permutation"]
    assert [len(v) for v in PC.CLASSES.values()] == [7, 7, 7, 6, 7, 6, 7] and len(PC.GENERATORS) == 47

@pytest.mark.parametrize("gen", list(PC.GENERATORS))
def test_every_generator_builds_with_exact_width_and_is_deterministic(gen):
    for v in (0, 1):
        a, b = PC.make_source(gen, 12, v), PC.make_source(gen, 12, v)
        assert a.num_qubits == 12 and a.size() > 0 and a.num_clbits == 0
        assert [(i.operation.name, [a.find_bit(q).index for q in i.qubits]) for i in a.data] == \
               [(i.operation.name, [b.find_bit(q).index for q in i.qubits]) for i in b.data]

def test_variants_differ_and_source_id_is_size_independent():
    assert PC.source_id("ghz", 3) == "ghz-v3"
    a, b = PC.make_source("hea_linear", 12, 0), PC.make_source("hea_linear", 12, 2)
    assert [i.operation.params for i in a.data] != [i.operation.params for i in b.data]

def _out_bits(qc, x_prep_seed, n):
    sv = Statevector(qc).probabilities(); idx = int(np.argmax(sv)); assert sv[idx] > 0.999   # classical reversible circuit
    return [(idx >> i) & 1 for i in range(n)]

def test_incrementer_adds_one():
    n = 8; m = n // 2
    for seed in range(6):
        bits = PC._bits(np.random.default_rng(seed), n); qc = PC.incrementer(n, np.random.default_rng(seed))
        out = _out_bits(qc, seed, n); x = sum(bits[i] << i for i in range(m)); y = sum(out[i] << i for i in range(m))
        assert y == (x + 1) % (1 << m)

def test_ripple_adder_adds():
    n = 8; k = 3
    for seed in range(6):
        bits = PC._bits(np.random.default_rng(seed), n); qc = PC.ripple_adder(n, np.random.default_rng(seed)); out = _out_bits(qc, seed, n)
        cin, a, b = bits[0], sum(bits[1 + i] << i for i in range(k)), sum(bits[1 + k + i] << i for i in range(k))
        total = a + b + cin; got_b = sum(out[1 + k + i] << i for i in range(k))
        assert got_b == total % (1 << k) and out[2 * k + 1] == (bits[2 * k + 1] ^ (total >> k))

def test_comparator_writes_carry_and_restores_inputs():
    n = 8; k = 3
    for seed in range(8):
        bits = PC._bits(np.random.default_rng(seed), n); out = _out_bits(PC.comparator(n, np.random.default_rng(seed)), seed, n)
        cin, a, b = bits[0], sum(bits[1 + i] << i for i in range(k)), sum(bits[1 + k + i] << i for i in range(k))
        assert out[:2 * k + 1] == bits[:2 * k + 1]                     # inputs restored
        assert out[n - 1] == (bits[n - 1] ^ int(a + cin > b))        # carry of a + ~b + cin

def test_w_state_ladder_is_a_w_state():
    n = 6; p = Statevector(PC.w_state_ladder(n, np.random.default_rng(0))).probabilities()
    assert np.allclose([p[1 << i] for i in range(n)], 1 / n, atol=1e-9)
