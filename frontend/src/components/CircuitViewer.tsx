import { useState } from "react";
import type { Circuit, Gate } from "../types/demo";

export function CircuitViewer({
  circuit,
  title,
  subtitle,
  changedGateIds,
}: {
  circuit: Circuit;
  title: string;
  subtitle?: string;
  changedGateIds?: ReadonlySet<number>;
}) {
  const [zoom, setZoom] = useState(1);
  const [gate, setGate] = useState<Gate | null>(null);
  const [showAllWires, setShowAllWires] = useState(false);
  const active = new Set(circuit.gates.flatMap((item) => item.qubits));
  const canShowActiveOnly = circuit.qubits.length > 12 && active.size > 0 && active.size < circuit.qubits.length;
  const visibleQubits = canShowActiveOnly && !showAllWires
    ? circuit.qubits.filter((q) => active.has(q))
    : circuit.qubits;
  const rows = new Map(visibleQubits.map((q, i) => [q, i]));
  // Reserve the complete vertical span of multi-wire gates to avoid crossing
  // another gate in the same displayed column. Gate order is unchanged.
  const occupied = visibleQubits.map(() => 0);
  const columns = circuit.gates.map((g) => {
    const indices = g.qubits.map((q) => rows.get(q)!);
    const low = Math.min(...indices),
      high = Math.max(...indices);
    const span = indices.length ? occupied.slice(low, high + 1) : [0];
    const column = Math.max(...span) + 1;
    for (let row = low; row <= high; row++) occupied[row] = column;
    return column;
  });
  const width = Math.max(480, 130 + Math.max(0, ...columns) * 58);
  const height = Math.max(150, visibleQubits.length * 46 + 30);
  const y = (q: number) => 38 + rows.get(q)! * 46;
  return (
    <section className="circuit-view">
      <div className="circuit-heading">
        <div>
          <h3>{title}</h3>
          <p>
            {subtitle ||
              `${circuit.logical_width} logical qubits · ${circuit.size} gates · depth ${circuit.depth}`}
          </p>
        </div>
        <div className="zoom-controls">
          <button
            aria-label={`Zoom out ${title}`}
            onClick={() => setZoom((z) => Math.max(0.4, z - 0.2))}
          >
            −
          </button>
          <button title="Reset zoom" onClick={() => setZoom(1)}>
            {Math.round(zoom * 100)}%
          </button>
          <button
            aria-label={`Zoom in ${title}`}
            onClick={() => setZoom((z) => Math.min(2, z + 0.2))}
          >
            +
          </button>
        </div>
      </div>
      {canShowActiveOnly && (
        <button
          type="button"
          className="wire-visibility"
          aria-pressed={showAllWires}
          onClick={() => setShowAllWires((value) => !value)}
        >
          {showAllWires
            ? `Show ${active.size} active wires`
            : `Showing ${active.size} active wires · show all ${circuit.qubits.length}`}
        </button>
      )}
      <div className="circuit-scroll">
        <svg
          role="img"
          aria-label={title}
          width={width * zoom}
          height={height * zoom}
          viewBox={`0 0 ${width} ${height}`}
        >
          {visibleQubits.map((q) => (
            <g key={q}>
              <text x="14" y={y(q) + 4} className="wire-label">
                {circuit.layout ? `p${q}` : `q${q}`} |0⟩
              </text>
              <line
                x1="82"
                x2={width - 20}
                y1={y(q)}
                y2={y(q)}
                className="wire"
              />
            </g>
          ))}
          {circuit.gates.map((g, index) => {
            const x = 90 + columns[index] * 58;
            const ys = g.qubits.map(y);
            const multi = g.qubits.length > 1;
            const label = g.name.toUpperCase();
            const controlled = [
              "cx",
              "cz",
              "cp",
              "crx",
              "cry",
              "crz",
              "ccx",
              "mcx",
            ].includes(g.name);
            const xTarget = ["cx", "ccx", "mcx"].includes(g.name);
            return (
              <g
                key={g.id}
                className={`gate ${multi ? "multi" : ""} gate-${g.name.replace(/[^a-z0-9]/gi, "-")} ${changedGateIds?.has(g.id) ? "gate-changed" : ""}`}
                tabIndex={0}
                role="button"
                aria-label={`${label} on ${g.qubits.join(", ")}`}
                onClick={() => setGate(g)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    setGate(g);
                  }
                }}
              >
                <title>
                  {label} · wires {g.qubits.join(", ")}
                  {g.params.length ? ` · ${g.params.join(", ")}` : ""}
                </title>
                {multi && (
                  <line
                    x1={x}
                    x2={x}
                    y1={Math.min(...ys)}
                    y2={Math.max(...ys)}
                    className="gate-link"
                  />
                )}
                {ys.map((yy, j) => (
                  <g key={j}>
                    {controlled && j < ys.length - 1 ? (
                      <circle className="control-dot" cx={x} cy={yy} r="5" />
                    ) : g.name === "swap" ? (
                      <path
                        className="gate-link swap-cross"
                        d={`M ${x - 7} ${yy - 7} l 14 14 M ${x - 7} ${yy + 7} l 14 -14`}
                      />
                    ) : xTarget ? (
                      <>
                        <circle
                          className="target-circle"
                          cx={x}
                          cy={yy}
                          r="13"
                        />
                        <path
                          className="gate-link"
                          d={`M ${x - 9} ${yy} h 18 M ${x} ${yy - 9} v 18`}
                        />
                      </>
                    ) : (
                      <>
                        <rect
                          x={x - 21}
                          y={yy - 16}
                          width="42"
                          height="32"
                          rx="6"
                        />
                        <text x={x} y={yy + 4} textAnchor="middle">
                          {controlled
                            ? label.slice(1)
                            : label.length > 5
                              ? label.slice(0, 4) + "…"
                              : label}
                        </text>
                      </>
                    )}
                  </g>
                ))}
              </g>
            );
          })}
        </svg>
      </div>
      <div className="circuit-footer mono">
        {gate ? (
          <span>
            <strong>{gate.name.toUpperCase()}</strong> · wires [
            {gate.qubits.join(", ")}] · params [
            {gate.params
              .map((p) => (typeof p === "number" ? p.toPrecision(5) : p))
              .join(", ")}
            ] · layer {gate.layer}
          </span>
        ) : (
          <span>Select a gate to inspect parameters · scroll to explore</span>
        )}
      </div>
      {circuit.layout && (
        <details className="layout-details">
          <summary>
            Logical → physical layout · {circuit.qubits.length} visible of{" "}
            {circuit.num_qubits} hardware wires
          </summary>
          <div>
            {circuit.layout.initial.map((p, i) => (
              <span key={i}>
                q{i}: p{p} → p{circuit.layout!.final[i]}
              </span>
            ))}
          </div>
        </details>
      )}
    </section>
  );
}
