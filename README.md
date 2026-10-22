# Quantum Privacy Firewall

A Qiskit-based framework for studying and reducing algorithmic-intent leakage in compiled quantum circuits.

Developed by Fork Around & Find Out for Q-Hack India 2026, under the Quantum Security & Cryptography track.

**Built with:** Python · Qiskit · scikit-learn · MQT QCEC · Jupyter · FastAPI · React

---

## Why we built this

A quantum algorithm doesn't go straight from a developer's code to a quantum processor.

Before it can execute, the circuit must be compiled into operations supported by the target hardware. Qiskit handles this through transpilation, which involves translating gates, mapping logical qubits onto physical qubits, routing interactions, and optimizing the resulting circuit.

This process changes how the program is represented, but it doesn't necessarily hide what the program does.

A compiled circuit still contains patterns. Some algorithms use particular combinations of gates. Others produce characteristic interaction patterns, circuit depths, or distributions of two-qubit operations across the processor.

An observer who can inspect the final circuit may be able to recognize these patterns and infer the type of algorithm being executed, even without seeing the original source code.

For developers working on proprietary quantum algorithms, this introduces a different kind of information-exposure problem.

The program's source code can remain private while its computational purpose becomes partially identifiable.

We wanted to investigate whether this information could be reduced before the circuit leaves the developer's environment.

That became Quantum Privacy Firewall.

## Research background

Our starting point was the work of Beat Buesser and Anil Kurmus at IBM Research, *Algorithmic Intent Leakage in Transpiled Quantum Circuits: An Initial Reverse-Engineering Study*, presented at IEEE Quantum Week 2026.

Their study investigates how accurately the broad algorithmic purpose of a quantum workload can be recovered from its backend-transpiled circuit.

The researchers use structural features extracted from physical circuits and a machine-learning classifier to distinguish seven categories of quantum algorithms.

Their results show that algorithm families can be highly recognizable when training and testing conditions match. They also demonstrate that changing compilation settings can significantly affect classification performance.

What interested us most was a direction discussed in their future work: using compilation randomization and structure-preserving transformations to make algorithmic intent harder to recover.

We contacted Dr. Buesser during our research, and he kindly shared additional material that helped us understand the experimental methodology.

We decided to build on that question.

**If a quantum circuit reveals information about its algorithm, can we produce a different circuit that performs the same computation but reveals less?**

QPF is our attempt to investigate that problem experimentally.

Our implementation is independent. We did not use IBM Research's original source code or dataset. The paper names its generators without defining them, so our generators are our own interpretation of the Table I names.

## What Quantum Privacy Firewall does

QPF combines a circuit-leakage auditor with an experimental privacy-aware compilation layer.

The auditor measures how much information about an algorithm's family can be recovered from its compiled representation.

The firewall then explores alternative implementations of the same quantum computation.

These alternatives are generated using different qubit layouts, gate decompositions, transpiler seeds, and operation orderings where the dependencies permit them.

A candidate cannot be selected simply because it looks different.

It must pass the applicable equivalence check, compile for the target backend, and satisfy the configured hardware-overhead limits. Whether the rewrite actually changes the compiled circuit's features is measured and reported separately.

Finally, QPF evaluates whether an attacker can still identify the algorithm after being retrained on protected circuits.

This last step matters. A transformation that confuses an existing classifier may become recognizable once the attacker has seen examples of it.

Our objective is to measure whether a defense remains useful under those conditions, rather than assuming that structural changes automatically provide confidentiality.

## How the system works

The project has two main parts: reproducing the algorithm-intent classification experiment and evaluating circuit transformations against that attacker.

### 1. Building the workload library

We implemented 47 circuit generators organized into seven algorithm-intent classes.

