/** The student's classes, one class, and one reading in it.
 *
 * The API is stubbed at the module, so these check what each page makes of
 * the data: progress counts, the filter, the colour choice, and where things
 * lead.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { StudentClassPage } from "./StudentClassPage";
import { StudentClassesPage } from "./StudentClassesPage";
import { StudentReadingPage } from "./StudentReadingPage";

vi.mock("../../components/AppTopBar", () => ({ AppTopBar: () => null }));

const api = vi.hoisted(() => ({
  getMyClasses: vi.fn(),
  getMyClass: vi.fn(),
  getReading: vi.fn(),
  getReadingSessions: vi.fn(),
}));

vi.mock("../../lib/api", async () => ({
  ...(await vi.importActual<typeof import("../../lib/api")>("../../lib/api")),
  ...api,
}));

const STRAMA = {
  id: "c1",
  name: "STRAMA",
  section: "K31",
  label: "STRAMA K31",
  readings: [
    { id: "r1", title: "Business Model", description: "Profit formula", class_name: "STRAMA K31", status: "complete" },
    { id: "r2", title: "Strategy", description: null, class_name: "STRAMA K31", status: "failed" },
    { id: "r3", title: "Strategic Vision", description: null, class_name: "STRAMA K31", status: "not_started" },
  ],
};

function show(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createMemoryRouter(
    [
      { path: "/", element: <StudentClassesPage /> },
      { path: "/classes/:classId", element: <StudentClassPage /> },
      { path: "/classes/:classId/readings/:readingId", element: <StudentReadingPage /> },
      { path: "/read/:readingId", element: <div>reading step</div> },
      { path: "/classes/:classId/readings/:readingId/sessions/:sessionId", element: <div>review page</div> },
    ],
    { initialEntries: [path] },
  );
  render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return router;
}

beforeEach(() => localStorage.clear());

describe("the classes page", () => {
  it("shows each class with its progress, including one with no readings", async () => {
    api.getMyClasses.mockResolvedValue([
      { id: "c1", name: "STRAMA", section: "K31", label: "STRAMA K31", reading_count: 3, finished_count: 2 },
      { id: "c2", name: "CSARCH2", section: "S12", label: "CSARCH2 S12", reading_count: 0, finished_count: 0 },
    ]);
    show("/");

    expect(await screen.findByText("2 of 3 readings finished")).toBeInTheDocument();
    expect(screen.getByText("0 of 0 readings finished")).toBeInTheDocument();
    expect(screen.getByText("K31")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /STRAMA/ })).toHaveAttribute("href", "/classes/c1");
  });

  it("keeps a chosen card colour", async () => {
    api.getMyClasses.mockResolvedValue([
      { id: "c1", name: "STRAMA", section: "K31", label: "STRAMA K31", reading_count: 1, finished_count: 0 },
    ]);
    show("/");

    await userEvent.click(await screen.findByLabelText("Change the colour of STRAMA K31"));
    await userEvent.click(screen.getByRole("button", { name: "Pink" }));

    expect(localStorage.getItem("senseei.class-colour.c1")).toBe("#f9a8d4");
  });

  it("opens Join a class from beside the heading", async () => {
    api.getMyClasses.mockResolvedValue([]);
    show("/");

    expect(await screen.findByText("No classes available")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "+ Join a class" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });
});

describe("the class page", () => {
  it("counts finished readings, passed or failed, and filters by them", async () => {
    api.getMyClass.mockResolvedValue(STRAMA);
    show("/classes/c1");

    expect(await screen.findByText("2 of 3 readings finished")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /Business Model|Strategy|Strategic Vision/ })).toHaveLength(3);

    await userEvent.click(screen.getByRole("button", { name: /To do/ }));
    expect(screen.getByRole("link", { name: /Strategic Vision/ })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Business Model/ })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /Finished/ }));
    expect(screen.queryByRole("link", { name: /Strategic Vision/ })).not.toBeInTheDocument();
  });

  it("opens a reading from its row", async () => {
    api.getMyClass.mockResolvedValue(STRAMA);
    show("/classes/c1");

    expect(await screen.findByRole("link", { name: /Strategy/ })).toHaveAttribute(
      "href",
      "/classes/c1/readings/r2",
    );
  });
});

describe("the reading page", () => {
  const reading = {
    id: "r1",
    title: "Business Model",
    description: "Profit formula",
    class_name: "STRAMA K31",
    content: "",
    core_components: ["how value is created", "how profit is made"],
    has_file: false,
  };

  it("lists core components and past sessions, and starts the reading", async () => {
    api.getMyClass.mockResolvedValue(STRAMA);
    api.getReading.mockResolvedValue(reading);
    api.getReadingSessions.mockResolvedValue([
      { id: "s2", index: 2, status: "complete", started_at: "2026-11-24T02:00:00Z", ended_at: null, attempt_count: 3 },
      { id: "s1", index: 1, status: "fallback", started_at: "2026-11-13T02:00:00Z", ended_at: null, attempt_count: 6 },
    ]);
    const router = show("/classes/c1/readings/r1");

    expect(await screen.findByText("how profit is made")).toBeInTheDocument();
    const attempt = await screen.findByRole("link", { name: /Attempt 1/ });
    expect(within(attempt).getByText("Failed")).toBeInTheDocument();
    expect(attempt).toHaveAttribute("href", "/classes/c1/readings/r1/sessions/s1");

    await userEvent.click(screen.getByRole("button", { name: "Start" }));
    expect(router.state.location.pathname).toBe("/read/r1");
  });

  it("says when there are no attempts yet", async () => {
    api.getMyClass.mockResolvedValue(STRAMA);
    api.getReading.mockResolvedValue(reading);
    api.getReadingSessions.mockResolvedValue([]);
    show("/classes/c1/readings/r1");

    expect(await screen.findByText("No attempts yet")).toBeInTheDocument();
  });

  it("refuses a reading that is not in the class", async () => {
    api.getMyClass.mockResolvedValue(STRAMA);
    api.getReading.mockResolvedValue({ ...reading, id: "r9" });
    api.getReadingSessions.mockResolvedValue([]);
    show("/classes/c1/readings/r9");

    expect(await screen.findByText(/Couldn't find this reading/)).toBeInTheDocument();
  });
});
