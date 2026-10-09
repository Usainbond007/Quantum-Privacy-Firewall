import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import type { RunRequest, RunState } from "../types/demo";

export function useRun() {
  const [run, setRun] = useState<RunState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [retry, setRetry] = useState(0);
  const submitController = useRef<AbortController | null>(null);
  useEffect(() => () => submitController.current?.abort(), []);
  const submit = useCallback(async (body: RunRequest) => {
    submitController.current?.abort();
    const controller = new AbortController();
    submitController.current = controller;
    setError(null);
    setSubmitting(true);
    setRun(null);
    try {
      const created = await api.start(body, controller.signal);
      setRun({
        ...created,
        status: "queued",
        progress: 0,
        stage: "Queued",
        result: null,
        error: null,
        created_at: "",
        updated_at: "",
      });
    } catch (err) {
      if (!controller.signal.aborted)
        setError(err instanceof Error ? err.message : "Could not start run");
    } finally {
      if (!controller.signal.aborted) setSubmitting(false);
    }
  }, []);
  const id = run?.id;
  const terminal = run?.status === "completed" || run?.status === "failed";
  useEffect(() => {
    if (!id || terminal) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    let failures = 0;
    async function poll() {
      try {
        const state = await api.run(id!, controller.signal);
        if (controller.signal.aborted) return;
        failures = 0;
        setError(null);
        setRun(state);
        if (state.status === "failed") setError(state.error || "Run failed");
        if (state.status === "completed" || state.status === "failed") return;
      } catch (err) {
        if (controller.signal.aborted) return;
        failures++;
        setError(
          `${err instanceof Error ? err.message : "Polling failed"}${failures < 5 ? " · Reconnecting…" : " · Polling paused. Retry to reconnect."}`,
        );
        if (failures >= 5) return;
      }
      timer = setTimeout(poll, Math.min(800 * 2 ** failures, 8000));
    }
    void poll();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [id, terminal, retry]);
  return {
    run,
    error,
    submit,
    retry: () => setRetry((x) => x + 1),
    busy: submitting || (!!run && !terminal),
  };
}
