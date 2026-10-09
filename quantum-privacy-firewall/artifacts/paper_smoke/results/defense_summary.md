# Defense evaluation on the paper-aligned benchmark

141 source circuits at 24 qubits, FakeNighthawk, optimization levels [0, 2], 2 repeated source-disjoint splits (mean±std). Macro-F1 of the attacker on held-out protected circuits; lower = less intent recoverable; chance = 0.143. Every protected candidate passed exact logical-equivalence checking (MQT QCEC) against its source circuit; UNKNOWN/FAIL candidates were excluded.

Unprotected, paper-style RF (pooled): **0.873±0.000**; per level: L0 0.839±0.012, L2 0.904±0.009

| budget | arm | static RF | adaptive RF (pooled) | adaptive L0 | adaptive L2 | norm-aware RF | Δdepth | Δ2Q | rewritten |
|---|---|---|---|---|---|---|---|---|---|
| 0% | guided | 0.844±0.006 | 0.864±0.008 | 0.822±0.010 | 0.891±0.021 | 0.837±0.014 | -1.0% | -1.9% | 24% |
| 0% | random | 0.865±0.005 | 0.884±0.012 | 0.833±0.019 | 0.913±0.001 | 0.835±0.008 | -0.5% | -1.5% | 13% |
| 20% | guided | 0.826±0.013 | 0.855±0.020 | 0.802±0.052 | 0.870±0.021 | 0.825±0.025 | -0.5% | -1.9% | 53% |
| 20% | random | 0.856±0.017 | 0.869±0.027 | 0.831±0.000 | 0.904±0.031 | 0.827±0.015 | -0.5% | -2.2% | 31% |

### Verification

{'PASS': 564} via {'dag_identity': 141, 'identical_logical_circuit': 141, 'mqt_qcec': 282}

### Fraction of verified rewrites that changed the attacker-visible Table II features

- decomp+layout|L0: 100%
- decomp+layout|L2: 100%
- decomp|L0: 99%
- decomp|L2: 75%
- layout|L0: 100%
- layout|L2: 98%
- reorder|L0: 0%
- reorder|L2: 1%
