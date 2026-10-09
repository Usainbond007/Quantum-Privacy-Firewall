from fastapi import APIRouter
from qpf.circuits import make_circuit
from ..schemas import CircuitRequest, CircuitJSON
from ..services.serialization import serialize_circuit

router = APIRouter()


@router.post("/circuits/preview", response_model=CircuitJSON)
def preview(request: CircuitRequest):
    return serialize_circuit(make_circuit(request.family, request.width, request.seed))
