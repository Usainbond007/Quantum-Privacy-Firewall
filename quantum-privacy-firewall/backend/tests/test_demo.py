import pytest
from qpf.verification import Verdict
from backend.app.schemas import RunRequest
from backend.app.services import demo


@pytest.mark.parametrize("family", ["qft", "grover", "qaoa", "graph_ghz", "random"])
def test_real_workflow(family, monkeypatch):
    monkeypatch.delenv("QPF_SURROGATE_PATH", raising=False)
    result, qasm = demo.run_demo(RunRequest(family=family, candidates=2, strategies=["decomp+layout"], budget=.5))
    assert result.baseline.compiled_verification.status == "PASS"
    assert len(result.alternatives) == 2
    assert qasm.startswith("OPENQASM 3.0;")
    assert result.scoring_method == "structural_feature_distance"
    for c in result.alternatives:
        if c.eligible:
            assert c.changed
            assert c.logical_verification.status == c.compiled_verification.status == "PASS"
            assert max(c.overheads.values()) <= .5 + 1e-12
    if result.selected:
        assert result.selected.eligible


def test_unchanged_has_explicit_no_candidate_result(monkeypatch):
    monkeypatch.setattr(demo.defenses, "apply_strategy", lambda base, *args, **kwargs: (base, None))
    result, _ = demo.run_demo(RunRequest(candidates=2))
    assert result.outcome == "NO_CHANGED_CANDIDATE"
    assert result.message == "No changed candidate within budget"
    assert result.selected is None
    assert all(not c.changed and c.reason == "Unchanged after compilation" for c in result.alternatives)


@pytest.mark.parametrize("status", ["FAIL", "UNKNOWN"])
def test_compiled_nonpass_never_selected(monkeypatch, status):
    original = demo.verify_compiled
    calls = 0
    def checker(logical, compiled):
        nonlocal calls
        calls += 1
        return original(logical, compiled) if calls == 1 else Verdict(status, "test", "no proof")
    monkeypatch.setattr(demo, "verify_compiled", checker)
    result, _ = demo.run_demo(RunRequest(candidates=2, budget=1))
    assert result.selected is None
    assert all(not c.eligible and c.compiled_verification.status == status for c in result.alternatives)


def test_candidate_errors_are_evidence_not_lost_runs(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("deliberate transformation failure")
    monkeypatch.setattr(demo.defenses, "apply_strategy", fail)
    result, _ = demo.run_demo(RunRequest(candidates=1))
    assert result.selected is None
    assert "deliberate transformation failure" in result.alternatives[0].reason
    assert result.alternatives[0].compiled_verification.status == "UNKNOWN"


def test_requested_backend_is_used_for_layout(monkeypatch):
    original = demo.defenses.compilation.random_connected_layout
    names = []
    def layout(n, rng, name):
        names.append(name)
        return original(n, rng, name=name)
    monkeypatch.setattr(demo.defenses.compilation, "random_connected_layout", layout)
    demo.run_demo(RunRequest(backend="FakeSherbrooke", candidates=1, strategies=["layout"]))
    assert names == ["FakeSherbrooke"]


def test_repeatable_selection_and_seeded_circuits(monkeypatch):
    monkeypatch.delenv("QPF_SURROGATE_PATH", raising=False)
    request = RunRequest(candidates=3)
    first, first_qasm = demo.run_demo(request)
    second, second_qasm = demo.run_demo(request)
    assert first.outcome == second.outcome
    assert first.selected == second.selected
    assert first.alternatives == second.alternatives
    assert first_qasm == second_qasm


def test_surrogate_receives_features_without_family_labels(monkeypatch):
    import numpy as np
    class Surrogate:
        calls = 0
        def predict_proba(self, values):
            assert values.shape == (1, 13)
            assert np.isfinite(values).all()
            self.calls += 1
            return np.array([[.4, .3, .2, .1]])
    model = Surrogate()
    monkeypatch.setattr(demo, "_scorer", lambda: (model, "frozen_surrogate_confidence", "Test frozen surrogate"))
    result, _ = demo.run_demo(RunRequest(candidates=3, budget=1))
    assert result.scoring_method == "frozen_surrogate_confidence"
    assert model.calls == 4
    assert result.selected.score == .4
