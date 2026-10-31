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
import { QuantumField } from "./components/QuantumField";
import { PixelField } from "./components/PixelField";
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
        <a href="#top" className="brand">
          <span className="brand-mark" aria-hidden="true"><i /><i /><i /><i /></span>
          <span className="brand-copy">QPF<span className="brand-sub">Quantum Privacy Firewall</span></span>
        </a>
        <nav className="topnav" aria-label="Sections">
          <a href="#method">Method</a>
          <a href="#workbench">Demo</a>
          <a href="#research">Results</a>
        </nav>
        <div className="topbar-right">
          <a className="nav-cta" href="#workbench">Open demo</a>
        </div>
      </header>
      <main>
        <section className="landing-hero" id="top">
          <img className="hero-chip-image" src="/visuals/quantum-chip.png" alt="" />
          <div className="hero-chip-grain" aria-hidden="true" />
          <div className="hero-content">
            <h1>Quantum<br />Privacy<br />Firewall<span className="hero-period">.</span></h1>
            <p>Same computation. A different circuit to inspect.</p>
            <div className="hero-actions">
              <a className="hero-primary" href="#workbench">Explore the demo</a>
            </div>
          </div>
        </section>
        <section className="pixel-signal-section" aria-label="Animated circuit signal">
          <div className="pixel-signal-copy"><strong>One computation.<br />Many visible forms.</strong></div>
          <PixelField />
        </section>
        <section className="method-section" id="method">
          <div className="method-intro">
            <h2>Circuit structure<br />can give you away.</h2>
            <p>Quantum circuits reveal recognizable gate patterns before they run. QPF rewrites the circuit, verifies equivalence, and tests what an attacker can still infer.</p>
          </div>
          <div className="method-circuit"><QuantumField /></div>
          <div className="method-track">
            <article><div><h3>01. Detect leakage</h3><p>Test what the circuit reveals about its algorithm family.</p></div></article>
            <article><div><h3>02. Rewrite</h3><p>Search equivalent forms within an overhead budget.</p></div></article>
            <article><div><h3>03. Verify</h3><p>Confirm that the computation is preserved.</p></div></article>
          </div>
        </section>
        <section className="board-section">
          <div className="board-copy"><h2>The pattern is<br />the exposure.</h2><p>Protect the circuit before submission.</p><a href="#workbench">Examine a circuit</a></div>
          <div className="board-visual"><img src="/visuals/circuit-board.png" alt="Circuit-board artwork with dense red traces on a blue ground" loading="lazy" /></div>
        </section>
        <section className="demo-section" id="workbench">
          <div className="demo-heading"><h2>Put a circuit through QPF.</h2></div>
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
              <p className="hint">Connect the local QPF API to begin.</p>
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
        </section>
        <section className="research-section" id="research">
          <div className="research-heading">
            <h2>Research evidence.</h2>
          </div>
          <AccuracySummary
            data={result?.benchmarks || benchmarks}
            budget={researchBudget}
            onBudgetChange={setResearchBudget}
            attacker={researchAttacker}
            onAttackerChange={setResearchAttacker}
          />
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
        </section>
        <footer>
          <div className="footer-top"><span className="footer-wordmark">QPF<span>.</span></span><p>Quantum circuit privacy,<br />verified at the gate level.</p></div>
          <div className="footer-bottom"><span>QPF</span><div><a href="#top">Back to top</a><a href="/docs" target="_blank" rel="noreferrer">API docs</a></div></div>
        </footer>
      </main>
    </div>
  );
}
