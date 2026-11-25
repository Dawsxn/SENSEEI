/** An unknown address and a crash each get a plain screen with a way home,
 *  rather than React Router's developer page. */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { NotFoundPage, RouteErrorPage } from "./ErrorPages";

vi.mock("../../components/AppTopBar", () => ({ AppTopBar: () => <header>top bar</header> }));

function Boom(): never {
  throw new Error("render failed");
}

function show(path: string) {
  const router = createMemoryRouter(
    [
      {
        errorElement: <RouteErrorPage />,
        children: [
          { path: "/", element: <p>home</p> },
          { path: "/boom", element: <Boom /> },
          { path: "*", element: <NotFoundPage /> },
        ],
      },
    ],
    { initialEntries: [path] },
  );
  render(<RouterProvider router={router} />);
  return router;
}

describe("a page that isn't there", () => {
  it("says so, and goes back to the classes", async () => {
    const router = show("/nowhere");
    expect(screen.getByRole("heading", { name: "Page not found" })).toBeInTheDocument();
    expect(
      screen.getByText("This page doesn't exist. Check the link, or go back to your classes."),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Back to classes" }));
    expect(router.state.location.pathname).toBe("/");
  });
});

describe("a page that crashed", () => {
  it("says something went wrong, and offers a reload", () => {
    // React logs the error it caught; that is expected here.
    const quiet = vi.spyOn(console, "error").mockImplementation(() => {});
    show("/boom");
    quiet.mockRestore();
    expect(screen.getByRole("heading", { name: "Something went wrong" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reload page" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Back to classes" })).toBeInTheDocument();
    expect(screen.queryByText(/Hey developer/)).not.toBeInTheDocument();
  });
});
