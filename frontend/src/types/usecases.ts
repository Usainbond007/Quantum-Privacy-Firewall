import type { Circuit } from "./demo";
export type Verification = { status: string; method: string; note: string };
export type Decision = {
  status: "BLOCK" | "WARN" | "RELEASE";
  reasons: string[];
};

export type GroverCandidate = {
  id: string;
  strategy: string;
  seed: number;
  verification: string;
  method: string;
  metrics: { depth: number; n2q: number; size: number };
  overhead: { depth: number; n2q: number };
  within_budget: boolean;
  compiled_verification: Verification;
  circuit: Circuit;
  total_variation: number;
  pattern_guess: string;
  pattern_recovers: boolean;
  exact_guess: string;
  exact_probability: number;
  exact_recovers: boolean;
  circuit_hash: string;
};

export type GroverResult = {
  elapsed_seconds: number;
  marked: string;
  budget: number;
  observer: string;
  baseline: {
    circuit: Circuit;
    probabilities: number[];
    compiled_verification: Verification;
    metrics: { depth: number; n2q: number; size: number };
    pattern_guess: string;
    exact_guess: string;
    exact_probability: number;
    circuit_hash: string;
  };
  candidates: GroverCandidate[];
  selected: string | null;
  summary: {
    verified: number;
    total: number;
    pattern_recovery_rate: number;
    exact_recovery_rate: number;
  };
  decision: Decision;
  receipt: Record<string, unknown>;
  scope: string[];
};

export type PortfolioPick = {
  tickers: string[];
  risk: number;
  ret: number;
  regret_vs_best: number;
  random_mean_regret: number;
};

export type PortfolioResult = {
  elapsed_seconds: number;
  workload: {
    circuit: Circuit;
    model: string;
    preparation: string;
    classical_feasible_count: number;
    asset_rows: { ticker: string; expected_return: number; variance: number }[];
  };
  data: {
    source: string;
    sha256: string;
    assets: string[];
    k: number;
    note: string;
  };
  preference: string;
  other: string;
  weights: Record<string, [number, number]>;
  direct: {
    circuit: Circuit;
    candidate_circuit: Circuit;
    bindings: number[];
    feasible_probability: number;
    preference_distribution_tv: number;
    attack_scope: string;
    structure_hash: string;
    structure_identical_across_preferences: boolean;
    structural_attacker_accuracy: number;
    chance: number;
    payload_attacker: {
      recovered_weights: [number, number];
      true_weights: [number, number];
      residual: number;
      recovered_label: string;
      correct: boolean;
    };
    rewrite: {
      strategy: string;
      verification: string;
      method: string;
      compiled_verification: Verification;
      baseline_metrics: { depth: number; n2q: number };
      metrics: { depth: number; n2q: number };
      overhead: { depth: number; n2q: number };
      total_variation: number;
    };
    decision: Decision;
  };
  sweep: {
    compiled_checks: Verification[];
    jobs: number;
    job_hash_a: string;
    job_hash_b: string;
    identical: boolean;
    picks: Record<string, PortfolioPick>;
    distinct_candidates: number;
    attacker_accuracy: number;
    decision: Decision;
  };
  scope: string[];
};
