/** A reload is not leaving: the tab remembers its session, and picks it back up.
 *  Try again loads the session as the server has it, and sends an answer again
 *  only if the server never got it. */

import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../lib/api";
import type { SessionTranscript } from "../review/types";
import type { StreamEvent } from "./types";
import { forgetSession, resume, useTutoringSession } from "./useTutoringSession";

const api = vi.hoisted(() => ({
  startSession: vi.fn(),
  submitResponse: vi.fn(),
  getSession: vi.fn(),
  getTranscript: vi.fn(),
}));
vi.mock("../../lib/api", async () => ({
  ...(await vi.importActual<typeof import("../../lib/api")>("../../lib/api")),
  ...api,
}));
vi.mock("../trial/trialLog", () => ({ logTrial: vi.fn() }));

async function* stream(...events: StreamEvent[]) {
  for (const e of events) yield e;
}

const opening: StreamEvent[] = [
  { type: "session", id: "s1", status: "in_progress", current_step: "State" } as StreamEvent,
  { type: "message_start", step: "State", kind: "first_attempt", moves: ["Prompt"], unmet: [] },
  { type: "message_end", id: "m1", content: "State it." },
  { type: "state", status: "in_progress", current_step: "State", terminal: false, attempts_used: 0, attempts_left: 5 },
];

function transcript(timeline: SessionTranscript["timeline"]): SessionTranscript {
  return {
    id: "s1", reading_id: "r1", reading_title: "Strategy", class_name: "STRAMA K31", class_id: "c1",
    core_components: [], student_name: "S", student_id: "u1", index: 1, status: "in_progress",
    started_at: "1", ended_at: null, steps: [], timeline,
  };
}
const asked = { role: "tutor" as const, step: "State" as const, content: "State it.", attempt_number: null, at: "1" };

beforeEach(() => {
  sessionStorage.clear();
  Object.values(api).forEach((f) => f.mockReset());
  api.getSession.mockResolvedValue({ status: "in_progress", current_step: "State" });
});

describe("a reload", () => {
  it("picks the tab's session back up instead of starting another", async () => {
    api.startSession.mockReturnValue(stream(...opening));
    const first = renderHook(() => useTutoringSession("r1", { remember: true }));
    await waitFor(() => expect(first.result.current.state.phase).toBe("awaiting_input"));
    first.unmount();

    api.getTranscript.mockResolvedValue(transcript([asked]));
    const again = renderHook(() => useTutoringSession("r1", { remember: true }));
    await waitFor(() => expect(again.result.current.state.phase).toBe("awaiting_input"));
    expect(api.startSession).toHaveBeenCalledOnce();
    expect(again.result.current.state.messages.map((m) => m.content)).toEqual(["State it."]);
  });

  it("starts a new one once Done has forgotten it", async () => {
    sessionStorage.setItem("senseei.session.r1", "s1");
    forgetSession("r1");
    api.startSession.mockReturnValue(stream(...opening));
    const { result } = renderHook(() => useTutoringSession("r1", { remember: true }));
    await waitFor(() => expect(result.current.state.phase).toBe("awaiting_input"));
    expect(api.getSession).not.toHaveBeenCalled();
  });

  it("starts a new one when the remembered session was left", async () => {
    sessionStorage.setItem("senseei.session.r1", "s0");
    api.getSession.mockResolvedValue({ status: "left", current_step: "State" });
    api.startSession.mockReturnValue(stream(...opening));
    const { result } = renderHook(() => useTutoringSession("r1", { remember: true }));
    await waitFor(() => expect(result.current.state.phase).toBe("awaiting_input"));
    expect(api.startSession).toHaveBeenCalledOnce();
    expect(sessionStorage.getItem("senseei.session.r1")).toBe("s1");
  });

  it("remembers nothing in the trial, which picks up its own way", async () => {
    api.startSession.mockReturnValue(stream(...opening));
    const { result } = renderHook(() => useTutoringSession("r1"));
    await waitFor(() => expect(result.current.state.phase).toBe("awaiting_input"));
    expect(sessionStorage.getItem("senseei.session.r1")).toBeNull();
  });
});

