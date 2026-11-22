/** The time pop-ups that stand in for a visible countdown. */
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { SESSION_NOTICES, TimeNotices } from "./TimeNotices";

describe("time pop-ups", () => {
  it("shows each point once as it is reached, until closed", async () => {
    const { rerender } = render(<TimeNotices left={20 * 60} notices={SESSION_NOTICES} />);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();

    rerender(<TimeNotices left={15 * 60} notices={SESSION_NOTICES} />);
    expect(screen.getByRole("status")).toHaveTextContent("15 minutes left");
    await userEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(screen.queryByRole("status")).not.toBeInTheDocument();

    rerender(<TimeNotices left={14 * 60} notices={SESSION_NOTICES} />);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    act(() => rerender(<TimeNotices left={60} notices={SESSION_NOTICES} />));
    // Jumping past 5 to 1 shows the most urgent, not both.
    expect(screen.getByRole("status")).toHaveTextContent("1 minute left");
  });

  it("does not show a point already passed when the screen opens", () => {
    const { rerender } = render(<TimeNotices left={4 * 60} notices={SESSION_NOTICES} />);
    rerender(<TimeNotices left={3 * 60} notices={SESSION_NOTICES} />);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});
