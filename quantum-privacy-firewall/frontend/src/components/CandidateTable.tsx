import type { Candidate, DemoResult } from "../types/demo";
import { VerdictBadge } from "./VerificationPanel";

export function CandidateTable({
  result,
  inspecting,
  onInspect,
}: {
  result: DemoResult;
  inspecting: Candidate | null;
  onInspect: (candidate: Candidate) => void;
}) {
  return (
    <section className="panel candidates">
      <div className="section-title justify-between">
        <div className="flex items-center gap-3">
          <span className="step-number">04</span>
          <h2>Candidate search</h2>
        </div>
        <span className="mono hint">
          {result.alternatives.filter((c) => c.eligible).length} /{" "}
          {result.alternatives.length} eligible
        </span>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Candidate / strategy</th>
              <th>Logical</th>
              <th>Compiled</th>
              <th>Max overhead</th>
              <th>
                {result.scoring_method === "frozen_surrogate_confidence"
                  ? "Confidence ↓"
                  : "Distance ↑"}
              </th>
              <th>Decision</th>
            </tr>
          </thead>
          <tbody>
            {[result.baseline, ...result.alternatives].map((c) => (
              <tr
                key={c.id}
                className={
                  inspecting?.id === c.id
                    ? "inspecting"
                    : result.selected?.id === c.id
                      ? "selected-row"
                      : ""
                }
              >
                <td>
                  <button
                    className="candidate-name"
                    onClick={() => onInspect(c)}
                  >
                    {c.id}
                    <span>{c.strategy.replaceAll("+", " + ")}</span>
                  </button>
                </td>
                <td>
                  <VerdictBadge status={c.logical_verification.status} />
                </td>
                <td>
                  <VerdictBadge status={c.compiled_verification.status} />
                </td>
                <td className="mono">
                  {c.overheads
                    ? `${(Math.max(0, ...Object.values(c.overheads)) * 100).toFixed(1)}%`
                    : "—"}
                </td>
                <td className="mono">{c.score?.toFixed(4) ?? "—"}</td>
                <td>
                  <span
                    className={
                      result.selected?.id === c.id ? "accent" : "decision"
                    }
                  >
                    {c.id === "baseline"
                      ? "Reference"
                      : result.selected?.id === c.id
                        ? "Selected ✓"
                        : c.reason || "Eligible alternative"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
