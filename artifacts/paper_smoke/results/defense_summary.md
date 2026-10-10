# Defense evaluation on the paper-aligned benchmark

141 source circuits at 24 qubits, FakeNighthawk, optimization levels [0, 2], 2 repeated source-disjoint splits (3 train / 1 validation / 1 test variants per generator), mean±std over splits. Metric: macro-F1 on held-out circuits (lower = less intent recoverable; chance 0.143). Only candidates whose logical rewrite passed equivalence verification (QCEC / DAG identity / identical circuit) and the overhead budget were eligible.

**Unprotected** (paper-style RF, pooled test): 0.814±0.015 (validation 0.861±0.010); per level: L0 0.701±0.040, L2 0.879±0.010; GBoost 0.785±0.000, LogReg 0.662±0.003; metadata-only control 0.762±0.014.

| budget | arm | static RF | adaptive RF | Δ abs | Δ rel | paired 95% CI of Δ | norm-aware RF | adaptive GBoost | adaptive LogReg | metadata-only | Δdepth | Δ2Q | rewritten |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0% | guided | 0.796±0.032 | 0.774±0.000 | 0.040±0.015 | 0.049±0.017 | [-0.023, +0.113] | 0.756±0.020 | 0.694±0.019 | 0.673±0.015 | 0.803±0.016 | -1.9% | -2.1% | 29% |
| 0% | random | 0.807±0.008 | 0.785±0.021 | 0.029±0.007 | 0.035±0.009 | [-0.019, +0.077] | 0.764±0.021 | 0.791±0.004 | 0.664±0.006 | 0.807±0.011 | -1.4% | -2.1% | 22% |
| 20% | guided | 0.766±0.005 | 0.718±0.017 | 0.096±0.031 | 0.117±0.036 | [+0.038, +0.159] | 0.740±0.049 | 0.663±0.019 | 0.653±0.035 | 0.727±0.016 | -0.9% | -2.4% | 59% |
| 20% | random | 0.812±0.027 | 0.777±0.031 | 0.037±0.017 | 0.046±0.021 | [-0.021, +0.093] | 0.760±0.017 | 0.764±0.001 | 0.647±0.008 | 0.768±0.004 | -1.3% | -2.7% | 43% |

Δ = unprotected macro-F1 − adaptive macro-F1 on the same splits (positive = defense helped). The paired CI resamples source circuits and pairs each protected circuit with its own unprotected version.

### Per-class F1 of the adaptive RF (pooled test)

| budget | arm | entanglement_generation | fourier_like | phase_oracle_like | amplitude_amplification | variational_ansatz | hamiltonian_simulation | arithmetic_permutation |
|---|---|---|---|---|---|---|---|---|
| unprotected | - | 0.790±0.049 | 0.983±0.017 | 0.686±0.114 | 0.818±0.091 | 0.769±0.077 | 0.871±0.089 | 0.781±0.031 |
| 0% | guided | 0.737±0.004 | 0.983±0.017 | 0.615±0.000 | 0.798±0.048 | 0.694±0.002 | 0.844±0.044 | 0.746±0.013 |
| 0% | random | 0.772±0.014 | 0.983±0.017 | 0.644±0.023 | 0.766±0.016 | 0.760±0.010 | 0.852±0.037 | 0.721±0.106 |
| 20% | guided | 0.746±0.013 | 0.923±0.000 | 0.618±0.003 | 0.541±0.019 | 0.692±0.000 | 0.862±0.062 | 0.646±0.021 |
| 20% | random | 0.778±0.068 | 0.928±0.005 | 0.709±0.149 | 0.699±0.084 | 0.703±0.011 | 0.875±0.042 | 0.745±0.055 |

### Verification (all generated candidates)

Status: {'PASS': 705}; methods: {'dag_identity': 141, 'identical_logical_circuit': 282, 'mqt_qcec': 282}

By strategy:

- decomp: {'PASS': 141}
- decomp+layout: {'PASS': 141}
- layout: {'PASS': 141}
- reorder: {'PASS': 141}
- seed: {'PASS': 141}

Non-PASS reasons: none (every candidate verified)

### Candidate rejections by budget (candidate x optimization level)

- budget 0%: {'over budget': 851, 'accepted': 559}
- budget 20%: {'accepted': 899, 'over budget': 511}

### Share of verified rewrites that changed the attacker-visible Table II features

- decomp+layout|L0: 100%
- decomp+layout|L2: 100%
- decomp|L0: 99%
- decomp|L2: 75%
- layout|L0: 100%
- layout|L2: 98%
- reorder|L0: 0%
- reorder|L2: 4%
- seed|L0: 99%
- seed|L2: 51%
