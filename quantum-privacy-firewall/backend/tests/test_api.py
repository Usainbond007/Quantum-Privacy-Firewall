from threading import Event
import time
import pytest
from fastapi.testclient import TestClient
from backend.app.main import create_app
from backend.app.schemas import RunRequest, RunState
from backend.app.services.jobs import JobManager, ROOT, now


def finish(client, identifier):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        state = client.get(f"/api/runs/{identifier}").json()
        if state["status"] in ("completed", "failed"):
            return state
        time.sleep(.02)
    pytest.fail("Run did not finish")


def test_all_endpoints_real_run_and_restart(tmp_path):
    manager = JobManager(tmp_path)
    with TestClient(create_app(manager)) as client:
        options = client.get("/api/options")
        assert client.get("/").headers["cache-control"] == "no-store"
        assert options.status_code == 200 and "graph_ghz" in options.json()["families"]
        preview = client.post("/api/circuits/preview", json={"family": "qft", "width": 4, "seed": 21})
        assert preview.status_code == 200 and preview.json()["gates"]
        response = client.post("/api/runs", json={"candidates": 1})
        assert response.status_code == 202
        identifier = response.json()["id"]
        state = finish(client, identifier)
        assert state["status"] == "completed", state.get("error")
        assert state["progress"] == 1
        assert client.get(f"/api/runs/{identifier}/exports/qasm").text.startswith("OPENQASM 3.0;")
        export = client.get(f"/api/runs/{identifier}/exports/metrics")
        assert export.json() == state["result"]
        assert "attachment" in export.headers["content-disposition"]
        assert client.get("/api/runs/00000000-0000-0000-0000-000000000000").status_code == 404
        assert client.get("/api/runs/../../secrets/exports/metrics").status_code != 200
    restored = JobManager(tmp_path)
    assert restored.get(identifier).status == "completed"
    restored.close()


@pytest.mark.parametrize("body", [{"width": 3}, {"width": 9}, {"width": 4.1}, {"seed": -1}, {"budget": 1.1}, {"candidates": 25}, {"strategies": []}, {"strategies": ["anything"]}, {"backend": "arbitrary"}, {"unknown": True}])
def test_validation(body, tmp_path):
    with TestClient(create_app(JobManager(tmp_path))) as client:
        assert client.post("/api/runs", json=body).status_code == 422


def test_queue_bounds_failure_and_premature_exports(tmp_path):
    started, release = Event(), Event()
    def blocked(request, progress):
        started.set()
        release.wait(10)
        raise RuntimeError("worker failure details")
    manager = JobManager(tmp_path, capacity=1, runner=blocked)
    try:
        with TestClient(create_app(manager)) as client:
            identifier = client.post("/api/runs", json={}).json()["id"]
            assert started.wait(3)
            assert client.post("/api/runs", json={}).status_code == 429
            assert client.get(f"/api/runs/{identifier}/exports/qasm").status_code == 409
            release.set()
            state = finish(client, identifier)
            assert state["status"] == "failed" and "worker failure details" in state["error"]
    finally:
        release.set()


def test_interrupted_state_becomes_failure_on_restart(tmp_path):
    identifier = "11111111-1111-4111-8111-111111111111"
    path = tmp_path / identifier
    path.mkdir()
    state = RunState(id=identifier, status="running", created_at=now(), updated_at=now())
    (path / "state.json").write_text(state.model_dump_json(), encoding="utf-8")
    manager = JobManager(tmp_path)
    assert manager.get(identifier).status == "failed"
    assert "restarted" in manager.get(identifier).error
    manager.close()


def test_runtime_defaults_to_repository():
    from pathlib import Path
    assert ROOT == Path(__file__).resolve().parents[2] / "runtime"
