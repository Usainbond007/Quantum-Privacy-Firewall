"""The bounded demo API contract. Width >= 4 also satisfies the QAOA generator."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

Family = Literal["qft", "grover", "qaoa", "graph_ghz", "random"]
Strategy = Literal["decomp", "reorder", "layout", "decomp+reorder", "decomp+layout", "reorder+layout", "decomp+reorder+layout"]
BACKENDS = ("FakeNighthawk", "FakeSherbrooke", "FakeBrisbane")
STRATEGIES = ["decomp", "reorder", "layout", "decomp+reorder", "decomp+layout", "reorder+layout", "decomp+reorder+layout"]


class CircuitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    family: Family = "graph_ghz"
    width: int = Field(default=4, ge=4, le=8, strict=True)
    seed: int = Field(default=21, ge=0, le=2**31 - 1, strict=True)


class RunRequest(CircuitRequest):
    backend: Literal["FakeNighthawk", "FakeSherbrooke", "FakeBrisbane"] = "FakeNighthawk"
    optimization_level: int = Field(default=2, ge=0, le=3, strict=True)
    transpile_seed: int = Field(default=11, ge=0, le=2**31 - 1, strict=True)
    candidates: int = Field(default=6, ge=1, le=24, strict=True)
    budget: float = Field(default=0.2, ge=0, le=1, allow_inf_nan=False)
    strategies: list[Strategy] = Field(default_factory=lambda: ["layout", "decomp+layout", "decomp+reorder"], min_length=1, max_length=7)


class Evidence(BaseModel):
    status: Literal["PASS", "FAIL", "UNKNOWN"]
    method: str
    note: str = ""


class Gate(BaseModel):
    id: int
    name: str
    qubits: list[int]
    clbits: list[int]
    params: list[float | str]
    layer: int


class CircuitJSON(BaseModel):
    num_qubits: int
    logical_width: int
    qubits: list[int]
    gates: list[Gate]
    depth: int
    size: int
    global_phase: float | str
    layout: dict[str, list[int]] | None


class Candidate(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
    id: str
    strategy: str
    seed: int
    logical_verification: Evidence
    compiled_verification: Evidence
    metrics: dict[str, int] | None = None
    overheads: dict[str, float] | None = None
    features: dict[str, float] | None = None
    changed: bool = False
    eligible: bool = False
    reason: str = ""
    score: float | None = None
    circuit: CircuitJSON | None = None
    attacker: "AttackerPrediction | None" = None


class AttackerPrediction(BaseModel):
    predicted_family: str
    confidence: float
    probabilities: dict[str, float]
    true_family_probability: float | None
    correct: bool | None
    model_source: str
    context_note: str


class ClassifierMetrics(BaseModel):
    accuracy: float
    balanced_accuracy: float
    macro_f1: float
    confusion: list[list[int]]
    labels: list[str]
    support: dict[str, int]


class BenchmarkBudget(BaseModel):
    budget: float
    attackers: dict[str, ClassifierMetrics]
    adaptive_rf_macro_f1_ci95: list[float]


class ResearchBenchmarks(BaseModel):
    status: Literal["available", "unavailable"]
    note: str
    profile: str = "quick"
    backend: str | None = None
    widths: list[int] = Field(default_factory=list)
    optimization_levels: list[int] = Field(default_factory=list)
    test_rows: int = 0
    test_circuits: int = 0
    chance: float | None = None
    baseline: ClassifierMetrics | None = None
    controls: dict[str, ClassifierMetrics] = Field(default_factory=dict)
    budgets: list[BenchmarkBudget] = Field(default_factory=list)
    baseline_macro_f1_ci95: list[float] = Field(default_factory=list)
    metadata_confound_warning: bool = False
    sources: list[str] = Field(default_factory=list)


class DemoResult(BaseModel):
    outcome: Literal["SELECTED", "NO_CHANGED_CANDIDATE"]
    message: str
    request: RunRequest
    input: CircuitJSON
    baseline: Candidate
    selected: Candidate | None
    alternatives: list[Candidate]
    scoring_method: str
    scoring_note: str
    elapsed_seconds: float
    benchmarks: ResearchBenchmarks | None = None
    attacker_note: str = ""


class RunState(BaseModel):
    id: str
    status: Literal["queued", "running", "completed", "failed"]
    progress: float = 0
    stage: str = "Queued"
    created_at: str
    updated_at: str
    result: DemoResult | None = None
    error: str | None = None


class RunCreated(BaseModel):
    id: str
    status: str
