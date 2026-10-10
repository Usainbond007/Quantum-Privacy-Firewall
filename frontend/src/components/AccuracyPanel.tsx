import { useState } from "react";
import type {
  Candidate,
  ClassifierMetrics,
  DemoResult,
  ResearchBenchmarks,
} from "../types/demo";
import { FAMILY_LABELS } from "./CircuitControls";
import { ATTACKER_NAMES as names, usesBaselineRF } from "../lib/benchmarks";

const percent = (value: number) => `${(value * 100).toFixed(2)}%`;

function ConfusionMatrix({
  metrics,
  title,
}: {
  metrics: ClassifierMetrics;
  title: string;
}) {
  const max = Math.max(1, ...metrics.confusion.flat());
  return (
    <div className="confusion-block">
      <h3>{title}</h3>
      <p className="hint">
        Rows = true family · columns = predicted family · cell = number of
        circuits compiled at an optimization level
      </p>
      <div className="table-scroll">
        <table className="confusion-table">
          <thead>
            <tr>
              <th>True ↓ / Predicted →</th>
              {metrics.labels.map((label) => (
                <th key={label}>{label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {metrics.confusion.map((row, i) => (
              <tr key={metrics.labels[i]}>
                <th>{metrics.labels[i]}</th>
                {row.map((count, j) => (
                  <td
                    key={j}
                    style={{
                      background: `rgba(${i === j ? "126, 194, 145" : "204, 132, 95"}, ${0.05 + (0.35 * count) / max})`,
                    }}
                    className="mono"
                  >
                    {count}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Prediction({
  candidate,
  title,
}: {
  candidate: Candidate;
  title: string;
}) {
  const prediction = candidate.attacker;
  return (
    <article className="prediction-card">
      <h3>{title}</h3>
      {prediction ? (
        <>
          <div className="prediction-heading">
            <strong>
              {FAMILY_LABELS[prediction.predicted_family] ||
                prediction.predicted_family}
            </strong>
            <span className="mono accent">
              {percent(prediction.confidence)}
            </span>
          </div>
          <p className="hint">
            Attacker{" "}
            {prediction.correct === null
              ? "cannot score this family"
              : prediction.correct
                ? "identified the family"
                : "misclassified the family"}{" "}
            · confidence score
          </p>
          <div className="probability-bars">
            {Object.entries(prediction.probabilities)
              .sort((a, b) => b[1] - a[1])
              .map(([family, probability]) => (
                <div className="probability-row" key={family}>
                  <span>{family}</span>
                  <div>
                    <i style={{ width: percent(probability) }} />
                  </div>
                  <span className="mono">{percent(probability)}</span>
                </div>
              ))}
          </div>
          <p className="hint">{prediction.context_note}</p>
        </>
      ) : (
        <p className="hint">Attacker inference unavailable for this circuit.</p>
      )}
    </article>
  );
}

export function AccuracyPanel({
  benchmarks,
  result,
  error,
  onRetry,
  researchBudget,
  onResearchBudgetChange,
  researchAttacker,
  onResearchAttackerChange,
}: {
  benchmarks: ResearchBenchmarks | null;
  result: DemoResult | null;
  error: string | null;
  onRetry: () => void;
  researchBudget?: number;
  onResearchBudgetChange?: (value: number) => void;
  researchAttacker?: string;
  onResearchAttackerChange?: (value: string) => void;
}) {
  const [localBudget, setLocalBudget] = useState(0.2);
  const budget = researchBudget ?? localBudget;
  const setBudget = onResearchBudgetChange ?? setLocalBudget;
  const [localAttacker, setLocalAttacker] = useState("adaptive_rf");
  const attacker = researchAttacker ?? localAttacker;
  const setAttacker = onResearchAttackerChange ?? setLocalAttacker;
  const data = result?.benchmarks || benchmarks;
  const entry =
    data?.budgets.find((b) => Math.abs(b.budget - budget) < 1e-9) ||
    data?.budgets[0];
  const protectedMetrics = entry?.attackers[attacker];
  const baseline = data?.baseline;
  const ci =
    attacker === "adaptive_rf" ? entry?.adaptive_rf_macro_f1_ci95 : null;
  return (
    <section id="attacker-accuracy" className="panel accuracy-panel">
      <div className="section-title justify-between">
        <div>
          <h2>Attacker accuracy & leakage</h2>
          <p className="hint">
            Saved research benchmark · {data?.profile || "quick"} profile
          </p>
        </div>
        <span className="eyebrow accent">Frozen test split</span>
      </div>
      {result && (
        <div className="current-inference">
          <div className="eyebrow">
            This demo run · frozen attacker predictions
          </div>
          <p className="hint">
            {result.attacker_note ||
              "The attacker confidence is shown before and after QPF selection."}
          </p>
          <div className="prediction-grid">
            <Prediction candidate={result.baseline} title="Baseline circuit" />
            {result.selected ? (
              <Prediction
                candidate={result.selected}
                title="Selected circuit"
              />
            ) : (
              <article className="prediction-card">
                <h3>Selected circuit</h3>
                <p className="hint">No changed verified candidate selected.</p>
              </article>
            )}
          </div>
        </div>
      )}
      {!data || data.status !== "available" || !baseline ? (
        <div className="benchmark-loading">
          <p className="hint">
            {error || data?.note || "Loading saved accuracy metrics…"}
          </p>
          {(error || data?.status === "unavailable") && (
            <button className="button secondary" onClick={onRetry}>
              Retry benchmark
            </button>
          )}
        </div>
      ) : (
        <>
          <div className="benchmark-context">
            <p>{data.note}</p>
            {!usesBaselineRF(attacker) && (
              <p>
                Before-firewall metrics use the saved original random-forest
                reference. Separate before scores for this attacker are not
                recorded.
              </p>
            )}
            <span className="mono">
              {data.backend} · widths {data.widths.join("/")} · optimization{" "}
              {data.optimization_levels.join("/")} · {data.test_circuits}{" "}
              distinct test circuits / {data.test_rows} compiled rows
            </span>
          </div>
          <div className="benchmark-filters">
            <label>
              Research budget
              <select
                value={entry?.budget ?? budget}
                onChange={(e) => setBudget(+e.target.value)}
              >
                {data.budgets.map((b) => (
                  <option key={b.budget} value={b.budget}>
                    {percent(b.budget)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Protected attacker
              <select
                value={attacker}
                onChange={(e) => setAttacker(e.target.value)}
              >
                {Object.keys(entry?.attackers || {}).map((name) => (
                  <option key={name} value={name}>
                    {names[name] || name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="accuracy-metrics">
            {(
              [
                ["Accuracy", "accuracy"],
                ["Balanced accuracy", "balanced_accuracy"],
                ["Macro-F1", "macro_f1"],
              ] as const
            ).map(([label, key]) => (
              <article key={key}>
                <div className="eyebrow">{label}</div>
                <div className="accuracy-comparison">
                  <div>
                    <strong className="mono">{percent(baseline[key])}</strong>
                    <span>Baseline</span>
                  </div>
                  <span aria-hidden="true">→</span>
                  <div>
                    <strong className="mono">
                      {protectedMetrics ? percent(protectedMetrics[key]) : "—"}
                    </strong>
                    <span>
                      Protected · {entry ? percent(entry.budget) : ""} budget
                    </span>
                  </div>
                </div>
                {protectedMetrics && (
                  <p className="hint">
                    {((protectedMetrics[key] - baseline[key]) * 100).toFixed(2)}{" "}
                    percentage points · lower attacker performance is better
                  </p>
                )}
              </article>
            ))}
          </div>
          <div className="benchmark-controls">
            <span>
              Chance accuracy:{" "}
              <strong>
                {data.chance !== null ? percent(data.chance) : "—"}
              </strong>
            </span>
            <span>
              Shuffled-label accuracy:{" "}
              <strong>
                {data.controls.shuffled
                  ? percent(data.controls.shuffled.accuracy)
                  : "—"}
              </strong>
            </span>
            <span>
              Metadata-only accuracy:{" "}
              <strong>
                {data.controls.metadata_only
                  ? percent(data.controls.metadata_only.accuracy)
                  : "—"}
              </strong>
            </span>
            <span>
              Baseline macro-F1 95% CI:{" "}
              <strong>
                {data.baseline_macro_f1_ci95.map(percent).join("–")}
              </strong>
            </span>
            {ci && (
              <span>
                Protected RF macro-F1 95% CI:{" "}
                <strong>{ci.map(percent).join("–")}</strong>
              </span>
            )}
          </div>
          {data.metadata_confound_warning && (
            <p className="confound-note">
              Metadata-only and full-feature attackers are shown side by side
              to make the leakage channel transparent.
            </p>
          )}
          <details className="accuracy-details">
            <summary>
              Confusion matrices, per-family results and all attackers
            </summary>
            <div className="confusion-grid">
              <ConfusionMatrix metrics={baseline} title="Baseline attacker" />
              {protectedMetrics && (
                <ConfusionMatrix
                  metrics={protectedMetrics}
                  title={names[attacker] || attacker}
                />
              )}
            </div>
            {protectedMetrics && (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Family</th>
                      <th>Test rows</th>
                      <th>Baseline recall</th>
                      <th>Protected recall</th>
                    </tr>
                  </thead>
                  <tbody>
                    {baseline.labels.map((label) => {
                      const baselineIndex = baseline.labels.indexOf(label),
                        protectedIndex = protectedMetrics.labels.indexOf(label);
                      const support = baseline.support[label];
                      return (
                        <tr key={label}>
                          <td>{FAMILY_LABELS[label] || label}</td>
                          <td className="mono">{support}</td>
                          <td className="mono">
                            {support
                              ? percent(
                                  baseline.confusion[baselineIndex][
                                    baselineIndex
                                  ] / support,
                                )
                              : "—"}
                          </td>
                          <td className="mono">
                            {protectedMetrics.support[label]
                              ? percent(
                                  protectedMetrics.confusion[protectedIndex][
                                    protectedIndex
                                  ] / protectedMetrics.support[label],
                                )
                              : "—"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Attacker</th>
                    <th>Accuracy</th>
                    <th>Balanced accuracy</th>
                    <th>Macro-F1</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(entry?.attackers || {}).map(
                    ([name, values]) => (
                      <tr key={name}>
                        <td>{names[name] || name}</td>
                        <td className="mono">{percent(values.accuracy)}</td>
                        <td className="mono">
                          {percent(values.balanced_accuracy)}
                        </td>
                        <td className="mono">{percent(values.macro_f1)}</td>
                      </tr>
                    ),
                  )}
                </tbody>
              </table>
            </div>
          </details>
          <details className="accuracy-details">
            <summary>Metric sources</summary>
            {data.sources.map((source) => (
              <p className="hint mono" key={source}>
                {source}
              </p>
            ))}
          </details>
        </>
      )}
    </section>
  );
}
