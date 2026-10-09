import type { DemoResult } from "../types/demo";

export function MetricCards({ result }: { result: DemoResult | null }) {
  const selected = result?.selected;
  const cards = [
    { key: "depth", label: "Circuit depth", unit: "layers" },
    { key: "n2q", label: "Two-qubit gates", unit: "operations" },
    { key: "active", label: "Active qubits", unit: "physical wires" },
  ];
  return (
    <div className="metric-grid">
      {cards.map(({ key, label, unit }) => (
        <section className="panel metric-card" key={key}>
          <div className="eyebrow">{label}</div>
          <div className="metric-value mono">
            {selected?.metrics?.[key] ?? result?.baseline.metrics?.[key] ?? "—"}
            {selected && (
              <span className="metric-baseline">
                / {result?.baseline.metrics?.[key]}
              </span>
            )}
          </div>
          <div className="metric-foot">
            <span>
              {unit}
              {selected
                ? " · selected / baseline"
                : result
                  ? " · baseline"
                  : ""}
            </span>
            {selected?.overheads && (
              <span
                className={
                  selected.overheads[key] <= 0 ? "accent" : "budget-delta"
                }
              >
                {selected.overheads[key] > 0 ? "+" : ""}
                {(selected.overheads[key] * 100).toFixed(1)}%
              </span>
            )}
          </div>
        </section>
      ))}
    </div>
  );
}
