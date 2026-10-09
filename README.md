# Quantum Privacy Firewall

Experimental, Qiskit-based **pre-submission circuit privacy audit** (Q-Hack India 2026).
It measures how well an observer who sees only the final backend-compiled circuit can guess the *algorithm family*, then tests
semantics-preserving rewrites under overhead budgets. It is **not** encryption and **not** proven obfuscation.

Independent, IBM-inspired study. Inspiration: IBM Research, *Algorithmic Intent Leakage in Transpiled Quantum Circuits: An Initial Reverse-Engineering Study*
(abstract only; no public code found). Families, features, defenses and code here are our own.

## Problem overview
A transpiler rewrites a program into the chip's native gates and wiring. That compiled circuit is what a cloud provider can observe, and its
structure can hint at what the program is for. This repo (1) quantifies that leakage, (2) generates verified rewrites, (3) checks whether a
**retrained** attacker still recovers the family, and (4) reports the privacy/overhead trade-off, including negative outcomes.

## Architecture (data flow)
```
logical circuit -> base_id (grouped 60/20/20 split) -> compile baseline (FakeNighthawk, opt levels) -> physical features
   -> baseline attacker (RF + controls)            -> candidates: layout / decomp / reorder (+ combinations)
   -> verify (Operator.equiv <=10 qubits, MQT QCEC above; UNKNOWN never PASS) -> compile each -> budget check (depth, 2Q gates, active qubits)
   -> label-free selection by a frozen surrogate (trained on train split only) -> retrain attackers on protected train groups
   -> evaluate once on the frozen protected test split -> report + release gate
```
Layout: `config/*.yaml`, `src/qpf/{circuits,compilation,features,verification,defenses,attacks,metrics,selection,pipeline,report}.py`,
`scripts/{build_dataset,train_baseline,run_defense,evaluate_adaptive,reproduce_all}.py`, `tests/`, `notebooks/demo.ipynb`, `artifacts/<profile>/`.

## Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
pytest -q                                   # 31 tests: splits, features, equivalence (incl. wrong circuits must FAIL), budgets, reproducibility
```

## Run
```bash
cd scripts
python reproduce_all.py --profile smoke     # ~30 s on 1 core   (tiny; for a pipeline check only)
python reproduce_all.py --profile quick     # ~2.5 min on 1 core (what the notebook and results below use)
python reproduce_all.py --profile full      # larger dataset (widths 6/8/10, 10 bases/cell, 4 opt levels); NOT completed in our 1-core sandbox, use --workers N
```
Step by step: `build_dataset.py` -> `train_baseline.py` -> `run_defense.py` -> `evaluate_adaptive.py` (each takes `--profile`, `--workers`).
`reproduce_all.py` exits non-zero if the release gate fails.

## Demo
`jupyter lab notebooks/demo.ipynb` (loads saved artifacts; set `RERUN = True` to recompute live). Terminal demo: `python scripts/reproduce_all.py --profile quick`.

### Interactive circuit lab

The web demo runs a **single selected circuit**, independently of `src/qpf/pipeline.py`.
It uses React, TypeScript, Vite and Tailwind with FastAPI and one bounded background worker.
The UI offers an SVG circuit viewer with zoom, gate parameter inspection, physical layout mappings,
baseline/selected comparisons, budget metrics, per-candidate verification evidence and downloads.

From the repository root, install Python dependencies and start the API:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r backend/requirements.txt
.venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal (Node.js 22.12+):

```powershell
cd frontend
npm ci
npm run dev
```

Open **http://localhost:5173**. Vite proxies `/api` to port 8000. For a single-server demo,
run `npm run build` inside `frontend`, then start or restart FastAPI and open
**http://127.0.0.1:8000**. The backend serves the generated `frontend/dist` bundle.
API documentation is at **http://127.0.0.1:8000/docs**.
On macOS/Linux, use `.venv/bin/python` in place of `.venv\Scripts\python`.
If Windows reserves port 8000, run the single-server demo with `--port 8765` and open
**http://127.0.0.1:8765** instead. Development mode requires updating the Vite proxy to the same API port.
`backend/requirements-lock.txt` records the validated Python 3.14 / Windows environment;
`frontend/package-lock.json` locks the frontend dependencies for `npm ci`.

The main integration is `backend/app/services/demo.py`:

1. Generate the requested logical circuit; compile and verify its baseline.
2. Generate seeded transformations using the existing defense functions.
3. Require logical equivalence `PASS` before compiling a candidate.
4. Verify each compiled circuit against the original logical computation, accounting for initial/final layouts and clean ancillas.
5. Calculate the existing physical metrics/features and enforce the existing budget rules for depth, two-qubit count and active wires.
6. Select a changed candidate with both checks `PASS`; retain every alternative and rejection reason.

The exact compiled check compares **all logical basis inputs** up to global phase. It compacts idle
hardware wires and checks the full clean-ancilla isometry on at most **10 active physical wires**.
Unsupported operations, missing layouts and larger active circuits return **UNKNOWN**; they never qualify
as verified candidates. A non-PASS baseline check fails the run with checker details.
The demo accepts widths **4–8** (the QAOA generator requires at least four for even widths),
**1–24 candidates**, optimization levels **0–3**, budgets **0–100%**, and allowlisted fake IBM backends.
Layout transformations use the user-selected backend.

If no changed candidate qualifies, the outcome is `NO_CHANGED_CANDIDATE`, with the explicit message
**“No changed candidate within budget”**, no selected candidate, and a verified baseline QASM export.
Changes are detected from compiled gates and physical wiring/layout; a global-phase-only difference
does not qualify. Candidate orderings that survive compilation count as observable changes.

By default selection maximizes the mean absolute distance across the existing 13 structural features,
then prefers lower maximum overhead and stable candidate ID. This is a descriptive score, **not a privacy estimate**.
To use a compatible frozen classifier, set `QPF_SURROGATE_PATH` to a **trusted local** joblib model trained
with `qpf.features.FEATURE_NAMES` in that order; selection then minimizes maximum family confidence.
No model is trained during a run, and family labels are never used for ranking. Single-circuit confidence
does not replace the research pipeline's adaptive attacker evaluation.

The **Attacker accuracy & leakage** panel is available before a demo run. Its baseline/protected
accuracy, balanced accuracy, macro-F1, per-family recall, confusion matrices, controls and saved
95% macro-F1 intervals come from the existing quick-profile frozen test dataset (8 distinct
circuits, 16 compiled rows). Select a research budget and attacker to inspect the measured
trade-off. Metrics are recomputed from the saved prediction CSVs and checked against their
summary JSON; missing or inconsistent artifacts show an explicit unavailable state.
These are archived dataset results, not accuracy measured from the current single circuit.

For each new run, the bundled frozen `artifacts/quick/models/baseline_rf.joblib` also predicts
the family of baseline and candidate circuits. The UI shows the predicted family, confidence,
full probability distribution and correct/incorrect result. These inference results do not
change the default structural selection method. `QPF_SURROGATE_PATH` overrides this attacker
as well as enabling confidence-based selection. Training context is shown explicitly; the
bundled model was trained on FakeNighthawk, widths 6/8 and optimization levels 0/2. The random
control is outside its family classes, so correctness is not scored. Confidence is not accuracy.
Every metrics export includes its benchmark snapshot and per-circuit attacker predictions.

| Endpoint | Behavior |
| --- | --- |
| `GET /api/options` | Available families, backends, strategies and limits |
| `GET /api/benchmarks` | Saved frozen-test accuracy, balanced accuracy, macro-F1, confusion matrices, controls and budget comparisons |
| `POST /api/circuits/preview` | Logical circuit JSON |
| `POST /api/runs` | HTTP 202 with a run ID; HTTP 429 when the queue is full |
| `GET /api/runs/{id}` | Queued/running/completed/failed state, progress, results and errors |
| `GET /api/runs/{id}/exports/qasm` | Selected transpiled OpenQASM 3 (baseline fallback when none qualifies) |
| `GET /api/runs/{id}/exports/metrics` | Request, circuits, metrics, all candidates and verification evidence as JSON |

Example run request:

```json
{
  "family": "graph_ghz", "width": 4, "seed": 21,
  "backend": "FakeNighthawk", "optimization_level": 2, "transpile_seed": 11,
  "candidates": 6, "budget": 0.2,
  "strategies": ["layout", "decomp+layout", "decomp+reorder"]
}
```

Circuit JSON contains `num_qubits`, `logical_width`, visible physical `qubits`, `gates`
(name, wire indices, parameters, classical bits and layer), `global_phase`, `depth`, `size`,
and initial/final logical-to-physical `layout` mappings. Idle hardware wires are omitted from
the displayed wire list while their original indices remain intact.

Run files are saved in gitignored `runtime/<uuid>/`. One running job plus three queued jobs are
admitted; the oldest terminal runs are evicted when the retained run count reaches 50.
Snapshots and completed exports survive restart; interrupted jobs become failed with a restart explanation.
Use **one Uvicorn process**; do not use multiple `--workers` with this local job store.
`QPF_RUNTIME_DIR` overrides storage, and `QPF_CORS_ORIGINS` sets comma-separated frontend origins.
This is a local demo, without authentication or a distributed job queue.

Validation:

```powershell
.venv\Scripts\python -m pytest -q
cd frontend
npm test
npm run build
```

## Measured results (profile `quick`, 1 run; generated by `scripts/make_results_md.py`, not hand-typed)
```
BASELINE (frozen test split, K=4 classes, chance=0.25)
  full-feature RF macro-F1 = 0.937  CI95 0.580-1.000
  shuffled-label control  = 0.409   metadata-only control = 0.874
  exit gate passed = True   metadata confound warning = True
