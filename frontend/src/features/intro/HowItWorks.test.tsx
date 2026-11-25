/** The SEE-I walkthrough: three screens, then on into the reading the first
 *  time, or back where the student was from the help icon. */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { HowItWorks } from "./HowItWorks";

const api = vi.hoisted(() => ({
  markIntroSeen: vi.fn(async () => undefined),
  getRubric: vi.fn(async () => ({
    version: "v3",
    steps: [{ step: "State", criteria: [{ name: "Brevity", requirement: "The statement is concise." }] }],
  })),
}));
vi.mock("../../lib/api", async () => ({
  ...(await vi.importActual<typeof import("../../lib/api")>("../../lib/api")),
  ...api,
}));
const me = vi.hoisted(() => ({ seen_intro: false }));
vi.mock("../auth/useAuth", () => ({
  useMe: () => ({ data: { id: "u", name: "S", email: "s@dlsu.edu.ph", role: "student", ...me } }),
}));

function show(entries: string[]) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createMemoryRouter(
    [
      { path: "/how-it-works", element: <HowItWorks /> },
      { path: "/read/:id", element: <p>reading step</p> },
      { path: "/classes/:id", element: <p>class page</p> },
    ],
    { initialEntries: entries, initialIndex: entries.length - 1 },
  );
  render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return router;
}

const forward = async (name = "Continue") =>
  userEvent.click(screen.getByRole("button", { name }));

beforeEach(() => {
  me.seen_intro = false;
  api.markIntroSeen.mockClear();
});

describe("the walkthrough", () => {
  it("runs the three screens before a first session, then goes on to the reading", async () => {
    const router = show(["/how-it-works?next=%2Fread%2Fr1"]);

    expect(screen.getByRole("heading", { name: "How SEE-I works" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Close" })).not.toBeInTheDocument();
    await forward();
    expect(screen.getByRole("heading", { name: "How a session works" })).toBeInTheDocument();
    await forward();
    expect(screen.getByRole("heading", { name: "Core components and the rubric" })).toBeInTheDocument();
    expect(await screen.findByText("The statement is concise.")).toBeInTheDocument();

    await forward();
    expect(api.markIntroSeen).toHaveBeenCalledOnce();
    expect(router.state.location.pathname).toBe("/read/r1");
  });

  it("goes back a screen", async () => {
    show(["/how-it-works?next=%2Fread%2Fr1"]);
    await forward();
    await forward("Back");
    expect(screen.getByRole("heading", { name: "How SEE-I works" })).toBeInTheDocument();
  });

  it("from the help icon, closes back to where the student was", async () => {
    me.seen_intro = true;
    const router = show(["/classes/c1", "/how-it-works"]);

    await userEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(router.state.location.pathname).toBe("/classes/c1");
    // already seen, so nothing to record
    expect(api.markIntroSeen).not.toHaveBeenCalled();
  });

  it("ends with Done when opened from the help icon", async () => {
    me.seen_intro = true;
    const router = show(["/classes/c1", "/how-it-works"]);
    await forward();
    await forward();
    await forward("Done");
    expect(router.state.location.pathname).toBe("/classes/c1");
  });

  it("follows only a path inside the app", async () => {
    const router = show(["/classes/c1", "/how-it-works?next=https%3A%2F%2Fexample.com"]);
    await userEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(router.state.location.pathname).toBe("/classes/c1");
  });
});
