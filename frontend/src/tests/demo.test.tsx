import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../LabApp";
import { CircuitViewer } from "../components/CircuitViewer";
import { CircuitComparison } from "../components/CircuitComparison";
import { api } from "../lib/api";
import recordedBenchmarks from "./fixtures/benchmarks.json";
import type {
  Candidate,
  Circuit,
  DemoResult,
  Options,
  RunState,
  ResearchBenchmarks,
} from "../types/demo";

const circuit: Circuit = {
  num_qubits: 4,
  logical_width: 4,
  qubits: [0, 1, 2, 3],
  gates: [
    { id: 0, name: "rz", qubits: [0], clbits: [], params: [0.5], layer: 1 },
    { id: 1, name: "cx", qubits: [0, 3], clbits: [], params: [], layer: 2 },
  ],
  depth: 2,
  size: 2,
  global_phase: 0,
  layout: null,
};
const evidence = {
  status: "PASS" as const,
  method: "exact_layout_isometry",
  note: "All inputs verified",
};
const baseline: Candidate = {
  id: "baseline",
  strategy: "baseline",
  seed: 11,
  logical_verification: evidence,
  compiled_verification: evidence,
  metrics: { depth: 2, n2q: 1, active: 2, size: 2 },
  features: {},
  overheads: { depth: 0, n2q: 0, active: 0 },
  changed: false,
  eligible: true,
  reason: "",
  score: 0,
  circuit,
};
const selected: Candidate = {
  ...baseline,
  id: "candidate-01",
  strategy: "layout",
  changed: true,
  score: 0.12,
  circuit: {
    ...circuit,
    qubits: [2, 4, 6, 8],
    num_qubits: 12,
    layout: { initial: [2, 4, 6, 8], final: [8, 4, 6, 2] },
    gates: [
      { id: 0, name: "rz", qubits: [2], clbits: [], params: [0.5], layer: 1 },
      { id: 1, name: "cx", qubits: [2, 8], clbits: [], params: [], layer: 2 },
    ],
  },
};
const options: Options = {
  families: ["graph_ghz", "qft"],
  backends: ["FakeNighthawk"],
  strategies: ["layout", "decomp+layout", "decomp+reorder"],
  widths: [4, 5],
  optimization_levels: [0, 1, 2, 3],
  max_candidates: 24,
  max_active_verification_qubits: 10,
  surrogate_configured: false,
};
const result: DemoResult = {
  outcome: "SELECTED",
  message: "Verified changed candidate selected",
  request: {
    family: "graph_ghz",
    width: 4,
    seed: 21,
    backend: "FakeNighthawk",
    optimization_level: 2,
    transpile_seed: 11,
    candidates: 6,
    budget: 0.2,
    strategies: ["layout", "decomp+layout", "decomp+reorder"],
  },
  input: circuit,
  baseline,
  selected,
  alternatives: [selected],
  scoring_method: "structural_feature_distance",
  scoring_note: "A descriptive score, not a privacy estimate.",
  elapsed_seconds: 0.3,
};
const completed: RunState = {
  id: "test-run",
  status: "completed",
  progress: 1,
  stage: "Complete",
  created_at: "",
  updated_at: "",
  result,
  error: null,
};

afterEach(() => vi.restoreAllMocks());
beforeEach(() => {
  vi.spyOn(api, "benchmarks").mockResolvedValue(
    recordedBenchmarks as ResearchBenchmarks,
  );
});

describe("circuit interactions", () => {
  it("zooms, inspects gate parameters by keyboard, and retains physical labels", async () => {
    const user = userEvent.setup();
    render(
      <CircuitViewer circuit={selected.circuit!} title="Physical circuit" />,
    );
    expect(screen.getByText("p8 |0⟩")).toBeTruthy();
    await user.click(
      screen.getByRole("button", { name: "Zoom in Physical circuit" }),
    );
    expect(screen.getByRole("button", { name: "120%" })).toBeTruthy();
    const gate = screen.getByRole("button", { name: "RZ on 2" });
    gate.focus();
    await user.keyboard("{Enter}");
    expect(screen.getByText(/params \[0.50000\]/)).toBeTruthy();
    await user.click(screen.getByText(/Logical → physical layout/));
    expect(screen.getByText("q0: p2 → p8")).toBeTruthy();
  });

  it("shows a fresh preview after a completed run and exposes the no-change outcome", async () => {
    const { rerender } = render(
      <CircuitComparison preview={null} result={result} />,
    );
    expect(screen.getByText("Selected compilation")).toBeTruthy();
    rerender(<CircuitComparison preview={circuit} result={result} />);
    await waitFor(() =>
      expect(screen.getByText("Input circuit preview")).toBeTruthy(),
    );
    rerender(
      <CircuitComparison
        preview={null}
        result={{
          ...result,
          selected: null,
          outcome: "NO_CHANGED_CANDIDATE",
          message: "No changed candidate within budget",
        }}
      />,
    );
    await waitFor(() =>
      expect(
        screen.getByText("No changed candidate within budget"),
      ).toBeTruthy(),
    );
  });
});