| Algorithm family | Representative circuits |
|---|---|
| Entanglement generation | GHZ states, graph states, cluster states |
| Fourier-like | Quantum Fourier Transform, inverse QFT, phase estimation |
| Phase/oracle-like | Parity oracles, phase oracles, diagonal phase patterns |
| Amplitude amplification | Grover search and related amplification circuits |
| Variational ansatz | Hardware-efficient ansätze, QAOA |
| Hamiltonian simulation | Trotterized Ising, XXZ and Heisenberg models |
| Arithmetic/permutation | Ripple adders, incrementers, Toffoli networks |

The paper-aligned benchmark uses six source variants per generator, with 24- and 48-qubit circuit configurations.

Across four transpiler optimization levels, this produces 2,256 transpiled circuit records.

We also developed generator tests during implementation. These caught errors in the incrementer, comparator, and parity-amplitude-amplification circuits, which were corrected before the reported final experiments.

The generator audit distinguishes 24 semantically tested generators, 20 structurally tested generators, and three analogue constructions. These categories reflect the different kinds of evidence available for their intended behavior.

Code: `src/qpf/paper_circuits.py`

### 2. Compiling the circuits

We use Qiskit to compile the workloads against FakeNighthawk, a 120-qubit simulated backend target.

The experiments cover optimization levels 0, 1, 2, and 3.

Transpilation converts the logical circuit into a backend-compatible representation, accounting for native gates and physical connectivity.

This is the representation observed by our attacker.

The choice of optimization level is important because the compiler can change gate distributions, interaction patterns, and circuit structure. We therefore study both classification within a compilation setting and transfer between different settings.

Code: `src/qpf/compilation.py`

### 3. Extracting structural features

Each transpiled circuit is represented by ten normalized features based on Table II of the original study.

They describe gate composition, how two-qubit operations are distributed over time, and how activity is distributed across the backend.

| Feature | Description |
|---|---|
| Two-qubit gate fraction | Relative frequency of two-qubit operations |
| Phase/rotation fraction | Relative frequency of phase and rotation operations |
| Single-qubit gate entropy | Diversity of single-qubit gate types |
| Two-qubit layer fraction | Fraction of layers containing two-qubit operations |
| Mean two-qubit activity | Average two-qubit operations per layer |
| Layer-load Gini | Concentration of two-qubit operations across layers |
| Used-edge fraction | Fraction of hardware edges used |
| Edge-load Gini | Concentration of operations across hardware edges |
| Maximum edge-load fraction | Activity concentrated on the most-used edge |
| Qubit-load Gini | Concentration of two-qubit operations across qubits |

The implementation also records basic circuit properties such as depth, gate count, two-qubit-gate count, and active physical qubits.

Those measurements are used for resource accounting and for control experiments that help us understand what the classifier is learning.

Some feature conventions are independently specified because the research document does not provide every computational detail.

Code: `src/qpf/paper_features.py`

### 4. Measuring algorithm-intent leakage

We train a Random Forest classifier to predict the algorithm family from the extracted features.

A central requirement is that different compiled versions of the same source circuit must not appear on both sides of the train/test split.

Otherwise, the model might recognize an example it has effectively encountered before, giving an inflated impression of generalization.

Our benchmark uses source-circuit-disjoint partitions and training-only grouped cross-validation for hyperparameter selection.

We evaluate classification under several conditions:

- Training and testing at the same optimization level.
- Transferring between optimization levels.
- Transferring between 24- and 48-qubit workloads.
- Training across both circuit sizes.
- Testing on generator types excluded from training.

We also compare the main classifier against shuffled-label and metadata-only controls.

Code: `src/qpf/paper_benchmark.py`

## The firewall

Once we have measured the attacker's performance, we investigate whether the observable circuit structure can be changed without altering the intended computation.

QPF currently explores the following strategies.

| Transformation | What changes |
|---|---|
| Gate re-decomposition | Equivalent sequences of quantum gates |
| Operation reordering | Ordering of operations where dependencies permit |
| Layout diversification | Mapping between logical and physical qubits |
| Transpiler-seed variation | Compilation decisions influenced by random seeds |
| Combined transformations | Multiple strategies applied together |

