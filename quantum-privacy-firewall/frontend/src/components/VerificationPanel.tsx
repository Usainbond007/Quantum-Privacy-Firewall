import type { Candidate, DemoResult, Evidence } from "../types/demo";

export function VerdictBadge({ status }: { status: Evidence["status"] }) {
  return <span className={`verdict ${status.toLowerCase()}`}>{status}</span>;
}
export function VerificationPanel({
  result,
  inspecting,
}: {
  result: DemoResult;
  inspecting: Candidate | null;
}) {
  const candidate = inspecting || result.selected || result.baseline;
  return (
    <section className="panel verification">
      <div className="section-title">
        <span className="step-number">03</span>
        <h2>Verification evidence</h2>
        <span className="mono hint">{candidate.id}</span>
      </div>
      <div className="evidence-grid">
        {[
          {
            title: "Logical equivalence",
            evidence: candidate.logical_verification,
          },
          {
            title: "Compiled equivalence",
            evidence: candidate.compiled_verification,
          },
        ].map(({ title, evidence }) => (
          <article key={title}>
            <div className="flex items-center justify-between gap-2">
              <h3>{title}</h3>
              <VerdictBadge status={evidence.status} />
            </div>
            <p className="mono method">
              {evidence.method.replaceAll("_", " ")}
            </p>
            <p>{evidence.note || "This check has not run."}</p>
          </article>
        ))}
      </div>
      <div className="scoring-note">
        <span className="eyebrow">
          Selection method · {result.scoring_method.replaceAll("_", " ")}
        </span>
        <p>{result.scoring_note}</p>
      </div>
    </section>
  );
}
