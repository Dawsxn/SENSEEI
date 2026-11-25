/** The instructor's two views of one student: in the class, and on a reading. */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { ClassStudentPage, StudentSessionsPage } from "./StudentPages";

const api = vi.hoisted(() => ({
  getMe: vi.fn(async () => ({ id: "p", name: "Prof", email: "p@dlsu.edu.ph", role: "instructor" })),
  getClassStudent: vi.fn(),
  getStudentSessions: vi.fn(),
}));
vi.mock("../../lib/api", async () => ({
  ...(await vi.importActual<typeof import("../../lib/api")>("../../lib/api")),
  ...api,
}));

function show(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createMemoryRouter(
    [
      { path: "/classes/:classId/students/:studentId", element: <ClassStudentPage /> },
      { path: "/classes/:classId/readings/:readingId/students/:studentId", element: <StudentSessionsPage /> },
    ],
    { initialEntries: [path] },
  );
  render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("a student in a class", () => {
  it("shows where they are on each reading, and opens the ones they started", async () => {
    api.getClassStudent.mockResolvedValue({
      id: "s1", name: "Rafael Lim", email: "rafael_lim@dlsu.edu.ph", enrolled_at: "2026-11-24T00:00:00Z",
      class_id: "c1", class_label: "STRAMA K31",
      readings: [
        { id: "r1", title: "Strategy", description: null, status: "stopped_early", steps_passed: 1,
          stopped_on: "Elaborate", session_id: "x1", last_session_at: "2026-11-18T00:00:00Z" },
        { id: "r2", title: "Strategic Vision", description: null, status: "not_started", steps_passed: 0,
          stopped_on: null, session_id: null, last_session_at: null },
      ],
    });
    show("/classes/c1/students/s1");
    expect(await screen.findByRole("heading", { name: "Rafael Lim" })).toBeInTheDocument();
    expect(screen.getByText("Flagged")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Strategy/ })).toHaveAttribute("href", "/classes/c1/readings/r1/students/s1");
    expect(screen.queryByRole("link", { name: /Strategic Vision/ })).not.toBeInTheDocument();
  });
});

describe("a student's sessions on a reading", () => {
  it("lists every attempt, newest first, with an earlier flag kept", async () => {
    api.getStudentSessions.mockResolvedValue({
      id: "s1", name: "Nikko Tan", email: "nikko_tan@dlsu.edu.ph", class_id: "c1", class_label: "STRAMA K31",
      reading_id: "r1", reading_title: "Strategy",
      sessions: [
        { id: "x2", index: 2, status: "complete", started_at: "2026-11-25T00:00:00Z", ended_at: null },
        { id: "x1", index: 1, status: "fallback", started_at: "2026-11-15T00:00:00Z", ended_at: null },
      ],
    });
    show("/classes/c1/readings/r1/students/s1");
    const links = await screen.findAllByRole("link", { name: /Attempt/ });
    expect(links.map((a) => a.textContent)).toEqual([
      expect.stringContaining("Attempt 2"),
      expect.stringContaining("Attempt 1"),
    ]);
    expect(links[1]).toHaveTextContent("Flagged");
    expect(links[0]).toHaveAttribute("href", "/classes/c1/readings/r1/sessions/x2");
  });
});
