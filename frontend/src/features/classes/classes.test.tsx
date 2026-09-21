/** The class dialogs: what they send, and what they say when it goes wrong.
 *
 * Both are forms, so both are checked by pressing Enter as well as clicking,
 * since that is how most people submit a two-field form.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

// The same module the component imports, so an error made here is the class the
// component checks for.
import { ApiError } from "../../lib/api";
import { JoinClassDialog } from "../readings/JoinClassDialog";
import { ClassFormDialog } from "./ClassFormDialog";

const joinClass = vi.hoisted(() => vi.fn());

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return { ...actual, joinClass };
});


function withQuery(ui: React.ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

// No reset between tests. Each one sets its own behaviour and checks its own call,
// and in vitest 2 resetting a mock (mockReset or mockClear) makes it report a
// rejection as unhandled even after the component has caught it.

describe("the class form", () => {
  it("shows the label students will see, and submits on Enter", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<ClassFormDialog mode="new" onSubmit={onSubmit} onCancel={vi.fn()} />);

    await userEvent.type(screen.getByLabelText("Name"), " STRAMA ");
    await userEvent.type(screen.getByLabelText("Section"), "K32{Enter}");

    expect(screen.getByText("Students see this as STRAMA K32.")).toBeInTheDocument();
    expect(onSubmit).toHaveBeenCalledWith({ name: "STRAMA", section: "K32" });
  });

  it("cannot be submitted with a field left empty", async () => {
    const onSubmit = vi.fn();
    render(<ClassFormDialog mode="new" onSubmit={onSubmit} onCancel={vi.fn()} />);

    await userEvent.type(screen.getByLabelText("Name"), "STRAMA{Enter}");

    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Create class" })).toBeDisabled();
  });

  it("names the clash when the class already exists", async () => {
    // Rejected when called, not when set up: a promise rejected ahead of time
    // counts as unhandled and fails the test before the component can catch it.
    const onSubmit = vi.fn(async () => {
      throw new ApiError(409, "dup");
    });
    render(
      <ClassFormDialog
        mode="edit"
        initial={{ name: "STRAMA", section: "K31" }}
        onSubmit={onSubmit}
        onCancel={vi.fn()}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("You already have STRAMA K31.")).toBeInTheDocument();
  });
});

describe("joining a class", () => {
  it("says what was joined, and admits when it has no readings yet", async () => {
    joinClass.mockResolvedValue({ class_id: "c1", label: "STRAMA K32", reading_count: 0 });
    withQuery(<JoinClassDialog onClose={vi.fn()} />);

    await userEvent.type(screen.getByLabelText("Join code"), "r96e rzae{Enter}");

    expect(joinClass).toHaveBeenLastCalledWith("R96E RZAE");
    expect(await screen.findByText("You joined STRAMA K32")).toBeInTheDocument();
    expect(screen.getByText(/no readings yet/)).toBeInTheDocument();
  });

  it("keeps the dialog open with an inline error for a wrong code", async () => {
    joinClass.mockImplementation(async () => {
      throw new ApiError(404, "nope");
    });
    withQuery(<JoinClassDialog onClose={vi.fn()} />);

    await userEvent.type(screen.getByLabelText("Join code"), "4KQ2-9TXN{Enter}");

    expect(await screen.findByText(/doesn.t match a class/)).toBeInTheDocument();
    expect(screen.getByLabelText("Join code")).toHaveValue("4KQ2-9TXN");
  });
});
