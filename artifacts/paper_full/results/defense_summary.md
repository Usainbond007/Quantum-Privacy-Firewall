# Defense evaluation on the paper-aligned benchmark

282 source circuits at 24 qubits, FakeNighthawk, optimization levels [0, 2, 3], 5 repeated source-disjoint splits (3 train / 1 validation / 2 test variants per generator), mean±std over splits. Metric: macro-F1 on held-out circuits (lower = less intent recoverable; chance 0.143). Only candidates whose logical rewrite passed equivalence verification (QCEC / DAG identity / identical circuit) and the overhead budget were eligible.

**Unprotected** (paper-style RF, pooled test): 0.916±0.007 (validation 0.934±0.022); per level: L0 0.859±0.035, L2 0.942±0.014, L3 0.933±0.008; GBoost 0.882±0.008, LogReg 0.728±0.012; metadata-only control 0.913±0.011.

| budget | arm | static RF | adaptive RF | Δ abs | Δ rel | paired 95% CI of Δ | norm-aware RF | adaptive GBoost | adaptive LogReg | metadata-only | Δdepth | Δ2Q | rewritten |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0% | guided | 0.887±0.012 | 0.904±0.022 | 0.012±0.023 | 0.013±0.025 | [-0.006, +0.030] | 0.865±0.007 | 0.873±0.022 | 0.713±0.018 | 0.893±0.014 | -2.3% | -2.8% | 36% |
| 0% | random | 0.909±0.011 | 0.914±0.017 | 0.002±0.015 | 0.003±0.017 | [-0.012, +0.016] | 0.880±0.013 | 0.889±0.014 | 0.728±0.006 | 0.907±0.012 | -1.3% | -2.3% | 22% |
| 10% | guided | 0.864±0.019 | 0.879±0.012 | 0.037±0.017 | 0.041±0.018 | [+0.017, +0.058] | 0.855±0.012 | 0.858±0.023 | 0.711±0.019 | 0.870±0.022 | -2.1% | -2.9% | 59% |
| 10% | random | 0.902±0.008 | 0.900±0.015 | 0.016±0.014 | 0.018±0.015 | [+0.001, +0.031] | 0.867±0.014 | 0.867±0.010 | 0.710±0.019 | 0.898±0.014 | -1.2% | -2.2% | 36% |
| 20% | guided | 0.831±0.017 | 0.878±0.021 | 0.038±0.016 | 0.042±0.017 | [+0.017, +0.059] | 0.847±0.012 | 0.855±0.007 | 0.691±0.016 | 0.851±0.014 | -0.6% | -1.9% | 65% |
| 20% | random | 0.881±0.012 | 0.887±0.012 | 0.029±0.014 | 0.032±0.015 | [+0.011, +0.049] | 0.853±0.013 | 0.862±0.012 | 0.715±0.016 | 0.888±0.020 | -0.3% | -2.0% | 42% |
| 50% | guided | 0.763±0.017 | 0.865±0.021 | 0.051±0.021 | 0.056±0.023 | [+0.029, +0.073] | 0.841±0.018 | 0.851±0.006 | 0.709±0.021 | 0.855±0.018 | +5.5% | +3.5% | 74% |
| 50% | random | 0.848±0.011 | 0.883±0.015 | 0.033±0.020 | 0.036±0.021 | [+0.013, +0.051] | 0.849±0.012 | 0.855±0.019 | 0.731±0.012 | 0.854±0.019 | +1.9% | +0.1% | 52% |

Δ = unprotected macro-F1 − adaptive macro-F1 on the same splits (positive = defense helped). The paired CI resamples source circuits and pairs each protected circuit with its own unprotected version.

### Per-class F1 of the adaptive RF (pooled test)

| budget | arm | entanglement_generation | fourier_like | phase_oracle_like | amplitude_amplification | variational_ansatz | hamiltonian_simulation | arithmetic_permutation |
|---|---|---|---|---|---|---|---|---|
| unprotected | - | 0.868±0.033 | 0.975±0.019 | 0.839±0.024 | 0.923±0.032 | 0.932±0.024 | 0.958±0.019 | 0.920±0.026 |
| 0% | guided | 0.853±0.040 | 0.975±0.029 | 0.827±0.048 | 0.901±0.019 | 0.936±0.028 | 0.956±0.025 | 0.881±0.010 |
| 0% | random | 0.863±0.029 | 0.977±0.024 | 0.849±0.019 | 0.927±0.022 | 0.927±0.035 | 0.955±0.031 | 0.899±0.028 |
| 10% | guided | 0.836±0.018 | 0.963±0.027 | 0.789±0.047 | 0.875±0.021 | 0.876±0.025 | 0.950±0.019 | 0.864±0.014 |
| 10% | random | 0.875±0.023 | 0.953±0.027 | 0.820±0.054 | 0.911±0.016 | 0.907±0.034 | 0.958±0.019 | 0.876±0.018 |
| 20% | guided | 0.834±0.020 | 0.948±0.023 | 0.806±0.029 | 0.880±0.041 | 0.879±0.035 | 0.956±0.022 | 0.845±0.036 |
| 20% | random | 0.840±0.031 | 0.945±0.034 | 0.826±0.036 | 0.887±0.012 | 0.880±0.030 | 0.958±0.023 | 0.875±0.022 |
| 50% | guided | 0.816±0.036 | 0.947±0.025 | 0.772±0.051 | 0.847±0.035 | 0.882±0.035 | 0.940±0.026 | 0.853±0.030 |
| 50% | random | 0.823±0.029 | 0.956±0.019 | 0.788±0.009 | 0.894±0.050 | 0.907±0.038 | 0.953±0.016 | 0.862±0.046 |

### Verification (all generated candidates)

Status: {'PASS': 1974}; methods: {'dag_identity': 564, 'identical_logical_circuit': 564, 'mqt_qcec': 846}

By strategy:

- decomp: {'PASS': 282}
- decomp+layout: {'PASS': 282}
- decomp+reorder: {'PASS': 282}
- layout: {'PASS': 282}
- reorder: {'PASS': 282}
- reorder+layout: {'PASS': 282}
- seed: {'PASS': 282}

Non-PASS reasons: none (every candidate verified)

### Candidate rejections by budget (candidate x optimization level)

- budget 0%: {'over budget': 3747, 'accepted': 2175}
- budget 10%: {'accepted': 3006, 'over budget': 2916}
- budget 20%: {'accepted': 3470, 'over budget': 2452}
- budget 50%: {'accepted': 4358, 'over budget': 1564}

### Share of verified rewrites that changed the attacker-visible Table II features

- decomp+layout|L0: 100%
- decomp+layout|L2: 100%
- decomp+layout|L3: 100%
- decomp+reorder|L0: 98%
- decomp+reorder|L2: 76%
- decomp+reorder|L3: 78%
- decomp|L0: 99%
- decomp|L2: 76%
- decomp|L3: 80%
- layout|L0: 100%
- layout|L2: 98%
- layout|L3: 98%
- reorder+layout|L0: 100%
- reorder+layout|L2: 98%
- reorder+layout|L3: 98%
- reorder|L0: 0%
- reorder|L2: 2%
- reorder|L3: 2%
- seed|L0: 100%
- seed|L2: 51%
- seed|L3: 51%
