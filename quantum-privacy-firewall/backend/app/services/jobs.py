"""One worker, bounded admission and retention, atomic snapshots and exports.

The server runs as one process. Old terminal runs are evicted at capacity;
pending work is never evicted. State survives restart as read-only snapshots.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import BoundedSemaphore, RLock
import os
from uuid import UUID, uuid4
from ..schemas import RunState
from .demo import run_demo

ROOT = Path(__file__).resolve().parents[3] / "runtime"


def now():
    return datetime.now(timezone.utc).isoformat()


class QueueFull(Exception):
    pass


class JobManager:
    def __init__(self, root=None, capacity=4, retention=50, runner=run_demo):
        self.root = Path(root or os.environ.get("QPF_RUNTIME_DIR", ROOT)).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.capacity = BoundedSemaphore(capacity)
        self.retention = retention
        self.runner = runner
        self.lock = RLock()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="qpf-demo")
        self.states = {}
        for path in sorted(self.root.glob("*/state.json"), key=lambda p: p.stat().st_mtime):
            try:
                state = RunState.model_validate_json(path.read_text(encoding="utf-8"))
                if str(UUID(state.id)) != path.parent.name:
                    continue
                if state.status in ("running", "queued"):
                    state.status, state.stage, state.error = "failed", "Interrupted", "Server restarted before the run finished"
                    state.updated_at = now()
                self.states[state.id] = state
                self._persist(state)
            except (ValueError, OSError):
                continue
        self._prune()

    def _prune(self):
        import shutil
        while len(self.states) >= self.retention:
            victim = next((s for s in self.states.values() if s.status in ("completed", "failed")), None)
            if victim is None:
                break
            # UUID paths originate from validated state or our own uuid4.
            target = (self.root / str(UUID(victim.id))).resolve()
            if target.parent != self.root:
                raise ValueError("Invalid runtime path")
            shutil.rmtree(target)
            del self.states[victim.id]

    def _persist(self, state):
        directory = self.root / state.id
        directory.mkdir(exist_ok=True)
        temporary = directory / "state.tmp"
        temporary.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        temporary.replace(directory / "state.json")

    def submit(self, request):
        if not self.capacity.acquire(blocking=False):
            raise QueueFull("Demo queue is full; try again after a run finishes")
        try:
            with self.lock:
                self._prune()
                identifier = str(uuid4())
                state = RunState(id=identifier, status="queued", created_at=now(), updated_at=now())
                self.states[identifier] = state
                self._persist(state)
                self.executor.submit(self._execute, identifier, request)
            return identifier
        except Exception:
            self.capacity.release()
            raise

    def _execute(self, identifier, request):
        def progress(value, stage):
            with self.lock:
                state = self.states[identifier]
                state.status, state.progress, state.stage = "running", value, stage
                state.updated_at = now()
                self._persist(state)
        try:
            progress(0, "Starting")
            result, qasm = self.runner(request, progress)
            directory = self.root / identifier
            (directory / "selected.qasm").write_text(qasm, encoding="utf-8")
            (directory / "metrics.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
            with self.lock:
                state = self.states[identifier]
                state.result, state.status, state.progress, state.stage = result, "completed", 1, "Complete"
                state.updated_at = now()
                self._persist(state)
        except Exception as exc:
            with self.lock:
                state = self.states[identifier]
                state.status, state.stage = "failed", "Failed"
                state.error = f"{type(exc).__name__}: {str(exc)[:500]}"
                state.updated_at = now()
                self._persist(state)
        finally:
            self.capacity.release()

    def get(self, identifier):
        with self.lock:
            state = self.states.get(identifier)
            return state.model_copy(deep=True) if state else None

    def export(self, identifier, filename):
        with self.lock:
            state = self.states.get(identifier)
            if state is None:
                raise KeyError(identifier)
            if state.status != "completed":
                raise ValueError("Exports are available only for completed runs")
            return (self.root / identifier / filename).read_bytes()

    def close(self):
        self.executor.shutdown(wait=True, cancel_futures=False)
