/** The trial's screens: signing in by ID, the countdown, a session picked back
 *  up after a reload, and how a participant's session ends. */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../../lib/api";
import type { SessionTranscript } from "../review/types";
import { ChatPanel } from "../tutoring/ChatPanel";
import { initialState, resume } from "../tutoring/useTutoringSession";
import { ParticipantSignIn } from "./ParticipantSignIn";
import { formatClock } from "./TrialClock";

const api = vi.hoisted(() => ({ participantSignIn: vi.fn() }));

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return { ...actual, ...api };
});

function renderSignIn() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createMemoryRouter(
    [
      { path: "/login", element: <ParticipantSignIn /> },
      { path: "/", element: <p>Home</p> },
    ],
    { initialEntries: ["/login"] },
  );
  render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("signing in with a participant ID", () => {
  it("says when the ID does not exist", async () => {
    api.participantSignIn.mockRejectedValueOnce(new ApiError(404, "no", "unknown"));
    renderSignIn();
    await userEvent.type(screen.getByLabelText("Participant ID"), "P-2222-2222{Enter}");
    expect(await screen.findByRole("alert")).toHaveTextContent("That ID doesn't exist.");
  });

  it("says when the ID no longer works", async () => {
    api.participantSignIn.mockRejectedValueOnce(new ApiError(403, "no", "inactive"));
    renderSignIn();
    await userEvent.type(screen.getByLabelText("Participant ID"), "P-2222-2222{Enter}");
    expect(await screen.findByRole("alert")).toHaveTextContent("That ID is no longer active.");
  });

  it("goes in when the ID works", async () => {
    api.participantSignIn.mockResolvedValueOnce({ ok: true });
    renderSignIn();
    await userEvent.type(screen.getByLabelText("Participant ID"), "p 7k3q 9txm");
    await userEvent.click(screen.getByRole("button", { name: "Start" }));
    expect(api.participantSignIn).toHaveBeenLastCalledWith("p 7k3q 9txm");
    expect(await screen.findByText("Home")).toBeInTheDocument();
  });
});

describe("the countdown", () => {
  it("reads as minutes and seconds", () => {
    expect(formatClock(40 * 60)).toBe("40:00");
    expect(formatClock(298)).toBe("4:58");
    expect(formatClock(0)).toBe("0:00");
  });
});

describe("a session picked back up", () => {
  const transcript: SessionTranscript = {
    id: "s1",
    reading_id: "r1",
    reading_title: "Cognitive Offloading",
    class_name: "TRIAL S1-A",
    student_name: "P-7K3Q-9TXM",
    index: 1,
    status: "in_progress",
    started_at: "2026-10-28T01:00:00Z",
    ended_at: null,
    steps: [],
    timeline: [
      { role: "tutor", step: "State", content: "State it.", attempt_number: null, at: "1" },
      { role: "student", step: "State", content: "An answer.", attempt_number: 1, at: "2" },
      { role: "tutor", step: "State", content: "Passed.", attempt_number: null, at: "3" },
      { role: "tutor", step: "Elaborate", content: "Elaborate.", attempt_number: null, at: "4" },
      { role: "student", step: "Elaborate", content: "Try one.", attempt_number: 1, at: "5" },
      { role: "tutor", step: "Elaborate", content: "Again.", attempt_number: null, at: "6" },
    ],
  };

  it("shows what was said, and counts the attempts on the current step", () => {
    const state = resume(transcript, "in_progress", "Elaborate");
    expect(state.messages.map((m) => [m.role, m.content])).toEqual([
      ["tutor", "State it."],
      ["student", "An answer."],
      ["tutor", "Passed."],
      ["tutor", "Elaborate."],
      ["student", "Try one."],
      ["tutor", "Again."],
    ]);
    expect([state.attemptsUsed, state.attemptsLeft, state.phase]).toEqual([1, 2, "awaiting_input"]);
  });

  it("is over if the session already ended", () => {
    expect(resume(transcript, "timed_out", "Elaborate").phase).toBe("terminal");
  });
});

describe("how a participant's session ends", () => {
  const running = { ...initialState, phase: "awaiting_input" as const, currentStep: "State" as const };

  it("tells them to stay seated when they finish early", () => {
    render(
      <ChatPanel
        state={{ ...running, phase: "terminal", status: "complete" }}
        onSubmit={vi.fn()}
        trial={{ timeUp: false }}
      />,
    );
    expect(screen.getByText("You're done. Please stay at your seat until time is up.")).toBeInTheDocument();
  });

  it("stops them answering once time is up", () => {
    render(<ChatPanel state={running} onSubmit={vi.fn()} trial={{ timeUp: true }} />);
    expect(screen.getByText("Time's up. Please wait for the next instructions.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Submit" })).not.toBeInTheDocument();
  });

  it("is unchanged for an ordinary student", () => {
    render(<ChatPanel state={running} onSubmit={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Submit" })).toBeInTheDocument();
  });
});
