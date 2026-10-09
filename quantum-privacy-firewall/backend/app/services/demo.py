"""Single-circuit workflow, independent of the dataset/retraining pipeline."""
from dataclasses import asdict
from pathlib import Path
import os
import time
import joblib
import numpy as np
import pandas as pd
from qiskit import qasm3
from qpf import circuits, compilation, defenses, features, selection, verification
from ..schemas import Candidate, DemoResult, RunRequest
from .serialization import serialize_circuit
from .verification import verify_compiled
from .accuracy import load_benchmarks, load_attacker, predict_attacker


def _scorer():
    # Only explicitly configured trusted local artifacts are deserialized.
    path = os.environ.get("QPF_SURROGATE_PATH")
    if path:
        model = joblib.load(Path(path))
        if getattr(model, "n_features_in_", None) != len(features.FEATURE_NAMES):
            raise ValueError("Surrogate feature count does not match the engine")
        return model, "frozen_surrogate_confidence", "Lower maximum family confidence is preferred. This is a single-circuit surrogate score, not a privacy guarantee."
    return None, "structural_feature_distance", "Higher mean absolute feature distance from baseline is preferred. No trained surrogate is configured; this score does not estimate privacy."


def run_demo(request: RunRequest, progress=lambda value, stage: None):
    start = time.perf_counter()
    model, method, note = _scorer()
    attacker_model, attacker_source, attacker_note = load_attacker()
    benchmarks = load_benchmarks()
    def assess(record):
        if attacker_model is not None and record.features is not None:
            try:
                record.attacker = predict_attacker(attacker_model, attacker_source, record.features, request)
            except Exception:
                # Inference errors must not be mislabeled as semantic or compile failures.
                record.attacker = None
    progress(0.03, "Generating input")
    logical = circuits.make_circuit(request.family, request.width, request.seed)
    progress(0.08, "Compiling baseline")
    baseline_tc, _ = compilation.compile_circuit(logical, request.optimization_level, request.transpile_seed, name=request.backend)
    baseline_metrics, baseline_features = features.analyze(baseline_tc)
    progress(0.14, "Verifying baseline compilation")
    baseline_verdict = verify_compiled(logical, baseline_tc)
    if baseline_verdict.status != "PASS":
        raise RuntimeError(f"Baseline compiled verification {baseline_verdict.status}: {baseline_verdict.note}")
    def score(values):
        vector = np.array([values[k] for k in features.FEATURE_NAMES], float)
        if model is not None:
            return float(model.predict_proba(vector.reshape(1, -1)).max())
        return float(np.abs(vector - np.array([baseline_features[k] for k in features.FEATURE_NAMES])).mean())
    baseline = Candidate(id="baseline", strategy="baseline", seed=request.transpile_seed,
        logical_verification=dict(status="PASS", method="identity", note="Original input"),
        compiled_verification=asdict(baseline_verdict), metrics=baseline_metrics, features=baseline_features,
        overheads={k: 0.0 for k in ("depth", "n2q", "active")}, score=score(baseline_features),
        circuit=serialize_circuit(baseline_tc, request.width), eligible=True)
    assess(baseline)
    alternatives, compiled_circuits = [], {}
    for i in range(request.candidates):
        strategy = request.strategies[i % len(request.strategies)]
        seed = (request.seed * 1000 + i + 1) % (2**31)
        progress(0.18 + 0.75 * i / request.candidates, f"Candidate {i + 1}/{request.candidates}: {strategy}")
        record = Candidate(id=f"candidate-{i + 1:02d}", strategy=strategy, seed=seed,
                           logical_verification=dict(status="UNKNOWN", method="not_run"),
                           compiled_verification=dict(status="UNKNOWN", method="not_run"))
        try:
            candidate, layout = defenses.apply_strategy(logical, strategy, seed, backend_name=request.backend)
            verdict = verification.verify(logical, candidate, operator_max_qubits=8)
            record.logical_verification = asdict(verdict)
            if verdict.status != "PASS":
                record.reason = f"Logical verification {verdict.status}"
            else:
                tc, _ = compilation.compile_circuit(candidate, request.optimization_level, request.transpile_seed, layout, request.backend)
                record.compiled_verification = asdict(verify_compiled(logical, tc))
                record.metrics, record.features = features.analyze(tc)
                record.circuit = serialize_circuit(tc, request.width)
                row = dict(base_id="demo", opt=request.optimization_level, strategy=strategy,
                           verify_status=record.compiled_verification.status, **record.metrics)
                df = selection.add_overheads(pd.DataFrame([row]), pd.DataFrame([dict(base_id="demo", opt=request.optimization_level, **baseline_metrics)]))
                record.overheads = {k: float(df.iloc[0]["d_" + k]) for k in ("depth", "n2q", "active")}
                # A layout-only wire relabel also counts as an observable change.
                record.changed = record.circuit.model_dump(exclude={"global_phase"}) != baseline.circuit.model_dump(exclude={"global_phase"})
                record.reason = selection.reject_reason(df.iloc[0], request.budget)
                if not record.changed and not record.reason:
                    record.reason = "Unchanged after compilation"
                record.eligible = not record.reason
                record.score = score(record.features)
                compiled_circuits[record.id] = tc
        except Exception as exc:
            record.eligible = False
            record.reason = f"Candidate error: {type(exc).__name__}: {str(exc)[:200]}"
        # Revalidate assignments and all evidence before returning the contract.
        assess(record)
        alternatives.append(Candidate.model_validate(record.model_dump()))
    progress(0.96, "Selecting verified candidate within budget")
    eligible = [c for c in alternatives if c.eligible]
    chosen = min(eligible, key=lambda c: (c.score if model is not None else -c.score,
                 max(0.0, *c.overheads.values()), c.id)) if eligible else None
    result = DemoResult(outcome="SELECTED" if chosen else "NO_CHANGED_CANDIDATE",
                        message="Verified changed candidate selected" if chosen else "No changed candidate within budget",
                        request=request, input=serialize_circuit(logical), baseline=baseline, selected=chosen,
                        alternatives=alternatives, scoring_method=method, scoring_note=note,
                        elapsed_seconds=time.perf_counter() - start, benchmarks=benchmarks, attacker_note=attacker_note)
    # An explicit no-change result exports the verified baseline as a fallback.
    selected_tc = compiled_circuits[chosen.id] if chosen else baseline_tc
    return result, qasm3.dumps(selected_tc)
