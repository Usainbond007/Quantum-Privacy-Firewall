# QPF use-case research: confidential cryptanalysis and portfolio optimization

Prepared 30 October 2026. This is a source-backed product/research plan, not a claim that the two domain extensions are already implemented. The priority is **secure-communications research first**, portfolio research second.

## Executive finding

QPF is currently a **quantum-job intent-leakage testbed**, not a cryptographic privacy system. Its distinctive product direction is a *pre-submission gate*: inspect a Qiskit job, show what an explicitly defined observer could infer, try verified low-overhead rewrites, retest an adaptive attacker, and release or block with a receipt. This directly extends the current benchmark and verifier. Neither existing result proves secrecy of a Grover oracle or a bank's portfolio preference. Both require new **secret-specific** attackers and correctness tests.

The [Q-Hack India rubric](https://www.quantumweek.tech/hackathon) weights technical implementation 30%, quantum relevance 20%, originality 20%, significance 10%, impact 10%, and clarity 10%. A reproducible negative security finding (for example, an oracle remains recoverable and QPF blocks submission) is more credible than an unsupported claim of encryption.

## A. What this repository actually contains

| Layer | Current implementation | Measured evidence or limitation |
|---|---|---|
| Intent families | [`src/qpf/paper_circuits.py`](../src/qpf/paper_circuits.py): 47 generators in seven coarse classes, including phase/oracle-like, amplitude amplification, and variational ansatz | Controlled generated circuits; neither a realistic cryptanalytic oracle dataset nor portfolio preference labels |
| Attacker | [`src/qpf/paper_features.py`](../src/qpf/paper_features.py), [`src/qpf/paper_benchmark.py`](../src/qpf/paper_benchmark.py): ten structural features, Random Forest, grouped splits | [`paper_comparison.md`](../artifacts/paper_full/results/paper_comparison.md): 282 sources, 2,256 compiled records, five source-disjoint splits; pooled accuracy 0.956 +/- 0.007; metadata-only 0.938 +/- 0.006; held-out generator 0.687 +/- 0.050. High metadata score is a confound, not evidence of secret leakage. |
| Defense | [`src/qpf/defenses.py`](../src/qpf/defenses.py): local decomposition, legal reorder, layout and transpile-seed diversification | Does not implement keyed problem masking, oracle hiding, or parameter privacy |
| Verification | [`src/qpf/verification.py`](../src/qpf/verification.py): PASS/FAIL/UNKNOWN via identical/DAG/operator/MQT QCEC | [`defense_summary.md`](../artifacts/paper_full/results/defense_summary.md): all 1,974 candidates passed **logical** verification (846 QCEC, 564 DAG, 564 identical); this does not establish secrecy or noisy utility |
| Adaptive evaluation | [`src/qpf/paper_defense.py`](../src/qpf/paper_defense.py): static/adaptive/normalization-aware attacks, budget and paired CI | At 20% budget adaptive RF macro-F1 0.916 -> 0.878, paired delta 0.038, 95% CI +0.017 to +0.059. Residual 0.878 is high. |
| Demonstration/API | [`scripts/demo_attack.py`](../scripts/demo_attack.py), [`backend/app/schemas.py`](../backend/app/schemas.py) | Terminal example is one QFT victim, not aggregate privacy. API accepts preset 4-8-qubit families only; no QASM/QPY upload or domain-specific risk analysis. |

The current `decompose_rewrite` and `random_reorder` create a fresh `QuantumCircuit(qc.num_qubits)` and some rules cast angles to `float`; thus measured/classically controlled or symbolic-parameter jobs are not safely covered as-is. The repo also has no attacker on actual Runtime parameter bindings, no oracle recovery measure, no real-data portfolio QAOA workflow, no hardware-noise utility study, and no general cloud-submission policy gate. Preserve the existing benchmark; extend in separate domain modules.

## 1. Secure communications: confidential *defensive cryptanalysis* job

### The precise real-world story

A communications-security team tests a **toy authentication predicate, reduced-round cipher, protocol constraint, or key-search condition** using a Grover oracle. The circuit may be submitted to a remote quantum execution service. The oracle can reveal the team's unreleased test condition, target pattern, or research direction to an entity with access to the **job artifact**. QPF sits on the developer side of that handoff. It does **not** secure traffic in transit, protect a QKD key, or claim that a neighboring cloud tenant can read another customer's job. The observer is an authorized-but-curious operator/collaborator, compromised credential holder, or recipient of a shared circuit artifact.

This is a credible *research-workflow* scenario, not evidence of a known bank/telecom breach. [IBM's Grover tutorial](https://quantum.cloud.ibm.com/docs/en/tutorials/grovers-algorithm) explicitly builds an oracle marking basis states; [Qiskit's Grover examples](https://qiskit-community.github.io/qiskit-algorithms/tutorials/07_grover_examples.html) show runnable Boolean and DIMACS-CNF phase oracles. [Quantum Leak](https://arxiv.org/abs/2401.01521) reports a **different** cloud timing side channel that can expose a Grover oracle; it motivates concern but QPF's structural rewrites are not tested against timing. [NIST's PQC FAQ](https://csrc.nist.gov/Projects/Post-Quantum-Cryptography/faqs) and its [practical Grover/AES analysis](https://csrc.nist.gov/csrc/media/Events/2024/fifth-pqc-standardization-conference/documents/papers/on-practical-cost-of-grover.pdf) make clear that a small demo is not a present-day break of AES or deployed communications.

### Core quantum construction and exposure

For a Boolean condition `f(x)`, the phase oracle acts as `O_f|x> = (-1)^f(x)|x>`. A Grover circuit alternates that oracle with diffusion/amplitude amplification, then measures candidate `x`. A circuit can hide obvious source names while still exposing gate-level structure and, at small sizes, the function itself. **Exact equivalence preserves the same `O_f`**: an observer able to run or analyze the full oracle can often recover its marked states. Therefore, passing QCEC is a correctness check, never proof that the oracle is secret.

Three secrets must not be conflated: **(i)** algorithm family (Grover vs QFT), **(ii)** oracle *type* (e.g. parity vs CNF), and **(iii)** specific predicate/marked strings. The existing QPF attacker tests only (i), broadly. For the cyber use case, (iii) matters most. An especially honest result may be that QPF reduces family-classifier confidence but fails to hide the marked state; the release gate then blocks. That contrast is scientifically interesting and judge-proof.

### Public runnable inputs and honest labels

| Resource | What to use | Important limit |
|---|---|---|
| [IBM Grover tutorial](https://quantum.cloud.ibm.com/docs/en/tutorials/grovers-algorithm) | Build a small phase-oracle + diffusion circuit and capture the original/bound/compiled views | Educational toy, not AES cryptanalysis |
| [Qiskit Algorithms Grover examples](https://qiskit-community.github.io/qiskit-algorithms/tutorials/07_grover_examples.html) | Boolean and DIMACS-CNF source instances; `PhaseOracleGate` for Qiskit 2.1+ as documented | Need pin versions and verify local compatibility |
| [Existing QPF amplitude-amplification generators](../src/qpf/paper_circuits.py) | Negative/positive controls for family recognition | Not independently sufficient for secret recovery; synthetic generator signatures can overfit |
| [NIST quantum cryptanalysis overview](https://www.nist.gov/publications/quantum-cryptanalysis-shor-grover-and-beyond) | Motivation and technical context | No claim of quantum advantage or actual attack on modern ciphers |

Generate balanced *synthetic* secret predicates with matched qubit count, depth, oracle implementation, number of marked states, compilation settings, and seeds. Split by **predicate template**, not just compiled copy, to avoid memorizing a near-duplicate. Also include visibly different Boolean families as a separate oracle-type task. A four-bit marked state has only 16 possibilities and is not a real secret; use it solely to demonstrate the measurement/evaluation pipeline.

### Build plan that directly extends QPF

1. Add a `GroverCase` loader for Qiskit-built Boolean/CNF oracles, circuit provenance, secret label stored **locally**, and a supported bound unitary kernel. Do not execute uploaded `.py` files. Accept bounded QPY/QASM3 later, with a parser-only path.
2. Compile to a pinned fake backend using the current QPF feature extractor. Keep the old **family attacker** as a context panel, then add **oracle recovery**: exact simulator/truth-table attacker for small `n`, plus structural and gate-sequence attackers with adaptive retraining. An exact attacker is a lower-bound sanity check; if it trivially recovers `f`, an ML score cannot justify release.
3. Run current candidate generation and logical verification only on supported unitary kernels. Preserve and check the measurement map. For a credible export, additionally verify compiled behavior/layout as supported by [MQT QCEC's compilation-flow guide](https://github.com/munich-quantum-toolkit/qcec/blob/main/docs/compilation_flow_verification.md). Fail closed on UNKNOWN.
4. Compare original/protected **distribution of Grover outputs** at equal shots on exact simulation and, if time permits, [Aer device-inspired noise](https://qiskit.github.io/qiskit-aer/tutorials/2_device_noise_simulation): marked-state success probability, total-variation distance, depth, two-qubit gate count, and runtime. A functionally equivalent circuit can still have worse noisy success.
5. Return `RELEASE`, `WARN`, or `BLOCK` based on a stated policy. A marked-state recovery score above threshold blocks; no green `protected` badge just because circuit structure changed. Save a sanitized receipt without the predicate.

**Potential research extension:** compare a faithfully attributed application-specific keyed input relabeling/local inverse with the baseline, then attack it knowing the method. A tiny bit-permutation/XOR mask is guessable and **not** cryptographic security. Any non-equivalent encoding needs a different correctness contract: recovered answer after local decoding, not `QCEC(original, submitted)`. A stronger genuinely confidential computation would require a different trust model/primitive; do not imply QPF already provides blind quantum computing.

### Cyber demo and figures

1. Show a safe, *synthetic* communications test condition. The human-readable predicate stays local; the compiled circuit is the outbound artifact.
2. Show the QPF family prediction and a separate oracle-recovery heatmap/probability table for original vs rewritten circuit. Make the label `family leakage` or `predicate recovery` unmistakable.
3. Show QCEC PASS/UNKNOWN, overhead Pareto plot, and equal-shot Grover success bars. If the predicate is recoverable, show a visible **BLOCK: same function remains exposed**. This is a real security decision, not a failed demo.
4. If a keyed comparator is actually implemented and measured, show local decode and residual oracle attack. Keep its claim scoped to the exact construction and attacker.

**Strongest defensible cyber pitch:** "Before a quantum cryptanalysis circuit leaves the lab, QPF tests whether the final job reveals its purpose or oracle, verifies any rewrite, and blocks it when the sensitive predicate remains recoverable." Not "QPF prevents eavesdropping" or "QPF makes Grover/AES secure."

## 2. Banking/portfolio: confidential QAOA research job

### The precise real-world story

An investment research desk evaluates candidate portfolios with a quantum-classical workflow. Its **public demonstration data** can be real market observations, but its chosen risk/return/diversification priorities are synthetic and private. A cloud-job observer may see the target circuit and the numeric parameter bindings. QPF should detect what this job discloses and block/reformulate unsafe submissions. [IBM's official multi-objective QAOA portfolio tutorial](https://quantum.cloud.ibm.com/docs/en/tutorials/quantum-approximate-multi-objective-optimization) is the best runnable anchor: eight illustrative assets for exact checking and a [40-asset committed market-data snapshot](https://raw.githubusercontent.com/Qiskit/documentation/main/datasets/tutorials/qmoo/market_data.csv) containing returns and covariance. [IBM/Vanguard's exploratory bond-ETF work](https://www.ibm.com/quantum/blog/vanguard-portfolio-optimization) establishes industry interest, not production use, a leak, or quantum advantage. The separate [Global Data Quantum portfolio function](https://quantum.cloud.ibm.com/docs/en/tutorials/global-data-quantum-optimizer) shows another vendor workflow; it is not QPF's implementation.

### Core quantum construction and exposure

For asset-selection bits `x_i`, with `sum(x_i)=K`, use the tutorial's risk, return, and diversification Hamiltonians and a constrained mixer. A simplified scalarized objective is `-c_r x^T Sigma x + c_mu mu^T x + c_d x^T D x`; the private vector `c` controls preference. The tutorial uses a parameterized ansatz and submits objective-weight vectors through Qiskit primitive jobs. [IBM's primitive input documentation](https://quantum.cloud.ibm.com/docs/en/guides/primitive-input-output) confirms that parameter values are part of the PUB workload. This creates two distinct observers:

| Observer | What can leak | QPF status |
|---|---|---|
| Structural-only | That this is a QAOA/variational workload; asset count, topology, resource pattern | Current seven-family benchmark partly tests this, but not preference privacy |
| Full job payload | Explicit weight bindings/angles, possibly market model encoded in Hamiltonian coefficients | Current QPF does **not** test or conceal this |
| Source/logs | Tickers, labels, comments, raw CSV, provenance | Outside current classifier; needs local handling/access control |

If the same parameterized circuit is submitted for two preferences and only binding arrays change, a structural-only preference classifier may be **at chance**. That is the correct result, while a parameter-reading baseline may recover the preference exactly. Gate rewrites do not hide a value plainly present in the job payload.

### Public data, validation, and prior art

Use the Qiskit [40-asset CSV](https://raw.githubusercontent.com/Qiskit/documentation/main/datasets/tutorials/qmoo/market_data.csv), pin commit/checksum, and choose a fixed 8- or 12-asset subset; state it is public market data. The tutorial's *eight-asset* values are hand-entered illustrative data, not a real bank portfolio. Its 40-asset example reports **85.5%** of exact Pareto hypervolume for hardware QAOA versus **84.4 +/- 1.3%** for matched random sampling; it expressly does **not** show quantum speedup. The [QAOA training pipeline](https://github.com/qiskit-community/qaoa_training_pipeline) and [Kotil et al.'s multi-objective QAOA paper](https://arxiv.org/abs/2503.22797) are implementation/method anchors.

[Enigma](https://arxiv.org/abs/2311.13546) is important prior art: application-level QAOA coefficient/node/edge transformations with local recovery. It cannot be presented as our invention. [OPAQUE](https://arxiv.org/abs/2502.16605), [SPYCE](https://arxiv.org/abs/2307.16799), and [HOST 2025's reverse-engineering study](https://doi.org/10.1109/HOST64725.2025.11050070) show that circuit obfuscation and attacks on it are active areas. QPF's possible novelty is an integrated, **attacker-tested, formally checked, cost-aware release policy** across observer types, not being the first privacy transformation.

### Build plan that directly extends QPF

1. Reproduce an 8-asset subset from the public 40-asset snapshot using the IBM tutorial's Hamiltonian/mixer recipe; freeze versions, `K`, subset, source CSV checksum, and seeds. Define three **synthetic** private preferences, such as risk-first/balanced/return-first.
2. Build an explicit artifact view of the outbound *ISA circuit plus PUB bindings*, and a structural-only view. Do not score one while implying the other. Add a trivial parameter-reading baseline before an ML attacker.
3. Test preference inference with group-held-out asset baskets, labels balanced within each basket, paired variation of **only** the weights, shuffled-label and metadata-only controls, adaptive post-defense training, and bootstrap intervals. If dataset size is tiny, call it an illustration, not evidence.
4. Reuse QPF's rewrite/budget/verification flow on bound supported unitary kernels, then compare decoded/selected portfolios and exact objective quality to baseline; use equal shots and a classical/random comparator. Record feasibility (`K` assets), risk, return, diversification, utility regret, Pareto hypervolume where appropriate, and noise-model caveats.
5. Implement `BLOCK` when confidential weights or coefficients remain explicitly readable. An optional narrow mode can submit a **fixed public sweep** of weight choices and select the preferred portfolio *locally* after results. If the outbound job is byte-identical across private preferences, the job carries no preference-specific information under that fixed-job model; it can still reveal the asset universe, Hamiltonian and candidate set. This adapts the tutorial's Pareto workflow; it is not new quantum cryptography and may cost more samples/jobs than a targeted run.

### Portfolio demo and figures

Use an 8-asset subset from the public CSV, `K=4`, and two private analyst preferences. Show the real-data input, cost Hamiltonian and XY-mixer circuit, structural-only versus full-payload exposure matrix, preference attack confusion matrices, and selected portfolios on a risk-return-diversification plot. Show an explicit `BLOCK` for a preference-bearing payload; if fixed public sweep is implemented, show **the same outbound job hash** under two different local preferences and different locally chosen portfolios. Label the security boundary precisely. Do not say the sweep hides a private covariance matrix or ticker universe; it does not.

## 3. Which use case should lead the pitch?

| Criterion | Confidential Grover cryptanalysis | Confidential portfolio QAOA |
|---|---|---|
| Fit to Security & Cryptography track | Direct and memorable: security for a quantum security research job | Indirect: protecting proprietary financial research |
| Existing code fit | Existing amplitude-amplification family and equivalence pipeline | Existing variational family, but no real portfolio Hamiltonian/payload attacker |
| Strongest external anchor | IBM Grover examples + published cloud timing leakage (different channel) | IBM real-data tutorial + IBM/Vanguard exploratory work |
| Hard security challenge | Full equivalent oracle often reveals `f`; must measure and potentially block | Numeric preference bindings can reveal `c` directly; must inspect payload and potentially block |
| Fastest truthful demo | Small oracle, exact recovery attacker, QCEC, overhead, BLOCK | 8-asset public snapshot, payload exposure, Pareto selection, BLOCK/fixed-sweep |
| Best role | **Flagship story** for cyber track | Credible second vertical: same preflight gate generalizes |

Do not tell judges that one experiment proves both. Show a common QPF engine with two **different protected facts**, two observation schemas, and two correct product decisions. The common technical contribution is a verification- and attacker-aware gate at the circuit-to-cloud boundary.

## 4. Decision table: existing evidence, proposed evidence, prohibited claims

| Statement | Status |
|---|---|
| "The compiled circuit can reveal coarse algorithm family in QPF's controlled benchmark." | **Measured** in this repo; cite the exact split/metadata caveats |
| "At 20% overhead, QPF reduces adaptive family attack macro-F1 from 0.916 to 0.878." | **Measured** on the saved synthetic benchmark; small absolute reduction, high residual leakage |
| "QPF hides a Grover oracle's marked state or an unreleased cipher property." | **Not measured; likely false for small full-circuit observer** without stronger mechanism |
| "QPF hides a portfolio manager's weight vector from the job recipient." | **Not measured; likely false when PUB bindings are visible** |
| "A locally fixed public Pareto sweep removes preference-specific job variation." | **Proposed design property** under explicit fixed-job assumptions; verify job hashes and metadata |
| "We have quantum advantage, protect AES/BB84, or serve an actual bank/customer." | **Unsupported**; never claim |

## 5. Shared engineering and evaluation checklist

- **Input:** safe local Qiskit API first; bounded QPY/QASM3 import only if time; no arbitrary Python execution. [QPY](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qpy) and [QASM3](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qasm3) have distinct fidelity/support tradeoffs.
- **Target:** pinned Qiskit version, fake backend, optimization level, seed, model/feature schema. Check backend ISA validity via [IBM's transpilation guide](https://quantum.cloud.ibm.com/docs/en/guides/transpile).
- **Correctness:** original/rewritten unitary where appropriate; terminal measurements and compiled layout preserved; UNKNOWN must block. For non-equivalent keyed transforms, define local decoding correctness separately.
- **Privacy:** define secret and observer for every result; exact/trivial attacker, structural attacker, payload attacker, adaptive retraining, grouped splits, random/shuffled control, uncertainty interval.
- **Utility/cost:** same shots and initial conditions; depth, two-qubit count, circuit run time, noisy success/portfolio quality, classical/random baseline. An [Aer noise model](https://qiskit.github.io/qiskit-aer/tutorials/2_device_noise_simulation) is simulation, not hardware validation.
- **Receipt:** provenance hashes, target, feature/model version, observer, secret tested, attacker score and residual risk, verification method/status, budget/cost, utility result, and release decision. No confidential predicate or weights in logs by default.

### Recommended 3-minute narrative

1. "Most quantum-security demos protect a message with quantum technology. We protect the **quantum job itself** before cloud submission." Show a small Grover communications-security research case.
2. Reveal the compiled circuit and two distinct attack results: *family recognition* and *oracle recovery*. Run rewrites, QCEC, overhead/utility checks. If recovery persists, QPF blocks. This is an honest, operational safety result.
3. Show the same engine on a public-data QAOA portfolio case: changing a private preference may leave structure unchanged while revealing numeric job bindings. QPF distinguishes those views; a fixed public sweep/local selection is an optional safe workflow if implemented and measured.
4. Close with the saved 24/48-qubit research numbers and the precise claim: **measured leakage, verified low-overhead mitigation where it works, explicit refusal where it does not**.

## Primary-source ledger

| Source | Directly useful fact | QPF use / boundary |
|---|---|---|
| [IBM Research, QCE 2026 intent study](https://research.ibm.com/publications/algorithmic-intent-leakage-in-transpiled-quantum-circuits-an-initial-reverse-engineering-study) | Seven-class structural intent inference from final transpiled circuits | Scientific starting point; QPF is independent implementation, not IBM endorsement |
| [IBM Grover tutorial](https://quantum.cloud.ibm.com/docs/en/tutorials/grovers-algorithm) | Oracle/amplitude-amplification construction | Runnable cyber workload, not proof of actual deployed cryptanalysis |
| [Qiskit Grover examples](https://qiskit-community.github.io/qiskit-algorithms/tutorials/07_grover_examples.html) | Boolean and DIMACS oracle examples | Public, reproducible secret-specific test seeds |
| [Quantum Leak](https://arxiv.org/abs/2401.01521) | Cloud timing side-channel oracle leakage | External motivation; different observer/attack channel |
| [NIST PQC FAQ](https://csrc.nist.gov/Projects/Post-Quantum-Cryptography/faqs), [Grover/AES cost](https://csrc.nist.gov/csrc/media/Events/2024/fifth-pqc-standardization-conference/documents/papers/on-practical-cost-of-grover.pdf) | Practical cryptanalysis limits | Prevent AES-break exaggeration |
| [IBM multi-objective portfolio tutorial](https://quantum.cloud.ibm.com/docs/en/tutorials/quantum-approximate-multi-objective-optimization), [market CSV](https://raw.githubusercontent.com/Qiskit/documentation/main/datasets/tutorials/qmoo/market_data.csv) | Working QAOA recipe, public real-data snapshot, honest random comparator | Reproducible finance test; no quantum-advantage claim |
| [Qiskit primitive input/output](https://quantum.cloud.ibm.com/docs/en/guides/primitive-input-output) | PUBs include parameter values | Full-payload threat model |
| [IBM/Vanguard study](https://www.ibm.com/quantum/blog/vanguard-portfolio-optimization), [GDQ optimizer tutorial](https://quantum.cloud.ibm.com/docs/en/tutorials/global-data-quantum-optimizer) | Industry exploratory quantum portfolio work | Real-world relevance, not production/privacy incident |
| [Enigma](https://arxiv.org/abs/2311.13546) | QAOA problem-level transformations and local recovery | Prior art/comparator, not QPF invention |
| [OPAQUE](https://arxiv.org/abs/2502.16605), [SPYCE](https://arxiv.org/abs/2307.16799), [HOST 2025](https://doi.org/10.1109/HOST64725.2025.11050070) | Obfuscation designs and structural attacks | Novelty context and adaptive-attack requirement |
| [MQT QCEC](https://mqt.readthedocs.io/projects/qcec/en/stable/), [compilation-flow guide](https://github.com/munich-quantum-toolkit/qcec/blob/main/docs/compilation_flow_verification.md) | Circuit/compilation equivalence; measurement mapping matters | Correctness gate, not privacy proof |
| [Qiskit Aer noise tutorial](https://qiskit.github.io/qiskit-aer/tutorials/2_device_noise_simulation) | Device-inspired simulation | Utility experiment, not hardware guarantee |
| [Official Q-Hack India page](https://www.quantumweek.tech/hackathon) | Track, timing, scoring | Tailor story to security and technical evaluation |

Social/company promotion was not used as proof of security efficacy. No cited source documents a present-day breach caused by algorithm-family leakage in a deployed cryptanalysis or portfolio workflow. This is an emerging **pre-submission risk** with a concrete research foundation, not an incident response product.
