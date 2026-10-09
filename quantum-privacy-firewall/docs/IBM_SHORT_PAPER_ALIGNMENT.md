# IBM QCE 2026 short-paper alignment (independent implementation)

Primary reference: Buesser and Kurmus, *Algorithmic Intent Leakage in Transpiled Quantum Circuits: An Initial Reverse-Engineering Study*, QCE 2026 short paper, supplied by the authors. Do not call this a source-code reproduction.

## Already in the uploaded project
The existing `qpf` attack/defense experiment, legacy 13-feature schema, React/FastAPI demonstration, saved quick-profile results and notebook are retained. None of the saved quick-profile metrics are evidence that the IBM paper has been reproduced.

## New in this extension
`src/qpf/paper_features.py` exposes `extract_paper_features(circuit, coupling_edges)` and the 10 ordered Table II feature names. It is intentionally separate from `src/qpf/features.py`; legacy trained classifiers MUST NOT be reused with the new schema. The previous permissive MQT-QCEC `startswith('equivalent')` handling was replaced by an exact status allowlist.

## Methodological ambiguities that must be confirmed with the authors
The short paper names but does not fully operationalize: (a) which gates belong to the phase/rotation family; (b) whether single-qubit type entropy is normalized; (c) scheduling definition for layers; (d) whether Gini denominators include unused physical edges/qubits; (e) how measurements and delays are handled; (f) full generator parameters, dataset sizes and hyperparameter grid. Our feature module declares its conventions in the docstring and MUST be called an interpretation, not the exact original.

## Paper-aligned benchmark still required
Implement Table I's seven families using documented, independently seeded source circuits; use source-circuit-disjoint splits; 24 and 48 logical qubits; optimization levels 0–3; FakeNighthawk target with native rz/sx/x/cz gates; five-fold CV hyperparameter tuning on training data only; holdout accuracy and macro-F1; cross-size and cross-optimization transfer. Document generator-to-class mappings. Compare observed results to paper Tables III/IV but NEVER copy them into the local results file.

## Defense evaluation
Keep the untouched test split isolated from candidate search. Refit adaptive attackers on protected training circuits. Report full vs metadata-only baseline, label-shuffle controls, strongest normalization-aware attacker, confidence intervals and paired privacy-cost results. Do not claim privacy until independent holdout adaptive metrics support it. Equivalence pass is not hardware fidelity.

## Scientific status
This release contains a feature-extractor extension and verification hardening, NOT a newly executed IBM reproduction or a proven firewall. Qiskit is not installed in the packaging runtime; Qiskit-dependent integration tests and frontend build remain unverified. Archived quick-profile outputs are prior experiments, not newly measured results.
