"""Dataset accuracy from saved predictions; per-circuit confidence is distinct."""
from pathlib import Path
import json
import os
import joblib
import numpy as np
import pandas as pd
from qpf import metrics, features
from ..schemas import AttackerPrediction, ResearchBenchmarks

ARTIFACTS = Path(__file__).resolve().parents[3] / "artifacts" / "quick"


def load_benchmarks(root=ARTIFACTS):
    root = Path(root)
    try:
        baseline = json.loads((root / "results/baseline.json").read_text())
        adaptive = json.loads((root / "results/adaptive.json").read_text())
        environment = json.loads((root / "manifests/environment.json").read_text())
        base_predictions = pd.read_csv(root / "predictions/baseline_predictions.csv")
        protected_predictions = pd.read_csv(root / "predictions/adaptive_predictions.csv")
        manifest = pd.read_csv(root / "manifests/dataset.csv")
        test_ids = set(manifest.loc[manifest.split == "test", "base_id"])
        original = base_predictions[(base_predictions.attacker == "rf_full") & (base_predictions.split == "test")]
        labels = baseline["full"]["labels"]
        def summarize(frame, saved=None):
            if frame.empty or not set(frame.base_id) <= test_ids:
                raise ValueError("Metrics require predictions on the frozen test circuits")
            computed = metrics.summarize(frame.y_true.to_numpy(), frame.y_pred.to_numpy(), labels)
            if saved and any(not np.isclose(computed[key], saved[key]) for key in ("accuracy", "balanced_accuracy", "macro_f1")):
                raise ValueError("Saved summary and prediction CSV disagree; rerun research evaluation")
            return computed
        controls = {}
        for name, attacker in (("shuffled", "rf_shuffled_labels"), ("metadata_only", "rf_metadata_only")):
            controls[name] = summarize(base_predictions[(base_predictions.attacker == attacker) & (base_predictions.split == "test")], baseline[name])
        budgets = []
        for budget, saved in adaptive["budgets"].items():
            rows = protected_predictions[np.isclose(protected_predictions.budget, float(budget))]
            budgets.append(dict(budget=float(budget), attackers={name: summarize(rows[rows.attacker == name], values) for name, values in saved["attackers"].items()},
                                adaptive_rf_macro_f1_ci95=saved["adaptive_rf_macro_f1_ci95"]))
        return ResearchBenchmarks(status="available",
            note="Saved quick-profile frozen-test evaluation recomputed from prediction CSVs.",
            backend=environment["backend"]["name"], widths=environment["config"]["dataset"]["widths"],
            optimization_levels=environment["config"]["backend"]["opt_levels"],
            test_rows=len(original), test_circuits=original.base_id.nunique(), chance=baseline["chance"],
            baseline=summarize(original, baseline["full"]), controls=controls, budgets=sorted(budgets, key=lambda b: b["budget"]),
            baseline_macro_f1_ci95=baseline["full_macro_f1_ci95"],
            metadata_confound_warning=baseline["exit_gate"]["metadata_confound_warning"],
            sources=["artifacts/quick/predictions/baseline_predictions.csv", "artifacts/quick/predictions/adaptive_predictions.csv",
                     "artifacts/quick/results/baseline.json", "artifacts/quick/results/adaptive.json"])
    except Exception as exc:
        return ResearchBenchmarks(status="unavailable", note=f"Saved benchmark unavailable: {type(exc).__name__}: {str(exc)[:200]}")


def load_attacker():
    configured = os.environ.get("QPF_SURROGATE_PATH")
    path = Path(configured) if configured else ARTIFACTS / "models/baseline_rf.joblib"
    try:
        model = joblib.load(path)  # Configured trusted file or bundled repository artifact only.
        if model.n_features_in_ != len(features.FEATURE_NAMES) or not hasattr(model, "classes_"):
            raise ValueError("Model is incompatible with the engine features")
        source = configured or "artifacts/quick/models/baseline_rf.joblib"
        return model, source, "Frozen attacker inference. Confidence is not accuracy; correct/incorrect describes only this circuit."
    except Exception as exc:
        return None, str(path), f"Attacker inference unavailable: {type(exc).__name__}: {str(exc)[:160]}"


def predict_attacker(model, source, values, request):
    vector = np.array([[values[name] for name in features.FEATURE_NAMES]], float)
    probabilities = np.asarray(model.predict_proba(vector)[0], float)
    if probabilities.shape != (len(model.classes_),) or not np.isfinite(probabilities).all():
        raise ValueError("Model returned invalid probabilities")
    distribution = {str(label): float(probability) for label, probability in zip(model.classes_, probabilities)}
    predicted = max(distribution, key=distribution.get)
    bundled = source == "artifacts/quick/models/baseline_rf.joblib"
    context = "Bundled attacker was trained on FakeNighthawk, widths 6/8 and optimization levels 0/2."
    if bundled and (request.backend != "FakeNighthawk" or request.width not in (6, 8) or request.optimization_level not in (0, 2)):
        context += " This run is outside that training context."
    if not bundled:
        context = "Configured model; training context is not recorded by this demo."
    if request.family not in distribution:
        context += " Input family is outside the classifier's classes."
    return AttackerPrediction(predicted_family=predicted, confidence=distribution[predicted], probabilities=distribution,
                              true_family_probability=distribution.get(request.family),
                              correct=predicted == request.family if request.family in distribution else None,
                              model_source=source, context_note=context)
