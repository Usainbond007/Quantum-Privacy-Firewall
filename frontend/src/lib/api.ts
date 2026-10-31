import type {
  Circuit,
  CircuitRequest,
  Options,
  RunRequest,
  RunState,
  ResearchBenchmarks,
} from "../types/demo";
import type { GroverResult, PortfolioResult } from "../types/usecases";

async function request<T>(
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method: body ? "POST" : "GET",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
    signal,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(
      typeof payload?.detail === "string"
        ? payload.detail
        : `Request failed (${response.status})`,
    );
  }
  return response.json() as Promise<T>;
}
export const api = {
  benchmarks: (signal?: AbortSignal) =>
    request<ResearchBenchmarks>("/benchmarks", undefined, signal),
  options: (signal?: AbortSignal) =>
    request<Options>("/options", undefined, signal),
  preview: (body: CircuitRequest, signal?: AbortSignal) =>
    request<Circuit>("/circuits/preview", body, signal),
  start: (body: RunRequest, signal?: AbortSignal) =>
    request<{ id: string; status: string }>("/runs", body, signal),
  run: (id: string, signal?: AbortSignal) =>
    request<RunState>(`/runs/${id}`, undefined, signal),
  grover: (body: { marked: string; budget: number }, signal?: AbortSignal) =>
    request<GroverResult>("/usecases/grover", body, signal),
  portfolio: (
    body: { preference: string; other: string },
    signal?: AbortSignal,
  ) => request<PortfolioResult>("/usecases/portfolio", body, signal),
  exportUrl: (id: string, kind: "qasm" | "metrics") =>
    `/api/runs/${id}/exports/${kind}`,
};
