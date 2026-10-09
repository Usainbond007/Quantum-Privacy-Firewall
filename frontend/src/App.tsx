import { useEffect, useRef, useState } from "react";
import { CircuitControls } from "./components/CircuitControls";
import { CircuitComparison } from "./components/CircuitComparison";
import { MetricCards } from "./components/MetricCards";
import { VerificationPanel } from "./components/VerificationPanel";
import { CandidateTable } from "./components/CandidateTable";
import { RunProgress } from "./components/RunProgress";
import { CircuitViewer } from "./components/CircuitViewer";
import { AccuracyPanel } from "./components/AccuracyPanel";
import { AccuracySummary } from "./components/AccuracySummary";
import { useRun } from "./hooks/useRun";
import { api } from "./lib/api";
import type {
  Candidate,
  Circuit,
  Options,
  RunRequest,
  ResearchBenchmarks,
} from "./types/demo";

const initial: RunRequest = {
  family: "graph_ghz",
  width: 4,
  seed: 21,
  backend: "FakeNighthawk",
  optimization_level: 2,
  transpile_seed: 11,
  candidates: 6,
  budget: 0.2,
  strategies: ["layout", "decomp+layout", "decomp+reorder"],
};

export default function App() {
  const [options, setOptions] = useState<Options | null>(null);
  const [config, setConfig] = useState(initial);
  const [preview, setPreview] = useState<Circuit | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [inspecting, setInspecting] = useState<Candidate | null>(null);
  const [optionRetry, setOptionRetry] = useState(0);
  const [benchmarks, setBenchmarks] = useState<ResearchBenchmarks | null>(null);
  const [benchmarkError, setBenchmarkError] = useState<string | null>(null);
  const [benchmarkRetry, setBenchmarkRetry] = useState(0);
  const [researchBudget, setResearchBudget] = useState(0.2);
  const [researchAttacker, setResearchAttacker] = useState("adaptive_rf");
  const previewController = useRef<AbortController | null>(null);
  const { run, error: runError, submit, retry, busy } = useRun();
  const result = run?.result || null;
  useEffect(() => {
    const controller = new AbortController();
    setError(null);
    api
      .options(controller.signal)
      .then(setOptions)
      .catch((err) => {
        if (!controller.signal.aborted) setError(err.message);
      });
    return () => controller.abort();
  }, [optionRetry]);
  useEffect(() => () => previewController.current?.abort(), []);
  useEffect(() => {
    const controller = new AbortController();
    setBenchmarkError(null);
    api
      .benchmarks(controller.signal)
      .then(setBenchmarks)
      .catch((err) => {
        if (!controller.signal.aborted)
          setBenchmarkError(
            err instanceof Error ? err.message : "Benchmark request failed",
          );
      });
    return () => controller.abort();
  }, [benchmarkRetry]);
  async function generatePreview() {
    previewController.current?.abort();
    const controller = new AbortController();
    previewController.current = controller;
    setPreviewing(true);
    setError(null);
    try {
      const next = await api.preview(
        { family: config.family, width: config.width, seed: config.seed },
        controller.signal,
      );
      if (!controller.signal.aborted) setPreview(next);
    } catch (err) {
      if (!controller.signal.aborted)
        setError(err instanceof Error ? err.message : "Preview failed");
    } finally {
      if (!controller.signal.aborted) setPreviewing(false);
    }
  }
  function changeConfig(next: RunRequest) {
    previewController.current?.abort();
    setPreviewing(false);
    setPreview(null);
    setConfig(next);
  }
  return (
    <div className="app-shell">
      <header className="topbar">
        <a href="/" className="brand">
          <span className="brand-mark">Q</span>
          <span>
            QUANTUM PRIVACY<span className="brand-sub">FIREWALL</span>
          </span>
        </a>
        <div className="topbar-right">
          <span className="environment-tag">
            <span className="status-dot" />
            LOCAL CIRCUIT LAB
          </span>
          <span className="version mono">DEMO / V0.1</span>
        </div>
      </header>
      <main>
        <AccuracySummary
          data={result?.benchmarks || benchmarks}
          budget={researchBudget}
          onBudgetChange={setResearchBudget}
          attacker={researchAttacker}
          onAttackerChange={setResearchAttacker}
        />
        <div className="hero">
          <div>
            <div className="eyebrow accent">Pre-submission circuit audit</div>
            <h1>
              Same computation.
              <br />
              <span>A different signature.</span>
            </h1>
            <p>
              Explore circuit transformations, verify their semantics,
              <br className="desktop-break" /> and inspect the trade-off in
              compiled structure.
            </p>
          </div>
          <div className="hero-aside">
            <span className="mono">GENERATE → TRANSFORM → VERIFY</span>
            <div className="hero-line" />
            <p>
              Equivalence is checked.
              <br />
              Privacy is an experiment.
            </p>
          </div>
        </div>
        {(error || runError) && (
          <div className="error-banner" role="alert">
            <span>{error || runError}</span>
            {!options ? (
              <button onClick={() => setOptionRetry((x) => x + 1)}>
                Retry connection
              </button>
            ) : runError && busy ? (
              <button onClick={retry}>Retry polling</button>
            ) : error ? (
              <button onClick={() => setError(null)}>Dismiss</button>
            ) : null}
          </div>
        )}
        <div className="lab-grid">
          {options ? (
            <CircuitControls
              options={options}
              value={config}
              onChange={changeConfig}
              onPreview={() => void generatePreview()}
              onRun={() => {
                previewController.current?.abort();
                setPreviewing(false);
                setPreview(null);
                setInspecting(null);
                setError(null);
                void submit(config);
              }}
              busy={busy}
              previewing={previewing}
            />
          ) : (
            <aside className="panel controls">
              <h2>Connecting to circuit engine…</h2>
              <p className="hint">Start the FastAPI server on port 8000.</p>
            </aside>
          )}
          <div className="workspace">
            <RunProgress run={run} />
            {result && (
              <div
                className={`outcome-banner ${result.selected ? "success" : ""}`}
              >
                <span>{result.selected ? "✓" : "∅"}</span>
                <div>
                  <strong>{result.message}</strong>
                  <p>
                    {result.selected
                      ? `${result.selected.strategy.replaceAll("+", " + ")} · both equivalence checks PASS · overhead within ${(result.request.budget * 100).toFixed(0)}%`
                      : "All candidates were unchanged, outside the budget, or lacked verified equivalence."}
                  </p>
                </div>
                <div className="export-buttons">
                  <a href={api.exportUrl(run!.id, "qasm")} download>
                    ↓ QASM
                  </a>
                  <a href={api.exportUrl(run!.id, "metrics")} download>
                    ↓ Evidence
                  </a>
                </div>
              </div>
            )}
            <MetricCards result={result} />
            <AccuracyPanel
              benchmarks={benchmarks}
              result={result}
              error={benchmarkError}
              onRetry={() => setBenchmarkRetry((x) => x + 1)}
              researchBudget={researchBudget}
              onResearchBudgetChange={setResearchBudget}
              researchAttacker={researchAttacker}
              onResearchAttackerChange={setResearchAttacker}
            />
            <CircuitComparison preview={preview} result={result} />
            {result && (
              <>
                <VerificationPanel result={result} inspecting={inspecting} />
                <CandidateTable
                  result={result}
                  inspecting={inspecting}
                  onInspect={setInspecting}
                />
                {inspecting?.circuit && (
                  <div className="panel">
                    <CircuitViewer
                      key={inspecting.id}
                      circuit={inspecting.circuit}
                      title={`Inspecting ${inspecting.id}`}
                    />
                  </div>
                )}
              </>
            )}
          </div>
        </div>
        <footer>
          <span>QPF / Quantum Privacy Firewall</span>
          <span>
            Fake backend snapshots · no hardware execution · no proven privacy
            guarantee
          </span>
          <a href="/docs" target="_blank" rel="noreferrer">
            API documentation ↗
          </a>
        </footer>
      </main>
    </div>
  );
}
