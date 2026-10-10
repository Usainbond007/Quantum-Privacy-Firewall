# Alignment with Buesser & Kurmus (IEEE Quantum Week 2026 short paper)

Independent implementation; **not** a source-code reproduction. The paper publishes no code and no generator definitions.

| Paper element | Implementation | Status |
|---|---|---|
| Table I, 7 intent classes, 47 generators | `src/qpf/paper_circuits.py` (our interpretation of each name) | done; audit tiers in `docs/GENERATOR_AUDIT.md` (24 semantic / 20 structural / 3 analogue) |
| FakeNighthawk, native rz/sx/x/cz | `compilation.py`, backend `FakeNighthawk` | done |
| 24 and 48 qubits, optimization levels 0-3 | `paper_benchmark.build_dataset` | done (2256 circuits) |
| Table II ten features | `src/qpf/paper_features.py` | done; conventions below |
| Source-disjoint splits, scaler on train, 5-fold CV grid search, accuracy + macro-F1 | `paper_benchmark.evaluate` (CV folds grouped by source) | done |
| Tables III / IV | `artifacts/paper_full/results/paper_comparison.*` | done, differences documented |
| Section V mitigation direction | `src/qpf/paper_defense.py` | done; modest effect, see README |

## Conventions the paper leaves open (our choices)
Phase/rotation gate set (`DEFAULT_PHASE_ROTATION_GATES`); barriers/delays excluded; greedy ASAP layering; natural-log single-qubit-type entropy (not normalized); Gini over all hardware edges and all physical qubits including idle (sensitivity run with used-only populations: 0.962 vs 0.956 accuracy); Table III pools sizes, Table IV pools optimization levels; transpile seed 11; 6 source variants per generator; RF grid in `config/paper.yaml`.

## Results that go beyond the paper
Metadata-only control (0.938 accuracy), generator-disjoint split (0.687), per-class results and confusion matrices, validation partition for the defense, paired source-bootstrap CIs, alternative classifiers, rejected-candidate accounting.
