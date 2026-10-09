import type { ResearchBenchmarks } from "../types/demo";
import { ATTACKER_NAMES, usesBaselineRF } from "../lib/benchmarks";

export function AccuracySummary({
  data,
  budget,
  onBudgetChange,
  attacker,
  onAttackerChange,
}: {
  data: ResearchBenchmarks | null;
  budget: number;
  onBudgetChange: (value: number) => void;
  attacker: string;
  onAttackerChange: (value: string) => void;
}) {
  const entry = data?.budgets.find(
    (item) => Math.abs(item.budget - budget) < 1e-9,
  );
  const before =
    data?.status === "available" ? data.baseline?.accuracy : undefined;
  const after =
    data?.status === "available"
      ? entry?.attackers[attacker]?.accuracy
      : undefined;
  const change =
    before !== undefined && after !== undefined ? (after - before) * 100 : null;
  const percent = (value: number | undefined) =>
    value === undefined ? "—" : `${(value * 100).toFixed(2)}%`;
  return (
    <section
      className="panel accuracy-summary"
      aria-label="Before and after firewall accuracy"
    >
      <div className="accuracy-summary-heading">
        <div>
          <h2>Attacker accuracy — before & after firewall</h2>
          <p>
            Saved test set · {ATTACKER_NAMES[attacker] || attacker} · lower
            accuracy is better for privacy
          </p>
        </div>
        <div className="accuracy-summary-filters">
          <label>
            Saved attacker test
            <select
              value={attacker}
              onChange={(event) => onAttackerChange(event.target.value)}
              disabled={data?.status !== "available"}
            >
              {Object.keys(entry?.attackers || ATTACKER_NAMES).map((name) => (
                <option key={name} value={name}>
                  {ATTACKER_NAMES[name] || name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Saved research budget
            <select
              value={budget}
              onChange={(event) => onBudgetChange(+event.target.value)}
              disabled={data?.status !== "available"}
            >
              {(data?.budgets.length
                ? data.budgets
                : [0.0, 0.1, 0.2, 0.5].map((value) => ({ budget: value }))
              ).map((item) => (
                <option value={item.budget} key={item.budget}>
                  {Math.round(item.budget * 100)}%
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>
      <div className="accuracy-summary-values">
        <div>
          <span>
            {usesBaselineRF(attacker)
              ? "Before firewall accuracy"
              : "Before firewall accuracy (RF reference)"}
          </span>
          <strong className="mono">{percent(before)}</strong>
        </div>
        <span className="accuracy-summary-arrow" aria-hidden="true">
          →
        </span>
        <div>
          <span>After firewall accuracy</span>
          <strong className="mono">{percent(after)}</strong>
        </div>
        <div className="accuracy-summary-verdict">
          <p>
            {change === null
              ? "Waiting for saved benchmark results."
              : !usesBaselineRF(attacker)
                ? `Protected attacker accuracy is ${Math.abs(change).toFixed(2)} percentage points ${change < 0 ? "below" : change > 0 ? "above" : "from"} the original RF reference.`
                : change > 0
                  ? `Accuracy increased by ${change.toFixed(2)} percentage points. This budget did not reduce attacker accuracy.`
                  : change < 0
                    ? `Attacker accuracy decreased by ${Math.abs(change).toFixed(2)} percentage points.`
                    : "Attacker accuracy was unchanged."}
          </p>
          <a href="#attacker-accuracy">Confusion matrices & full metrics ↓</a>
        </div>
      </div>
      <p className="accuracy-summary-source">
        Archived quick-profile results: {data?.test_circuits || "—"} test
        circuits / {data?.test_rows || "—"} compiled rows. These percentages are
        not accuracy measured from the current single-circuit run.
        {!usesBaselineRF(attacker) &&
          " Before is the saved original random-forest reference. A separate before-firewall score for this attacker is not recorded."}
      </p>
    </section>
  );
}
