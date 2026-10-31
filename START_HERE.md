# Quantum Privacy Firewall — Research Desk

This release implements the selected light Research Desk design in the supplied React/FastAPI project. Start with Confidential Cryptanalysis, then Portfolio Optimization. Circuit Lab preserves the original experiment and its integrations. Research & evidence separates saved family-level results from new live domain results.

## Fastest start: one server, prebuilt frontend

Use Python 3.12 (tested) and a fresh environment. No IBM account, API key, GPU or hardware access is needed. The public market snapshot is bundled; experiments need no live market download.

### Windows PowerShell

Open PowerShell in the extracted project folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-demo.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

### macOS / Linux

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-demo.txt
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` in your browser. Keep that terminal running. The included `frontend/dist` is the built React application, served by FastAPI. API documentation: `http://127.0.0.1:8000/docs`.

Run a single Uvicorn process. Existing workbench jobs use the original in-memory store. This is a local research demonstration, not an authenticated production service.

## Frontend development

Node 22.12+ or 24 is recommended (Node 24 was tested). Keep the backend above running. In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open the address Vite prints (normally `http://127.0.0.1:5173`). The Vite proxy now consistently targets port **8000**, including API documentation. It no longer targets the old ZIP's port 8567.

To rebuild the one-server version:

```bash
cd frontend
npm run build
```

Refresh the FastAPI-served page after building. If the dist folder did not exist when FastAPI started, restart FastAPI once. Hash routes (`#cryptanalysis`, `#portfolio`, `#lab`, `#research`) work without server rewrite rules.

## What actually runs

- **Cryptanalysis:** four-qubit, single-marked-state Grover circuit; three amplification iterations; 12 decomposition/reordering candidates; pattern reader and exact statevector reader on logical circuits; unitary equivalence and layout-aware compiled checks; compiled depth/two-qubit overhead; exact distribution distance; backend BLOCK/WARN assessment. No UI fabricates observations.
- **Portfolio:** eight bundled public assets, four held; private synthetic risk/return weights; fixed-angle cost and XY-mixer construction; actual least-squares reconstruction of original bindings; bound-circuit rewrite, logical/compiled verification and resource overhead; three-setting public sweep; exact candidate selection and exhaustive 70-portfolio classical comparator; SHA-256 comparison of the logical template and public bindings. Direct disclosure produces BLOCK; the scoped public-sweep alternative produces WARN when compiled checks pass.
- **Original lab:** preset generation, asynchronous runs, polling, candidate inspection, frozen family predictions, saved benchmarks and exports remain available.

No quantum cloud job is submitted. BLOCK is a local assessment, not enforcement on an external service. RELEASE is defined in the policy but is not falsely issued by these demonstrations.

## Important corrections and scope

The uploaded portfolio circuit applied its cost phase to a single basis state, so weights could not influence output probabilities. This release adds fixed number-conserving XY preparation **before** the cost layer, followed by XY mixing. Tests verify preference sensitivity and four-asset feasibility. This is still a simplified, fixed-angle QAOA-style ansatz—not a variationally trained optimizer or a full reproduction of IBM's multi-objective tutorial.

The use-case attacks inspect logical circuit artifacts/bindings. Compiled equivalence is tested separately. Recovery from compiled payloads and post-rewrite portfolio bindings is not claimed. Noise, hardware utility, general confidentiality, production banking and quantum advantage are not established.

Structural and fixed-sweep `1/3` baselines are analytical under uniform priors, not measured ML accuracy. The UI explicitly distinguishes these from actual weight reconstruction. Fixed-sweep hashes include the logical template and full bindings, not transport metadata, timing, credentials or Runtime job envelopes.

All inputs go to the local FastAPI process. Do not describe them as browser-only. Shareable receipts omit explicit marked strings and weights, but circuit fingerprints are not secret-hiding commitments and tiny domains can be enumerated.

## Validation

```bash
# repository root, activated environment or substitute its python path
python -m pytest -q tests backend/tests
cd frontend
npm test
npm run build
```

This release passed 180 Python tests and 17 frontend tests, plus a production build and live HTTP checks of both use-case endpoints, the options/benchmark endpoints and the served frontend. Frontend tests use recorded live-backend responses as fixtures; production never imports those fixtures. Tests cover previous lab behavior, both new case flows, edited-input invalidation, failure states, all 16 toy targets, meaningful portfolio interference, feasibility, hash coverage and fail-closed compiled UNKNOWN.

Rendered browser visual QA remains pending: the environment's automatic approval review rejected opening the cloud browser because browser selection was not explicitly authorized. Functional DOM tests and build checks are complete; they are not a substitute for screenshot-based visual inspection. See `design-qa.md`.

## Troubleshooting

- API unavailable: start FastAPI on 8000 and click Retry in the header. Vite alone cannot compute experiments.
- Install failures: use a fresh Python 3.12 environment and `requirements-demo.txt`. The original general requirements and older lock are retained for research provenance; the demo requirements match the bundled classifier's scikit-learn version.
- First run: fake backend initialization may take longer. The UI displays elapsed time and errors rather than fake progress percentages.
- Re-entered inputs: evidence remains labeled as belonging to the previous run until a new assessment succeeds.
- Compiled UNKNOWN: the exact verifier has a 10-active-wire bound; UNKNOWN is not PASS. The live use cases here stay small, but changed compilation behavior can exceed the bound.

For a presentation sequence and defensible novelty wording, read `JUDGE_DEMO.md`.
