/** The instructor's readings: the list, and what deleting one says. */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { LibraryListPage } from "./LibraryListPage";
import { deleteBody } from "./LibraryReadingPage";

const api = vi.hoisted(() => ({
  getMe: vi.fn(async () => ({ id: "p", name: "Prof", email: "p@dlsu.edu.ph", role: "instructor" })),
  getLibrary: vi.fn(),
}));
vi.mock("../../lib/api", async () => ({
  ...(await vi.importActual<typeof import("../../lib/api")>("../../lib/api")),
  ...api,
}));

function show() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createMemoryRouter([{ path: "/library", element: <LibraryListPage /> }], {
    initialEntries: ["/library"],
  });
  render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("the readings list", () => {
  it("shows two classes at most, then how many more", async () => {
    api.getLibrary.mockResolvedValue([
      { id: "r1", title: "Strategy", description: null, classes: ["STRAMA K31", "STRAMA K32", "STSWENG S11"],
        session_count: 12, created_at: "" },
      { id: "r2", title: "Recovery", description: null, classes: [], session_count: 0, created_at: "" },
    ]);
    show();
    const row = await screen.findByRole("link", { name: /Strategy/ });
    expect(row).toHaveAttribute("href", "/library/r1");
    expect(within(row).getByText("STRAMA K32")).toBeInTheDocument();
    expect(within(row).queryByText("STSWENG S11")).not.toBeInTheDocument();
    expect(within(row).getByText("+1")).toBeInTheDocument();
    expect(within(row).getByText("12 sessions")).toBeInTheDocument();
    expect(screen.getByText("Not in a class")).toBeInTheDocument();
  });

  it("says when there are none", async () => {
    api.getLibrary.mockResolvedValue([]);
    show();
    expect(await screen.findByText("No readings available")).toBeInTheDocument();
  });
});

describe("deleting a reading", () => {
  it("counts what goes with it", () => {
    expect(deleteBody(3, 12)).toBe(
      "This removes the reading from 3 classes and deletes its 12 sessions. You can't undo this.",
    );
    expect(deleteBody(1, 1)).toBe(
      "This removes the reading from 1 class and deletes its 1 session. You can't undo this.",
    );
    expect(deleteBody(2, 0)).toBe("This removes the reading from 2 classes. You can't undo this.");
    expect(deleteBody(0, 0)).toBe("You can't undo this.");
  });
});
