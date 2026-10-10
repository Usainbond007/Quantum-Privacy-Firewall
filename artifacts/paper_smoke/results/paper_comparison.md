# Paper-aligned benchmark: measured vs reported

Independent implementation. Generators, feature conventions and dataset size are our interpretation; the paper does not publish them. Differences from the paper's numbers are therefore expected and are NOT evidence for or against the paper.

Profile `smoke`: 141 source circuits, 282 transpiled circuits, 2 repeated source-disjoint splits, chance = 0.143.

### Optimization-level generalization (sizes pooled)

Each cell: ours accuracy / macro-F1 (mean±std over splits) · paper accuracy / macro-F1.

| train \ test | L0 | L2 |
|---|---|---|
| L0 | 0.840±0.011 / 0.839±0.012<br>paper 0.958 / 0.958 | 0.234±0.064 / 0.187±0.057<br>paper 0.300 / 0.271 |
| L2 | 0.223±0.032 / 0.169±0.039<br>paper 0.295 / 0.244 | 0.904±0.011 / 0.904±0.009<br>paper 0.982 / 0.982 |

### Controls and stricter checks (pooled test, mean±std)

| setting | accuracy | macro-F1 |
|---|---|---|
| Table II features, source-disjoint (paper-style) | 0.872±0.000 | 0.873±0.000 |
| Shuffled-label control | 0.117±0.000 | 0.124±0.002 |
| Unnormalized size metadata only (n_gates, depth, n2q, width) | 0.883±0.011 | 0.882±0.009 |
| Generator-disjoint split (whole generators held out) | 0.649±0.018 | 0.647±0.024 |
| Gini over used edges/qubits only (convention sensitivity) | 0.872±0.011 | 0.874±0.011 |

### Per-class results, pooled source-disjoint test (mean±std over splits)

| intent class | precision | recall | F1 |
|---|---|---|---|
| entanglement_generation | 0.811±0.046 | 0.893±0.036 | 0.848±0.009 |
| fourier_like | 0.938±0.062 | 1.000±0.000 | 0.967±0.033 |
| phase_oracle_like | 0.867±0.049 | 0.714±0.071 | 0.783±0.063 |
| amplitude_amplification | 0.917±0.083 | 0.833±0.000 | 0.871±0.038 |
| variational_ansatz | 1.000±0.000 | 0.786±0.071 | 0.878±0.045 |
| hamiltonian_simulation | 0.923±0.077 | 0.917±0.000 | 0.918±0.038 |
| arithmetic_permutation | 0.756±0.056 | 0.964±0.036 | 0.845±0.022 |

Confusion matrix (sum over splits; rows = true class, columns = predicted):

```
   25     0     1     0     0     0     2
    0    28     0     0     0     0     0
    4     0    20     2     0     0     2
    0     0     0    20     0     0     4
    1     1     2     0    22     2     0
    0     1     0     0     0    22     1
    1     0     0     0     0     0    27
```
