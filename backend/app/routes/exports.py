from uuid import UUID
from fastapi import APIRouter, HTTPException, Request, Response

router = APIRouter()


def download(identifier, request, filename, media_type):
    try:
        payload = request.app.state.jobs.export(str(identifier), filename)
    except KeyError as exc:
        raise HTTPException(404, "Run not found or expired") from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return Response(payload, media_type=media_type,
                    headers={"Content-Disposition": f'attachment; filename="qpf-{identifier}-{filename}"'})


@router.get("/runs/{identifier}/exports/qasm")
def qasm(identifier: UUID, request: Request):
    return download(identifier, request, "selected.qasm", "application/qasm")


@router.get("/runs/{identifier}/exports/metrics")
def metrics(identifier: UUID, request: Request):
    return download(identifier, request, "metrics.json", "application/json")