These transformations can produce different physical circuit structures, but not every attempted rewrite survives compilation.

For example, Qiskit's optimizer may remove or normalize a gate sequence, leaving the resulting circuit structurally unchanged.

For that reason, QPF evaluates the compiled output rather than treating every logical rewrite as a successful transformation.

Code: `src/qpf/defenses.py`

### Equivalence verification

Changing a quantum circuit is only useful if the intended computation is preserved.

Our verification pipeline uses Qiskit operator checks, MQT QCEC where applicable, and structural-identity checks.

Verification outcomes are recorded as `PASS`, `FAIL`, or `UNKNOWN`.

Only candidates with sufficient equivalence evidence are eligible for selection. A candidate that cannot be verified is not silently accepted.

The reported full defense experiment contains 1,974 candidate records with the following logical-equivalence verification outcomes:

| Verification method | Count |
|---|---:|
| MQT QCEC | 846 |
| DAG identity | 564 |
| Identical logical circuit | 564 |
| Total | 1,974 |

These checks establish the applicable logical-equivalence properties under their verification assumptions. They are separate from measurements of execution fidelity on noisy physical hardware.

Code: `src/qpf/verification.py`

### Hardware-overhead budgets

An equivalent circuit may still be impractical if it requires too many additional operations.

QPF therefore measures the cost of each candidate relative to the original compiled circuit.

The current experiments consider circuit depth, two-qubit-gate count, and active physical qubits.

We evaluate overhead budgets of 0%, 10%, 20%, and 50%.

Candidates that exceed the configured limits are excluded.

Among eligible candidates, guided selection picks the one that a frozen surrogate classifier, trained on training circuits only, is least confident about. No labels are used at selection time. We also compare this strategy with randomly selecting an eligible circuit, allowing us to investigate whether the guidance adds value beyond circuit diversification alone.

Code: `src/qpf/selection.py`

### Evaluating an adaptive attacker

A classifier trained only on original circuits may perform poorly on transformed circuits because the new examples follow a different distribution.

That is not sufficient evidence that the underlying algorithmic information has disappeared.

An informed attacker may be able to retrain on transformed examples.

QPF therefore evaluates static, adaptive, and normalization-aware attackers.

The adaptive attacker is trained on protected training circuits and evaluated on protected circuits it has not previously seen.

The normalization-aware evaluation applies an additional compilation-based normalization step before classification.

We use these experiments to distinguish changes that affect a frozen classifier from changes that remain useful against a more informed attacker.

Code: `src/qpf/paper_defense.py`

## What we found

The following figures come from the project's recorded full benchmark and defense experiments.

### Reproducing the intent-leakage experiment

Our independently implemented benchmark shows the same broad pattern reported in the original study: high classification performance when compiler settings match, and substantially different performance when the compilation regime changes.

| Evaluation | Our result |
|---|---:|
| Within optimization level | 0.93–0.99 accuracy |
| Cross-level transfer, excluding levels 2 ↔ 3 | 0.22–0.52 accuracy |
| Level 2 → 3 | 0.906 |
| Level 3 → 2 | 0.912 |
| Within 24-qubit setting | 0.935 |
| Within 48-qubit setting | 0.960 |
| 24 → 48 transfer | 0.634 |
| 48 → 24 transfer | 0.250 |
| Joint training, tested at 24 qubits | 0.953 |
| Joint training, tested at 48 qubits | 0.960 |

These results are not numerically identical to the original study. Our generators, dataset construction, and some feature conventions are independently implemented.

The broad behavior is nevertheless similar.

We also found two results that changed how we interpreted the attack.

First, a classifier trained only on basic circuit metadata achieved approximately 0.938 accuracy, compared with 0.956 using the full structural feature representation.

Second, classification on held-out generator types dropped to approximately 0.687 ± 0.050.

These observations suggest that circuit complexity and generator-specific characteristics account for a substantial part of the measured classification signal.

They also show why high classification accuracy should not automatically be interpreted as recovery of deeper proprietary algorithm details.

