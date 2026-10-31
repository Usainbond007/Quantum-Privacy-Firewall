import numpy as np
import pytest
from fastapi.testclient import TestClient
from qpf import preflight as P
from backend.app.main import create_app


def test_grover_candidates_verified_and_exact_reader_recovers():
    r = P.grover_check("1010")
    assert r["summary"]["verified"] == r["summary"]["total"]
    assert r["summary"]["exact_recovery_rate"] == 1.0
    assert r["decision"]["status"] == "BLOCK"
    assert "marked" not in r["receipt"]
    assert "1010" not in r["receipt"].values()
    assert r["receipt"]["contains_predicate"] is False


def test_grover_pattern_reader_reads_original():
    assert P.pattern_reader(P.grover_circuit("1010")) == "1010"


def test_grover_rejects_bad_input():
    with pytest.raises(ValueError):
        P.grover_check("12")


def test_portfolio_weights_recovered_from_bindings():
    r = P.portfolio_check("balanced", "return_first")
    pr = r["direct"]["payload_attacker"]
    assert pr["correct"] and pr["residual"] < 1e-9
    assert r["direct"]["decision"]["status"] == "BLOCK"
    assert r["direct"]["rewrite"]["verification"] == "PASS"


def test_sweep_job_independent_of_preference():
    r = P.portfolio_check("risk_first", "return_first")
    assert r["sweep"]["identical"]
    assert r["sweep"]["jobs"] == 3


def test_market_data_checksum():
    assert P.load_market()[2].startswith("291b31d9")


def test_routes():
    c = TestClient(create_app())
    assert (
        c.post("/api/usecases/grover", json={"marked": "0110"}).json()["marked"]
        == "0110"
    )
    assert c.post("/api/usecases/grover", json={"marked": "abc"}).status_code == 422
    assert (
        c.post(
            "/api/usecases/portfolio",
            json={"preference": "balanced", "other": "balanced"},
        ).status_code
        == 422
    )
