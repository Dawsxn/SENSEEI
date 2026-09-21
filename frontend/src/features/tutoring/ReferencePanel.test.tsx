/** The two reference panels.
 *
 * The rubric assertions are about fidelity: what the panel shows has to be the
 * requirement the server sent, character for character. A student reading a
 * tidied-up version of the rubric is reading a different standard from the one
 * the Assessment Agent applied.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ComponentsPanel, RubricPanel } from "./ReferencePanel";
import type { Rubric } from "./types";

const getRubric = vi.hoisted(() => vi.fn());

vi.mock("../../lib/api", () => ({ getRubric }));

const BREVITY =
  "The statement is concise and straight to the point. It does not contain any unnecessary filler, repetition, or tangents.";

const rubric: Rubric = {
  version: "v3",
  steps: [
    {
      step: "State",
      criteria: [
        { name: "Brevity", requirement: BREVITY },
        { name: "Clarity", requirement: "The statement is clear and precise." },
      ],
    },
    {
      step: "Elaborate",
      criteria: [{ name: "Coherence", requirement: "It hangs together." }],
    },
  ],
};

function renderWithQuery(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  getRubric.mockReset();
  getRubric.mockResolvedValue(rubric);
});

describe("the rubric panel", () => {
  it("shows the requirement exactly as the server sent it", async () => {
    renderWithQuery(<RubricPanel currentStep="State" unmet={[]} onClose={vi.fn()} />);
    expect(await screen.findByText(BREVITY)).toBeInTheDocument();
  });

  it("opens on the step the student is actually on", async () => {
    renderWithQuery(
      <RubricPanel currentStep="Elaborate" unmet={[]} onClose={vi.fn()} />,
    );
    expect(await screen.findByText("It hangs together.")).toBeInTheDocument();
    // State is the other step now, so it is collapsed to a row, not expanded
    expect(screen.queryByText(BREVITY)).not.toBeInTheDocument();
    expect(screen.getByText("State")).toBeInTheDocument();
  });

  it("explains the marking only when something was missed", async () => {
    const { unmount } = renderWithQuery(
      <RubricPanel currentStep="State" unmet={["Brevity"]} onClose={vi.fn()} />,
    );
    expect(await screen.findByText(/Red marks what your last attempt missed/)).toBeInTheDocument();
    unmount();

    renderWithQuery(<RubricPanel currentStep="State" unmet={[]} onClose={vi.fn()} />);
    await screen.findByText(BREVITY);
    expect(screen.queryByText(/Red marks/)).not.toBeInTheDocument();
  });

  it("closes on Escape", async () => {
    const onClose = vi.fn();
    renderWithQuery(<RubricPanel currentStep="State" unmet={[]} onClose={onClose} />);
    await screen.findByText(BREVITY);

    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
  });
});

describe("the components panel", () => {
  it("lists the reading's core components", () => {
    render(
      <ComponentsPanel
        components={["delegating mental tasks", "reduced effort"]}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByText("delegating mental tasks")).toBeInTheDocument();
    expect(screen.getByText("reduced effort")).toBeInTheDocument();
  });

  it("says so plainly when a reading has none", () => {
    render(<ComponentsPanel components={[]} onClose={vi.fn()} />);
    expect(screen.getByText(/no core components yet/)).toBeInTheDocument();
  });
});
