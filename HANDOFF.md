# HANDOFF — Quantum Privacy Firewall, paper-aligned extension

Written while two long experiments were still running. **Nothing below claims a running experiment has passed.**
Repo root = this folder (`work/`, a git repo; first snapshot commit `e482a8c`, later commits follow).

## 1. What this session built (on top of `QPF_IBM_Aligned_Research_Extension.zip`)
Goal: make the project a direct continuation of Buesser & Kurmus (QCE 2026), reusing the paper's protocol, then run the
defense (their Section V direction) against the paper's own attacker.

| Piece | File | Status |
|---|---|---|
| 47 Table I generators, 7 classes (our interpretation of the names) | `src/qpf/paper_circuits.py` | implemented, unit-tested |
| Table II ten features (+ "used-only" Gini sensitivity switch) | `src/qpf/paper_features.py` | implemented, unit-tested |
| Dataset builder: FakeNighthawk, 24/48 qubits, opt 0-3, 6 variants/generator | `src/qpf/paper_benchmark.py`, `scripts/build_paper_dataset.py` | **done** (2256 rows, 0 errors) |
| Source-disjoint splits, RF + 5-fold grouped CV grid search, Table III/IV-style transfer, controls, generator-disjoint check | `paper_benchmark.evaluate`, `scripts/run_paper_benchmark.py` | **RUNNING** (see §3) |
| Measured-vs-reported tables (paper numbers only in `config/paper_reference.json`) | `src/qpf/paper_compare.py` | implemented; report written when benchmark ends |
| Defense on the paper benchmark: verified rewrites, guided vs random selection, static/adaptive/normalization-aware attackers | `src/qpf/paper_defense.py`, `scripts/run_paper_defense.py` | **RUNNING** (see §3) |
| Verification hardening: exact status allowlist; sound DAG-identity fast path for reorder-only rewrites | `src/qpf/verification.py` | done, tested |
| Checkpoint/resume (added after the runs started) | `paper_benchmark.evaluate`, `paper_defense.build_candidates` / norm cache | smoke-tested; **not active in the two running processes** |

Unchanged from the previous version: legacy 4-family/13-feature research code, `artifacts/quick/*`, FastAPI + React demo.

## 2. Testing status (this container: Linux, Python 3.13.16, qiskit 2.5.2, qiskit-ibm-runtime 0.50.0, mqt-qcec 3.11.0)
- `pytest tests backend/tests` → **127 passed** (run after the final code edits, with the long runs active).
- Frontend: `npm ci`, `npx vitest run` → 8 passed, `npm run build` → OK (run before the checkpoint edits, which do not touch the frontend).
- Generator semantics verified by test: Cuccaro ripple adder, incrementer (+1), comparator (carry written, inputs restored), W-state ladder. Other generators are only tested for exact width, determinism, non-empty — **their circuit semantics are not otherwise verified**.
- NOT tested: legacy `reproduce_all.py --profile full`; the Windows/Python 3.14 environment named in the README; 48-qubit exact equivalence checking (never attempted).

## 3. Currently running (started ~19:41 container clock; check with `ps aux | grep run_paper_`)
1. **Benchmark** — PID 2506, `python3 run_paper_benchmark.py --profile full`, log `../full_bench.log` (snapshot in `logs/full_bench.snapshot.log`).
   Stage 1 (Table II features, 5 splits) finished; stage 2 (Gini-used sensitivity) was at split 0 of 5 when this was written.
   It runs the OLD code: **no per-split checkpoints, results are written only at the very end** to
   `artifacts/paper_full/results/paper_benchmark.json` + `paper_comparison.md`. If it dies, all of it is recomputed (about 3-4 min per split, 5 splits per stage).
2. **Defense** — PIDs 2508/5236, `python3 run_paper_defense.py --profile full --workers 1`, log `../full_def.log`.
   Candidate stage finished and `artifacts/paper_full/defense/candidates.csv` is saved (1692 candidates x 3 opt levels).
   It is now computing normalization-aware features for 4359 circuits (kept only in memory by the old code), then evaluates 5 splits and writes
   `artifacts/paper_full/results/paper_defense.json` + `defense_summary.md`.

Do not restart either unless it has died. Wait for the processes to exit, then copy `../full_*.log` into `logs/` and commit `artifacts/paper_full/`.

