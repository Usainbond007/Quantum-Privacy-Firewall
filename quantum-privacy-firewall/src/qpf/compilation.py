"""Backend-targeted compilation (plan M0/M1). Backend objects are cached per process."""
import time, warnings, numpy as np, networkx as nx
from qiskit import transpile
warnings.filterwarnings("ignore")
_B = {}

def get_backend(name="FakeNighthawk"):
    if name not in _B:
        from qiskit_ibm_runtime import fake_provider
        _B[name] = getattr(fake_provider, name)()
    return _B[name]

def backend_info(name="FakeNighthawk"):
    b = get_backend(name)
    return {"name": name, "num_qubits": b.num_qubits, "operations": sorted(b.operation_names)}

def random_connected_layout(n, rng, name="FakeNighthawk"):
    """Random connected set of n physical qubits in random order (layout diversification)."""
    key = ("g", name)
    if key not in _B: _B[key] = nx.Graph(list(get_backend(name).coupling_map.get_edges()))
    g = _B[key]; nodes = list(g.nodes)
    chosen = {nodes[int(rng.integers(len(nodes)))]}
    while len(chosen) < n:
        frontier = sorted({v for u in chosen for v in g[u]} - chosen)
        chosen.add(frontier[int(rng.integers(len(frontier)))])
    out = sorted(chosen); rng.shuffle(out)
    return [int(x) for x in out]

def compile_circuit(qc, opt, seed, layout=None, name="FakeNighthawk"):
    t = time.perf_counter()
    tc = transpile(qc, backend=get_backend(name), optimization_level=int(opt),
                   seed_transpiler=int(seed), initial_layout=layout)
    return tc, time.perf_counter() - t
