import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { UseCases } from "../components/UseCases";
import { api } from "../lib/api";
import type { GroverResult } from "../types/usecases";

const grover: GroverResult = {
  elapsed_seconds: 1,
  marked: "1010",
  budget: 0.2,
  observer: "holder of the submitted circuit file",
  baseline: {
    circuit: {
      num_qubits: 4,
      logical_width: 4,
      qubits: [0, 1, 2, 3],
      gates: [],
      depth: 0,
      size: 0,
      global_phase: 0,
      layout: null,
    },
    probabilities: [],
    compiled_verification: { status: "PASS", method: "test", note: "fixture" },
    metrics: { depth: 40, n2q: 20, size: 90 },
    pattern_guess: "1010",
    exact_guess: "1010",
    exact_probability: 0.96,
    circuit_hash: "abc",
  },
  candidates: [
    {
      id: "c01",
      strategy: "decomp",
      seed: 1,
      verification: "PASS",
      method: "operator_equiv",
      metrics: { depth: 40, n2q: 20, size: 90 },
      overhead: { depth: 0.01, n2q: 0 },
      within_budget: true,
      circuit: {
        num_qubits: 4,
        logical_width: 4,
        qubits: [0, 1, 2, 3],
        gates: [],
        depth: 0,
        size: 0,
        global_phase: 0,
        layout: null,
      },
      total_variation: 0,
      compiled_verification: {
        status: "PASS",
        method: "test",
        note: "fixture",
      },
      pattern_guess: "1111",
      pattern_recovers: false,
      exact_guess: "1010",
      exact_probability: 0.96,
      exact_recovers: true,
      circuit_hash: "def",
    },
  ],
  selected: "c01",
  summary: {
    verified: 1,
    total: 1,
    pattern_recovery_rate: 0,
    exact_recovery_rate: 1,
  },
  decision: { status: "BLOCK", reasons: ["Exact simulation recovers it."] },
  receipt: { decision: "BLOCK", contains_predicate: false },
  scope: ["Four-bit marked state is not a real secret."],
};

const portfolioStub = new Promise<never>(() => {});

beforeEach(() => {
  vi.spyOn(api, "portfolio").mockReturnValue(portfolioStub);
});

afterEach(() => vi.restoreAllMocks());

describe("use cases", () => {
  it("runs the Grover check and shows a block with its scope notes", async () => {
    const spy = vi.spyOn(api, "grover").mockResolvedValue(grover);
    render(<UseCases />);
    await waitFor(() =>
      expect(spy).toHaveBeenCalledWith({ marked: "1010", budget: 0.2 }),
    );
    expect(await screen.findByText("Do not submit this circuit")).toBeTruthy();
    expect(screen.getByText("BLOCK")).toBeTruthy();
    expect(screen.getByText(/not a real secret/)).toBeTruthy();
  });

  it("disables the check for an invalid marked state", async () => {
    vi.spyOn(api, "grover").mockResolvedValue(grover);
    render(<UseCases />);
    const input = screen.getByLabelText("Marked state");
    await userEvent.clear(input);
    await userEvent.type(input, "10");
    expect(
      (
        screen.getAllByRole("button", {
          name: "Run the check",
        })[0] as HTMLButtonElement
      ).disabled,
    ).toBe(true);
  });

  it("surfaces request errors", async () => {
    vi.spyOn(api, "grover").mockRejectedValue(new Error("boom"));
    render(<UseCases />);
    expect(await screen.findByRole("alert")).toBeTruthy();
  });
});
