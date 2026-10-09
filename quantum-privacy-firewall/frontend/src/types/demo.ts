export type Status = "PASS" | "FAIL" | "UNKNOWN";
export interface Evidence {
  status: Status;
  method: string;
  note: string;
}
export interface Gate {
  id: number;
  name: string;
  qubits: number[];
  clbits: number[];
  params: (number | string)[];
  layer: number;
}
export interface Circuit {
  num_qubits: number;
  logical_width: number;
  qubits: number[];
  gates: Gate[];
  depth: number;
  size: number;
  global_phase: number | string;
  layout: { initial: number[]; final: number[] } | null;
}
export interface CircuitRequest {
  family: string;
  width: number;
  seed: number;
}
export interface RunRequest extends CircuitRequest {
  backend: string;
  optimization_level: number;
  transpile_seed: number;
  candidates: number;
  budget: number;
  strategies: string[];
}
export interface Options {
  families: string[];
  backends: string[];
  strategies: string[];
  widths: number[];
  optimization_levels: number[];
  max_candidates: number;
  max_active_verification_qubits: number;
  surrogate_configured: boolean;
}
export interface Candidate {
  id: string;
  strategy: string;
  seed: number;
  logical_verification: Evidence;
  compiled_verification: Evidence;
  metrics: Record<string, number> | null;
  features: Record<string, number> | null;
  overheads: Record<string, number> | null;
  changed: boolean;
  eligible: boolean;
  reason: string;
  score: number | null;
  circuit: Circuit | null;
  attacker?: AttackerPrediction | null;
}
export interface AttackerPrediction {
  predicted_family: string;
  confidence: number;
  probabilities: Record<string, number>;
  true_family_probability: number | null;
  correct: boolean | null;
  model_source: string;
  context_note: string;
}
export interface ClassifierMetrics {
  accuracy: number;
  balanced_accuracy: number;
  macro_f1: number;
  confusion: number[][];
  labels: string[];
  support: Record<string, number>;
}
export interface ResearchBenchmarks {
  status: "available" | "unavailable";
  note: string;
  profile: string;
  backend: string | null;
  widths: number[];
  optimization_levels: number[];
  test_rows: number;
  test_circuits: number;
  chance: number | null;
  baseline: ClassifierMetrics | null;
  controls: Record<string, ClassifierMetrics>;
  budgets: {
    budget: number;
    attackers: Record<string, ClassifierMetrics>;
    adaptive_rf_macro_f1_ci95: number[];
  }[];
  baseline_macro_f1_ci95: number[];
  metadata_confound_warning: boolean;
  sources: string[];
}
export interface DemoResult {
  outcome: "SELECTED" | "NO_CHANGED_CANDIDATE";
  message: string;
  request: RunRequest;
  input: Circuit;
  baseline: Candidate;
  selected: Candidate | null;
  alternatives: Candidate[];
  scoring_method: string;
  scoring_note: string;
  elapsed_seconds: number;
  benchmarks?: ResearchBenchmarks | null;
  attacker_note?: string;
}
export interface RunState {
  id: string;
  status: "queued" | "running" | "completed" | "failed";
  progress: number;
  stage: string;
  created_at: string;
  updated_at: string;
  result: DemoResult | null;
  error: string | null;
}
