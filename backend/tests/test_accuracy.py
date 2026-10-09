import shutil
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient
from backend.app.main import create_app
from backend.app.schemas import RunRequest
from backend.app.services.accuracy import ARTIFACTS, load_benchmarks, load_attacker, predict_attacker
from backend.app.services.demo import run_demo
from backend.app.services.jobs import JobManager
from qpf.features import FEATURE_NAMES


def test_benchmark_metrics_and_endpoint_trace_to_frozen_predictions(tmp_path):
    with TestClient(create_app(JobManager(tmp_path))) as client:
        response = client.get("/api/benchmarks")
        assert response.status_code == 200
        data = response.json()
    assert data["status"] == "available"
    assert data["baseline"]["accuracy"] == .9375
    assert data["baseline"]["balanced_accuracy"] == .9375
    assert np.isclose(data["baseline"]["macro_f1"], .9365079365079365)
    assert data["test_rows"] == 16 and data["test_circuits"] == 8
    assert data["chance"] == .25
    assert [b["attackers"]["adaptive_rf"]["accuracy"] for b in data["budgets"]] == [.9375, .875, 1.0, .625]
    assert sum(map(sum, data["baseline"]["confusion"])) == data["test_rows"]
    assert data["metadata_confound_warning"]


def test_missing_benchmark_is_explicitly_unavailable(tmp_path):
    assert load_benchmarks(tmp_path).status == "unavailable"


def test_mismatched_csv_does_not_display_stale_summary_or_ci(tmp_path):
    for folder in ("results", "predictions", "manifests"):
        shutil.copytree(ARTIFACTS / folder, tmp_path / folder)
    path = tmp_path / "predictions/baseline_predictions.csv"
    rows = pd.read_csv(path)
    rows.loc[0, "y_pred"] = "grover"
    rows.to_csv(path, index=False)
    benchmark = load_benchmarks(tmp_path)
    assert benchmark.status == "unavailable" and "disagree" in benchmark.note


def test_model_predictions_are_distributions_not_accuracy(monkeypatch):
    monkeypatch.delenv("QPF_SURROGATE_PATH", raising=False)
    result, _ = run_demo(RunRequest(candidates=1))
    assert result.benchmarks.status == "available"
    prediction = result.baseline.attacker
    assert prediction is not None
    assert np.isclose(sum(prediction.probabilities.values()), 1)
    assert prediction.confidence == max(prediction.probabilities.values())
    assert prediction.correct == (prediction.predicted_family == result.request.family)
    assert "outside that training context" in prediction.context_note
    assert "accuracy" not in prediction.model_dump()


def test_random_control_has_no_correctness_score(monkeypatch):
    monkeypatch.delenv("QPF_SURROGATE_PATH", raising=False)
    model, source, _ = load_attacker()
    prediction = predict_attacker(model, source, dict.fromkeys(FEATURE_NAMES, 0), RunRequest(family="random"))
    assert prediction.correct is None and prediction.true_family_probability is None
    assert "outside the classifier" in prediction.context_note
