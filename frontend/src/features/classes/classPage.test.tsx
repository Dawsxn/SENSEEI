/** The instructor's classes and class page: cards, the three tabs, the menus,
 *  and adding a reading the instructor already has. */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ClassDetailPage } from "./ClassDetailPage";
import { ClassListPage } from "./ClassListPage";

const api = vi.hoisted(() => ({
  getMe: vi.fn(async () => ({ id: "p", name: "Prof", email: "p@dlsu.edu.ph", role: "instructor" })),
  getClasses: vi.fn(),
  getClass: vi.fn(),
  getClassStatistics: vi.fn(),
  getLibrary: vi.fn(),
  addReadingsToClass: vi.fn(async () => undefined),
}));
vi.mock("../../lib/api", async () => ({
  ...(await vi.importActual<typeof import("../../lib/api")>("../../lib/api")),
  ...api,
}));
vi.mock("../auth/useAuth", async () => ({
  ...(await vi.importActual<typeof import("../auth/useAuth")>("../auth/useAuth")),
  useTrialMode: () => false,
}));

const CLASS = {
  id: "c1",
  name: "STRAMA",
  section: "K31",
  label: "STRAMA K31",
  join_code: "4KQ2-9TXM",
  mode: "seei",
  students: [
    { id: "s1", name: "Nikko Tan", email: "nikko_tan@dlsu.edu.ph", enrolled_at: "2026-11-24T00:00:00Z" },
  ],
  readings: [{ id: "r1", title: "Strategy", description: "Coordinated actions to outperform rivals" }],
};

function show(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createMemoryRouter(
    [
      { path: "/classes", element: <ClassListPage /> },
      { path: "/classes/:classId", element: <ClassDetailPage /> },
      { path: "/classes/:classId/readings/:readingId", element: <p>reading page</p> },
      { path: "/library/new", element: <p>upload page</p> },
    ],
    { initialEntries: [path] },
  );
  render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return router;
}

beforeEach(() => {
  localStorage.clear();
  api.getClass.mockResolvedValue(CLASS);
  api.getClassStatistics.mockResolvedValue({
    statistics: { session_count: 0, pass_rates: [], failed_criteria: [], average_attempts: [] },
    readings: [{ id: "r1", title: "Strategy", description: null, session_count: 5, flagged_count: 1 }],
    flagged_student_ids: ["s1"],
  });
  api.addReadingsToClass.mockClear();
});

describe("the classes page", () => {
  it("shows each class as a card, with its students and readings", async () => {
    api.getClasses.mockResolvedValue([
      { id: "c1", name: "STRAMA", section: "K31", label: "STRAMA K31", join_code: "4KQ2-9TXM", mode: "seei", student_count: 3, reading_count: 1 },
    ]);
    show("/classes");
    expect(await screen.findByText("3 students · 1 reading")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /STRAMA/ })).toHaveAttribute("href", "/classes/c1");
    expect(screen.queryByText("4KQ2-9TXM")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "+ New class" })).toBeInTheDocument();
  });

  it("says when there are none", async () => {
    api.getClasses.mockResolvedValue([]);
    show("/classes");
    expect(await screen.findByText("No classes available")).toBeInTheDocument();
  });
});

describe("the class page", () => {
  it("opens on its readings, with the join code in the header", async () => {
    show("/classes/c1");
    expect(await screen.findByRole("heading", { name: "STRAMA" })).toBeInTheDocument();
    expect(screen.getByText("4KQ2-9TXM")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Readings\s*1/ })).toHaveAttribute("aria-selected", "true");
    expect(await screen.findByText("5 sessions")).toBeInTheDocument();
  });

  it("marks a reading with how many of its students are flagged", async () => {
    show("/classes/c1");
    expect(await screen.findByText("1 flagged")).toBeInTheDocument();
  });

  it("lists the students on their own tab, flagged ones marked, with remove in each one's menu", async () => {
    const router = show("/classes/c1");
    await userEvent.click(await screen.findByRole("tab", { name: /Students/ }));
    expect(await screen.findByText("Flagged")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Nikko Tan/ })).toHaveAttribute("href", "/classes/c1/students/s1");
    expect(router.state.location.pathname).toBe("/classes/c1");
    await userEvent.click(screen.getByRole("button", { name: "Options for Nikko Tan" }));
    await userEvent.click(screen.getByRole("menuitem", { name: "Remove from class" }));
    expect(screen.getByText("Remove Nikko Tan?")).toBeInTheDocument();
  });

  it("keeps editing and deleting the class in its menu", async () => {
    show("/classes/c1");
    await userEvent.click(await screen.findByRole("button", { name: "Class options" }));
    const menu = screen.getByRole("menu");
    expect(within(menu).getAllByRole("menuitem").map((m) => m.textContent)).toEqual([
      "Edit class",
      "New join code",
      "Delete class",
    ]);
  });

  it("says when the statistics have nothing to show yet", async () => {
    show("/classes/c1");
    await userEvent.click(await screen.findByRole("tab", { name: "Statistics" }));
    expect(await screen.findByText("Statistics show once a student finishes a session.")).toBeInTheDocument();
  });

  it("uploads a new reading with this class ticked", async () => {
    const router = show("/classes/c1");
    await userEvent.click(await screen.findByRole("button", { name: "+ Add reading" }));
    await userEvent.click(screen.getByRole("menuitem", { name: "Upload a new reading" }));
    expect(router.state.location.pathname + router.state.location.search).toBe("/library/new?class=c1");
  });

  it("adds a reading it does not have yet from the instructor's readings", async () => {
    api.getLibrary.mockResolvedValue([
      { id: "r1", title: "Strategy", description: null, classes: ["STRAMA K31"], session_count: 5, created_at: "" },
      { id: "r2", title: "Business Model", description: null, classes: ["STSWENG S11"], session_count: 0, created_at: "" },
    ]);
    show("/classes/c1");
    await userEvent.click(await screen.findByRole("button", { name: "+ Add reading" }));
    await userEvent.click(screen.getByRole("menuitem", { name: "Choose from your readings" }));

    const dialog = await screen.findByRole("dialog");
    // the one it already has is not offered
    expect(within(dialog).queryByText("Strategy")).not.toBeInTheDocument();
    await userEvent.click(await within(dialog).findByText("Business Model"));
    await userEvent.click(within(dialog).getByRole("button", { name: "Add" }));
    expect(api.addReadingsToClass).toHaveBeenCalledWith("c1", ["r2"]);
  });
});
