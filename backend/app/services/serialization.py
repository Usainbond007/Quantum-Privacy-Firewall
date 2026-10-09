"""Serialize gates on their original wire indices; omit idle hardware wires in the view."""
import math
from .verification import layout_indices


def scalar(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else str(value)
    except (TypeError, ValueError):
        return str(value)


def serialize_circuit(qc, logical_width=None):
    width = logical_width or qc.num_qubits
    layout = layout_indices(qc, width) if qc.layout is not None else None
    clocks = [0] * qc.num_qubits
    gates, touched = [], set()
    for i, inst in enumerate(qc.data):
        qs = [qc.find_bit(q).index for q in inst.qubits]
        layer = max((clocks[q] for q in qs), default=0) + 1
        for q in qs:
            clocks[q] = layer
        touched.update(qs)
        gates.append(dict(id=i, name=inst.operation.name, qubits=qs,
                          clbits=[qc.find_bit(c).index for c in inst.clbits],
                          params=[scalar(p) for p in inst.operation.params], layer=layer))
    if layout:
        touched.update(layout["initial"])
        touched.update(layout["final"])
    elif qc.layout is None:
        touched.update(range(qc.num_qubits))
    return dict(num_qubits=qc.num_qubits, logical_width=width, qubits=sorted(touched), gates=gates,
                depth=max(clocks, default=0), size=qc.size(), global_phase=scalar(qc.global_phase), layout=layout)
