import { useEffect, useState } from "react";
import type { Circuit, DemoResult } from "../types/demo";
import { CircuitViewer } from "./CircuitViewer";

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
          <CircuitViewer
            key={`base-${result.request.seed}`}
            circuit={result.baseline.circuit!}
            title="Baseline compilation"
            subtitle={`${result.request.backend} · optimization ${result.request.optimization_level} · original circuit`}
          />
          {result.selected?.circuit ? (
            <CircuitViewer
              key={result.selected.id + result.elapsed_seconds}
              circuit={result.selected.circuit}
              title="Selected compilation"
              subtitle={`${result.selected.strategy.replaceAll("+", " + ")} · seed ${result.selected.seed} · verified equivalent`}
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