PROTECTED (adaptive attackers retrained on protected training groups; frozen test split)
  budget | adaptive RF | logreg | gboost | norm-aware | d.depth | d.2Q | protected%
      0% |       0.937 |  0.817 |  0.937 |      0.782 |     -2.0% |  -4.0% |     24%
     10% |       0.874 |  0.874 |  0.806 |      0.718 |     -1.8% |  -3.3% |     61%
     20% |       1.000 |  0.816 |  0.813 |      0.879 |     -1.1% |  -3.9% |     70%
     50% |       0.626 |  0.679 |  0.441 |      0.873 |      3.7% |  -1.4% |     86%
```
Reading (all from the artifacts): the baseline classifier beats the shuffled-label control, but the **metadata-only control is nearly as good**
(confound warning = True), so a large part of the measured "leakage" in this small dataset may be circuit size/complexity rather than algorithmic structure.
Test sets are small (4 circuits per class), confidence intervals are wide, and the protected results are mixed: no budget shows a clear, robust drop across
all retrained attackers (the normalization-aware attacker recovers at 50%). **We therefore do not claim privacy protection.** If this holds at larger scale,
the deliverable is the *Quantum Circuit Leakage Auditor* (baseline audit) from the plan's fallback. `reorder` rewrites never survive compilation (survival 0.00 in `defense.json`).

## Validity rules enforced in code
Grouped splits by `base_id`; selection never reads labels (surrogate trained on train split only, checked by the release gate); attackers are retrained on
protected data; controls (chance, shuffled labels, metadata-only); all selected circuits verified PASS; every reported number is recomputed from saved predictions
(`release_gate.json`). FakeNighthawk is a fake-backend snapshot, not live hardware. Operator/QCEC equivalence is checked on the *logical* circuit; compilation is trusted Qiskit.

## Limitations
Small controlled dataset; our own 4 families and 13 features (the IBM poster's exact definitions are not public); no hardware runs; no formal privacy guarantee.
