/** How a trial participant's SEE-I session ends: a strip in place of the answer
 * box, saying how it ended, with the way on to the post-test. */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ChatPanel } from "./ChatPanel";
import { initialState, type TutoringState } from "./useTutoringSession";

vi.mock("../trial/trialLog", () => ({ logTrial: vi.fn() }));

const ended = (status: TutoringState["status"]): TutoringState => ({
  ...initialState,
  phase: "terminal",
  status,
});

describe("the end of a trial session", () => {
  it.each([
    ["complete", "Session complete", "You finished all four steps."],
    ["fallback", "Session ended", "You've used all your attempts, so the session has ended."],
    ["timed_out", "Time's up", "Your session has ended."],
  ] as const)("says how it ended (%s) and waits for Continue", async (status, title, line) => {
    const onContinue = vi.fn();
    render(<ChatPanel state={ended(status)} onSubmit={vi.fn()} trial={{ timeUp: false, onContinue }} />);
    expect(screen.getByText(title)).toBeInTheDocument();
    expect(screen.getByText(line)).toBeInTheDocument();
    expect(onContinue).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Continue to post-test" }));
    expect(onContinue).toHaveBeenCalledOnce();
  });

  it("calls it time up when the clock runs out mid-step", () => {
    const running: TutoringState = { ...initialState, phase: "awaiting_input", status: "in_progress" };
    render(<ChatPanel state={running} onSubmit={vi.fn()} trial={{ timeUp: true, onContinue: vi.fn() }} />);
    expect(screen.getByText("Time's up")).toBeInTheDocument();
  });

  it("keeps the old wording when the class has no post-test", () => {
    render(<ChatPanel state={ended("complete")} onSubmit={vi.fn()} trial={{ timeUp: false }} />);
    expect(screen.queryByRole("button", { name: "Continue to post-test" })).not.toBeInTheDocument();
    expect(screen.getByText(/You're done/)).toBeInTheDocument();
  });

  it("tells a student how to start a new line", () => {
    const running: TutoringState = { ...initialState, phase: "awaiting_input", status: "in_progress" };
    render(<ChatPanel state={running} onSubmit={vi.fn()} />);
    expect(screen.getByText("Shift+Enter for a new line")).toBeInTheDocument();
  });
});
