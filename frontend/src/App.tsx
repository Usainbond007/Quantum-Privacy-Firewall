import { useEffect, useState } from "react";
import LabApp from "./LabApp";
import { CasePage, ResearchPage } from "./components/ResearchDesk";
import { api } from "./lib/api";

type Page = "cryptanalysis" | "portfolio" | "lab" | "research";
const pages: [Page, string, string][] = [
  ["cryptanalysis", "Confidential", "Cryptanalysis"],
  ["portfolio", "Portfolio", "Optimization"],
  ["lab", "Circuit Lab", ""],
  ["research", "Research & evidence", ""],
];
const fromHash = (): Page => {
  const v = location.hash.slice(1);
  return pages.some(([p]) => p === v) ? (v as Page) : "cryptanalysis";
};
export default function App() {
  const [page, setPage] = useState<Page>(fromHash);
  const [labVisited, setLabVisited] = useState(page === "lab");
  const [connected, setConnected] = useState<boolean | null>(null);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const f = () => setPage(fromHash());
    window.addEventListener("hashchange", f);
    return () => window.removeEventListener("hashchange", f);
  }, []);
  useEffect(() => {
    if (page === "lab") setLabVisited(true);
    window.scrollTo(0, 0);
  }, [page]);
  useEffect(() => {
    const c = new AbortController();
    setConnected(null);
    api
      .options(c.signal)
      .then(() => setConnected(true))
      .catch(() => {
        if (!c.signal.aborted) setConnected(false);
      });
    return () => c.abort();
  }, [retry]);
  return (
    <div className="desk">
      <aside className="desk-sidebar">
        <a className="desk-brand" href="#cryptanalysis">
          <strong>
            QPF<span>.</span>
          </strong>
          <span>Quantum Privacy Firewall</span>
        </a>
        <div className="nav-caption">RESEARCH WORKSPACE</div>
        <nav aria-label="Main navigation">
          {pages.map(([id, a, b], i) => (
            <a
              key={id}
              href={`#${id}`}
              aria-current={page === id ? "page" : undefined}
            >
              <span className="nav-number">
                {String(i + 1).padStart(2, "0")}
              </span>
              <span>
                {a}
                {b && (
                  <>
                    <br />
                    {b}
                  </>
                )}
              </span>
            </a>
          ))}
        </nav>
        <div className="sidebar-note">
          <span className="eyebrow">THE PRINCIPLE</span>
          <p>
            Verify the computation.
            <br />
            Test the disclosure.
            <br />
            Explain the decision.
          </p>
          <small>
            Independent research prototype
            <br />
            Q-Hack India · 2026
          </small>
        </div>
      </aside>
      <div className="desk-main">
        <header className="desk-top">
          <span>
            Research desk <span className="header-divider">/</span>{" "}
            <strong>
              {page === "lab"
                ? "Circuit lab"
                : page === "research"
                  ? "Evidence & methods"
                  : "Use cases"}
            </strong>
          </span>
          <div className="connection">
            <span className={`connection-dot ${connected ? "online" : ""}`} />
            {connected === null
              ? "Connecting to engine"
              : connected
                ? "Local API connected"
                : "API unavailable"}
            {connected === false && (
              <button onClick={() => setRetry((r) => r + 1)}>Retry</button>
            )}
            <span className="small-tag">Simulation only</span>
          </div>
        </header>
        <main className="desk-content">
          <div hidden={page !== "cryptanalysis"}>
            <CasePage kind="cryptanalysis" />
          </div>
          <div hidden={page !== "portfolio"}>
            <CasePage kind="portfolio" />
          </div>
          {labVisited && (
            <div hidden={page !== "lab"} className="legacy-lab">
              <LabApp />
            </div>
          )}
          {page === "research" && <ResearchPage />}
        </main>
        <footer className="desk-footer">
          <span>QPF · Observe → Rewrite → Verify → Assess</span>
          <span>Local assessment only. No cloud submission.</span>
          <a href="/docs" target="_blank" rel="noreferrer">
            API documentation ↗
          </a>
        </footer>
      </div>
    </div>
  );
}
