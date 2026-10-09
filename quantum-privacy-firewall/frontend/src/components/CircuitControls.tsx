import type { Options, RunRequest } from "../types/demo";

export const FAMILY_LABELS: Record<string, string> = {
  qft: "Quantum Fourier transform",
  grover: "Grover search",
  qaoa: "QAOA optimization",
  graph_ghz: "Graph / GHZ state",
  random: "Random control",
};
interface Props {
  options: Options;
  value: RunRequest;
  onChange: (value: RunRequest) => void;
  onPreview: () => void;
  onRun: () => void;
  busy: boolean;
  previewing: boolean;
}
export function CircuitControls({
  options,
  value,
  onChange,
  onPreview,
  onRun,
  busy,
  previewing,
}: Props) {
  const update = <K extends keyof RunRequest>(key: K, next: RunRequest[K]) =>
    onChange({ ...value, [key]: next });
  const valid =
    value.strategies.length > 0 &&
    [value.seed, value.transpile_seed].every(
      (seed) => Number.isInteger(seed) && seed >= 0 && seed <= 2147483647,
    ) &&
    Number.isInteger(value.candidates) &&
    value.candidates >= 1 &&
    value.candidates <= options.max_candidates;
  return (
    <aside className="panel controls">
      <div className="section-title">
        <span className="step-number">01</span>
        <h2>Configure circuit</h2>
      </div>
      <fieldset disabled={busy}>
        <label>
          Algorithm family
          <select
            value={value.family}
            onChange={(e) => update("family", e.target.value)}
          >
            {options.families.map((f) => (
              <option key={f} value={f}>
                {FAMILY_LABELS[f] || f}
              </option>
            ))}
          </select>
        </label>
        <div className="field-pair">
          <label>
            Qubits
            <select
              value={value.width}
              onChange={(e) => update("width", +e.target.value)}
            >
              {options.widths.map((w) => (
                <option key={w}>{w}</option>
              ))}
            </select>
          </label>
          <label>
            Circuit seed
            <input
              type="number"
              min="0"
              max="2147483647"
              value={value.seed}
              onChange={(e) => update("seed", +e.target.value)}
            />
          </label>
        </div>
        <label>
          Target backend
          <select
            value={value.backend}
            onChange={(e) => update("backend", e.target.value)}
          >
            {options.backends.map((b) => (
              <option key={b}>{b}</option>
            ))}
          </select>
        </label>
        <div className="field-pair">
          <label>
            Optimization
            <select
              value={value.optimization_level}
              onChange={(e) => update("optimization_level", +e.target.value)}
            >
              {options.optimization_levels.map((o) => (
                <option key={o} value={o}>
                  Level {o}
                </option>
              ))}
            </select>
          </label>
          <label>
            Candidates
            <input
              type="number"
              min="1"
              max={options.max_candidates}
              value={value.candidates}
              onChange={(e) => update("candidates", +e.target.value)}
            />
          </label>
        </div>
        <label>
          Compiler seed
          <input
            type="number"
            min="0"
            max="2147483647"
            value={value.transpile_seed}
            onChange={(e) => update("transpile_seed", +e.target.value)}
          />
        </label>
        <div className="budget-heading">
          <label htmlFor="budget">Overhead budget</label>
          <span className="mono accent">{Math.round(value.budget * 100)}%</span>
        </div>
        <input
          id="budget"
          type="range"
          min="0"
          max="100"
          step="5"
          value={value.budget * 100}
          onChange={(e) => update("budget", +e.target.value / 100)}
        />
        <div className="range-labels">
          <span>0% · strict</span>
          <span>100% · exploratory</span>
        </div>
        <p className="hint">
          Caps depth, two-qubit gates and active wires independently.
        </p>
        <div className="label-text">Transformation strategies</div>
        <div className="strategy-list">
          {options.strategies.map((strategy) => (
            <label className="checkbox-label" key={strategy}>
              <input
                type="checkbox"
                checked={value.strategies.includes(strategy)}
                onChange={(e) =>
                  update(
                    "strategies",
                    e.target.checked
                      ? [...value.strategies, strategy]
                      : value.strategies.filter((s) => s !== strategy),
                  )
                }
              />
              <span>{strategy.replaceAll("+", " + ")}</span>
            </label>
          ))}
        </div>
      </fieldset>
      <button
        className="button secondary w-full"
        onClick={onPreview}
        disabled={busy || previewing || !valid}
      >
        {previewing ? "Generating preview…" : "Preview input circuit"}
      </button>
      <button
        className="button primary w-full"
        onClick={onRun}
        disabled={busy || !valid}
      >
        {busy ? "Run in progress…" : "Run firewall"}
        <span aria-hidden="true">↗</span>
      </button>
      <p className="hint text-center">
        Deterministic seeds. Local fake backend. No hardware submission.
      </p>
    </aside>
  );
}