## 4. Exact commands to resume (run from `scripts/`, `pip install -r requirements.txt` first)
```bash
cd scripts
# dataset (resumes by (generator,variant,size,opt); safe to re-run)
python3 build_paper_dataset.py --profile full --workers 2
# benchmark (new code resumes per split from artifacts/paper_full/results/partial/*.json)
python3 run_paper_benchmark.py --profile full
# defense (new code skips candidates already in defense/candidates.csv and reuses defense/norm_features.csv if present)
python3 run_paper_defense.py --profile full --workers 2
# cheap end-to-end check of everything (~3 min total)
python3 build_paper_dataset.py --profile smoke && python3 run_paper_benchmark.py --profile smoke && python3 run_paper_defense.py --profile smoke --workers 1
# tests
cd .. && python3 -m pytest -q tests backend/tests
```
Resume limits: the defense **evaluation** (5 splits x 4 budgets x 2 arms) has no per-split checkpoint; it restarts from the cached candidates/norm features (minutes, not hours).
Until the old processes finish, `norm_features.csv` does not exist, so a restart would recompute it (~tens of minutes).

## 5. Seeds and configuration (all in `config/paper.yaml`)
`seed: 7` (splits), `transpile_seed: 11`, generator rng `[2026, generator_index, variant, n]`, candidate seeds `(gen_idx*100+variant)*1000+k+1`,
`variants: 6`, `test_variants: 2`, `n_splits: 5`, `cv_folds: 5`, RF grid in the file, defense: 24 qubits, opt levels [0,2,3], strategies
[layout, decomp, reorder, decomp+reorder, decomp+layout, reorder+layout], budgets [0, 0.1, 0.2, 0.5], QCEC timeout 30 s.
Dataset hash (sha256, first 16): `a3d5f34bf93ab32f` (`artifacts/paper_full/features/dataset.csv`). Environment: `logs/environment.txt`.

## 6. INVALIDATED results (do not use)
Two generator bugs were found by semantic tests after the first runs had started:
- `incrementer`: ancilla qubits were randomly set to |1> (not a valid +1 circuit).
- `comparator`: carry uncompute used MAJ instead of its exact inverse (inputs not restored).

Invalidated and already removed/regenerated:
- the 96 dataset rows of `incrementer` and `comparator` (regenerated; the other 45 generators are unaffected because every generator has its own rng stream);
- the first full benchmark and defense runs (killed; they used the buggy rows; their outputs were never saved);
- `artifacts/paper_smoke/*` produced before the fix, and `logs/STALE_smoke_defense_pre_fix.log`. Pre-fix smoke figures quoted in chat (e.g. pooled accuracy 0.904, defense F1 0.906 → 0.826) are **invalid**;
- the original `full_bench.log` / `full_def.log` of those killed runs were overwritten by the relaunch.
Also: an earlier chat message said "49 generators"; the correct number is **47** (7+7+7+6+7+6+7), as asserted in code.
The `verification.py` DAG fast path was added after the first (killed) smoke defense run; verification results from before it are not reused.

## 7. Unfinished / honest limitations
- Both full runs above: results do not exist yet. No claim about reproduction quality or defense effect is supported until `paper_comparison.md` and `defense_summary.md` exist and are read.
- Generators, feature conventions (phase-gate set, layer scheduling, entropy not normalized, Gini over all edges/qubits incl. idle) and dataset size are OUR interpretation; the paper publishes none of them. Unresolved questions are in `docs/BEAT_RESEARCH_NOTE.md`.
- Defense is evaluated at 24 qubits only; it verifies the logical rewrite (QCEC / DAG identity / identical circuit), not the compiled physical circuit (trusts the Qiskit transpiler). 48-qubit verification not attempted.
- Table III/IV in our pipeline pool sizes (Table III) and optimization levels (Table IV); the paper does not say how it pooled.
- README and `docs/*.md` still describe the previous state ("abstract only", "still required"); they must be rewritten once results exist (§8).
- Legacy `artifacts/quick` results (adaptive RF 1.000 at 20% budget, CI 0.58-1.00, metadata confound warning) are unchanged and still weak.

## 8. Remaining to-do, in order
1. Wait for both processes; verify each exits 0 and the result files exist; copy logs to `logs/`; commit `artifacts/paper_full/`.
2. Read `artifacts/paper_full/results/paper_comparison.md` and `defense_summary.md`; write the numbers (not adjectives) into the README.
3. Rewrite README intro (cite the full paper, remove "abstract only"), `docs/IBM_SHORT_PAPER_ALIGNMENT.md`, `docs/BEAT_RESEARCH_NOTE.md` to match what actually ran.
4. Re-run `pytest tests backend/tests`, `npm run build`; delete `__pycache__`, `frontend/node_modules`, `frontend/dist` before zipping.
5. Optional: per-split checkpoint for the defense evaluation; repeat with more variants or additional backends.
