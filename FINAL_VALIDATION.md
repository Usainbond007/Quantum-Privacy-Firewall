# Final validation and research-claim boundaries

## What this release is

An independent, paper-aligned Qiskit research implementation and prototype based on Beat Buesser and Anil Kurmus, *Algorithmic Intent Leakage in Transpiled Quantum Circuits: An Initial Reverse-Engineering Study* (QCE 2026). The paper's Table I names 47 generators grouped into seven families; Table II defines ten features; the paper tests FakeNighthawk at 24/48 qubits and optimization levels 0–3. Our circuit definitions, randomization, feature conventions and exact RF hyperparameter grid are our interpretations, **not original IBM source code**.

## Verification performed in this delivery environment

- Python compilation of repository source: passed.
- `tests/test_artifact_integrity.py`: 4 passed.
- Archived dataset: 2,256 rows, 282 source IDs, no duplicate generator/variant/size/optimization keys, all rows recorded OK.
- Archived defense candidates: 5,076 candidate/optimization rows, no duplicate keys, recorded PASS. These statuses were not independently rerun.
- Full benchmark JSON and full adaptive-defense JSON: **not present in the uploaded snapshot**.
- Full Qiskit tests, end-to-end quantum runs, frontend build: **not executed here**. This runtime lacks Qiskit and package-index access.

## What was improved

1. Added fail-closed, source/config-fingerprinted cache manifests to paper dataset, benchmark checkpoints, defense candidates and normalization cache.
2. Made dataset and candidate CSV writes atomic; rejects duplicate keys and incomplete candidate/optimization groups.
3. Prevented `--reuse-candidates` from bypassing provenance validation.
4. Added an evidence-only artifact auditor and a notebook that never confuses cached results with fresh execution.
5. Added an explicit one-time adoption script for the archived dataset whose SHA256 is recorded in Claude's handoff. Candidate adoption requires explicit acknowledgement that stored verification labels are not independently proven.

## Important limitation: cache migration

The snapshot was created before cache provenance manifests existed. It is unsafe to silently trust its rows after modifying generators or the feature extractor. For the **exact** archived full dataset only, `scripts/adopt_verified_dataset.py` checks the SHA256 prefix documented in `HANDOFF.md`, row count, source count, duplicates and status before writing a manifest. This is provenance bookkeeping, **not** proof of semantic correctness. `scripts/adopt_snapshot_candidates.py` similarly validates candidate keys and recorded statuses, but cannot attest to equivalence and should be used only if the same original corrected code and configuration are retained. A stronger path is to regenerate candidates.

## Local commands (Qiskit-enabled environment)

```bash
python -m pip install -r requirements.txt
python -m pytest -q tests backend/tests
python scripts/audit_submission.py --output evidence_audit.json
python scripts/adopt_verified_dataset.py
# Only if explicitly choosing to reuse archived candidates:
python scripts/adopt_snapshot_candidates.py
python scripts/run_paper_benchmark.py --profile full
python scripts/run_paper_defense.py --profile full --workers 2 --reuse-candidates
```

To regenerate rather than adopt archived artifacts, use a **fresh project copy/output directory** with old `artifacts/paper_full` removed, then run `build_paper_dataset.py --profile full` followed by the two evaluation scripts. Never mix data generated from different source revisions.

## Claims allowed in the presentation

- The IBM authors report intent recoverability from backend-transpiled circuits under their experimental protocol (cite their supplied paper).
- Our repository implements independently constructed paper-aligned generators, features, and an attack/defense research pipeline.
- The archived dataset and candidate counts are documented and pass basic structural integrity checks.

## Claims NOT supported yet

- Exact reproduction of the IBM authors' numerical results.
- Independently verified equivalence of all 47 generator implementations and all 1,692 candidates.
- Successful reduction in adaptive attacker classification performance.
- Guaranteed obfuscation, security, secrecy, or production-ready protection.

## Final evidence required before calling the defense effective

`artifacts/paper_full/results/paper_benchmark.json`, `paper_comparison.md`, `paper_defense.json`, `defense_summary.md`; test logs and package versions; evidence of held-out adaptive and normalization-aware macro-F1 reduction versus unprotected and random controls; verification coverage; depth/2Q overhead; and clear statistical uncertainty. Negative results must be reported, not hidden.
