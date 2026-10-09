"""Logical circuit families (plan M1). Every circuit is a pure function of (family, width, seed)."""
import numpy as np, networkx as nx
from qiskit import QuantumCircuit
from qiskit.synthesis.qft import synth_qft_full

FAMILIES = ("qft", "grover", "qaoa", "graph_ghz")
CONTROL = "random"

def _qft(n, rng):
    qc = QuantumCircuit(n)
    for i in np.flatnonzero(rng.integers(0, 2, n)): qc.x(int(i))
    qc.compose(synth_qft_full(n, approximation_degree=int(rng.integers(0, 3)), do_swaps=True), inplace=True)
    return qc

def _grover(n, rng):
    marked = rng.integers(0, 2, n); qc = QuantumCircuit(n); qc.h(range(n))
    def mcz():
        qc.h(n - 1); qc.mcx(list(range(n - 1)), n - 1); qc.h(n - 1)
    for _ in range(int(rng.integers(1, 3))):
        for i, b in enumerate(marked):
            if b == 0: qc.x(i)
        mcz()
        for i, b in enumerate(marked):
            if b == 0: qc.x(i)
        qc.h(range(n)); qc.x(range(n)); mcz(); qc.x(range(n)); qc.h(range(n))
    return qc

def _qaoa(n, rng):
    g = nx.random_regular_graph(3 if n % 2 == 0 else 2, n, seed=int(rng.integers(1 << 31)))
    qc = QuantumCircuit(n); qc.h(range(n))
    for _ in range(int(rng.integers(1, 4))):
        gamma, beta = rng.uniform(0, np.pi, 2)
        for u, v in g.edges: qc.rzz(float(2 * gamma), u, v)
        for q in range(n): qc.rx(float(2 * beta), q)
    return qc

def _graph_ghz(n, rng):
    qc = QuantumCircuit(n)
    if rng.random() < 0.5:                       # GHZ-type: entangle along a random tree
        order = [int(x) for x in rng.permutation(n)]; qc.h(order[0])
        for i in range(1, n): qc.cx(order[int(rng.integers(0, i))], order[i])
    else:                                        # graph state on a connected random graph
        for _ in range(200):
            g = nx.gnp_random_graph(n, float(rng.uniform(0.25, 0.5)), seed=int(rng.integers(1 << 31)))
            if nx.is_connected(g): break
        else: g = nx.path_graph(n)
        qc.h(range(n))
        for u, v in g.edges: qc.cz(u, v)
    return qc

def _random(n, rng):
    qc = QuantumCircuit(n)
    for _ in range(int(rng.integers(6, 16))):
        for i in range(n): qc.rz(float(rng.uniform(0, 6.28)), i); qc.sx(i)
        p = rng.permutation(n)
        for a, b in zip(p[::2], p[1::2]): qc.cz(int(a), int(b))
    return qc

_GEN = {"qft": _qft, "grover": _grover, "qaoa": _qaoa, "graph_ghz": _graph_ghz, CONTROL: _random}

def make_circuit(family, width, seed):
    return _GEN[family](int(width), np.random.default_rng(int(seed)))
