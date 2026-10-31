import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { AccuracyPanel } from "../components/AccuracyPanel";
import type { ResearchBenchmarks } from "../types/demo";
import recorded from "./fixtures/benchmarks.json";

const benchmarks = recorded as ResearchBenchmarks;

it("shows dataset metrics, changes budget and attacker, and opens confusion matrices", async () => {
  const user = userEvent.setup();
  render(
    <AccuracyPanel
      benchmarks={benchmarks}
      result={null}
      error={null}
      onRetry={() => {}}
    />,
  );
  expect(screen.getAllByText("93.75%").length).toBeGreaterThan(1);
  expect(screen.getByText(/Chance accuracy/).textContent).toContain("25.00%");
  expect(
    screen.getByText(/8 distinct test circuits \/ 16 compiled rows/),
  ).toBeTruthy();
  await user.selectOptions(screen.getByLabelText("Research budget"), "0.5");
  expect(screen.getAllByText("62.50%").length).toBeGreaterThan(1);
  await user.selectOptions(
    screen.getByLabelText("Protected attacker"),
    "adaptive_rf_normalization_aware",
  );
  const expected = benchmarks.budgets.find((b) => b.budget === 0.5)!.attackers
    .adaptive_rf_normalization_aware.accuracy;
  expect(
    screen.getAllByText(`${(expected * 100).toFixed(2)}%`).length,
  ).toBeGreaterThan(1);
  await user.click(
    screen.getByText(
      "Confusion matrices, per-family results and all attackers",
    ),
  );
  expect(
    screen.getByRole("heading", { name: "Baseline attacker" }),
  ).toBeTruthy();
  expect(
    screen.getByRole("heading", { name: "Normalization-aware random forest" }),
  ).toBeTruthy();
  expect(
    screen.getByText(/Metadata-only classification is nearly as strong/),
  ).toBeTruthy();
});

it("shows unavailable benchmarks explicitly and permits retry", async () => {
  const retry = vi.fn();
  const user = userEvent.setup();
  render(
    <AccuracyPanel
      benchmarks={{
        ...benchmarks,
        status: "unavailable",
        baseline: null,
        note: "Saved prediction files are missing",
      }}
      result={null}
      error={null}
      onRetry={retry}
    />,
  );
  expect(screen.queryByText("93.75%")).toBeNull();
  expect(screen.getByText("Saved prediction files are missing")).toBeTruthy();
  await user.click(screen.getByRole("button", { name: "Retry benchmark" }));
  expect(retry).toHaveBeenCalledOnce();
});
