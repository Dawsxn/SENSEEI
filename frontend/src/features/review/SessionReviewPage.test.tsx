/** The session review, for both sides: the instructor reads how each answer
 *  was judged, the student reads the criteria they missed, as tags they can
 *  tap for the rubric. */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { SessionReviewPage } from "./SessionReviewPage";
import type { SessionTranscript } from "./types";

const transcript: SessionTranscript = {
  id: "s1",
  reading_id: "r1",
  reading_title: "Business Model",
  class_name: "STSWENG S11",
  class_id: "c1",
  core_components: ["how value is created"],
  student_name: "Mateo Cruz",
  index: 1,
  status: "fallback",
  started_at: "2026-11-13T01:00:00Z",
  ended_at: "2026-11-13T01:22:00Z",
  steps: [
    { step: "State", attempts: 1, passed: true },
    { step: "Elaborate", attempts: 1, passed: false },
  ],
  timeline: [
    { role: "tutor", step: "State", content: "State it.", attempt_number: null, at: "2026-11-13T01:01:00Z" },
    {
      role: "student", step: "State", content: "A plan to make money.", attempt_number: 1, at: "2026-11-13T01:02:00Z",
      judgment: { verdict: "PASS", criteria: [{ criterion: "Brevity", passed: true, reason: null }] },
    },
    { role: "tutor", step: "Elaborate", content: "Now elaborate.", attempt_number: null, at: "2026-11-13T01:03:00Z" },
    {
      role: "student", step: "Elaborate", content: "It has a value proposition.", attempt_number: 1, at: "2026-11-13T01:04:00Z",
      judgment: {
        verdict: "FAIL",
        criteria: [
          { criterion: "Completeness", passed: false, reason: "Leaves out the profit formula." },
          { criterion: "Own Words", passed: true, reason: "ok" },
          { criterion: "Accuracy", passed: true, reason: "ok" },
        ],
      },
    },
    { role: "tutor", step: "Elaborate", content: "What is the other part?", attempt_number: null, at: "2026-11-13T01:05:00Z" },
  ],
};

const role = vi.hoisted(() => ({ value: "instructor" }));
vi.mock("./useTranscript", () => ({ useTranscript: () => ({ data: transcript }) }));
vi.mock("../auth/useAuth", () => ({ useMe: () => ({ data: { role: role.value } }) }));
vi.mock("../../components/AppTopBar", () => ({ AppTopBar: () => null }));
vi.mock("../readings/useReadings", () => ({
  useMyClass: () => ({
    data: { id: "c1", label: "STSWENG S11", readings: [{ id: "r1" }] },
  }),
}));
vi.mock("../classes/useClasses", () => ({
  useClass: () => ({ data: { id: "c1", label: "STSWENG S11" } }),
}));
vi.mock("../../lib/api", async () => ({
  ...(await vi.importActual<typeof import("../../lib/api")>("../../lib/api")),
  getRubric: async () => ({
    version: "v3",
    steps: [
      { step: "State", criteria: [{ name: "Brevity", requirement: "The statement is concise." }] },
      { step: "Elaborate", criteria: [{ name: "Completeness", requirement: "The elaboration explains the concept in its fullness." }] },
    ],
  }),
}));

function show(path = "/classes/c1/readings/r1/sessions/s1") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createMemoryRouter(
    [{ path: "/classes/:classId/readings/:readingId/sessions/:sessionId", element: <SessionReviewPage /> }],
    { initialEntries: [path] },
  );
  render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("the session review", () => {
  it("shows the instructor each answer's verdict, the failed criteria with reasons, and the passed ones", () => {
    role.value = "instructor";
    show();
    expect(screen.getByRole("heading", { name: "Mateo Cruz" })).toBeInTheDocument();
    // numbered within each step, as the tries are stored
    expect(screen.getAllByText("Try 1")).toHaveLength(2);
    expect(screen.getByText("Not passed")).toBeInTheDocument();
    expect(screen.getByText("Leaves out the profit formula.")).toBeInTheDocument();
    expect(screen.getByText("Own Words, Accuracy")).toBeInTheDocument();
    // the instructor has the reasons, so no tags
    expect(screen.queryByLabelText("Criteria not met")).not.toBeInTheDocument();
  });

  it("leads back through the breadcrumb to the reading and its class", () => {
    role.value = "student";
    show();
    // the trail, and on a phone the link back up, both go to the reading
    for (const link of screen.getAllByRole("link", { name: /Business Model/ })) {
      expect(link).toHaveAttribute("href", "/classes/c1/readings/r1");
    }
    expect(screen.getByRole("link", { name: "STSWENG S11" })).toHaveAttribute("href", "/classes/c1");
  });

  it("sums up each step, including the ones never reached", () => {
    role.value = "student";
    show();
    expect(screen.getByText(/Attempt 1 · .* · 22 minutes/)).toBeInTheDocument();
    expect(screen.getAllByText("1 try")).toHaveLength(2);
    expect(screen.getAllByText("Not reached")).toHaveLength(2);
  });

  it("shows the student the missed criteria under the tutor's reply, and opens the rubric on a tap", async () => {
    role.value = "student";
    show();
    const tags = screen.getByLabelText("Criteria not met");
    expect(screen.queryByText("Leaves out the profit formula.")).not.toBeInTheDocument();

    await userEvent.click(within(tags).getByRole("button", { name: "Completeness" }));
    expect(await screen.findByText("Rubric · Elaborate")).toBeInTheDocument();
    expect(screen.getByText("The elaboration explains the concept in its fullness.")).toBeInTheDocument();
  });

  it("opens the core components", async () => {
    role.value = "student";
    show();
    await userEvent.click(screen.getByRole("button", { name: /Components/ }));
    expect(screen.getByText("how value is created")).toBeInTheDocument();
  });

  it("refuses an address that names another reading", () => {
    role.value = "student";
    show("/classes/c1/readings/r9/sessions/s1");
    expect(screen.getByText("Couldn't load this session.")).toBeInTheDocument();
  });
});
