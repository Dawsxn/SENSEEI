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
    ["fallback", "Session ended", "You've used all your tries for this step, so the session has ended."],
    ["timed_out", "Time's up", "Your session has ended, and anything you typed was sent."],
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

  it("sends what was typed when time runs out, flagged as time up", async () => {
    const running: TutoringState = {
      ...initialState, phase: "awaiting_input", status: "in_progress", currentStep: "Elaborate",
    };
    const onSubmit = vi.fn();
    const { rerender } = render(
      <ChatPanel state={running} onSubmit={onSubmit} trial={{ timeUp: false, onContinue: vi.fn() }} />,
    );
    await userEvent.type(screen.getByRole("textbox"), "  half an answer ");
    expect(onSubmit).not.toHaveBeenCalled();
    rerender(<ChatPanel state={running} onSubmit={onSubmit} trial={{ timeUp: true, onContinue: vi.fn() }} />);
    expect(onSubmit).toHaveBeenCalledOnce();
    expect(onSubmit).toHaveBeenCalledWith("half an answer", true);
  });

  it("sends nothing at time up when the box is empty", () => {
    const running: TutoringState = { ...initialState, phase: "awaiting_input", status: "in_progress" };
    const onSubmit = vi.fn();
    render(<ChatPanel state={running} onSubmit={onSubmit} trial={{ timeUp: true, onContinue: vi.fn() }} />);
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("shows no attempt dots on the trial, where there is no limit", () => {
    const running: TutoringState = {
      ...initialState, phase: "awaiting_input", status: "in_progress", currentStep: "State",
      messages: [{ key: "m", role: "tutor", step: "State", content: "State it.", unmet: [], streaming: false }],
    };
    const { rerender } = render(<ChatPanel state={running} onSubmit={vi.fn()} />);
    expect(screen.getByLabelText(/Try 1 of/)).toBeInTheDocument();
    rerender(<ChatPanel state={running} onSubmit={vi.fn()} trial={{ timeUp: false }} />);
    expect(screen.queryByLabelText(/Try 1 of/)).not.toBeInTheDocument();
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
