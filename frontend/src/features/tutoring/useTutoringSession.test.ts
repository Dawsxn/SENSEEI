import { describe, expect, it } from "vitest";

import { initialState, reduce, type Action, type TutoringState } from "./useTutoringSession";
import type { StreamEvent } from "./types";

/** Fold a list of actions over the reducer, as the hook would dispatch them. */
function run(actions: Action[], from: TutoringState = initialState): TutoringState {
  return actions.reduce(reduce, from);
}

const ev = (event: StreamEvent): Action => ({ type: "event", event });

describe("the tutoring reducer", () => {
  it("opens a session and streams the first prompt", () => {
    const state = run([
      { type: "start" },
      ev({ type: "session", id: "s1", reading_id: "r1", reading_title: "Strategy", status: "in_progress", current_step: "State", started_at: "", ended_at: null }),
      ev({ type: "message_start", step: "State", kind: "first_attempt", moves: ["Prompt"] }),
      ev({ type: "delta", text: "State the " }),
      ev({ type: "delta", text: "concept." }),
      ev({ type: "message_end", id: "m1", content: "State the concept." }),
      ev({ type: "state", status: "in_progress", current_step: "State", terminal: false, attempts_used: 0, attempts_left: 3 }),
    ]);

    expect(state.sessionId).toBe("s1");
    expect(state.phase).toBe("awaiting_input");
    expect(state.messages).toHaveLength(1);
    expect(state.messages[0]).toMatchObject({
      role: "tutor",
      content: "State the concept.",
      streaming: false,
    });
  });

  it("builds a tutor message by accumulating deltas, with a caret until it ends", () => {
    const mid = run([
      ev({ type: "message_start", step: "State", kind: "first_attempt", moves: ["Prompt"] }),
      ev({ type: "delta", text: "Half" }),
    ]);
    expect(mid.messages[0].streaming).toBe(true);
    expect(mid.messages[0].content).toBe("Half");

    const done = run([ev({ type: "message_end", id: "m", content: "Half done" })], mid);
    expect(done.messages[0].streaming).toBe(false);
    expect(done.messages[0].content).toBe("Half done");
  });

  it("echoes the student's answer before the reply streams", () => {
    const state = run([{ type: "student", text: "my answer" }], {
      ...initialState,
      sessionId: "s1",
      phase: "awaiting_input",
    });
    expect(state.phase).toBe("streaming");
    expect(state.messages.at(-1)).toMatchObject({ role: "student", content: "my answer" });
  });

  it("on a pass, keeps both the acknowledgement and the next step's prompt", () => {
    const state = run([
      { type: "student", text: "good" },
      ev({ type: "message_start", step: "State", kind: "passed", moves: ["Acknowledgement", "Transition"] }),
      ev({ type: "delta", text: "Well done." }),
      ev({ type: "message_end", id: "m2", content: "Well done." }),
      ev({ type: "message_start", step: "Elaborate", kind: "first_attempt", moves: ["Prompt"] }),
      ev({ type: "delta", text: "Now elaborate." }),
      ev({ type: "message_end", id: "m3", content: "Now elaborate." }),
      ev({ type: "state", status: "in_progress", current_step: "Elaborate", terminal: false, attempts_used: 0, attempts_left: 3 }),
    ], { ...initialState, sessionId: "s1", phase: "awaiting_input" });

    const kinds = state.messages.map((m) => `${m.role}:${m.kind ?? ""}`);
    expect(kinds).toEqual(["student:", "tutor:passed", "tutor:first_attempt"]);
    expect(state.currentStep).toBe("Elaborate");
    expect(state.phase).toBe("awaiting_input");
  });

  it("tracks attempts on a retry", () => {
    const state = run([
      ev({ type: "message_start", step: "State", kind: "retry", moves: [] }),
      ev({ type: "message_end", id: "m", content: "Try again." }),
      ev({ type: "state", status: "in_progress", current_step: "State", terminal: false, attempts_used: 1, attempts_left: 2 }),
    ], { ...initialState, phase: "streaming" });
    expect(state.attemptsUsed).toBe(1);
    expect(state.attemptsLeft).toBe(2);
    expect(state.phase).toBe("awaiting_input");
  });

  it("ends the session on a terminal state event", () => {
    const state = run([
      ev({ type: "message_start", step: "State", kind: "final_fail", moves: [] }),
      ev({ type: "message_end", id: "m", content: "That wasn't enough." }),
      ev({ type: "message_start", step: "State", kind: "fallback", moves: ["Fallback"] }),
      ev({ type: "delta", text: "Your instructor has been notified." }),
      ev({ type: "message_end", id: "f", content: "Your instructor has been notified." }),
      ev({ type: "state", status: "fallback", current_step: "State", terminal: true, attempts_used: 3, attempts_left: 0 }),
    ], { ...initialState, phase: "streaming" });

    expect(state.phase).toBe("terminal");
    expect(state.status).toBe("fallback");
    expect(state.messages.at(-1)).toMatchObject({ role: "fallback" });
  });

  it("surfaces an error event and stops any half-streamed message", () => {
    const state = run([
      ev({ type: "message_start", step: "State", kind: "retry", moves: [] }),
      ev({ type: "delta", text: "partial" }),
      ev({ type: "error", detail: "tutor failed: TimeoutError" }),
    ], { ...initialState, phase: "streaming" });

    expect(state.phase).toBe("error");
    expect(state.error).toContain("tutor failed");
    expect(state.messages.at(-1)?.streaming).toBe(false);
  });
});
