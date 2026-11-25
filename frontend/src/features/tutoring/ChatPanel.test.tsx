/** How a SEE-I session ends, and what an error says: a strip in place of the
 * answer box. A trial participant's says how it ended, with the way on to the
 * post-test; anyone else's offers the reading and the review. */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ChatPanel } from "./ChatPanel";
import { initialState, type TutoringState } from "./useTutoringSession";

vi.mock("../trial/trialLog", () => ({ logTrial: vi.fn() }));
const navigate = vi.hoisted(() => vi.fn());
vi.mock("react-router-dom", () => ({ useNavigate: () => navigate }));

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

const links = { reading: "/classes/c1/readings/r1", review: "/classes/c1/readings/r1/sessions/s1" };

describe("the end of a session outside the trial", () => {
  it("says it is complete, and offers the reading and the review", async () => {
    render(<ChatPanel state={ended("complete")} onSubmit={vi.fn()} links={links} />);
    expect(screen.getByText("Session complete")).toBeInTheDocument();
    expect(screen.getByText("You passed all four steps of SEE-I.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Back to reading" }));
    expect(navigate).toHaveBeenCalledWith(links.reading);
    await userEvent.click(screen.getByRole("button", { name: "Review session" }));
    expect(navigate).toHaveBeenCalledWith(links.review);
  });

  it("does not repeat why it ended when the tries ran out", () => {
    render(<ChatPanel state={ended("fallback")} onSubmit={vi.fn()} links={links} />);
    expect(screen.getByText("Session ended")).toBeInTheDocument();
    expect(screen.queryByText(/instructor has been notified/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Back to reading" })).toBeInTheDocument();
  });
});

describe("an error outside the trial", () => {
  const failed = (error: string, answered: boolean): TutoringState => ({
    ...initialState,
    phase: "error",
    error,
    sessionId: "s1",
    messages: answered
      ? [{ key: "a", role: "student", step: "State", content: "my answer", unmet: [], streaming: false }]
      : [],
  });

  it.each([
    ["could not reach the server: TypeError", true,
      "You're not connected to the internet. Check your connection and try again."],
    ["request failed: 500", true, "Something went wrong while sending your answer."],
    ["request failed: 500", false, "Something went wrong while starting this session."],
  ] as const)("says what went wrong (%s) and offers Try again", async (error, answered, text) => {
    const onRetry = vi.fn();
    render(<ChatPanel state={failed(error, answered)} onSubmit={vi.fn()} onRetry={onRetry} />);
    expect(screen.getByRole("alert")).toHaveTextContent(text);
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("keeps the trial's strip as it was", () => {
    render(
      <ChatPanel state={failed("request failed: 500", true)} onSubmit={vi.fn()} trial={{ timeUp: false }} />,
    );
    expect(screen.getByText(/reload\s+to continue/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Try again" })).not.toBeInTheDocument();
  });
});
