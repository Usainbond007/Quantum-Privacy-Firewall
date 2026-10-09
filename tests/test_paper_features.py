"""Dependency-light contract tests for the independent Table II implementation."""
from qpf.paper_features import PAPER_FEATURE_NAMES, extract_paper_features

class Op:
    def __init__(self,name,n): self.name=name; self.num_qubits=n
class Inst:
    def __init__(self,name,qubits): self.operation=Op(name,len(qubits)); self.qubits=qubits
class Circuit:
    def __init__(self):
        self.qubits=['q0','q1','q2']; self.num_qubits=3
        self.data=[Inst('rz',['q0']),Inst('cz',['q0','q1']),Inst('x',['q2'])]

def test_schema_and_simple_values():
    f=extract_paper_features(Circuit(), [(0,1),(1,2)])
    assert tuple(f)==PAPER_FEATURE_NAMES
    assert abs(f['two_qubit_fraction']-1/3)<1e-12
    assert abs(f['phase_rotation_fraction']-1/3)<1e-12
    assert f['used_hardware_edge_fraction']==0.5
    assert f['max_edge_load_fraction']==1.0
    assert all(0<=v for v in f.values())

def test_target_required():
    try: extract_paper_features(Circuit(), [])
    except ValueError: pass
    else: raise AssertionError('Must reject unknown coupling map')
