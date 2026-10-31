# A three-minute demonstration

## 0:00–0:35 — Start from the real problem

Open Confidential Cryptanalysis → Workload.

“Our starting point is a normal classical question: which input satisfies this private test? To study it with Grover search, the team encodes the condition into an oracle and adds amplitude amplification. The job artifact itself now carries clues about the condition. QPF inspects that artifact before the researcher shares it.”

Use the three-step explanation. State that this is a four-bit synthetic example, not a current attack on AES. The value is testing the disclosure boundary, not demonstrating speedup.

## 0:35–1:30 — Show the live negative finding

Keep pattern `1010`, budget `20%`, and click Run live assessment.

- The backend builds the circuit and evaluates 12 rewrites.
- Compare original and selected candidate: logical and compiled equivalence, resource overhead and output-distribution distance.
- The pattern reader may miss a rewritten form. The exact logical simulator still identifies the same target as the most likely outcome.
- The result is BLOCK. A correct rewrite does not mean a secret is hidden.
- Select a candidate row to show the actual verification method; open Transform to inspect its gate-level circuit.

Say: “This is the important outcome: QPF does not paint a circuit green just because the gates look different. It explains which attack changed and which exposure remains.”

## 1:30–2:20 — Show why the observer matters

Open Portfolio Optimization. Compare risk-first with return-first; run the assessment.

“The classical decision is to choose four of eight assets. Our quantum cost angles encode a private risk/return preference. The template can be identical across preferences while the numeric bindings reveal the weights. A reader with the public market data reconstructs them. Structural obfuscation alone does not address that payload.”

Show recovered weights, reconstruction residual, feasibility and correctness/cost evidence. Direct disclosure is BLOCK. Explain that this parameter attack is against original logical bindings, not a measured post-rewrite compiled attack.

## 2:20–2:45 — Show a different workflow

Scroll to the fixed public sweep. Show the two identical full SHA-256 values, three compiled PASS checks, and local portfolio picks.

“Everyone submits the same public candidate sweep. The private choice is made locally afterward. The logical job no longer changes with the analyst’s preference, but the public model and asset universe remain visible. It also takes three circuit evaluations instead of one. That is a scoped WARN, not a claim of encrypted quantum computation.”

The table compares choices with exact enumeration and uniform random portfolios. Explain regret rather than claiming quantum advantage. Results are exact noiseless simulations, not finite-shot hardware runs.

## 2:45–3:00 — State the contribution precisely

Open Research & evidence, then optionally Circuit Lab.

“Our contribution is the integration: a declared observer and sensitive fact, attack-tested circuit changes, equivalence checks, resource budgets and an explicit assessment with a receipt. The saved family benchmark and these domain-specific experiments answer different questions. We build on existing obfuscation research; we do not claim to have invented quantum cryptography.”

## Likely questions

**If you block the Grover circuit, is the firewall working?**
It correctly identifies a supported disclosure risk and refuses a privacy claim. It does not provide a mechanism that makes that full function secret. Actual cloud enforcement is outside this local demo.

**Is this post-quantum cryptography or QKD?**
No. It assesses information disclosed by quantum computation artifacts. It does not protect a communications channel or replace PQC.

**Does passing verification establish security?**
No. It establishes the scoped functional-equivalence contract. Security depends on the secret, observer and attacker tests. UNKNOWN must never be treated as PASS.

**Where is the novelty?**
The proposed engineering/research contribution is the joint verification-, attacker- and budget-aware decision workflow across two different secrets and observer views. A broad first-of-its-kind claim would require a fuller literature comparison. Enigma, SPYCE and OPAQUE are acknowledged prior art.

**Does fixed sweep hide the bank's market model?**
No. Only preference-specific variation is removed from the compared logical template and bindings. Market coefficients, assets, timing and metadata are not hidden by that hash comparison.

**How do you transition from classical to quantum?**
A Boolean predicate becomes a phase oracle plus amplification. A constrained classical portfolio objective becomes cost angles plus number-preserving mixing. This app compares against tractable classical reference calculations and does not claim an advantage at these sizes.
