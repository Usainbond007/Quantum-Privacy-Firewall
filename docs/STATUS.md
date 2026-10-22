# Project status

All benchmark and defense runs are complete. Date of the last full run: 2026-10-10.

## Verified
- `python -m pytest -q tests backend/tests`: 167 tests (generator semantics, splits, features, budgets, equivalence checks including wrong circuits and the DAG shortcut, backend API).
- Frontend: `npm ci`, `npx vitest run`, `npm run build` (8 tests).
- Benchmark outputs: `artifacts/paper_full/results/paper_benchmark.json`, `paper_comparison.{md,csv,json}`. Defense outputs: `paper_defense.json`, `defense_summary.{md,csv}`. Both use 5 repeated splits.
- Generator audit: `docs/GENERATOR_AUDIT.md` (24 semantic / 20 structural / 3 analogue of 47).

## Superseded results
Rows and runs produced before the fixes to `incrementer`, `comparator` and `parity_amplitude_amplification` were discarded and regenerated. `artifacts/paper_full` was rebuilt after all three fixes. `artifacts/quick` (the original 4-family pipeline) is unchanged.

## Rerun
From `scripts/`: `./run_all_paper.sh full 2`. Every stage resumes (dataset per row, benchmark per split under `results/partial/`, defense per candidate and `defense/norm_features.csv`). Delete `artifacts/paper_full/results` and `defense/norm_features.csv` to recompute results.

## Known limits
- Generators and feature conventions are our interpretation of the paper.
- Defense equivalence is checked on the logical rewrite at 24 qubits, not on the compiled circuit.
- Single backend (FakeNighthawk).
- The metadata-only control is nearly as accurate as the ten features.
- The defense effect is small (about 0.04-0.05 macro-F1).
- The defense evaluation has no per-split checkpoint (minutes to rerun).
- The normalization-aware attacker has no paired unprotected baseline.
