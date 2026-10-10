# HANDOFF — Quantum Privacy Firewall (final state)

All experiments are COMPLETE; nothing is running. Last full-run date: container clock 2026-10-10. Git history in this folder (`git log`).

## Done and verified
- `pytest tests backend/tests` → **167 passed** (generator semantics, splits, features, budgets, equivalence incl. wrong circuits and DAG-shortcut hardening, backend API).
- Frontend (`npm ci`, `npx vitest run`, `npm run build`) passed earlier in this session (8 tests); frontend code unchanged since.
- Benchmark (`artifacts/paper_full/results/paper_benchmark.json`, `paper_comparison.{md,csv,json}`) and defense (`paper_defense.json`, `defense_summary.{md,csv}`) generated from the final code and the final dataset (hash in `logs/`), with 5 splits each.
- Generator audit: `docs/GENERATOR_AUDIT.md` (24 semantic / 20 structural / 3 analogue of 47).

## Invalidated earlier artifacts (all replaced)
Rows/runs made before the fixes to `incrementer`, `comparator`, `parity_amplitude_amplification`; every pre-fix smoke figure quoted in chat; `logs/STALE_smoke_defense_pre_fix.log`. Current `artifacts/paper_full` was rebuilt after all three fixes. Legacy `artifacts/quick` (old 4-family pipeline) is untouched and weak.

## Resume / rerun (from `scripts/`)
`./run_all_paper.sh full 2` — every stage resumes (dataset by row, benchmark by split under `results/partial/`, defense by candidate and `defense/norm_features.csv`). Delete `artifacts/paper_full/results` and `defense/norm_features.csv` to force recomputation of results.

## Known limits (also in README)
Generators/feature conventions are our interpretation; defense verified at 24 qubits on the logical rewrite only; single backend; metadata-only control is nearly as accurate as the features; defense effect is small (≈0.04-0.05 macro-F1). The defense evaluation has no per-split checkpoint (minutes to rerun). Norm-aware attacker has no paired unprotected baseline.