### Does the firewall help?

We evaluated the defense against a Random Forest attacker retrained on protected circuits.

The reported unprotected adaptive baseline was 0.916 ± 0.007 macro-F1.

| Overhead budget | Guided defense | Random eligible selection | Paired 95% CI for guided reduction |
|---|---:|---:|---|
| 0% | 0.904 | 0.914 | −0.006 to +0.030 |
| 10% | 0.879 | 0.900 | +0.017 to +0.058 |
| 20% | 0.878 | 0.887 | +0.017 to +0.059 |
| 50% | 0.865 | 0.883 | +0.029 to +0.073 |

At the 50% budget, adaptive attacker macro-F1 decreased from 0.916 to 0.865.

This is an absolute reduction of 0.051.

The selected circuits in that setting recorded approximately 5.5% additional depth and 3.5% additional two-qubit gates.

Guided selection performed better than random eligible-candidate selection in the reported comparisons.

However, the attacker still achieved relatively high classification performance.

The results therefore support a modest reduction in algorithm-family recoverability under the tested conditions, not complete protection of the algorithm.

The metadata-only control remained strong, and the normalization-aware evaluation does not currently provide a directly paired unprotected baseline from which to estimate a separate defense effect.

The defense experiments cover 24-qubit circuits at optimization levels 0, 2 and 3, whereas the attack benchmark includes both 24- and 48-qubit circuits at levels 0-3. Equivalence is checked on the logical rewrites rather than on the final compiled circuits, and all experiments use one simulated backend (FakeNighthawk), a single transpile seed and six variants per generator. Of the 47 generators, 24 are checked semantically, 20 structurally and 3 are structural analogues; the earlier four-family results in `artifacts/quick` are exploratory and are not evidence of a working defense. These distinctions define the scope of the reported results.

These findings are an important part of the project. They show both what our transformations accomplish and where the remaining information exposure lies.

## Running the project

The repository contains the paper-aligned benchmark, the original exploratory pipeline, Jupyter demonstrations, and an interactive web application.

### Requirements

- Python 3.10 or newer, with a compatible Qiskit environment (the backend lock file records a Python 3.14 / Windows environment)
- Git
- Python dependencies from `requirements.txt`
- Node.js 20.19+ or 22.12+ for the React application (Vite 7)

### Installation

Clone the repository:

```bash
git clone https://github.com/Usainbond007/qpf.git
cd qpf
```

Create a virtual environment:

```bash
python -m venv .venv
```

On macOS or Linux:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -e .
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e .
```

### Run a smaller experiment

The smoke profile is useful for checking the experiment pipeline without running the full benchmark.

From the repository root:

```bash
python scripts/build_paper_dataset.py --profile smoke
python scripts/run_paper_benchmark.py --profile smoke
python scripts/run_paper_defense.py --profile smoke
```

Smoke results are intended for functional checks and should not be substituted for the full benchmark.

### Reproduce the paper-aligned experiments

On a Unix-compatible shell:

```bash
cd scripts
./run_all_paper.sh full 2
```

The script runs dataset construction, benchmark evaluation, and defense evaluation.

Saved artifacts and checkpointing support recovery of long-running work, although not every computation has the same checkpoint granularity.

The main outputs are stored under:

`artifacts/paper_full/`

These include benchmark results, comparison tables, defense results, and saved intermediate data.

### Run the notebooks

The paper-aligned notebook is:

```bash
jupyter lab notebooks/attack_and_defense.ipynb
```

It walks through the attack, candidate transformations, verification, and saved benchmark results.

The original interactive notebook is:

```bash
jupyter lab notebooks/demo.ipynb
```

This notebook uses the earlier four-family, 13-feature experimental pipeline. Its results should not be confused with the seven-family paper-aligned benchmark.

A terminal example is also available:

```bash
python scripts/attack_example.py
```

## Interactive circuit lab

Alongside the research scripts, we developed a web interface for exploring individual quantum circuits.

The application uses FastAPI for the backend and React for the frontend.

It allows users to select a circuit, generate transformation candidates, inspect verification outcomes, compare physical circuit representations, and examine resource costs.

The circuit viewer supports zooming, gate inspection, and logical-to-physical qubit mapping.

The interactive lab and the full research benchmark serve different purposes.

The lab demonstrates the transformation process for a selected circuit. The benchmark evaluates attacker performance across datasets.

A single-circuit prediction should not be interpreted as a dataset-level privacy measurement.

### Start the backend

From the repository root, after installing the backend dependencies:

```bash
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

