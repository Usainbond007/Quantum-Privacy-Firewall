from uuid import UUID
from fastapi import APIRouter, HTTPException, Request
from ..schemas import RunRequest, RunState, RunCreated
from ..services.jobs import QueueFull

router = APIRouter()


@router.post("/runs", response_model=RunCreated, status_code=202)
def create_run(body: RunRequest, request: Request):
    try:
        identifier = request.app.state.jobs.submit(body)
    except QueueFull as exc:
        raise HTTPException(429, str(exc), headers={"Retry-After": "5"}) from exc
    return dict(id=identifier, status="queued")


@router.get("/runs/{identifier}", response_model=RunState)
def get_run(identifier: UUID, request: Request):
    state = request.app.state.jobs.get(str(identifier))
    if state is None:
        raise HTTPException(404, "Run not found or expired")
    return state
