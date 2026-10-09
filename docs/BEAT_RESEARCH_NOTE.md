# Research note for Dr. Beat Buesser

We thank Beat Buesser and Anil Kurmus for sharing the QCE 2026 short paper. Our current repository is an independently built Qiskit intent-leakage and defense laboratory. We are adapting it to the paper's seven intent categories and ten named structural features, while separately evaluating semantics-preserving compiler transformations under adaptive retraining and explicit hardware-overhead budgets.

The original paper reports intent classification, not successful mitigation. Our existing quick-profile results do not establish robust adaptive privacy improvement. The new Table-II implementation is an interpretation pending clarification of implementation conventions, not an exact reproduction of the authors' source code.

Questions for the authors: Can you share precise definitions of phase/rotation gate family, temporal layer construction, entropy normalization and Gini populations, and the circuit-generation/Random Forest hyperparameter settings? Do you consider adaptive-attack evaluation of verified low-overhead transformations a useful next step?
