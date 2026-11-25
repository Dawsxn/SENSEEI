/** The tutoring screen's two decisions: which reading pane, and what exit does.
 *
 * jsdom has no canvas, so the PDF viewer itself cannot be rendered here and is
 * stubbed. What is worth locking is the logic in front of it — a reading with a
 * stored file gets the viewer and one without falls back to its extracted text,
 * and leaving a running session asks first while leaving a finished one does
 * not, by the exit or by the browser's back. Outside the trial, a reading that
 * did not load takes the screen.
 */

import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../lib/api";
import type { ReadingDetail } from "../readings/types";
import { TutoringScreen } from "./TutoringScreen";
import { initialState, type Phase, type TutoringState } from "./useTutoringSession";

const navigate = vi.hoisted(() => vi.fn());

vi.mock("react-router-dom", async () => ({
  ...(await vi.importActual<typeof import("react-router-dom")>("react-router-dom")),
  useParams: () => ({ readingId: "r1" }),
  useNavigate: () => navigate,
}));

// Not a trial participant: the trial's hooks answer as they would for a student.
vi.mock("../trial/useTrial", () => ({
  useIsParticipant: () => false,
  useTrialStatus: () => ({ data: undefined }),
  useTestHandoff: () => undefined,
}));
vi.mock("../trial/TrialClock", () => ({ TrialClock: () => null, useTimeUp: () => false }));

vi.mock("./PdfPanel", () => ({
  PdfPanel: ({ fileUrl }: { fileUrl: string }) => <div>pdf viewer: {fileUrl}</div>,
}));

const session = vi.hoisted(() => ({ state: null as unknown as TutoringState }));
const reading = vi.hoisted(() => ({
  current: null as ReadingDetail | null,
  error: null as unknown,
  refetch: vi.fn(),
}));
const api = vi.hoisted(() => ({ leaveSession: vi.fn(async () => undefined) }));
vi.mock("../../lib/api", async () => ({
  ...(await vi.importActual<typeof import("../../lib/api")>("../../lib/api")),
  ...api,
}));

vi.mock("./useTutoringSession", async () => {
  const actual =
    await vi.importActual<typeof import("./useTutoringSession")>("./useTutoringSession");
  return {
    ...actual,
    useTutoringSession: () => ({ state: session.state, submit: vi.fn(), retry: vi.fn() }),
  };
});

vi.mock("../readings/useReadings", () => ({
  useReading: () => ({
    data: reading.error ? undefined : reading.current,
    isLoading: false,
    isError: !!reading.error,
    error: reading.error,
    refetch: reading.refetch,
  }),
}));

const base: ReadingDetail = {
  id: "r1",
  title: "Strategy",
  description: null,
  class_name: "STRAMA K31",
  class_id: "c1",
  content: "the extracted text",
  core_components: [],
  has_file: true,
};

function renderScreen(detail: ReadingDetail = base, phase: Phase = "awaiting_input") {
  reading.current = detail;
  session.state = { ...initialState, phase, sessionId: "s1" };
  const router = createMemoryRouter(
    [
      { path: "/classes", element: <p>the class page</p> },
      { path: "/tutor/:readingId", element: <TutoringScreen /> },
    ],
    { initialEntries: ["/classes", "/tutor/r1"], initialIndex: 1 },
  );
  render(<RouterProvider router={router} />);
  return router;
}

beforeEach(() => {
  navigate.mockClear();
  api.leaveSession.mockClear();
  reading.error = null;
  reading.refetch.mockClear();
});

describe("the reading pane", () => {
  it("shows the PDF viewer when the reading has a stored file", async () => {
    renderScreen();
    expect(await screen.findByText(/pdf viewer: \/readings\/r1\/file/)).toBeInTheDocument();
    expect(screen.queryByText("the extracted text")).not.toBeInTheDocument();
  });

  it("falls back to the extracted text when it does not", async () => {
    renderScreen({ ...base, has_file: false });
    expect(await screen.findByText("the extracted text")).toBeInTheDocument();
    expect(screen.queryByText(/pdf viewer/)).not.toBeInTheDocument();
  });
});

describe("leaving a session", () => {
  it("asks before discarding a session that is still running", async () => {
    renderScreen(base, "awaiting_input");
    await userEvent.click(screen.getByRole("button", { name: "Leave session" }));

    expect(screen.getByRole("alertdialog")).toBeInTheDocument();
    // asking is not leaving: nothing happens until the student confirms
    expect(navigate).not.toHaveBeenCalled();
  });

  it("stays put when the student backs out", async () => {
    renderScreen(base, "awaiting_input");
    await userEvent.click(screen.getByRole("button", { name: "Leave session" }));
    await userEvent.click(screen.getByRole("button", { name: "Stay" }));

    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(navigate).not.toHaveBeenCalled();
  });

  it("returns to the reading list once the student confirms", async () => {
    renderScreen(base, "awaiting_input");
    await userEvent.click(screen.getByRole("button", { name: "Leave session" }));
    await userEvent.click(screen.getByRole("button", { name: "Leave" }));

    expect(navigate).toHaveBeenCalledWith("/");
    // kept on the server as left, rather than lingering as in progress
    expect(api.leaveSession).toHaveBeenCalledWith("s1");
  });

  it("asks the same on the browser's back, and leaves once confirmed", async () => {
    const router = renderScreen(base, "awaiting_input");
    await act(() => router.navigate(-1));
    expect(screen.getByRole("alertdialog")).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/tutor/r1");

    await userEvent.click(screen.getByRole("button", { name: "Leave" }));
    expect(api.leaveSession).toHaveBeenCalledWith("s1");
    expect(router.state.location.pathname).toBe("/classes");
  });

  it("does not ask when the session has already ended", async () => {
    // a finished session is read-only, so there is no progress to discard and
    // the confirmation would have exactly one sensible answer
    renderScreen(base, "terminal");
    await userEvent.click(screen.getByRole("button", { name: "Leave session" }));

    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(navigate).toHaveBeenCalledWith("/");
    expect(api.leaveSession).not.toHaveBeenCalled();
  });
});

describe("a reading that did not load", () => {
  it("offers to try again, with nothing else on the screen", async () => {
    reading.error = new ApiError(500, "reading r1: 500");
    renderScreen();
    expect(screen.getByText("Couldn't load this reading.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "View rubric" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(reading.refetch).toHaveBeenCalled();
  });

  it("offers the way back when the reading does not exist", async () => {
    reading.error = new ApiError(404, "reading r1: 404");
    renderScreen();
    expect(screen.getByText("This reading isn't available.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Back to classes" }));
    expect(navigate).toHaveBeenCalledWith("/");
  });
});
