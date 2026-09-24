/** The class dashboard: what the statistics show, and what the roster says. */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { ClassReadingPage } from "./ClassReadingPage";
import { StatisticsSection } from "./StatisticsSection";
import type { ClassReadingDetail, Statistics } from "./types";

const api = vi.hoisted(() => ({ getClassReading: vi.fn(), getMe: vi.fn() }));

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return { ...actual, ...api };
});

api.getMe.mockResolvedValue({ id: "p", name: "Prof", email: "p@dlsu.edu.ph", role: "instructor" });

const STATS: Statistics = {
  session_count: 2,
  pass_rates: [
    { step: "State", passed: 2, total: 2, percent: 100 },
    { step: "Elaborate", passed: 1, total: 5, percent: 20 },
  ],
  failed_criteria: [
    { criterion: "Completeness", failures: 4 },
    { criterion: "Coherence", failures: 3 },
  ],
  average_attempts: [{ step: "Elaborate", average: 2 }],
};

const READING: ClassReadingDetail = {
  id: "r1",
  title: "Strategy",
  description: "Coordinated actions",
  class_id: "c1",
  class_label: "STRAMA K31",
  statistics: STATS,
  students: [
    {
      id: "s1", name: "Bea", email: "bea@dlsu.edu.ph", status: "stopped_early",
      steps_passed: 1, stopped_on: "Elaborate", session_id: "sess-bea",
      last_session_at: "2026-09-19T02:00:00Z",
    },
    {
      id: "s2", name: "Chelsea", email: "chelsea@dlsu.edu.ph", status: "not_started",
      steps_passed: 0, stopped_on: null, session_id: null, last_session_at: null,
    },
    {
      id: "s3", name: "Mateo", email: "mateo@dlsu.edu.ph", status: "completed",
      steps_passed: 4, stopped_on: null, session_id: "sess-mateo",
      last_session_at: "2026-09-18T02:00:00Z",
    },
  ],
};

function renderReading() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createMemoryRouter(
    [
      { path: "/classes/:classId/readings/:readingId", element: <ClassReadingPage /> },
      { path: "/classes/:classId", element: <p>Class page</p> },
      { path: "/review/:sessionId", element: <p>Transcript</p> },
    ],
    { initialEntries: ["/classes/c1/readings/r1"] },
  );
  render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return router;
}

describe("the statistics", () => {
  it("shows all three, in the rubric's own words", () => {
    render(<StatisticsSection statistics={STATS} scope="For this reading only." />);

    // The scope is the heading's tooltip, reachable by name for a screen reader.
    expect(
      screen.getByRole("button", { name: "For this reading only." }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Share of attempts/ })).toBeInTheDocument();
    expect(screen.getByText("100%")).toBeInTheDocument();
    expect(screen.getByText("20%")).toBeInTheDocument();
    expect(screen.getByText("Completeness")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByText("2.0")).toBeInTheDocument();
  });

  it("says there is nothing yet rather than showing zeroes", () => {
    render(
      <StatisticsSection
        statistics={{ session_count: 0, pass_rates: [], failed_criteria: [], average_attempts: [] }}
        scope="Across all readings in this class."
      />,
    );

    expect(screen.getByText("No sessions yet")).toBeInTheDocument();
    expect(screen.queryByText("Pass rate by step")).not.toBeInTheDocument();
  });
});

describe("the roster", () => {
  it("says how far each student got, and where one stopped", async () => {
    api.getClassReading.mockResolvedValue(READING);
    renderReading();

    expect(await screen.findByText("Strategy")).toBeInTheDocument();
    expect(screen.getAllByText("Stopped early").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Stopped on Elaborate/).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Completed").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Not started").length).toBeGreaterThan(0);
  });

  it("opens a student's transcript, except for one who never started", async () => {
    api.getClassReading.mockResolvedValue(READING);
    renderReading();
    await screen.findByText("Strategy");

    // By text rather than by role: a disabled button is not in the a11y tree.
    const row = (name: string) => screen.getByText(name).closest("button")!;
    expect(row("Chelsea")).toBeDisabled();

    await userEvent.click(row("Mateo"));
    expect(await screen.findByText("Transcript")).toBeInTheDocument();
  });

  it("goes back to the class it belongs to", async () => {
    api.getClassReading.mockResolvedValue(READING);
    const router = renderReading();

    await userEvent.click(await screen.findByRole("button", { name: /STRAMA K31/ }));
    expect(router.state.location.pathname).toBe("/classes/c1");
  });
});
