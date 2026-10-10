# Research note for Dr. Beat Buesser (draft; edit before sending)

Thank you for sharing the QCE 2026 short paper. We built an independent Qiskit implementation of your protocol (seven classes, 47 generators interpreted from Table I, ten Table II features, FakeNighthawk, 24/48 qubits, optimization levels 0-3, source-disjoint splits, RF with training-only grid search). The qualitative findings reproduce: strong within-regime recovery, weak cross-regime transfer, strong level 2<->3 transfer, joint size training restores accuracy. Numerical differences exist (e.g. level-1 transfer is stronger and 48->24 transfer weaker in our data) and we have not tuned to match.

Two additional controls we ran, which you may find useful: an RF on unnormalized size metadata alone reaches 0.938 accuracy (vs 0.956 for the ten features), and holding out whole generators lowers accuracy to 0.687±0.050.

Following your Section V we then tested verified semantics-preserving rewrites (layout, transpiler-seed, decomposition, reordering) against an attacker retrained on protected circuits. All 1974 candidates were verified (24 qubits); the best adaptive-attacker macro-F1 reduction is about 0.05 absolute at a 50% overhead budget (0.916 -> 0.865), about half to two-thirds of that from random selection, so we do not claim meaningful privacy.

Questions: exact definitions of the phase/rotation gate family, layer construction, entropy normalization, Gini populations; generator parameters, dataset size and the RF grid; and whether you consider adaptive-attack evaluation of low-overhead transformations a useful next step.
