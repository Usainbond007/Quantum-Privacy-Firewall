import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from qpf import paper_circuits as PC
from collections import Counter
c = Counter(PC.AUDIT.values()); L = ["# Generator audit (Table I, 47 generators)", "",
  "The paper names the generators but does not define them; every generator is our interpretation. The tier says how much of each is actually verified by `tests/test_generator_audit.py` and `tests/test_paper_circuits.py`:", "",
  "- **semantic**: a mathematical invariant is checked (statevector, truth table / classical reference, stabilizers, analytic probability, Bernstein-Vazirani recovery).",
  "- **structural**: gate content and qubit topology are checked against the named construction; the dynamics/semantics are NOT checked.",
  "- **analogue**: only normalisation, exact width and determinism are checked; the circuit is a structural stand-in for its name.", "",
  f"Totals: {c['semantic']} semantic, {c['structural']} structural, {c['analogue']} analogue (of {len(PC.AUDIT)}).", "", "| class | generator | tier |", "|---|---|---|"]
for g, k in PC.GENERATORS.items(): L.append(f"| {k} | {g} | {PC.AUDIT[g]} |")
L += ["", "Bugs found by this audit and fixed: `incrementer` (ancillas randomly initialised), `comparator` (carry uncompute not the inverse), `parity_amplitude_amplification` (phase-kickback ancilla prepared in |+> instead of |->, so the oracle was a no-op)."]
pathlib.Path(__file__).resolve().parents[1].joinpath("docs/GENERATOR_AUDIT.md").write_text("\n".join(L) + "\n"); print(dict(c))
