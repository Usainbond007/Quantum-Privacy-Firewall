import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CasePage } from "../components/ResearchDesk";
import App from "../App";
import { api } from "../lib/api";
import groverFixture from "./fixtures/grover-live.json";
import portfolioFixture from "./fixtures/portfolio-live.json";
import type { GroverResult, PortfolioResult } from "../types/usecases";
const gr = groverFixture as unknown as GroverResult;
const pr = portfolioFixture as unknown as PortfolioResult;
beforeEach(() => {
  vi.spyOn(api, "grover").mockResolvedValue(gr);
  vi.spyOn(api, "portfolio").mockResolvedValue(pr);
});
afterEach(() => vi.restoreAllMocks());
describe("Research desk live workflow", () => {
  it("does not invent initial results or run without an explicit action", () => {
    render(<CasePage kind="cryptanalysis" />);
    expect(screen.getByText("Not assessed")).toBeTruthy();
    expect(api.grover).not.toHaveBeenCalled();
  });
  it("runs the backend, shows evidence, and invalidates the displayed verdict on edits", async () => {
    const u = userEvent.setup();
    render(<CasePage kind="cryptanalysis" />);
    await u.click(screen.getByRole("button", { name: "Run live assessment" }));
    await screen.findByText("All rewrite candidates");
    expect(api.grover).toHaveBeenCalledWith(
      { marked: "1010", budget: 0.2 },
      expect.any(AbortSignal),
    );
    expect(screen.getByText("BLOCK")).toBeTruthy();
    await u.click(screen.getByRole("button", { name: /Workload From/ }));
    await u.clear(screen.getByLabelText("Marked state"));
    await u.type(screen.getByLabelText("Marked state"), "0110");
    expect(screen.getByText("Rerun needed")).toBeTruthy();
    expect(
      screen.getByText(/Evidence below belongs to the previous run/),
    ).toBeTruthy();
  });
  it("disables invalid input and keeps API errors visible", async () => {
    const u = userEvent.setup();
    vi.mocked(api.grover).mockRejectedValue(new Error("Engine unavailable"));
    render(<CasePage kind="cryptanalysis" />);
    await u.click(screen.getByRole("button", { name: "Run live assessment" }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(screen.getByText("Not assessed")).toBeTruthy();
    await u.clear(screen.getByLabelText("Marked state"));
    await u.type(screen.getByLabelText("Marked state"), "10");
    expect(
      (
        screen.getByRole("button", {
          name: "Run live assessment",
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(true);
  });
  it("makes observer access a real explanatory interaction", async () => {
    const u = userEvent.setup();
    render(<CasePage kind="cryptanalysis" />);
    await u.click(screen.getByRole("button", { name: /Observer See/ }));
    await u.click(screen.getByRole("button", { name: "Structure only" }));
    expect(screen.getByText(/Identifying Grover is not the same/)).toBeTruthy();
    await u.click(
      screen.getByRole("button", { name: "Full logical artifact" }),
    );
    expect(screen.getByText(/stronger small-circuit attacker/)).toBeTruthy();
  });
  it("shows portfolio recovery separately from the public sweep caveats", async () => {
    const u = userEvent.setup();
    render(<CasePage kind="portfolio" />);
    await u.click(screen.getByRole("button", { name: "Run live assessment" }));
    await screen.findByText("A fixed public sweep changes what leaves the lab");
    expect(screen.getAllByText("BLOCK").length).toBeGreaterThan(0);
    expect(screen.getByText("WARN")).toBeTruthy();
    expect(screen.getByText(/MATCH · identical/)).toBeTruthy();
    expect(
      screen.getByText(/No privacy improvement is claimed for that rewrite/),
    ).toBeTruthy();
  });
  it("navigates between two independent cases", async () => {
    vi.spyOn(api, "options").mockResolvedValue({} as never);
    vi.spyOn(window, "scrollTo").mockImplementation(() => {});
    window.location.hash = "cryptanalysis";
    render(<App />);
    const nav = screen.getByRole("navigation", { name: "Main navigation" });
    await userEvent.click(
      within(nav).getByRole("link", { name: /Portfolio Optimization/ }),
    );
    await waitFor(() =>
      expect(screen.getByRole("heading", { level: 1 }).textContent).toBe(
        "Portfolio optimization",
      ),
    );
    expect(screen.getByLabelText("Private preference")).toBeTruthy();
  });
});
