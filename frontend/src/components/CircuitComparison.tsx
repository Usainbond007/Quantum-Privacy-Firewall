import { useEffect, useState } from "react";
import type { Circuit, DemoResult, Gate } from "../types/demo";
import { CircuitViewer } from "./CircuitViewer";

function changedGateIds(source: Gate[], reference: Gate[]) {
  const signature = (gate: Gate) =>
    JSON.stringify([gate.name, gate.qubits, gate.params]);
  const remaining = new Map<string, number>();
  for (const gate of reference) {
    const key = signature(gate);
    remaining.set(key, (remaining.get(key) || 0) + 1);
  }
  const changed = new Set<number>();
  for (const gate of source) {
    const key = signature(gate);
    const count = remaining.get(key) || 0;
    if (count) remaining.set(key, count - 1);
    else changed.add(gate.id);
  }
  return changed;
}

export function CircuitComparison({
  preview,
  result,
}: {
  preview: Circuit | null;
  result: DemoResult | null;
}) {
  const [tab, setTab] = useState<"compiled" | "logical">("compiled");
  useEffect(() => {
    if (preview) setTab("logical");
  }, [preview]);
  useEffect(() => {
    if (result) setTab("compiled");
  }, [result]);
  const baselineCircuit = result?.baseline.circuit;
  const selectedCircuit = result?.selected?.circuit;
  const baselineChanged = baselineCircuit && selectedCircuit
    ? changedGateIds(baselineCircuit.gates, selectedCircuit.gates)
    : undefined;
  const selectedChanged = baselineCircuit && selectedCircuit
    ? changedGateIds(selectedCircuit.gates, baselineCircuit.gates)
    : undefined;
  const baselineMetrics = result?.baseline.metrics;
  const selectedMetrics = result?.selected?.metrics;
  return (
    <section className="panel comparison">
      <div className="section-title justify-between">
        <div className="flex items-center gap-3">
          <span className="step-number">02</span>
          <h2>Circuit workspace</h2>
        </div>
        <div className="tabs">
          <button
            className={tab === "compiled" ? "active" : ""}
            onClick={() => setTab("compiled")}
          >
            Compiled comparison
          </button>
          <button
            className={tab === "logical" ? "active" : ""}
            onClick={() => setTab("logical")}
          >
            Logical input
          </button>
        </div>
      </div>
      {tab === "logical" && (preview || result?.input) ? (
        <CircuitViewer
          key={JSON.stringify(preview || result?.input)}
          circuit={(preview || result?.input)!}
          title={preview ? "Input circuit preview" : "Run input circuit"}
        />
      ) : result ? (
        <>
          {selectedCircuit && (
            <div className="circuit-delta" aria-label="Circuit changes">
              <div><span>Depth</span><strong>{baselineMetrics?.depth ?? baselineCircuit?.depth} <span>to</span> {selectedMetrics?.depth ?? selectedCircuit.depth}</strong></div>
              <div><span>Two-qubit gates</span><strong>{baselineMetrics?.n2q ?? "—"} <span>to</span> {selectedMetrics?.n2q ?? "—"}</strong></div>
              <div><span>Gate-pattern changes</span><strong>{selectedChanged?.size ?? 0}</strong></div>
              <p>Bright outlines mark gates with changed type, wire, or parameter. Both circuits remain equivalent.</p>
            </div>
          )}
          <CircuitViewer
            key={`base-${result.request.seed}`}
            circuit={result.baseline.circuit!}
            title="Baseline compilation"
            subtitle={`${result.request.backend} · optimization ${result.request.optimization_level} · original circuit`}
            changedGateIds={baselineChanged}
          />
          {result.selected?.circuit ? (
            <CircuitViewer
              key={result.selected.id + result.elapsed_seconds}
              circuit={result.selected.circuit}
              title="Selected compilation"
              subtitle={`${result.selected.strategy.replaceAll("+", " + ")} · seed ${result.selected.seed} · verified equivalent`}
              changedGateIds={selectedChanged}
            />
          ) : (
            <div className="empty-selected">
              <span className="empty-icon">∅</span>
              <h3>No changed candidate within budget</h3>
              <p>
                Inspect candidate evidence below. The verified baseline remains
                available for export.
              </p>
            </div>
          )}
        </>
      ) : preview ? (
        <CircuitViewer
          key={JSON.stringify(preview)}
          circuit={preview}
          title="Input circuit preview"
        />
      ) : (
        <div className="workspace-empty">
          <div className="quantum-mark">|ψ⟩</div>
          <h3>No circuit loaded</h3>
          <div className="empty-wires">
            <span>q0 ─── H ───●─────────</span>
            <span>q1 ──────── ⊕ ── RZ ──</span>
            <span>q2 ─── H ──────────────</span>
          </div>
        </div>
      )}
    </section>
  );
}
