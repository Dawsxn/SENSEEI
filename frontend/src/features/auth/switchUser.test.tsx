/** Switch user: offered only when the server says so, and it really switches. */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AppTopBar } from "../../components/AppTopBar";

const api = vi.hoisted(() => ({ getMe: vi.fn(), getDevUsers: vi.fn(), devLogin: vi.fn() }));

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return { ...actual, ...api };
});

function renderBar() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createMemoryRouter(
    [
      { path: "/somewhere", element: <AppTopBar /> },
      { path: "/", element: <p>Home</p> },
    ],
    { initialEntries: ["/somewhere"] },
  );
  render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

const ME = { id: "t", name: "Tester", email: "tester@dlsu.edu.ph", role: "student" as const };

describe("switch user", () => {
  it("is not offered unless the server allows it", async () => {
    api.getMe.mockResolvedValue({ ...ME, can_switch: false });
    renderBar();

    await userEvent.click(await screen.findByRole("button", { name: "Account" }));
    expect(await screen.findByText("Sign out")).toBeInTheDocument();
    expect(screen.queryByText("Switch user")).not.toBeInTheDocument();
  });

  it("switches to the chosen person and starts over from home", async () => {
    api.getMe.mockResolvedValue({ ...ME, can_switch: true });
    api.getDevUsers.mockResolvedValue([
      { id: "t", name: "Tester", email: "tester@dlsu.edu.ph", role: "student" },
      { id: "p", name: "Prof. Reyes", email: "a.reyes@dlsu.edu.ph", role: "instructor" },
    ]);
    api.devLogin.mockResolvedValue(undefined);
    renderBar();

    await userEvent.click(await screen.findByRole("button", { name: "Account" }));
    await userEvent.click(await screen.findByText("Switch user"));

    // the current person is marked and cannot be picked again
    expect(await screen.findByText("You")).toBeInTheDocument();
    await userEvent.click(screen.getByText("Prof. Reyes"));

    expect(api.devLogin).toHaveBeenLastCalledWith("p");
    expect(await screen.findByText("Home")).toBeInTheDocument();
  });
});