describe("full frontend workflow", () => {
  it("updates the top accuracy card for every saved attacker and budget and syncs both selectors", async () => {
    const user = userEvent.setup();
    vi.spyOn(api, "options").mockResolvedValue(options);
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Circuit workbench" }));
    const overview = screen.getByRole("region", {
      name: "Before and after firewall accuracy",
    });
    await waitFor(() =>
      expect(within(overview).getByText("93.75%")).toBeTruthy(),
    );
    for (const budget of recordedBenchmarks.budgets) {
      await user.selectOptions(
        screen.getByLabelText("Saved research budget"),
        String(budget.budget),
      );
      for (const [attacker, metrics] of Object.entries(budget.attackers)) {
        await user.selectOptions(
          screen.getByLabelText("Saved attacker test"),
          attacker,
        );
        const after = within(overview).getByText(
          "After firewall accuracy",
        ).parentElement!;
        expect(
          within(after).getByText(`${(metrics.accuracy * 100).toFixed(2)}%`),
        ).toBeTruthy();
        expect(
          (screen.getByLabelText("Protected attacker") as HTMLSelectElement)
            .value,
        ).toBe(attacker);
      }
    }
    await user.selectOptions(
      screen.getByLabelText("Protected attacker"),
      "adaptive_logreg",
    );
    expect(
      (screen.getByLabelText("Saved attacker test") as HTMLSelectElement).value,
    ).toBe("adaptive_logreg");
    expect(
      within(overview).getByText("Before firewall accuracy (RF reference)"),
    ).toBeTruthy();
    expect(
      within(overview).getByText(
        /A separate before-firewall score for this attacker is not recorded/,
      ),
    ).toBeTruthy();
  });
  it("shows before/after accuracy below the workbench and keeps research budgets in sync", async () => {
    const user = userEvent.setup();
    vi.spyOn(api, "options").mockResolvedValue(options);
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Circuit workbench" }));
    const overview = await screen.findByRole("region", {
      name: "Before and after firewall accuracy",
    });
    await waitFor(() =>
      expect(within(overview).getByText("93.75%")).toBeTruthy(),
    );
    expect(within(overview).getByText("100.00%")).toBeTruthy();
    expect(within(overview).getByText("Before firewall accuracy")).toBeTruthy();
    expect(within(overview).getByText("After firewall accuracy")).toBeTruthy();
    expect(
      screen.getByRole("heading", { level: 1 }).compareDocumentPosition(
        overview,
      ) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    await user.selectOptions(
      screen.getByLabelText("Saved research budget"),
      "0.5",
    );
    expect(within(overview).getByText("62.50%")).toBeTruthy();
    expect(
      (screen.getByLabelText("Research budget") as HTMLSelectElement).value,
    ).toBe("0.5");
    expect(
      screen
        .getByRole("link", { name: "Confusion matrices & full metrics ↓" })
        .getAttribute("href"),
    ).toBe("#attacker-accuracy");
  });
  it("loads options, previews, submits current settings, polls, and shows evidence and exports", async () => {
    const user = userEvent.setup();
    vi.spyOn(api, "options").mockResolvedValue(options);
    vi.spyOn(api, "preview").mockResolvedValue(circuit);
    const start = vi
      .spyOn(api, "start")
      .mockResolvedValue({ id: "test-run", status: "queued" });
    vi.spyOn(api, "run").mockResolvedValue(completed);
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Circuit workbench" }));
    await user.click(
      await screen.findByRole("button", { name: "Preview input circuit" }),
    );
    expect(await screen.findByText("Input circuit preview")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Overhead budget"), {
      target: { value: "35" },
    });
    await user.click(screen.getByRole("button", { name: /Run firewall/ }));
    expect(
      await screen.findByText("Verified changed candidate selected"),
    ).toBeTruthy();
    expect(start.mock.calls[0][0].budget).toBe(0.35);
    expect(
      screen.getByRole("link", { name: "↓ QASM" }).getAttribute("href"),
    ).toBe("/api/runs/test-run/exports/qasm");
    expect(screen.getByText("Candidate search")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: /candidate-01/ }));
    expect(screen.getByText("Inspecting candidate-01")).toBeTruthy();
    expect(screen.getAllByText("PASS").length).toBeGreaterThan(3);
  });

  it("switches the circuit family from a demo preset", async () => {
    const user = userEvent.setup();
    vi.spyOn(api, "options").mockResolvedValue(options);
    render(<App />);
    await user.click(await screen.findByRole("button", { name: "QFT" }));
    expect((screen.getByLabelText("Algorithm family") as HTMLSelectElement).value).toBe("qft");
  });

  it("displays actionable submission errors", async () => {
    const user = userEvent.setup();
    vi.spyOn(api, "options").mockResolvedValue(options);
    vi.spyOn(api, "start").mockRejectedValue(new Error("Demo queue is full"));
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Circuit workbench" }));
    await user.click(
      await screen.findByRole("button", { name: /Run firewall/ }),
    );
    expect(await screen.findByRole("alert")).toHaveProperty(
      "textContent",
      "Demo queue is full",
    );
    expect(
      (
        screen.getByRole("button", {
          name: /Run firewall/,
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(false);
  });
});
