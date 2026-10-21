/** Withdrawing a participant: it asks first, names the ID, and says when the ID
 *  does not exist. */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../../lib/api";
import { WithdrawCard } from "./WithdrawCard";

const api = vi.hoisted(() => ({ withdrawParticipant: vi.fn() }));

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return { ...actual, ...api };
});

function renderCard() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <WithdrawCard />
    </QueryClientProvider>,
  );
}

describe("withdrawing a participant", () => {
  it("asks first, then deletes the ID it named", async () => {
    api.withdrawParticipant.mockResolvedValueOnce(undefined);
    renderCard();
    await userEvent.type(screen.getByLabelText("Participant ID to withdraw"), "p-7k3q-9txm{Enter}");
    expect(api.withdrawParticipant).not.toHaveBeenCalled();
    expect(screen.getByText("Delete P-7K3Q-9TXM?")).toBeInTheDocument();
    await userEvent.click(screen.getAllByRole("button", { name: "Delete" }).at(-1)!);
    expect(api.withdrawParticipant).toHaveBeenCalledWith("P-7K3Q-9TXM");
    expect(await screen.findByText("Deleted P-7K3Q-9TXM.")).toBeInTheDocument();
  });

  it("says when the ID does not exist", async () => {
    api.withdrawParticipant.mockRejectedValueOnce(new ApiError(404, "no"));
    renderCard();
    await userEvent.type(screen.getByLabelText("Participant ID to withdraw"), "P-2222-2222{Enter}");
    await userEvent.click(screen.getAllByRole("button", { name: "Delete" }).at(-1)!);
    expect(await screen.findByText("That ID doesn't exist.")).toBeInTheDocument();
  });
});
