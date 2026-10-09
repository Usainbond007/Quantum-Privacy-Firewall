export const ATTACKER_NAMES: Record<string, string> = {
  static_baseline_rf: "Static random forest",
  adaptive_rf: "Adaptive random forest",
  adaptive_logreg: "Adaptive logistic regression",
  adaptive_gboost: "Adaptive gradient boosting",
  adaptive_rf_normalization_aware: "Normalization-aware random forest",
};

export function usesBaselineRF(attacker: string) {
  return attacker === "adaptive_rf" || attacker === "static_baseline_rf";
}
