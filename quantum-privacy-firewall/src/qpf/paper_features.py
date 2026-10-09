"""Paper-aligned *independent interpretation* of Buesser & Kurmus QCE 2026 Table II.

This is NOT author source code. Definitions requiring conventions (gate families,
layer scheduling, denominator for hardware edges) are explicitly parameterized.
No model trained on legacy_v1 features may be used with these features.
"""
from collections import Counter, defaultdict
from math import log
import numpy as np
from .features import gini

PAPER_FEATURE_VERSION = 'qce2026_table2_interpretation_v1'
PAPER_FEATURE_NAMES = (
    'two_qubit_fraction', 'phase_rotation_fraction', 'single_qubit_type_entropy',
    'two_qubit_layer_fraction', 'mean_two_qubit_operations_per_layer',
    'layer_two_qubit_gini', 'used_hardware_edge_fraction',
    'edge_two_qubit_gini', 'max_edge_load_fraction', 'qubit_two_qubit_gini'
)
DEFAULT_PHASE_ROTATION_GATES = frozenset({'rz', 'rx', 'ry', 'p', 'u', 'u1', 'u2', 'u3', 'r', 'rxx', 'ryy', 'rzz', 'rzx', 'cp', 'crx', 'cry', 'crz'})

def _entropy(counts):
    counts = np.asarray(list(counts), dtype=float)
    if not len(counts) or counts.sum() <= 0: return 0.0
    p = counts[counts > 0] / counts.sum()
    return float(-(p * np.log(p)).sum())  # natural-log Shannon entropy; NOT normalized

def extract_paper_features(circuit, coupling_edges, phase_gates=DEFAULT_PHASE_ROTATION_GATES, gini_population='all'):
    """Return Table-II-ordered features from observable final physical circuit.

    `coupling_edges` must be the target's full list of physical two-qubit edges.
    Assumptions: barriers/delays excluded; all other instructions counted;
    greedy ASAP per-qubit layer scheduling; undirected edges; edge Gini
    calculated over ALL hardware edges (including unused); qubit Gini over
    ALL physical circuit qubits (including idle). No logical metadata used.
    ``gini_population='used'`` restricts features 8 and 10 to edges / qubits that carry at least one
    two-qubit gate (a sensitivity check on the paper's unspecified convention).
    """
    if gini_population not in ('all', 'used'): raise ValueError('gini_population must be all|used')
    if not coupling_edges: raise ValueError('Target coupling edges are required for feature 7')
    n = circuit.num_qubits
    if n <= 0: raise ValueError('Circuit has no qubits')
    qidx = {q:i for i,q in enumerate(circuit.qubits)}
    edges = {tuple(sorted(map(int,e))) for e in coupling_edges}
    if any(a == b or a < 0 or b >= n for a,b in edges):
        raise ValueError('Coupling edges must index physical circuit qubits')
    clocks = [0]*n; layer_load=defaultdict(int); edge_load=Counter(); qubit_load=np.zeros(n)
    names_1q=Counter(); total=two=phase=0
    for inst in circuit.data:
        op=inst.operation; name=op.name
        if name in ('barrier','delay'): continue
        qs=[qidx[q] for q in inst.qubits]
        if not qs: continue
        layer=1+max(clocks[q] for q in qs)
        for q in qs: clocks[q]=layer
        total += 1
        if name in phase_gates: phase += 1
        if len(qs)==1: names_1q[name]+=1
        if len(qs)==2:
            edge=tuple(sorted(qs))
            if edge not in edges: raise ValueError(f'Two-qubit operation uses non-target edge {edge}')
            two+=1; layer_load[layer]+=1; edge_load[edge]+=1
            qubit_load[qs[0]]+=1; qubit_load[qs[1]]+=1
    depth=max(clocks,default=0)
    loads=np.array([layer_load[t] for t in range(1,depth+1)],dtype=float)
    edge_values=np.array([edge_load[e] for e in sorted(edges)],dtype=float)
    if gini_population=='used':
        edge_values=edge_values[edge_values>0]; qubit_load=qubit_load[qubit_load>0]
    d=max(total,1)
    return dict(zip(PAPER_FEATURE_NAMES, (
        two/d, phase/d, _entropy(names_1q.values()),
        float(np.count_nonzero(loads)/depth) if depth else 0.,
        float(loads.mean()) if len(loads) else 0.,
        gini(loads), len(edge_load)/len(edges), gini(edge_values),
        max(edge_load.values(),default=0)/max(two,1), gini(qubit_load)
    )))
