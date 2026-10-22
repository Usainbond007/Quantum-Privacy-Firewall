from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from qpf.circuits import FAMILIES, CONTROL
from .routes import circuits, runs, exports
from .schemas import BACKENDS, STRATEGIES
from .services.jobs import JobManager
from .services.accuracy import load_benchmarks
from .schemas import ResearchBenchmarks


def create_app(job_manager=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.jobs = job_manager or JobManager()
        yield
        app.state.jobs.close()

    app = FastAPI(title="Quantum Privacy Firewall Demo", version="0.1.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware,
                       allow_origins=os.environ.get("QPF_CORS_ORIGINS", "http://127.0.0.1").split(","),
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

    @app.get("/api/options")
    def options():
        return dict(families=[*FAMILIES, CONTROL], backends=list(BACKENDS), strategies=STRATEGIES,
                    widths=list(range(4, 9)), optimization_levels=list(range(4)),
                    max_candidates=24, max_active_verification_qubits=10,
                    budget_metrics=["depth", "n2q", "active"],
                    surrogate_configured=bool(os.environ.get("QPF_SURROGATE_PATH")))

    @app.get("/api/benchmarks", response_model=ResearchBenchmarks)
    def benchmarks():
        return load_benchmarks()

    for router in (circuits.router, runs.router, exports.router):
        app.include_router(router, prefix="/api")
    return app


app = create_app()
