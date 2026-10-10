# Paper-aligned benchmark: measured vs reported

Independent implementation. Generators, feature conventions and dataset size are our interpretation; the paper does not publish them. Differences from the paper's numbers are therefore expected and are NOT evidence for or against the paper.

Profile `full`: 282 source circuits, 2256 transpiled circuits, 5 repeated source-disjoint splits, chance = 0.143.

### Optimization-level generalization (sizes pooled)

Each cell: ours accuracy / macro-F1 (mean±std over splits) · paper accuracy / macro-F1.

| train \ test | L0 | L1 | L2 | L3 |
|---|---|---|---|---|
| L0 | 0.932±0.011 / 0.932±0.012<br>paper 0.958 / 0.958 | 0.443±0.022 / 0.392±0.028<br>paper 0.499 / 0.474 | 0.269±0.027 / 0.239±0.033<br>paper 0.300 / 0.271 | 0.248±0.026 / 0.219±0.030<br>paper 0.285 / 0.261 |
| L1 | 0.331±0.030 / 0.285±0.032<br>paper 0.397 / 0.372 | 0.991±0.004 / 0.991±0.005<br>paper 0.933 / 0.931 | 0.478±0.012 / 0.435±0.017<br>paper 0.414 / 0.359 | 0.523±0.013 / 0.473±0.014<br>paper 0.374 / 0.312 |
| L2 | 0.215±0.012 / 0.165±0.005<br>paper 0.295 / 0.244 | 0.430±0.026 / 0.384±0.043<br>paper 0.357 / 0.277 | 0.954±0.007 / 0.955±0.007<br>paper 0.982 / 0.982 | 0.906±0.015 / 0.906±0.016<br>paper 0.937 / 0.937 |
| L3 | 0.215±0.032 / 0.180±0.033<br>paper 0.254 / 0.212 | 0.489±0.039 / 0.469±0.046<br>paper 0.357 / 0.278 | 0.912±0.010 / 0.912±0.010<br>paper 0.970 / 0.970 | 0.939±0.016 / 0.939±0.016<br>paper 0.978 / 0.979 |

### Circuit-size generalization (optimization levels pooled)

Each cell: ours accuracy / macro-F1 (mean±std over splits) · paper accuracy / macro-F1.

| train \ test | 24q | 48q | 24+48 |
|---|---|---|---|
| 24q | 0.935±0.012 / 0.935±0.012<br>paper 0.971 / 0.972 | 0.634±0.008 / 0.568±0.011<br>paper 0.607 / 0.560 | 0.784±0.009 / 0.773±0.010<br>paper 0.792 / 0.792 |
| 48q | 0.250±0.029 / 0.197±0.041<br>paper 0.579 / 0.567 | 0.960±0.007 / 0.960±0.008<br>paper 0.988 / 0.988 | 0.605±0.016 / 0.652±0.015<br>paper 0.780 / 0.786 |
| 24+48 | 0.953±0.008 / 0.953±0.008<br>paper 0.956 / 0.956 | 0.960±0.006 / 0.960±0.006<br>paper 0.988 / 0.987 | 0.956±0.007 / 0.957±0.007<br>paper 0.971 / 0.972 |

### Controls and stricter checks (pooled test, mean±std)

| setting | accuracy | macro-F1 |
|---|---|---|
| Table II features, source-disjoint (paper-style) | 0.956±0.007 | 0.957±0.007 |
| Shuffled-label control | 0.138±0.011 | 0.135±0.013 |
| Unnormalized size metadata only (n_gates, depth, n2q, width) | 0.938±0.006 | 0.939±0.006 |
| Generator-disjoint split (whole generators held out) | 0.687±0.050 | 0.677±0.061 |
| Gini over used edges/qubits only (convention sensitivity) | 0.962±0.006 | 0.962±0.006 |

### Per-class results, pooled source-disjoint test (mean±std over splits)

| intent class | precision | recall | F1 |
|---|---|---|---|
| entanglement_generation | 0.909±0.014 | 0.961±0.020 | 0.934±0.015 |
| fourier_like | 0.984±0.014 | 0.998±0.004 | 0.991±0.006 |
| phase_oracle_like | 0.955±0.019 | 0.871±0.029 | 0.911±0.021 |
| amplitude_amplification | 0.965±0.008 | 0.927±0.032 | 0.946±0.019 |
| variational_ansatz | 0.986±0.012 | 0.963±0.017 | 0.974±0.005 |
| hamiltonian_simulation | 0.986±0.012 | 0.985±0.011 | 0.985±0.005 |
| arithmetic_permutation | 0.922±0.023 | 0.989±0.007 | 0.954±0.011 |

Confusion matrix (sum over splits; rows = true class, columns = predicted):

```
  538     0    14     1     3     0     4
    0   559     0     0     1     0     0
   51     4   488     7     4     0     6
    0     0     0   445     0     3    32
    2     4     9     2   539     4     0
    0     1     0     1     0   473     5
    1     0     0     5     0     0   554
```