### Start the frontend

In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open:

`http://localhost:5173`

The backend API documentation is available at:

`http://127.0.0.1:8000/docs`

The application can also serve a built frontend from FastAPI after running `npm run build`.

Run a single Uvicorn process (no `--workers`), since the job store is local. This is a local demo without authentication or a distributed job queue.

## Repository guide

| Path | What you'll find |
|---|---|
| `src/qpf/paper_circuits.py` | Seven-family quantum circuit generators |
| `src/qpf/paper_features.py` | Ten paper-aligned structural features |
| `src/qpf/paper_benchmark.py` | Classification and transfer experiments |
| `src/qpf/paper_defense.py` | Adaptive defense evaluation |
| `src/qpf/defenses.py` | Circuit transformation strategies |
| `src/qpf/verification.py` | Equivalence-verification logic |
| `src/qpf/selection.py` | Budget rejection rules (guided and random selection for the benchmark are in `paper_defense.py`) |
| `config/` | Experiment configurations and seeds |
| `scripts/` | Command-line experiment entry points |
| `notebooks/` | Research demonstrations |
| `backend/` | FastAPI application |
| `frontend/` | React application |
| `tests/` | Automated tests |
| `artifacts/` | Saved datasets and experiment outputs |
| `docs/` | Generator audit and experiment status |

The repository retains the earlier four-family research pipeline for comparison and for parts of the interactive demonstration.

The seven-family, ten-feature benchmark is the primary experiment discussed in this README.

## Testing and reproducibility

Run the Python tests from the repository root:

```bash
python -m pytest -q tests backend/tests
```

For the frontend:

```bash
cd frontend
npm ci
npm test
npm run build
```

The project status report records 167 passing Python tests and eight passing frontend tests in the team's validated environment.

The tests cover circuit-generator behavior, dataset partitioning, feature extraction, equivalence checks, rejection of incorrect transformations, budget handling, API behavior, and reproducibility-related checks.

Experiment configurations, random seeds, and saved outputs are retained to make the reported results traceable.

The generator audit and experiment status are documented separately in:

- `docs/GENERATOR_AUDIT.md`
- `docs/STATUS.md`

## Research and acknowledgments

Our primary research reference is:

Beat Buesser and Anil Kurmus.  
*Algorithmic Intent Leakage in Transpiled Quantum Circuits: An Initial Reverse-Engineering Study.*  
IBM Research, IEEE Quantum Week 2026.

[IBM Research publication](https://research.ibm.com/publications/algorithmic-intent-leakage-in-transpiled-quantum-circuits-an-initial-reverse-engineering-study)

We are grateful to Dr. Beat Buesser for responding to our research inquiry and sharing additional material that helped us better understand the study.

QPF is an independent implementation and experimental extension of that research direction. The original study's authors are not responsible for our implementation, experimental choices, or conclusions.

We also acknowledge the tools and open-source projects used throughout development, particularly Qiskit, scikit-learn, MQT QCEC, FastAPI, and React.

## Team

**Fork Around & Find Out**

Q-Hack India 2026  
Quantum Security & Cryptography

---

Quantum Privacy Firewall began with a simple question: how much can someone learn about a quantum algorithm from the circuit that eventually reaches the hardware?

Our work attempts to answer the next question—whether we can change that observable circuit without changing the computation, and whether doing so makes the algorithm harder to identify even when the attacker knows how the defense works.