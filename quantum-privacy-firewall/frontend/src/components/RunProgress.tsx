import type { RunState } from "../types/demo";

export function RunProgress({ run }: { run: RunState | null }) {
  if (!run) return null;
  return (
    <div className="panel run-progress" role="status" aria-live="polite">
      <div className="flex justify-between gap-3">
        <span>
          <span
            className={
              run.status === "running" || run.status === "queued"
                ? "status-dot pulse"
                : "status-dot"
            }
          />
          {run.stage}
        </span>
        <span className="mono">{Math.round(run.progress * 100)}%</span>
      </div>
      <div
        className="progress-track"
        role="progressbar"
        aria-valuenow={Math.round(run.progress * 100)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Firewall run progress"
      >
        <div style={{ width: `${run.progress * 100}%` }} />
      </div>
      <p className="mono">
        Run {run.id}{" "}
        {run.result && `· ${run.result.elapsed_seconds.toFixed(2)}s`}
      </p>
    </div>
  );
}
