/** "Before you start": what may close it, since closing it starts a participant's clock. */
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ReadingIntroDialog } from "./ReadingIntroDialog";

const overlay = () => screen.getByRole("dialog").parentElement as HTMLElement;

describe("Before you start", () => {
  it("on the trial, starts only from the Start button", async () => {
    const onStart = vi.fn();
    render(<ReadingIntroDialog onStart={onStart} startOnly />);
    fireEvent.mouseDown(overlay());
    fireEvent.click(overlay());
    await userEvent.keyboard("{Escape}");
    expect(onStart).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Start" }));
    expect(onStart).toHaveBeenCalledOnce();
  });

  it("doesn't close when text is selected and the mouse is let go outside the box", () => {
    const onStart = vi.fn();
    render(<ReadingIntroDialog onStart={onStart} body="The goal of this session is to understand the concept: strategy." />);
    // The press begins on the text inside the box and ends on the overlay.
    fireEvent.mouseDown(screen.getByText(/The goal of this session/));
    fireEvent.click(overlay());
    expect(onStart).not.toHaveBeenCalled();
    // A real click on the overlay still closes it outside the trial.
    fireEvent.mouseDown(overlay());
    fireEvent.click(overlay());
    expect(onStart).toHaveBeenCalledOnce();
  });
});
