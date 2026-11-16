/** The sign-in screen: which one shows, and the reason a Google sign-in was
 *  refused, on the trial instance as well as the ordinary one. */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import type { AuthConfig } from "./types";
import { SignInScreen } from "./SignInScreen";

const api = vi.hoisted(() => ({ getAuthConfig: vi.fn() }));

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return { ...actual, ...api };
});

function renderAt(url: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createMemoryRouter([{ path: "/login", element: <SignInScreen /> }], {
    initialEntries: [url],
  });
  return render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

const config = (trial: boolean) =>
  ({ dev_bypass: false, trial_mode: trial }) as AuthConfig;

describe("the sign-in screen", () => {
  it("shows nothing until it knows whether this is the trial", () => {
    api.getAuthConfig.mockReturnValue(new Promise(() => {}));
    const { container } = renderAt("/login");
    expect(container).toBeEmptyDOMElement();
  });

  it("tells the trial's research team a non-DLSU account was refused", async () => {
    api.getAuthConfig.mockResolvedValue(config(true));
    renderAt("/login?error=not_dlsu");
    expect(await screen.findByText(/isn't a DLSU address/)).toBeInTheDocument();
    expect(screen.queryByText("Continue with Google")).not.toBeInTheDocument();
  });

  it("still tells the ordinary sign-in a non-DLSU account was refused", async () => {
    api.getAuthConfig.mockResolvedValue(config(false));
    renderAt("/login?error=not_dlsu");
    expect(await screen.findByText(/isn't a DLSU address/)).toBeInTheDocument();
    expect(screen.getByText("Continue with Google")).toBeInTheDocument();
  });
});
