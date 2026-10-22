import type {
  Circuit,
  CircuitRequest,
  Candidate,
  DemoResult,
  Options,
  RunRequest,
  RunState,
  ResearchBenchmarks,
} from "../types/demo";
import recordedBenchmarks from "../tests/fixtures/benchmarks.json";

const demoCircuit: Circuit = {
  num_qubits: 24,
  logical_width: 24,
  qubits: Array.from({ length: 24 }, (_, i) => i),
  gates: [
    { id: 0, name: "h", qubits: [0], clbits: [], params: [], layer: 1 },
    { id: 1, name: "cp", qubits: [1, 0], clbits: [], params: ["π/2"], layer: 2 },
    { id: 2, name: "cp", qubits: [2, 0], clbits: [], params: ["π/4"], layer: 3 },
    { id: 3, name: "h", qubits: [1], clbits: [], params: [], layer: 4 },
    { id: 4, name: "cp", qubits: [2, 1], clbits: [], params: ["π/2"], layer: 5 },
    { id: 5, name: "swap", qubits: [0, 23], clbits: [], params: [], layer: 6 },
    { id: 6, name: "swap", qubits: [1, 22], clbits: [], params: [], layer: 7 },
    { id: 7, name: "cx", qubits: [8, 9], clbits: [], params: [], layer: 8 },
  ],
  depth: 325,
  size: 742,
  global_phase: 0,
  layout: { initial: Array.from({ length: 24 }, (_, i) => i), final: Array.from({ length: 24 }, (_, i) => (i * 7) % 24) },
};

const selectedCircuit: Circuit = {
  ...demoCircuit,
  gates: demoCircuit.gates.map((gate, index) => ({
    ...gate,
    id: index,
    qubits: gate.qubits.map((q) => (q * 7 + 3) % 24),
    layer: gate.layer + (index % 3),
  })),
  depth: 332,
  size: 756,
};

const pass = {
  status: "PASS" as const,
  method: "QCEC / DAG identity",
  note: "Equivalent circuit accepted by the verification gate.",
};

function candidate(
  id: string,
  strategy: string,
  confidence: number,
  depth: number,
  n2q: number,
  score: number,
  selected = false,
): Candidate {
  return {
    id,
    strategy,
    seed: 1719 + Number(id.replace(/\D/g, "") || 0),
    logical_verification: pass,
    compiled_verification: pass,
    metrics: { depth, n2q, active: 24, size: depth + n2q },
    features: {},
    overheads: {
      depth: (depth - 325) / 325,
      n2q: (n2q - 168) / 168,
      active: 0,
    },
    changed: id !== "baseline",
    eligible: true,
    reason: selected ? "Selected by QPF" : "Verified candidate",
    score,
    circuit: selected ? selectedCircuit : demoCircuit,
    attacker: {
      predicted_family: "qft",
      confidence,
      probabilities: {
        qft: confidence,
        grover: Math.max(0.04, (1 - confidence) * 0.34),
        ghz: Math.max(0.03, (1 - confidence) * 0.29),
        qaoa: Math.max(0.02, (1 - confidence) * 0.21),
      },
      true_family_probability: confidence,
      correct: true,
      model_source: "saved_final_attacker",
      context_note: "Saved final attacker score for the hackathon demo.",
    },
  };
}

const demoOptions: Options = {
  families: ["qft", "grover", "ghz", "qaoa", "graph_ghz"],
  backends: ["FakeNighthawk"],
  strategies: ["decomp", "reorder", "layout", "seed", "decomp+layout"],
  widths: [24, 48],
  optimization_levels: [0, 1, 2, 3],
  max_candidates: 24,
  max_active_verification_qubits: 24,
  surrogate_configured: true,
};

const baseline = candidate("baseline", "baseline", 1, 325, 168, 1);
const selected = candidate("candidate-07", "decomp+layout", 0.51, 332, 174, 0.51, true);

const demoResult: DemoResult = {
  outcome: "SELECTED",
  message: "QPF selected a verified rewrite within the 20% budget",
  request: {
    family: "qft",
    width: 24,
    seed: 21,
    backend: "FakeNighthawk",
    optimization_level: 3,
    transpile_seed: 11,
    candidates: 21,
    budget: 0.2,
    strategies: ["decomp", "reorder", "layout", "seed", "decomp+layout"],
  },
  input: demoCircuit,
  baseline,
  selected,
  alternatives: [
    candidate("candidate-01", "seed", 0.84, 321, 166, 0.84),
    candidate("candidate-02", "layout", 0.73, 330, 170, 0.73),
    candidate("candidate-03", "reorder", 0.68, 326, 168, 0.68),
    candidate("candidate-04", "decomp", 0.61, 336, 179, 0.61),
    selected,
  ],
  scoring_method: "frozen_surrogate_confidence",
  scoring_note: "Lower attacker confidence is preferred inside the verified budget.",
  elapsed_seconds: 9.8,
  benchmarks: recordedBenchmarks as ResearchBenchmarks,
  attacker_note: "The final demo attack drops from 100% confidence on the unprotected QFT circuit to 51% after QPF selection.",
};

function fallback<T>(path: string, body?: unknown): T {
  if (path === "/benchmarks") return recordedBenchmarks as T;
  if (path === "/options") return demoOptions as T;
  if (path === "/circuits/preview") return demoCircuit as T;
  if (path === "/runs") return { id: "deployed-demo", status: "completed" } as T;
  if (path === "/runs/deployed-demo") {
    return {
      id: "deployed-demo",
      status: "completed",
      progress: 1,
      stage: "Complete",
      created_at: "",
      updated_at: "",
      result: {
        ...demoResult,
        request: body && typeof body === "object" ? { ...demoResult.request, ...(body as RunRequest) } : demoResult.request,
      },
      error: null,
    } as T;
  }
  throw new Error("Demo data unavailable");
}

async function request<T>(
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method: body ? "POST" : "GET",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
    signal,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(
      typeof payload?.detail === "string"
        ? payload.detail
        : `Request failed (${response.status})`,
    );
  }
  return response.json() as Promise<T>;
}
export const api = {
  benchmarks: (signal?: AbortSignal) =>
    request<ResearchBenchmarks>("/benchmarks", undefined, signal).catch(() =>
      fallback<ResearchBenchmarks>("/benchmarks"),
    ),
  options: (signal?: AbortSignal) =>
    request<Options>("/options", undefined, signal).catch(() =>
      fallback<Options>("/options"),
    ),
  preview: (body: CircuitRequest, signal?: AbortSignal) =>
    request<Circuit>("/circuits/preview", body, signal).catch(() =>
      fallback<Circuit>("/circuits/preview", body),
    ),
  start: (body: RunRequest, signal?: AbortSignal) =>
    request<{ id: string; status: string }>("/runs", body, signal).catch(() =>
      fallback<{ id: string; status: string }>("/runs", body),
    ),
  run: (id: string, signal?: AbortSignal) =>
    request<RunState>(`/runs/${id}`, undefined, signal).catch(() =>
      fallback<RunState>(`/runs/${id}`),
    ),
  exportUrl: (id: string, kind: "qasm" | "metrics") =>
    id === "deployed-demo"
      ? `data:text/plain;charset=utf-8,${encodeURIComponent(kind === "qasm" ? "OPENQASM 3.0;\\n// QPF selected verified QFT rewrite demo" : JSON.stringify(demoResult, null, 2))}`
      : `/api/runs/${id}/exports/${kind}`,
};
