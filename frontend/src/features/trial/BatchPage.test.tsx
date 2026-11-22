/** A batch's IDs by class, the filter that printing follows, and copying an ID. */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";

import { BatchPage } from "./BatchPage";
import type { Batch, BatchParticipant } from "./types";

const p = (code: string, cls: "a" | "b", status: BatchParticipant["status"] = "not_used"): BatchParticipant => ({
  id: code,
  code,
  class_id: cls,
  class_label: cls === "a" ? "TRIAL S1-A" : "TRIAL S1-B",
  mode: cls === "a" ? "seei" : "chatbot",
  status,
});

// Shuffled, as the server sends them.
const batch: Batch = {
  id: "b1",
  name: "Sitting 1",
  created_at: "2026-11-22T00:00:00Z",
  closed_at: null,
  participants: [p("P-ZZZZ-0001", "b"), p("P-BBBB-0002", "a"), p("P-CCCC-0003", "b", "voided"), p("P-AAAA-0004", "a")],
};

vi.mock("./useTrial", () => ({ useBatch: () => ({ data: batch }) }));
vi.mock("../../components/AppTopBar", () => ({ AppTopBar: () => null }));

function renderPage() {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={["/participants/b1"]}>
        <Routes>
          <Route path="/participants/:batchId" element={<BatchPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const codesIn = (el: HTMLElement) => within(el).getAllByText(/^P-/).map((n) => n.textContent);

describe("a batch's page", () => {
  it("lists the IDs by group, SEE-I first, and filters to one group with printing following", async () => {
    renderPage();
    const seei = screen.getByRole("region", { name: "SEE-I" });
    expect(codesIn(seei)).toEqual(["P-AAAA-0004", "P-BBBB-0002"]);
    expect(screen.getByRole("region", { name: "Chatbot" })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /^SEE-I/ }));
    expect(screen.queryByRole("region", { name: "Chatbot" })).not.toBeInTheDocument();
    expect(screen.getByText("Prints SEE-I only")).toBeInTheDocument();
    // The printed sheet: only SEE-I's slips, under its line.
    expect(screen.getByText("SEE-I · TRIAL S1-A · 2 slips")).toBeInTheDocument();
    expect(screen.queryByText(/CHATBOT|Chatbot · TRIAL/)).not.toBeInTheDocument();
  });

  it("copies an ID, but offers no copy for a voided one", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    renderPage();
    expect(screen.queryByRole("button", { name: "Copy P-CCCC-0003" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Copy P-AAAA-0004" }));
    expect(writeText).toHaveBeenCalledWith("P-AAAA-0004");
    expect(await screen.findByText("Copied")).toBeInTheDocument();
  });
});
