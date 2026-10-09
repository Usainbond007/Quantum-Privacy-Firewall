"""Semantics-preserving transformation families (plan M3):
   decomp  : equivalent local decompositions     reorder : random legal (dependency-respecting) reordering
   layout  : random connected physical layout (compile-time diversification; logical circuit unchanged)"""
import numpy as np
from qiskit import QuantumCircuit
from . import compilation

def _cx(o, op, q, r): o.h(q[1]); o.cz(q[0], q[1]); o.h(q[1])
def _cz(o, op, q, r): o.h(q[1]); o.cx(q[0], q[1]); o.h(q[1])
def _h(o, op, q, r): o.rz(np.pi / 2, q[0]); o.sx(q[0]); o.rz(np.pi / 2, q[0])        # H = RZ(pi/2) SX RZ(pi/2) up to phase
def _x(o, op, q, r): o.sx(q[0]); o.sx(q[0])
def _rx(o, op, q, r): o.h(q[0]); o.rz(float(op.params[0]), q[0]); o.h(q[0])
def _swap(o, op, q, r):
    a, b = q if r.random() < 0.5 else q[::-1]; o.cx(a, b); o.cx(b, a); o.cx(a, b)
def _cp(o, op, q, r):
    th = float(op.params[0]); c, t = q
    o.p(th / 2, c); o.cx(c, t); o.p(-th / 2, t); o.cx(c, t); o.p(th / 2, t)
def _rzz(o, op, q, r): o.cx(q[0], q[1]); o.rz(float(op.params[0]), q[1]); o.cx(q[0], q[1])
RULES = {"cx": _cx, "cz": _cz, "h": _h, "x": _x, "rx": _rx, "swap": _swap, "cp": _cp, "rzz": _rzz}

def decompose_rewrite(qc, rng, p=0.7):
    out = QuantumCircuit(qc.num_qubits); out.global_phase = qc.global_phase
    for inst in qc.data:
        op, qs = inst.operation, [qc.find_bit(q).index for q in inst.qubits]
        if op.name in RULES and rng.random() < p: RULES[op.name](out, op, qs, rng)
        else: out.append(op, qs)
    return out

def random_reorder(qc, rng):
    ops = [(i.operation, [qc.find_bit(q).index for q in i.qubits]) for i in qc.data]
    n = len(ops); indeg = [0] * n; succ = [[] for _ in range(n)]; last = {}
    for k, (_, qs) in enumerate(ops):
        for p in {last[q] for q in qs if q in last}: succ[p].append(k); indeg[k] += 1
        for q in qs: last[q] = k
    ready = [k for k in range(n) if indeg[k] == 0]
    out = QuantumCircuit(qc.num_qubits); out.global_phase = qc.global_phase
    while ready:
        k = ready.pop(int(rng.integers(len(ready)))); out.append(*ops[k])
        for s in succ[k]:
            indeg[s] -= 1
            if indeg[s] == 0: ready.append(s)
    assert out.size() == qc.size()
    return out

def apply_strategy(base, strategy, seed, backend_name="FakeNighthawk"):
    """-> (candidate logical circuit, initial_layout or None). Deterministic in (strategy, seed)."""
    rng = np.random.default_rng(int(seed)); parts = strategy.split("+"); cand, layout = base, None
    if "decomp" in parts: cand = decompose_rewrite(cand, rng)
    if "reorder" in parts: cand = random_reorder(cand, rng)
    if "layout" in parts: layout = compilation.random_connected_layout(base.num_qubits, rng, name=backend_name)
    return cand, layout
