import { useEffect, useState, type ReactNode } from "react";
import { api } from "../lib/api";
import type {
  Decision,
  GroverResult,
  PortfolioResult,
} from "../types/usecases";

const pct = (x: number) => `${(x * 100).toFixed(0)}%`;
const signed = (x: number) => `${x >= 0 ? "+" : ""}${(x * 100).toFixed(1)}%`;
const label = (s: string) => s.replace("_", " ");

function DecisionBanner({ d, title }: { d: Decision; title: string }) {
  return (
    <div className={`uc-decision uc-${d.status.toLowerCase()}`} role="status">
      <div className="uc-decision-tag">{d.status}</div>
      <div>
        <strong>{title}</strong>
        <ul>
          {d.reasons.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function Bar({
  label: text,
  value,
  chance,
  tone,
  note,
}: {
  label: string;
  value: number;
  chance?: number;
  tone: "bad" | "ok";
  note?: string;
}) {
  return (
    <div className="uc-bar">
      <div className="uc-bar-top">
        <span>{text}</span>
        <strong>{pct(value)}</strong>
      </div>
      <div
        className="uc-bar-track"
        role="img"
        aria-label={`${text}: ${pct(value)}`}
      >
        <div className={`uc-bar-fill ${tone}`} style={{ width: pct(value) }} />
        {chance !== undefined && (
          <div
            className="uc-bar-chance"
            style={{ left: pct(chance) }}
            title={`chance ${pct(chance)}`}
          />
        )}
      </div>
      {note && <small>{note}</small>}
    </div>
  );
}

function Scope({ items }: { items: string[] }) {
  return (
    <div className="uc-scope">
      <div className="eyebrow">What this does not show</div>
      <ul>
        {items.map((i) => (
          <li key={i}>{i}</li>
        ))}
      </ul>
    </div>
  );
}

function Stat({ k, v, note }: { k: string; v: string; note?: string }) {
  return (
    <div className="uc-stat">
      <span className="mono">{k}</span>
      <strong>{v}</strong>
      {note && <small>{note}</small>}
    </div>
  );
}

function GroverCase() {
  const [marked, setMarked] = useState("1010");
  const [budget, setBudget] = useState(0.2);
  const [res, setRes] = useState<GroverResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const valid = /^[01]{4}$/.test(marked);
  useEffect(() => {
    void run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  async function run() {
    setBusy(true);
    setErr(null);
    try {
      setRes(await api.grover({ marked, budget }));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }
  const sel = res?.candidates.find((c) => c.id === res.selected);
  return (
    <section className="panel uc-case">
      <div className="uc-head">
        <h3>Live check: a Grover circuit</h3>
        <p>
          <strong>Protected fact:</strong> the marked state.{" "}
          <strong>Observer:</strong> anyone holding the submitted circuit file.
          The marked state stays on this machine; only the circuit leaves.
        </p>
      </div>
      <div className="uc-form">
        <label>
          <span className="mono">MARKED STATE (4 BITS, LOCAL ONLY)</span>
          <input
            value={marked}
            maxLength={4}
            onChange={(e) => setMarked(e.target.value.replace(/[^01]/g, ""))}
            aria-label="Marked state"
          />
        </label>
        <label>
          <span className="mono">OVERHEAD BUDGET</span>
          <select
            value={budget}
            onChange={(e) => setBudget(Number(e.target.value))}
            aria-label="Overhead budget"
          >
            {[0, 0.1, 0.2, 0.5].map((b) => (
              <option key={b} value={b}>
                {pct(b)}
              </option>
            ))}
          </select>
        </label>
        <button className="uc-run" disabled={!valid || busy} onClick={run}>
          {busy ? "Checking…" : "Run the check"}
        </button>
      </div>
      {err && (
        <div className="error-banner" role="alert">
          <span>{err}</span>
        </div>
      )}
      {res && (
        <div className="uc-result">
          <DecisionBanner
            d={res.decision}
            title={
              res.decision.status === "BLOCK"
                ? "Do not submit this circuit"
                : "Submission needs review"
            }
          />
          <div className="uc-bars">
            <Bar
              label="Pattern reader (looks for X gates)"
              value={res.summary.pattern_recovery_rate}
              tone="ok"
              note="Share of verified rewrites where it still finds the marked state. 100% on the original circuit."
            />
            <Bar
              label="Exact simulation"
              value={res.summary.exact_recovery_rate}
              tone="bad"
              note={`Finds the marked state with probability ${res.baseline.exact_probability.toFixed(2)}.`}
            />
          </div>
          <div className="uc-stats">
            <Stat
              k="REWRITES VERIFIED"
              v={`${res.summary.verified} / ${res.summary.total}`}
              note="equivalence checked on the logical circuit"
            />
            {sel && (
              <Stat
                k="SELECTED OVERHEAD"
                v={`${signed(sel.overhead.depth)} depth`}
                note={`${signed(sel.overhead.n2q)} two-qubit gates`}
              />
            )}
          </div>
          <p className="uc-reading">
            The pattern reader looks for X gates around the oracle. Local
            rewrites break it for some candidates. The exact reader simulates
            the circuit and still finds the marked state every time, because a
            verified rewrite computes the same function.
          </p>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>CANDIDATE</th>
                  <th>REWRITE</th>
                  <th>VERIFIED</th>
                  <th>DEPTH</th>
                  <th>2Q GATES</th>
                  <th>PATTERN READER</th>
                  <th>EXACT READER</th>
                </tr>
              </thead>
              <tbody>
                {res.candidates.map((c) => (
                  <tr
                    key={c.id}
                    className={c.id === res.selected ? "uc-sel" : ""}
                  >
                    <td className="mono">
                      {c.id}
                      {c.id === res.selected ? " (selected)" : ""}
                    </td>
                    <td>{c.strategy.replaceAll("+", " + ")}</td>
                    <td>
                      {c.verification} · {c.method}
                    </td>
                    <td>{signed(c.overhead.depth)}</td>
                    <td>{signed(c.overhead.n2q)}</td>
                    <td>{c.pattern_recovers ? "recovered" : "missed"}</td>
                    <td>{c.exact_recovers ? "recovered" : "missed"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="uc-receipt">
            <div className="eyebrow">Receipt (no predicate stored)</div>
            <pre>{JSON.stringify(res.receipt, null, 2)}</pre>
          </div>
          <Scope items={res.scope} />
        </div>
      )}
    </section>
  );
}

const PREFS = ["risk_first", "balanced", "return_first"];

function PortfolioCase() {
  const [pref, setPref] = useState("risk_first");
  const [other, setOther] = useState("return_first");
  const [res, setRes] = useState<PortfolioResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    void run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  async function run() {
    setBusy(true);
    setErr(null);
    try {
      setRes(await api.portfolio({ preference: pref, other }));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }
  const d = res?.direct;
  return (
    <section className="panel uc-case">
      <div className="uc-head">
        <h3>Live check: a QAOA portfolio job</h3>
        <p>
          <strong>Protected fact:</strong> the risk and return weighting.{" "}
          <strong>Observer:</strong> whoever sees the circuit and its parameter
          values. The desk picks 4 of 8 assets.
        </p>
      </div>
      <div className="uc-form">
        <label>
          <span className="mono">PRIVATE PREFERENCE</span>
          <select
            value={pref}
            onChange={(e) => setPref(e.target.value)}
            aria-label="Private preference"
          >
            {PREFS.map((p) => (
              <option key={p} value={p}>
                {label(p)}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="mono">COMPARE WITH</span>
          <select
            value={other}
            onChange={(e) => setOther(e.target.value)}
            aria-label="Compare with"
          >
            {PREFS.map((p) => (
              <option key={p} value={p}>
                {label(p)}
              </option>
            ))}
          </select>
        </label>
        <button
          className="uc-run"
          disabled={busy || pref === other}
          onClick={run}
        >
          {busy ? "Checking…" : "Run the check"}
        </button>
      </div>
      {err && (
        <div className="error-banner" role="alert">
          <span>{err}</span>
        </div>
      )}
      {res && d && (
        <div className="uc-result">
          <p className="uc-reading">
            {res.data.note} Source:{" "}
            <a href={res.data.source} target="_blank" rel="noreferrer">
              Qiskit documentation dataset
            </a>
            , checksum{" "}
            <span className="mono">{res.data.sha256.slice(0, 12)}</span>; assets{" "}
            {res.data.assets.join(", ")}.
          </p>
          <div className="uc-two">
            <div className="uc-col">
              <h3>Submit as is</h3>
              <DecisionBanner d={d.decision} title="Do not submit" />
              <div className="uc-bars">
                <Bar
                  label="Structure-only attacker"
                  value={d.structural_attacker_accuracy}
                  chance={d.chance}
                  tone="ok"
                  note="At chance: compiled structure is identical across preferences."
                />
                <Bar
                  label="Parameter reader"
                  value={d.payload_attacker.correct ? 1 : 0}
                  chance={d.chance}
                  tone="bad"
                />
              </div>
              <div className="uc-stats">
                <Stat
                  k="WEIGHTS READ BACK"
                  v={d.payload_attacker.recovered_weights
                    .map((x) => x.toFixed(2))
                    .join(" / ")}
                  note={`true weights: ${d.payload_attacker.true_weights.map((x) => x.toFixed(2)).join(" / ")}`}
                />
                <Stat
                  k="GATE REWRITE"
                  v={d.rewrite.verification}
                  note={`${d.rewrite.strategy}, ${d.rewrite.method}; parameter values unchanged`}
                />
              </div>
            </div>
            <div className="uc-col">
              <h3>Fixed public sweep, choose locally</h3>
              <DecisionBanner
                d={res.sweep.decision}
                title="Submit with caveats"
              />
              <div className="uc-stats">
                <Stat
                  k="JOB HASH, YOUR PREFERENCE"
                  v={res.sweep.job_hash_a}
                  note={label(res.preference)}
                />
                <Stat
                  k="JOB HASH, OTHER PREFERENCE"
                  v={res.sweep.job_hash_b}
                  note={
                    res.sweep.identical
                      ? `${label(res.other)}; identical job`
                      : `${label(res.other)}; jobs differ`
                  }
                />
              </div>
              <div className="uc-bars">
                <Bar
                  label="Preference attacker"
                  value={res.sweep.attacker_accuracy}
                  chance={res.sweep.attacker_accuracy}
                  tone="ok"
                  note="At chance: the job does not depend on the preference."
                />
              </div>
            </div>
          </div>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>PRIVATE PREFERENCE</th>
                  <th>PORTFOLIO PICKED LOCALLY</th>
                  <th>RISK</th>
                  <th>RETURN</th>
                  <th>GAP TO BEST</th>
                  <th>RANDOM PORTFOLIO GAP</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(res.sweep.picks).map(([k, p]) => (
                  <tr key={k}>
                    <td>{label(k)}</td>
                    <td>{p.tickers.join(", ")}</td>
                    <td>{p.risk.toFixed(3)}</td>
                    <td>{p.ret.toFixed(3)}</td>
                    <td>{p.regret_vs_best.toFixed(3)}</td>
                    <td>{p.random_mean_regret.toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Scope items={res.scope} />
        </div>
      )}
    </section>
  );
}

const Sec = ({
  id,
  title,
  children,
}: {
  id: string;
  title: string;
  children: ReactNode;
}) => (
  <section id={id} className="art-sec">
    <h2>{title}</h2>
    {children}
  </section>
);

const Table = ({ head, rows }: { head: string[]; rows: string[][] }) => (
  <div className="table-scroll art-table">
    <table>
      <thead>
        <tr>
          {head.map((h) => (
            <th key={h}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r[0]}>
            {r.map((c, i) => (
              <td key={i}>{c}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

const TOC: [string, string][] = [
  ["summary", "Summary"],
  ["repo", "What the repository contains"],
  ["comms", "Secure communications"],
  ["finance", "Portfolio optimization"],
  ["lead", "Which case leads"],
  ["claims", "What we can claim"],
  ["checklist", "Evaluation checklist"],
  ["narrative", "Three-minute narrative"],
  ["sources", "Sources"],
];

const SOURCES: [string, string, string][] = [
  [
    "IBM Research, QCE 2026 intent study",
    "https://research.ibm.com/publications/algorithmic-intent-leakage-in-transpiled-quantum-circuits-an-initial-reverse-engineering-study",
    "Seven-class structural intent inference from final transpiled circuits. Our scientific starting point; QPF is an independent implementation.",
  ],
  [
    "IBM Grover tutorial",
    "https://quantum.cloud.ibm.com/docs/en/tutorials/grovers-algorithm",
    "Oracle and amplitude amplification construction.",
  ],
  [
    "Qiskit Grover examples",
    "https://qiskit-community.github.io/qiskit-algorithms/tutorials/07_grover_examples.html",
    "Boolean and DIMACS oracle examples.",
  ],
  [
    "Quantum Leak",
    "https://arxiv.org/abs/2401.01521",
    "A cloud timing side channel that can expose a Grover oracle. A different attack from the ones QPF tests.",
  ],
  [
    "NIST PQC FAQ",
    "https://csrc.nist.gov/Projects/Post-Quantum-Cryptography/faqs",
    "Context on practical cryptanalysis limits.",
  ],
  [
    "NIST: practical cost of Grover",
    "https://csrc.nist.gov/csrc/media/Events/2024/fifth-pqc-standardization-conference/documents/papers/on-practical-cost-of-grover.pdf",
    "Why a small demo is not an attack on AES.",
  ],
  [
    "IBM multi-objective portfolio tutorial",
    "https://quantum.cloud.ibm.com/docs/en/tutorials/quantum-approximate-multi-objective-optimization",
    "Working QAOA recipe with a public market-data snapshot and an honest random comparator.",
  ],
  [
    "Market data CSV",
    "https://raw.githubusercontent.com/Qiskit/documentation/main/datasets/tutorials/qmoo/market_data.csv",
    "The 40-asset snapshot; we use 8 assets.",
  ],
  [
    "Qiskit primitive input and output",
    "https://quantum.cloud.ibm.com/docs/en/guides/primitive-input-output",
    "Parameter values are part of the submitted workload.",
  ],
  [
    "IBM and Vanguard portfolio study",
    "https://www.ibm.com/quantum/blog/vanguard-portfolio-optimization",
    "Industry interest in quantum portfolio work; not a production system or a leak.",
  ],
  [
    "Enigma",
    "https://arxiv.org/abs/2311.13546",
    "Prior art: QAOA problem-level transformations with local recovery. Not our invention.",
  ],
  ["OPAQUE", "https://arxiv.org/abs/2502.16605", "Circuit obfuscation design."],
  ["SPYCE", "https://arxiv.org/abs/2307.16799", "Circuit obfuscation design."],
  [
    "MQT QCEC",
    "https://mqt.readthedocs.io/projects/qcec/en/stable/",
    "Equivalence checking. A correctness gate, not a privacy proof.",
  ],
  [
    "Q-Hack India",
    "https://www.quantumweek.tech/hackathon",
    "Track, timing and scoring.",
  ],
];

export function UseCases() {
  return (
    <div className="art">
      <aside className="art-toc" aria-label="Contents">
        <div className="eyebrow">Contents</div>
        <ul>
          {TOC.map(([id, t]) => (
            <li key={id}>
              <a href={`#${id}`}>{t}</a>
            </li>
          ))}
        </ul>
      </aside>
      <article className="art-body">
        <header className="art-hero">
          <div className="eyebrow">Quantum Privacy Firewall</div>
          <h1>Checking what a quantum job gives away before it is submitted</h1>
          <p>
            Two use cases: a confidential cryptanalysis test and a confidential
            portfolio optimization. Both run on the same engine. Both are small
            demonstrations, and each page section says what it does and does not
            show.
          </p>
        </header>

        <Sec id="summary" title="Summary">
          <p>
            QPF is a testbed for intent leakage in quantum jobs. It is not a
            cryptographic privacy system. The useful product idea is a gate
            before submission: inspect a Qiskit job, show what a defined
            observer could infer, try rewrites that are checked for equivalence,
            retest an attacker, and then release or block the job with a
            receipt.
          </p>
          <p>
            Passing an equivalence check does not hide anything. A verified
            rewrite computes the same function, so if the function is the
            secret, the right answer is to block. Both live checks below end
            that way on at least one path.
          </p>
        </Sec>

        <Sec id="repo" title="What the repository contains">
          <Table
            head={["Layer", "Implementation", "Evidence and limits"]}
            rows={[
              [
                "Intent families",
                "47 circuit generators in seven classes (src/qpf/paper_circuits.py)",
                "Generated circuits. Not a realistic oracle dataset and not portfolio labels.",
              ],
              [
                "Attacker",
                "Ten structural features, Random Forest, grouped splits",
                "282 sources, 2,256 compiled circuits. Accuracy 0.956; metadata-only 0.938; held-out generator 0.687. The high metadata score is a confound.",
              ],
              [
                "Defense",
                "Local decomposition, legal reordering, layout and transpile-seed changes",
                "No keyed masking, oracle hiding or parameter privacy.",
              ],
              [
                "Verification",
                "PASS, FAIL or UNKNOWN using identical circuit, DAG, operator and MQT QCEC checks",
                "All 1,974 candidate circuits passed logical verification. This says nothing about secrecy or noisy utility.",
              ],
              [
                "Adaptive evaluation",
                "Static, adaptive and normalization-aware attackers with paired confidence intervals",
                "At a 20% budget, macro-F1 fell from 0.916 to 0.878 (paired change 0.038, 95% interval +0.017 to +0.059). The remaining 0.878 is high.",
              ],
              [
                "Demo and API",
                "Terminal example, FastAPI backend, this frontend",
                "The workbench takes preset families of 4 to 8 qubits. The checks on this page are new and cover one toy case each.",
              ],
            ]}
          />
        </Sec>

        <Sec
          id="comms"
          title="Secure communications: a confidential cryptanalysis job"
        >
          <h3>The story</h3>
          <p>
            A security team tests a toy authentication predicate, a
            reduced-round cipher or a key-search condition with a Grover oracle,
            and sends the circuit to a remote quantum service. The oracle can
            reveal the team&rsquo;s test condition or research direction to
            whoever holds the job file. QPF sits on the developer side of that
            handoff. It does not protect traffic in transit or a QKD key, and it
            does not address another tenant reading your job.
          </p>
          <h3>What is exposed</h3>
          <p>
            A Grover circuit alternates an oracle for a condition f(x) with a
            diffusion step. Hiding names does not hide gate structure, and at
            small sizes it does not hide the function either. Exact equivalence
            keeps the same oracle, so an observer who can run or analyze the
            full circuit can often recover the marked states.
          </p>
          <p>
            Three different secrets should not be mixed up: the algorithm family
            (Grover versus QFT), the oracle type (parity versus CNF) and the
            specific marked strings. The existing QPF attacker only tests the
            first. For this use case the third matters most.
          </p>
          <GroverCase />
          <h3>What this result means</h3>
          <p>
            Local rewrites can break a simple structural reader, but an exact
            simulation still finds the marked state in every verified candidate,
            so QPF blocks the job. A four-bit state has only 16 possibilities
            and is used to show the pipeline, not as a real secret.
          </p>
          <h3>Claim we can defend</h3>
          <p>
            &ldquo;Before a quantum cryptanalysis circuit leaves the lab, QPF
            tests whether the final job reveals its purpose or oracle, verifies
            any rewrite, and blocks it when the sensitive predicate remains
            recoverable.&rdquo; We do not claim that QPF prevents eavesdropping
            or makes Grover or AES secure.
          </p>
        </Sec>

        <Sec
          id="finance"
          title="Portfolio optimization: a confidential QAOA job"
        >
          <h3>The story</h3>
          <p>
            An investment research desk evaluates candidate portfolios with a
            quantum-classical workflow. The market data is public. The
            desk&rsquo;s risk, return and diversification priorities are
            private. A cloud observer sees the circuit and the numeric parameter
            values that go with it. IBM&rsquo;s multi-objective QAOA portfolio
            tutorial is the runnable anchor, and the IBM and Vanguard work shows
            industry interest, not production use or a leak.
          </p>
          <h3>What is exposed</h3>
          <Table
            head={["Observer", "What can leak", "QPF status"]}
            rows={[
              [
                "Structure only",
                "That this is a QAOA job; asset count; topology; resource pattern",
                "The family benchmark partly covers this, not preference privacy.",
              ],
              [
                "Full job payload",
                "The weight values, and market-model coefficients in the Hamiltonian",
                "Not covered by the family benchmark. Tested by the check below.",
              ],
              [
                "Source and logs",
                "Tickers, labels, comments, raw CSV",
                "Outside the classifier. Needs local handling and access control.",
              ],
            ]}
          />
          <p>
            If the same parameterized circuit is submitted for two preferences
            and only the bound values differ, a structure-only classifier is at
            chance. That is the correct result. A reader of the parameter values
            recovers the preference exactly. Gate rewrites do not hide a value
            that is written in the job.
          </p>
          <PortfolioCase />
          <h3>What this result means</h3>
          <p>
            Submitted as is, the job is blocked. Submitting a fixed public sweep
            of weight choices and picking the result locally makes the job
            identical for every analyst, so it carries no information about the
            preference. It still shows the asset universe and the market-data
            Hamiltonian, and it costs more runs. This adapts the
            tutorial&rsquo;s Pareto workflow and is not new cryptography. Enigma
            is prior art for problem-level transformations; QPF&rsquo;s
            contribution is the combination of attacker tests, equivalence
            checks, cost and a release policy.
          </p>
        </Sec>

        <Sec id="lead" title="Which case leads">
          <Table
            head={["", "Grover cryptanalysis", "Portfolio QAOA"]}
            rows={[
              [
                "Fit to the security track",
                "Direct and easy to explain",
                "Indirect: protecting proprietary research",
              ],
              [
                "Fit to existing code",
                "Amplitude-amplification family and the verification pipeline",
                "Variational family, but no portfolio payload attacker before this work",
              ],
              [
                "Hard security problem",
                "A full equivalent oracle often reveals f, so the gate must block",
                "Numeric weights can reveal the preference directly, so the gate must block",
              ],
              [
                "Role",
                "Lead story",
                "Second vertical showing the gate generalizes",
              ],
            ]}
          />
          <p>
            One experiment does not prove both. The shared piece is the engine:
            two different protected facts, two observation schemas and two
            product decisions.
          </p>
        </Sec>

        <Sec id="claims" title="What we can and cannot claim">
          <Table
            head={["Statement", "Status"]}
            rows={[
              [
                "The compiled circuit reveals coarse algorithm family in QPF's controlled benchmark.",
                "Measured in this repository, with the split and metadata caveats.",
              ],
              [
                "At a 20% budget QPF lowers adaptive family-attack macro-F1 from 0.916 to 0.878.",
                "Measured on the saved synthetic benchmark. Small reduction, high remaining leakage.",
              ],
              [
                "QPF hides a Grover oracle's marked state.",
                "Measured on a four-bit toy: false. An exact simulation recovers it after every verified rewrite.",
              ],
              [
                "QPF hides a portfolio weight vector from the job recipient.",
                "Measured on an eight-asset toy: false when the parameter values are visible.",
              ],
              [
                "A fixed public sweep removes preference-specific job variation.",
                "Measured on the toy: the job hash is identical for two preferences. Holds under the fixed-job assumption only.",
              ],
              [
                "Quantum advantage, protection of AES or BB84, or service to a real bank.",
                "Unsupported. Never claim.",
              ],
            ]}
          />
        </Sec>

        <Sec id="checklist" title="Evaluation checklist">
          <ul>
            <li>
              <strong>Input:</strong> local Qiskit objects first. No execution
              of uploaded Python.
            </li>
            <li>
              <strong>Target:</strong> pinned Qiskit version, fake backend,
              optimization level and seed.
            </li>
            <li>
              <strong>Correctness:</strong> original and rewritten unitary,
              measurements preserved. UNKNOWN must block.
            </li>
            <li>
              <strong>Privacy:</strong> name the secret and the observer for
              every result. Use an exact attacker, a structural attacker, a
              payload attacker, adaptive retraining, grouped splits, controls
              and intervals.
            </li>
            <li>
              <strong>Utility and cost:</strong> same shots, depth, two-qubit
              count, run time, success or portfolio quality against a random
              baseline. A noise model is simulation, not hardware.
            </li>
            <li>
              <strong>Receipt:</strong> hashes, target, model version, observer,
              secret tested, attacker score, verification method, budget,
              decision. No predicate or weights in logs.
            </li>
          </ul>
        </Sec>

        <Sec id="narrative" title="Three-minute narrative">
          <ol>
            <li>
              Most quantum security work protects a message. QPF checks the
              quantum job itself before submission. Show the Grover case.
            </li>
            <li>
              Reveal the two attack results and the verified rewrites. The
              marked state is still recoverable, so QPF blocks.
            </li>
            <li>
              Show the portfolio case. Changing a private preference leaves the
              structure unchanged but changes the numbers. QPF tells the two
              views apart and offers a fixed public sweep.
            </li>
            <li>
              Close with the saved 24 and 48 qubit numbers and the claim:
              measured leakage, verified low-overhead mitigation where it works,
              and a refusal where it does not.
            </li>
          </ol>
        </Sec>

        <Sec id="sources" title="Sources">
          <ul className="art-sources">
            {SOURCES.map(([t, u, n]) => (
              <li key={u}>
                <a href={u} target="_blank" rel="noreferrer">
                  {t}
                </a>
                <span>{n}</span>
              </li>
            ))}
          </ul>
          <p className="uc-reading">
            No cited source documents a present-day breach caused by algorithm
            family leakage in a deployed cryptanalysis or portfolio workflow.
            This is an emerging pre-submission risk, not an incident response
            product.
          </p>
        </Sec>
      </article>
    </div>
  );
}
