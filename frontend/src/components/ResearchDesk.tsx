import { useEffect, useRef, useState, type ReactNode } from "react";
import { api } from "../lib/api";
import { CircuitViewer } from "./CircuitViewer";
import { AccuracyPanel } from "./AccuracyPanel";
import type { ResearchBenchmarks } from "../types/demo";
import type { GroverResult, PortfolioResult } from "../types/usecases";
const pct = (n: number) => `${(n * 100).toFixed(1)}%`;
const delta = (n: number) => `${n >= 0 ? "+" : ""}${pct(n)}`;
const nice = (s: string) => s.replaceAll("_", " ");
const steps = [
  ["Workload", "From a classical problem"],
  ["Observer", "See what leaves the lab"],
  ["Transform", "Test supported changes"],
  ["Evidence", "Verify and assess"],
];
const prefs = ["risk_first", "balanced", "return_first"];
function Badge({ children }: { children: ReactNode }) {
  return (
    <span
      className={`evidence-badge ${children === "PASS" ? "pass" : children === "BLOCK" || children === "FAIL" ? "block" : "neutral"}`}
    >
      {children}
    </span>
  );
}
function Section({
  title,
  eyebrow,
  children,
}: {
  title: string;
  eyebrow?: string;
  children: ReactNode;
}) {
  return (
    <section className="desk-section">
      {eyebrow && <div className="eyebrow">{eyebrow}</div>}
      <h2>{title}</h2>
      {children}
    </section>
  );
}
function Table({ heads, rows }: { heads: string[]; rows: ReactNode[][] }) {
  return (
    <div className="desk-table-scroll">
      <table className="desk-table">
        <thead>
          <tr>
            {heads.map((h) => (
              <th key={h}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {r.map((c, j) => (
                <td key={j}>{c}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
function download(data: unknown, file: string) {
  const u = URL.createObjectURL(
    new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
  );
  const a = document.createElement("a");
  a.href = u;
  a.download = file;
  a.click();
  setTimeout(() => URL.revokeObjectURL(u), 1000);
}
export function CasePage({ kind }: { kind: "cryptanalysis" | "portfolio" }) {
  const cyber = kind === "cryptanalysis";
  const [step, setStep] = useState(0),
    [observer, setObserver] = useState("artifact"),
    [marked, setMarked] = useState("1010"),
    [budget, setBudget] = useState(0.2),
    [pref, setPref] = useState("risk_first"),
    [other, setOther] = useState("return_first");
  const [grover, setGrover] = useState<GroverResult | null>(null),
    [portfolio, setPortfolio] = useState<PortfolioResult | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState<string | null>(null),
    [policy, setPolicy] = useState(false),
    [selected, setSelected] = useState<string | null>(null),
    [seconds, setSeconds] = useState(0);
  const abort = useRef<AbortController | null>(null);
  useEffect(() => () => abort.current?.abort(), []);
  useEffect(() => {
    if (!busy) return;
    setSeconds(0);
    const t = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, [busy]);
  const result = cyber ? grover : portfolio;
  const stale = cyber
    ? !!grover && (marked !== grover.marked || budget !== grover.budget)
    : !!portfolio &&
      (pref !== portfolio.preference || other !== portfolio.other);
  const decision = cyber ? grover?.decision : portfolio?.direct.decision;
  const candidate = grover?.candidates.find(
    (c) => c.id === (selected || grover.selected),
  );
  const valid = cyber ? /^[01]{4}$/.test(marked) : pref !== other;
  async function run() {
    if (!valid || busy) return;
    abort.current?.abort();
    const c = new AbortController();
    abort.current = c;
    setBusy(true);
    setError(null);
    try {
      if (cyber) {
        const r = await api.grover({ marked, budget }, c.signal);
        setGrover(r);
        setSelected(r.selected || r.candidates[0]?.id || null);
      } else
        setPortfolio(
          await api.portfolio({ preference: pref, other }, c.signal),
        );
      setStep(3);
    } catch (e) {
      if (!c.signal.aborted)
        setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      if (!c.signal.aborted) setBusy(false);
    }
  }
  const receipt = cyber
    ? grover?.receipt
    : portfolio
      ? {
          schema_version: 2,
          decision: portfolio.direct.decision,
          sweep_decision: portfolio.sweep.decision,
          dataset_sha256: portfolio.data.sha256,
          public_sweep_hash: portfolio.sweep.job_hash_a,
          sweep_compiled_checks: portfolio.sweep.compiled_checks,
          same_public_job: portfolio.sweep.identical,
          logical_verification: portfolio.direct.rewrite.verification,
          compiled_verification: portfolio.direct.rewrite.compiled_verification,
          scope: portfolio.scope,
          enforcement: "Local assessment only; no cloud submission",
        }
      : null;
  const controls = (
    <div className="case-controls">
      {cyber ? (
        <>
          <label>
            Test pattern · 4 bits
            <input
              aria-label="Marked state"
              value={marked}
              maxLength={4}
              disabled={busy}
              onChange={(e) => setMarked(e.target.value.replace(/[^01]/g, ""))}
            />
          </label>
          <label>
            Overhead budget
            <select
              aria-label="Overhead budget"
              value={budget}
              disabled={busy}
              onChange={(e) => setBudget(Number(e.target.value))}
            >
              {[0, 0.1, 0.2, 0.5].map((v) => (
                <option key={v} value={v}>
                  {pct(v)}
                </option>
              ))}
            </select>
          </label>
        </>
      ) : (
        <>
          <label>
            Private preference
            <select
              aria-label="Private preference"
              value={pref}
              disabled={busy}
              onChange={(e) => setPref(e.target.value)}
            >
              {prefs.map((p) => (
                <option key={p} value={p}>
                  {nice(p)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Compare against
            <select
              aria-label="Compare with"
              value={other}
              disabled={busy}
              onChange={(e) => setOther(e.target.value)}
            >
              {prefs.map((p) => (
                <option key={p} value={p}>
                  {nice(p)}
                </option>
              ))}
            </select>
          </label>
        </>
      )}
      <button
        className="primary-action"
        disabled={!valid || busy}
        onClick={() => void run()}
      >
        {busy
          ? `Running checks · ${seconds}s`
          : result
            ? "Run again"
            : "Run live assessment"}
      </button>
    </div>
  );
  return (
    <article className="case-page">
      <div className="case-heading">
        <div className="eyebrow">
          {cyber
            ? "01 / CONFIDENTIAL QUANTUM RESEARCH"
            : "02 / PRIVATE INVESTMENT RESEARCH"}
        </div>
        <h1>
          {cyber ? "Confidential cryptanalysis" : "Portfolio optimization"}
        </h1>
        <p>
          {cyber
            ? "A security team’s test condition can be exposed by the quantum job built to evaluate it. Inspect the leakage before sharing the circuit."
            : "An investment desk’s private priorities can be read from its quantum job. Inspect the payload, then compare a preference-independent workflow."}
        </p>
        <div className="case-meta">
          <span>
            {cyber ? "Grover search" : "Constrained QAOA-style ansatz"}
          </span>
          <span>
            {cyber
              ? "4 qubits · synthetic predicate"
              : "8 assets · public market snapshot"}
          </span>
          <span>Live local computation</span>
        </div>
      </div>
      <nav className="workflow-steps" aria-label={`${kind} workflow`}>
        {steps.map(([name, sub], i) => (
          <button
            key={name}
            aria-current={step === i ? "step" : undefined}
            onClick={() => setStep(i)}
          >
            <span className="step-number">{i + 1}</span>
            <span>
              <strong>{name}</strong>
              <small>{sub}</small>
            </span>
          </button>
        ))}
      </nav>
      <div className="case-columns">
        <div className="case-body">
          {busy && (
            <div className="run-notice" role="status">
              <span className="loading-ring" />
              Computing circuits, attacks and verification. The first run can
              take a minute.
            </div>
          )}
          {error && (
            <div className="run-error" role="alert">
              <strong>Assessment could not finish.</strong>
              <p>{error}</p>
              <p>
                Check that FastAPI is running on port 8000, then retry. No
                result has been invented.
              </p>
              <button onClick={() => void run()} disabled={busy}>
                Retry assessment
              </button>
            </div>
          )}
          {stale && (
            <div className="stale-notice" role="status">
              Inputs changed. Evidence below belongs to the previous run. Run
              again to assess these inputs.
            </div>
          )}
          {!valid && (
            <p className="validation-message">
              {cyber
                ? "Enter exactly four binary digits."
                : "Choose two different preferences to compare."}
            </p>
          )}
          {step === 0 && (
            <>
              <Section
                title={
                  cyber
                    ? "The problem starts with a classical question"
                    : "A familiar decision. A different computing workflow."
                }
              >
                <p>
                  {cyber
                    ? "Which input satisfies our confidential test? A communications-security team might study a toy authentication rule before publication. Here, the rule marks one of 16 four-bit strings. A classical search can test those strings directly."
                    : "Which four of eight assets best match our risk and return priorities? Classically, we can enumerate all 70 feasible portfolios. The market data is public; the analyst’s chosen trade-off is private."}
                </p>
                <div className="journey">
                  <div>
                    <span>01 · CLASSICAL INPUT</span>
                    <h3>
                      {cyber ? "Define the test" : "Define the objective"}
                    </h3>
                    <p>
                      {cyber
                        ? "A Boolean condition f(x). This demo uses one marked string."
                        : "Minimize weighted risk minus weighted return, holding exactly four assets."}
                    </p>
                  </div>
                  <div>
                    <span>02 · QUANTUM WORKLOAD</span>
                    <h3>
                      {cyber ? "Encode an oracle" : "Encode cost & mixer"}
                    </h3>
                    <p>
                      {cyber
                        ? "The oracle changes the target’s phase. Three Grover iterations amplify its output probability."
                        : "Cost angles encode the weights. XY mixing preserves the four-asset constraint."}
                    </p>
                  </div>
                  <div>
                    <span>03 · QPF CHECK</span>
                    <h3>Inspect before sharing</h3>
                    <p>
                      {cyber
                        ? "Run two attackers, rewrite the circuit, verify it and measure residual exposure."
                        : "Recover weights from the payload. Compare a rewrite and a fixed public sweep."}
                    </p>
                  </div>
                </div>
                <div className="quiet-note">
                  {cyber
                    ? "A small, noiseless simulation—not a break of AES or deployed cryptography. No quantum speedup is demonstrated."
                    : "A fixed-angle research circuit, not a trained optimizer or investment recommendation. Exact classical enumeration is the reference; no quantum speedup is claimed."}
                </div>
              </Section>
              <Section
                title={
                  cyber
                    ? "Build the Grover workload"
                    : "Build the portfolio workload"
                }
                eyebrow="RUNNABLE EXPERIMENT"
              >
                <p>
                  {cyber
                    ? "Choose a synthetic test pattern and the allowed increase in compiled depth and two-qubit gates. The backend evaluates 12 rewrite candidates."
                    : "Compare two synthetic preferences. The backend builds the cost circuit, tests weight recovery and simulates a fixed three-preference public sweep."}
                </p>
                {controls}
                <small className="form-note">
                  Inputs go to your local FastAPI process. No job is submitted
                  to a quantum cloud.
                </small>
                {result && (
                  <div className="inline-result">
                    <Badge>{decision?.status}</Badge>
                    <span>
                      Computed in {result.elapsed_seconds.toFixed(1)}s.
                    </span>
                    <button onClick={() => setStep(3)}>
                      Inspect evidence →
                    </button>
                  </div>
                )}
              </Section>
              {cyber && grover && (
                <CircuitViewer
                  circuit={grover.baseline.circuit}
                  title="Original Grover circuit"
                />
              )}
              {!cyber && portfolio && (
                <>
                  <CircuitViewer
                    circuit={portfolio.workload.circuit}
                    title="Parameterized portfolio circuit"
                  />
                  <Section title="The data behind the job">
                    <p>{portfolio.data.note}</p>
                    <Table
                      heads={[
                        "Asset",
                        "Expected return (dataset units)",
                        "Variance",
                      ]}
                      rows={portfolio.workload.asset_rows.map((a) => [
                        a.ticker,
                        a.expected_return.toFixed(6),
                        a.variance.toFixed(6),
                      ])}
                    />
                    <details>
                      <summary>Dataset provenance</summary>
                      <a
                        href={portfolio.data.source}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Qiskit public market dataset ↗
                      </a>
                      <code className="hash">
                        SHA-256: {portfolio.data.sha256}
                      </code>
                    </details>
                  </Section>
                </>
              )}
            </>
          )}
          {step === 1 && (
            <>
              <Section
                title="Change the observer, change the privacy question"
                eyebrow="THREAT MODEL"
              >
                <p>
                  The observer already has access to a shared job artifact—for
                  example, its recipient or an operator. This does not assume
                  that another cloud tenant can read your job.
                </p>
                <div className="segmented" aria-label="Observer access">
                  <button
                    aria-pressed={observer === "structure"}
                    onClick={() => setObserver("structure")}
                  >
                    Structure only
                  </button>
                  <button
                    aria-pressed={observer === "artifact"}
                    onClick={() => setObserver("artifact")}
                  >
                    Full logical artifact
                  </button>
                </div>
                {observer === "structure" ? (
                  <>
                    <h3>Gate patterns can reveal the type of work.</h3>
                    <p>
                      {cyber
                        ? "Gate counts, depth and connectivity can suggest an algorithm family. The family classifier in Circuit Lab tests this separate question. Identifying Grover is not the same as recovering its marked string."
                        : "The parameterized template is the same for every preference. A structure-only observer cannot distinguish the preferences from it alone. The 1/3 uniform-prior guessing baseline is analytical, not a trained classifier result."}
                    </p>
                    <a href="#lab" className="text-link">
                      Open the family-leakage circuit lab →
                    </a>
                  </>
                ) : (
                  <>
                    <h3>
                      {cyber
                        ? "An equivalent function can still expose the predicate."
                        : "The numbers in the job can disclose the preference."}
                    </h3>
                    <p>
                      {cyber
                        ? "A simple attacker looks for X gates around the oracle. A stronger small-circuit attacker computes the exact output distribution and selects the most likely string. Rewrites can defeat the first while leaving the second effective."
                        : "Knowing the public risk matrix and returns, a payload reader solves a linear system to recover the risk/return weights from the logical template’s numeric angle bindings. This is a reconstruction, not a confidence score."}
                    </p>
                  </>
                )}
                <Table
                  heads={["Information", "Observed?", "What we test"]}
                  rows={
                    cyber
                      ? [
                          [
                            "Algorithm family",
                            "Structural clues",
                            "Separate benchmark / Circuit Lab",
                          ],
                          [
                            "Marked string",
                            "Encoded in circuit function",
                            "Pattern reader + exact logical simulation",
                          ],
                          [
                            "Cloud timing / transport",
                            "Outside this experiment",
                            "Not tested",
                          ],
                        ]
                      : [
                          [
                            "Asset universe & model",
                            "Public in this demo",
                            "Dataset provenance",
                          ],
                          [
                            "Private weights",
                            "Encoded in original bindings",
                            "Least-squares reconstruction",
                          ],
                          [
                            "Runtime credentials / timing",
                            "Outside this experiment",
                            "Not tested",
                          ],
                        ]
                  }
                />
              </Section>
              {cyber && grover && (
                <Section title="What the original circuit reveals">
                  <Table
                    heads={["Attacker", "Recovered string", "Evidence"]}
                    rows={[
                      [
                        "Pattern reader",
                        grover.baseline.pattern_guess,
                        "Original logical gate pattern",
                      ],
                      [
                        "Exact simulator",
                        grover.baseline.exact_guess,
                        `${pct(grover.baseline.exact_probability)} probability of this output`,
                      ],
                    ]}
                  />
                  <p>Output probability is not classifier accuracy.</p>
                </Section>
              )}
              {!cyber && portfolio && (
                <Section title="Recovered from actual input bindings">
                  <Table
                    heads={["Weight", "Input", "Recovered"]}
                    rows={portfolio.direct.payload_attacker.true_weights.map(
                      (w, i) => [
                        i === 0 ? "Risk" : "Return",
                        w.toFixed(4),
                        portfolio.direct.payload_attacker.recovered_weights[
                          i
                        ].toFixed(4),
                      ],
                    )}
                  />
                  <p>
                    Residual:{" "}
                    <code>
                      {portfolio.direct.payload_attacker.residual.toExponential(
                        2,
                      )}
                    </code>
                    . {portfolio.direct.attack_scope}
                  </p>
                  <details>
                    <summary>Inspect numeric bindings</summary>
                    <pre>
                      {JSON.stringify(portfolio.direct.bindings, null, 2)}
                    </pre>
                  </details>
                </Section>
              )}
              {!result && (
                <div className="empty-evidence">
                  <strong>No observation results yet</strong>
                  <p>Run the assessment to inspect actual attacker outputs.</p>
                  {controls}
                </div>
              )}
            </>
          )}
          {step === 2 && (
            <>
              <Section
                title="Change the representation. Check the computation."
                eyebrow="QPF TRANSFORMATIONS"
              >
                <p>
                  QPF generates alternatives, checks equivalence, measures
                  compiled cost and retests exposure. A visually different
                  circuit is not automatically private.
                </p>
                <Table
                  heads={[
                    "Transformation",
                    "Available here",
                    "Correctness contract",
                  ]}
                  rows={
                    cyber
                      ? [
                          [
                            "Local decomposition",
                            "4 seeds",
                            "Same logical unitary",
                          ],
                          [
                            "Dependency-safe reordering",
                            "4 seeds",
                            "Same logical unitary",
                          ],
                          [
                            "Decomposition + reordering",
                            "4 seeds",
                            "Same logical unitary",
                          ],
                          [
                            "Layout diversification",
                            "In Circuit Lab",
                            "Layout-aware equivalence",
                          ],
                        ]
                      : [
                          [
                            "Decomposition + reordering",
                            "Bound portfolio circuit",
                            "Same logical unitary",
                          ],
                          [
                            "Fixed public sweep",
                            "3 public weights for every analyst",
                            "Identical template + bindings",
                          ],
                          [
                            "Local choice",
                            "From simulated candidates",
                            "Classical feasibility / utility",
                          ],
                        ]
                  }
                />
              </Section>
              {!cyber && (
                <Section title="Keep the preference out of the outbound job">
                  <p>
                    Run the same public set of weights for everyone. After
                    results return, choose a portfolio locally with the private
                    preference. The job can be identical even when local choices
                    differ.
                  </p>
                  <div className="quiet-note">
                    This removes preference-specific variation under a narrow
                    fixed-job model. It does not hide assets, the model, timing
                    or identity. It costs three circuit evaluations rather than
                    one.
                  </div>
                </Section>
              )}
              {controls}
              {cyber && grover && (
                <Section title="Inspect a computed candidate">
                  <label className="candidate-picker">
                    Candidate
                    <select
                      value={selected || ""}
                      onChange={(e) => setSelected(e.target.value)}
                    >
                      {grover.candidates.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.id} · {c.strategy} · seed {c.seed}
                        </option>
                      ))}
                    </select>
                  </label>
                  {candidate && (
                    <>
                      <div className="inline-result">
                        <Badge>{candidate.verification}</Badge>
                        <span>Logical equivalence · {candidate.method}</span>
                      </div>
                      <CircuitViewer
                        circuit={candidate.circuit}
                        title={`Rewritten circuit ${candidate.id}`}
                      />
                    </>
                  )}
                </Section>
              )}
              {!cyber && portfolio && (
                <CircuitViewer
                  circuit={portfolio.direct.candidate_circuit}
                  title="Rewritten bound portfolio circuit"
                />
              )}
            </>
          )}
          {step === 3 && (
            <>
              {!result ? (
                <Section title="Evidence starts with a run">
                  <p>
                    No experiment has been run for this case. Release requires
                    correctness, cost and secret-specific evidence.
                  </p>
                  {controls}
                  <Table
                    heads={["Check", "State"]}
                    rows={[
                      ["Attacker observations", "Not run"],
                      ["Logical / compiled equivalence", "Not run"],
                      ["Resource overhead / utility", "Not run"],
                      ["Release eligibility", "Unavailable until assessed"],
                    ]}
                  />
                </Section>
              ) : cyber && grover ? (
                <GroverEvidence
                  r={grover}
                  selected={selected}
                  onSelect={setSelected}
                />
              ) : portfolio ? (
                <PortfolioEvidence r={portfolio} />
              ) : null}
              {result && (
                <>
                  <Section title="Scope of this result">
                    <ul className="scope-list">
                      {result.scope.map((s) => (
                        <li key={s}>{s}</li>
                      ))}
                    </ul>
                  </Section>
                  <details className="receipt-detail">
                    <summary>Inspect the shareable assessment receipt</summary>
                    <p>
                      Explicit private inputs are omitted. Hashes are
                      identifiers, not confidentiality protection; tiny input
                      spaces can be guessed.
                    </p>
                    <pre>{JSON.stringify(receipt, null, 2)}</pre>
                    <button
                      className="secondary-action"
                      onClick={() =>
                        download(receipt, `qpf-${kind}-receipt.json`)
                      }
                    >
                      Download receipt JSON
                    </button>
                  </details>
                  {controls}
                </>
              )}
            </>
          )}
        </div>
        <aside className="assessment-aside">
          <span className="eyebrow">LOCAL POLICY ASSESSMENT</span>
          <div
            className={`decision-card ${busy || stale ? "pending" : decision?.status.toLowerCase() || "pending"}`}
            role="status"
          >
            <span className="decision-overline">
              {busy
                ? "COMPUTING"
                : stale
                  ? "INPUTS CHANGED"
                  : result
                    ? "LATEST RUN"
                    : "AWAITING EVIDENCE"}
            </span>
            <strong>
              {busy
                ? "Running"
                : stale
                  ? "Rerun needed"
                  : decision?.status || "Not assessed"}
            </strong>
            <p>
              {busy
                ? "Waiting for backend evidence."
                : stale
                  ? "The previous decision does not apply to edited inputs."
                  : decision
                    ? decision.reasons[0]
                    : "Run the experiment to measure exposure and verify rewrites."}
            </p>
          </div>
          <p className="aside-caption">
            {cyber
              ? "The sensitive fact is the test predicate, not just the algorithm’s name."
              : "The sensitive fact is the analyst’s preference, not the public market data."}
          </p>
          <div className="aside-rule" />
          <h3>What a verdict means</h3>
          <p>
            Equivalence checks correctness. Attacker tests measure specific
            exposure. Neither alone proves secrecy.
          </p>
          <button
            className="text-link"
            onClick={() => setPolicy(!policy)}
            aria-expanded={policy}
          >
            {policy ? "Hide policy ↑" : "View release policy →"}
          </button>
          {policy && (
            <div className="policy-definitions">
              <p>
                <Badge>RELEASE</Badge> All required correctness, cost and scoped
                privacy checks pass. Neither demo establishes general
                confidentiality.
              </p>
              <p>
                <Badge>WARN</Badge> A scoped workflow reduces exposure with
                explicit limitations. No automatic submission.
              </p>
              <p>
                <Badge>BLOCK</Badge> Sensitive information is recovered,
                verification is FAIL/UNKNOWN, or no eligible candidate meets the
                budget.
              </p>
            </div>
          )}
          <div className="aside-rule" />
          <h3>Present this finding</h3>
          <p>
            {cyber
              ? "“We change the circuit without changing its computation. If a stronger reader still recovers the secret, QPF refuses to call it protected.”"
              : "“Hiding circuit shape does not hide parameter values. A fixed public job moves the private decision back to the analyst.”"}
          </p>
          {result && (
            <button
              className="secondary-action"
              onClick={() => download(receipt, `qpf-${kind}-receipt.json`)}
            >
              Export receipt
            </button>
          )}
          <small className="aside-foot">
            Research decision support.
            <br />
            No external job is submitted or blocked by this app.
          </small>
        </aside>
      </div>
    </article>
  );
}
function GroverEvidence({
  r,
  selected,
  onSelect,
}: {
  r: GroverResult;
  selected: string | null;
  onSelect: (s: string) => void;
}) {
  const sel = r.candidates.find((c) => c.id === r.selected),
    inspect = r.candidates.find((c) => c.id === selected);
  return (
    <>
      <Section
        title="The rewrite can pass. The disclosure can remain."
        eyebrow="COMPUTED RESULT"
      >
        <p>
          {r.summary.verified} of {r.summary.total} logical candidates passed
          equivalence. Across verified candidates, the pattern reader recovered
          the string in {pct(r.summary.pattern_recovery_rate)} and the exact
          simulator in {pct(r.summary.exact_recovery_rate)}. These are
          candidate-level results for one input, not population accuracy.
        </p>
        <Table
          heads={["Check", "Original", "Selected candidate"]}
          rows={[
            [
              "Pattern reader",
              r.baseline.pattern_guess,
              sel
                ? `${sel.pattern_guess} · ${sel.pattern_recovers ? "recovered" : "missed"}`
                : "No eligible candidate",
            ],
            [
              "Exact simulator",
              r.baseline.exact_guess,
              sel
                ? `${sel.exact_guess} · ${sel.exact_recovers ? "recovered" : "missed"}`
                : "—",
            ],
            [
              "Most-likely output probability",
              pct(r.baseline.exact_probability),
              sel ? pct(sel.exact_probability) : "—",
            ],
            [
              "Logical equivalence",
              "Reference",
              sel ? <Badge>{sel.verification}</Badge> : "—",
            ],
            [
              "Compiled equivalence",
              <Badge>{r.baseline.compiled_verification.status}</Badge>,
              sel ? <Badge>{sel.compiled_verification.status}</Badge> : "—",
            ],
            [
              "Compiled depth",
              r.baseline.metrics.depth,
              sel ? `${sel.metrics.depth} (${delta(sel.overhead.depth)})` : "—",
            ],
            [
              "Compiled two-qubit gates",
              r.baseline.metrics.n2q,
              sel ? `${sel.metrics.n2q} (${delta(sel.overhead.n2q)})` : "—",
            ],
            [
              "Output-distribution distance",
              "0 (reference)",
              sel ? sel.total_variation.toExponential(2) : "—",
            ],
          ]}
        />
        <p className="quiet-note">
          Attacks inspect logical circuits. Compiled equivalence checks all
          basis inputs with layout mapping where supported. No noise or hardware
          utility is measured.
        </p>
      </Section>
      <Section title="All rewrite candidates">
        <p>
          Selection requires logical PASS, compiled PASS and the cost budget.
          Selection does not mean privacy. Select a row to inspect its checks.
        </p>
        <Table
          heads={[
            "Candidate",
            "Rewrite",
            "Logical",
            "Compiled",
            "Depth Δ",
            "2Q Δ",
            "Budget",
            "Exact recovery",
          ]}
          rows={r.candidates.map((c) => [
            <button
              className="row-link"
              onClick={() => onSelect(c.id)}
              aria-pressed={selected === c.id}
            >
              {c.id}
              {r.selected === c.id ? " · selected" : ""}
            </button>,
            c.strategy,
            <Badge>{c.verification}</Badge>,
            <Badge>{c.compiled_verification.status}</Badge>,
            delta(c.overhead.depth),
            delta(c.overhead.n2q),
            c.within_budget ? "Within" : "Exceeded",
            c.exact_recovers ? "Recovered" : "Missed",
          ])}
        />
        {inspect && (
          <div className="inspection-note">
            <strong>
              {inspect.id} · {inspect.compiled_verification.method}
            </strong>
            <p>{inspect.compiled_verification.note}</p>
            <p>
              Logical check: {inspect.method}. Exact distribution distance:{" "}
              {inspect.total_variation.toExponential(2)}.
            </p>
          </div>
        )}
      </Section>
      <details>
        <summary>Exact original output distribution · all 16 strings</summary>
        <Table
          heads={["String", "Probability", "Synthetic target"]}
          rows={r.baseline.probabilities.map((p, i) => [
            i.toString(2).padStart(4, "0"),
            pct(p),
            i.toString(2).padStart(4, "0") === r.marked ? "Yes" : "—",
          ])}
        />
      </details>
    </>
  );
}
function PortfolioEvidence({ r }: { r: PortfolioResult }) {
  const d = r.direct;
  return (
    <>
      <Section
        title="Structure hides the preference. The payload reveals it."
        eyebrow="COMPUTED RESULT"
      >
        <Table
          heads={["Observation", "Evidence", "Interpretation"]}
          rows={[
            [
              "Template structure",
              d.structure_identical_across_preferences
                ? "Identical"
                : "Different",
              "1/3 guessing baseline under uniform priors; not measured ML accuracy",
            ],
            [
              "Original payload reconstruction",
              d.payload_attacker.correct
                ? "Preference recovered"
                : "Not recovered",
              `Residual ${d.payload_attacker.residual.toExponential(2)}`,
            ],
            [
              "Risk / return weights",
              d.payload_attacker.recovered_weights
                .map((v) => v.toFixed(4))
                .join(" / "),
              "Least-squares recovery using public coefficients",
            ],
            [
              "Direct submission",
              <Badge>{d.decision.status}</Badge>,
              d.decision.reasons[0],
            ],
          ]}
        />
      </Section>
      <Section title="Verify the rewrite, measure its cost">
        <Table
          heads={["Check", "Result", "Evidence"]}
          rows={[
            [
              "Logical equivalence",
              <Badge>{d.rewrite.verification}</Badge>,
              d.rewrite.method,
            ],
            [
              "Compiled equivalence",
              <Badge>{d.rewrite.compiled_verification.status}</Badge>,
              d.rewrite.compiled_verification.note,
            ],
            [
              "Compiled depth",
              `${d.rewrite.baseline_metrics.depth} → ${d.rewrite.metrics.depth}`,
              delta(d.rewrite.overhead.depth),
            ],
            [
              "Two-qubit gates",
              `${d.rewrite.baseline_metrics.n2q} → ${d.rewrite.metrics.n2q}`,
              delta(d.rewrite.overhead.n2q),
            ],
            [
              "Output-distribution distance",
              d.rewrite.total_variation.toExponential(2),
              "Original vs rewritten bound circuit",
            ],
            [
              "Four-asset feasibility",
              pct(d.feasible_probability),
              "Exact probability mass on valid portfolios",
            ],
            [
              "Preference sensitivity",
              d.preference_distribution_tv.toExponential(2),
              "Distribution distance between the input preferences",
            ],
          ]}
        />
        <p className="quiet-note">
          Parameter reconstruction tests the original logical bindings. Recovery
          from the rewritten bound circuit and compiled payload is not
          implemented. No privacy improvement is claimed for that rewrite.
        </p>
      </Section>
      <Section title="A fixed public sweep changes what leaves the lab">
        <div className="inline-result">
          <Badge>{r.sweep.decision.status}</Badge>
          <span>Same public job; private choice happens locally.</span>
        </div>
        <p>
          The backend evaluates three public weight settings for either analyst,
          then chooses locally from each circuit’s six most probable feasible
          outputs. It compares that choice to all{" "}
          {r.workload.classical_feasible_count} feasible classical portfolios.
        </p>
        <div className="hash-comparison">
          <div>
            <span>Public job · {nice(r.preference)}</span>
            <code>{r.sweep.job_hash_a}</code>
          </div>
          <div>
            <span>Public job · {nice(r.other)}</span>
            <code>{r.sweep.job_hash_b}</code>
          </div>
          <strong>
            {r.sweep.identical
              ? "MATCH · identical logical template and bindings"
              : "DIFFERENT · not preference-independent"}
          </strong>
        </div>
        <Table
          heads={["Public sweep job", "Compiled check", "Method"]}
          rows={r.sweep.compiled_checks.map((c, i) => [
            `Public weight setting ${i + 1}`,
            <Badge>{c.status}</Badge>,
            c.method,
          ])}
        />
        <p>
          Cost: {r.sweep.jobs} circuit evaluations vs 1 targeted evaluation (+
          {(r.sweep.jobs - 1) * 100}%). {r.sweep.distinct_candidates} distinct
          candidate portfolios. This uses exact probabilities, not finite-shot
          samples.
        </p>
        <Table
          heads={[
            "Local preference",
            "Selected portfolio",
            "Risk",
            "Return",
            "Regret vs exact best",
            "Random mean regret",
          ]}
          rows={Object.entries(r.sweep.picks).map(([k, p]) => [
            nice(k),
            p.tickers.join(", "),
            p.risk.toFixed(4),
            p.ret.toFixed(4),
            p.regret_vs_best.toFixed(4),
            p.random_mean_regret.toFixed(4),
          ])}
        />
        <p>
          Lower regret is better. Risk and return use source dataset units. The
          comparator is uniform random choice among feasible portfolios. No
          quantum advantage is inferred.
        </p>
        <ul className="scope-list">
          {r.sweep.decision.reasons.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ul>
        <p className="quiet-note">
          Hashes cover this logical job representation only. Assets and the
          model remain visible. Identity, timing, transport and access patterns
          are outside the check.
        </p>
      </Section>
    </>
  );
}
export function ResearchPage() {
  const [data, setData] = useState<ResearchBenchmarks | null>(null),
    [error, setError] = useState<string | null>(null),
    [retry, setRetry] = useState(0),
    [budget, setBudget] = useState(0.2),
    [attacker, setAttacker] = useState("adaptive_rf");
  useEffect(() => {
    const c = new AbortController();
    setError(null);
    api
      .benchmarks(c.signal)
      .then(setData)
      .catch((e) => {
        if (!c.signal.aborted) setError(e.message);
      });
    return () => c.abort();
  }, [retry]);
  return (
    <article className="research-page">
      <div className="case-heading">
        <div className="eyebrow">RESEARCH / CLAIMS / LIMITS</div>
        <h1>Make the evidence the pitch.</h1>
        <p>
          QPF brings together exposure tests, correctness checks, resource
          budgets and an explicit decision before sharing a quantum job.
        </p>
      </div>
      <Section title="The judge-facing story">
        <div className="pitch-steps">
          <p>
            <strong>1 · The transition</strong> A classical problem becomes a
            quantum circuit and numeric parameters. Those artifacts can disclose
            its intent or private inputs.
          </p>
          <p>
            <strong>2 · The intervention</strong> QPF tests a named observer,
            generates equivalent rewrites and checks what changed—including
            whether the sensitive fact is still recoverable.
          </p>
          <p>
            <strong>3 · The result</strong> Grover can remain BLOCK despite
            correct rewrites. The portfolio case contrasts a revealing payload
            with a fixed public sweep and local choice.
          </p>
          <p>
            <strong>4 · The contribution</strong> An integrated, attacker-aware
            and cost-aware assessment. The obfuscation methods and public-sweep
            idea are not claimed as new cryptography.
          </p>
        </div>
      </Section>
      <Section title="Three claims that must stay separate">
        <Table
          heads={["Question", "Evidence", "What it does not prove"]}
          rows={[
            [
              "Does the circuit reveal its family?",
              "Saved benchmark / live frozen model",
              "Domain-secret recovery",
            ],
            [
              "Can this secret be recovered?",
              "Live use-case backend tests",
              "General attack accuracy or cloud incidents",
            ],
            [
              "Does the rewrite preserve computation?",
              "Logical / compiled equivalence",
              "Secrecy, noisy utility or quantum advantage",
            ],
          ]}
        />
      </Section>
      <Section title="Saved family-leakage benchmark">
        <p>
          Repository artifacts—not results from the current use-case run.
          Inspect the profile, support, controls and caveats below. The API’s
          available profile is authoritative.
        </p>
        <AccuracyPanel
          benchmarks={data}
          result={null}
          error={error}
          onRetry={() => setRetry((v) => v + 1)}
          researchBudget={budget}
          onResearchBudgetChange={setBudget}
          researchAttacker={attacker}
          onResearchAttackerChange={setAttacker}
        />
      </Section>
      <Section title="Research anchors & prior art">
        <ul className="source-list">
          {[
            [
              "IBM Research · Algorithmic intent leakage",
              "https://research.ibm.com/publications/algorithmic-intent-leakage-in-transpiled-quantum-circuits-an-initial-reverse-engineering-study",
              "Structural family inference; independent QPF implementation.",
            ],
            [
              "IBM · Grover’s algorithm",
              "https://quantum.cloud.ibm.com/docs/en/tutorials/grovers-algorithm",
              "Oracle construction and amplitude amplification.",
            ],
            [
              "IBM · Multi-objective portfolio optimization",
              "https://quantum.cloud.ibm.com/docs/en/tutorials/quantum-approximate-multi-objective-optimization",
              "Workflow and public dataset; this app uses a simplified risk/return model.",
            ],
            [
              "Enigma · QAOA privacy transformations",
              "https://arxiv.org/abs/2311.13546",
              "Prior application-level obfuscation; not a QPF invention.",
            ],
            [
              "SPYCE",
              "https://arxiv.org/abs/2307.16799",
              "Prior circuit obfuscation.",
            ],
            [
              "OPAQUE",
              "https://arxiv.org/abs/2502.16605",
              "Prior obfuscation research.",
            ],
            [
              "MQT QCEC",
              "https://mqt.readthedocs.io/projects/qcec/en/stable/",
              "Equivalence checking, not confidentiality verification.",
            ],
          ].map(([title, url, note]) => (
            <li key={url}>
              <a href={url} target="_blank" rel="noreferrer">
                {title} ↗
              </a>
              <p>{note}</p>
            </li>
          ))}
        </ul>
      </Section>
    </article>
  );
}