describe("Try again", () => {
  async function failedAnswer() {
    api.startSession.mockReturnValue(stream(...opening));
    api.submitResponse.mockReturnValueOnce(
      stream({ type: "error", detail: "could not reach the server: TypeError" }),
    );
    const hook = renderHook(() => useTutoringSession("r1", { remember: true }));
    await waitFor(() => expect(hook.result.current.state.phase).toBe("awaiting_input"));
    await act(() => hook.result.current.submit("my answer"));
    expect(hook.result.current.state.phase).toBe("error");
    return hook;
  }

  it("sends the answer again when the server never got it", async () => {
    const { result } = await failedAnswer();
    api.getTranscript.mockResolvedValue(transcript([asked]));
    api.submitResponse.mockReturnValueOnce(
      stream(
        { type: "message_start", step: "State", kind: "retry", moves: [], unmet: [] },
        { type: "message_end", id: "m2", content: "Say more." },
        { type: "state", status: "in_progress", current_step: "State", terminal: false, attempts_used: 1, attempts_left: 4 },
      ),
    );
    await act(() => result.current.retry());
    expect(api.submitResponse).toHaveBeenLastCalledWith("s1", "my answer", expect.anything());
    expect(result.current.state.messages.map((m) => m.content)).toEqual(["State it.", "my answer", "Say more."]);
    expect(result.current.state.phase).toBe("awaiting_input");
  });

  it("does not send it twice when the server already has it", async () => {
    const { result } = await failedAnswer();
    api.getTranscript.mockResolvedValue(
      transcript([
        asked,
        { role: "student", step: "State", content: "my answer", attempt_number: 1, at: "2" },
        { role: "tutor", step: "State", content: "Say more.", attempt_number: null, at: "3" },
      ]),
    );
    await act(() => result.current.retry());
    expect(api.submitResponse).toHaveBeenCalledOnce();
    expect(result.current.state.messages.map((m) => m.content)).toEqual(["State it.", "my answer", "Say more."]);
    expect(result.current.state.phase).toBe("awaiting_input");
  });

  it("starts over when the session never got its opening", async () => {
    api.startSession
      .mockReturnValueOnce(stream(opening[0], { type: "error", detail: "stream interrupted: TypeError" }))
      .mockReturnValueOnce(stream(...opening));
    const { result } = renderHook(() => useTutoringSession("r1", { remember: true }));
    await waitFor(() => expect(result.current.state.phase).toBe("error"));
    api.getSession.mockRejectedValue(new ApiError(404, "session s1: 404"));
    api.getTranscript.mockRejectedValue(new ApiError(404, "transcript s1: 404"));
    await act(() => result.current.retry());
    expect(api.startSession).toHaveBeenCalledTimes(2);
    expect(result.current.state.phase).toBe("awaiting_input");
  });
});

describe("picking up", () => {
  const timeline: SessionTranscript["timeline"] = [
    asked,
    {
      role: "student", step: "State", content: "too vague", attempt_number: 1, at: "2",
      judgment: {
        verdict: "FAIL",
        criteria: [
          { criterion: "Brevity", passed: false, reason: null },
          { criterion: "Clarity", passed: true, reason: null },
        ],
      },
    },
    { role: "tutor", step: "State", content: "Try again.", attempt_number: null, at: "3" },
  ];

  it("brings back the tags an answer earned, outside the trial", () => {
    const state = resume(transcript(timeline), "in_progress", "State", true);
    expect(state.messages.map((m) => m.unmet)).toEqual([[], [], ["Brevity"]]);
  });

  it("leaves them off in the trial, as it ran", () => {
    const state = resume(transcript(timeline), "in_progress", "State");
    expect(state.messages.every((m) => m.unmet.length === 0)).toBe(true);
  });
});
