"""Security/correctness regressions for the enhanced, bounded demonstrations."""

import numpy as np
from qiskit.quantum_info import Statevector
from qpf import preflight as p


def test_all_toy_predicates_recovered_and_bit_order_is_consistent():
    for i in range(16):
        marked = format(i, "04b")
        guess, prob = p.exact_reader(p.grover_circuit(marked))
        assert guess == marked
        assert prob > 0.96
        assert p.pattern_reader(p.grover_circuit(marked)) == marked


def test_portfolio_cost_actually_changes_probabilities_and_preserves_budget():
    mu, sigma, _ = p.load_market()
    tpl, params = p.portfolio_template()
    distributions = []
    for w in p.PREFERENCES.values():
        qc = p._bind(tpl, params, p.bindings_for(w, mu, sigma))
        prob = Statevector(qc).probabilities()
        assert np.isclose(sum(v for i, v in enumerate(prob) if i.bit_count() == p.K), 1)
        distributions.append(prob)
    assert np.abs(distributions[0] - distributions[-1]).sum() / 2 > 0.01


def test_hash_covers_numeric_and_symbolic_parameters():
    mu, sigma, _ = p.load_market()
    tpl, params = p.portfolio_template()
    a = p._bind(tpl, params, p.bindings_for(p.PREFERENCES["risk_first"], mu, sigma))
    b = p._bind(tpl, params, p.bindings_for(p.PREFERENCES["return_first"], mu, sigma))
    assert len(p._circuit_hash(a)) == 64
    assert p._circuit_hash(a) != p._circuit_hash(b)
    assert p._circuit_hash(a) != p._circuit_hash(tpl)


def test_unknown_compiled_verification_blocks_selection(monkeypatch):
    monkeypatch.setattr(
        p,
        "_evidence",
        lambda *args: dict(status="UNKNOWN", method="test", note="unsupported"),
    )
    r = p.grover_check("0101", seeds=(1,))
    assert r["selected"] is None
    assert r["decision"]["status"] == "BLOCK"


def test_selected_candidate_and_utility_evidence():
    r = p.grover_check("0110", seeds=(1,))
    chosen = next(c for c in r["candidates"] if c["id"] == r["selected"])
    assert chosen["verification"] == chosen["compiled_verification"]["status"] == "PASS"
    assert chosen["within_budget"]
    assert chosen["total_variation"] < 1e-10
    assert r["decision"]["status"] == "BLOCK"


def test_sweep_fixed_for_all_pairs_and_regret_is_nonnegative():
    results = [
        p.portfolio_check(a, b)
        for a, b in [("risk_first", "balanced"), ("balanced", "return_first")]
    ]
    assert results[0]["sweep"]["job_hash_a"] == results[1]["sweep"]["job_hash_b"]
    for r in results:
        assert r["sweep"]["identical"]
        assert r["sweep"]["decision"]["status"] == "WARN"
        assert r["direct"]["payload_attacker"]["residual"] < 1e-9
        for choice in r["sweep"]["picks"].values():
            assert len(choice["tickers"]) == p.K
            assert choice["regret_vs_best"] >= -1e-10
