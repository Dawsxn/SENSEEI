/** The reading step: what it shows, and where it sends the student.
 *
 * The navigation assertions are the point. This screen exists so that no
 * session is created until the student says they have read the material, and
 * that promise is kept by one thing: Done is the only route into /tutor.
 *
 * jsdom has no canvas, so the PDF viewer is stubbed as it is for the tutoring
 * screen.
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../lib/api";
import type { ReadingDetail } from "../readings/types";
import { ReadingStepScreen } from "./ReadingStepScreen";

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
  useStartTrialClock: () => undefined,
  useTestHandoff: () => undefined,
}));
vi.mock("../trial/TrialClock", () => ({ TrialClock: () => null, useTimeUp: () => false }));
vi.mock("@tanstack/react-query", async () => ({
  ...(await vi.importActual<typeof import("@tanstack/react-query")>("@tanstack/react-query")),
  useQueryClient: () => ({ setQueryData: vi.fn() }),
}));

vi.mock("./PdfPanel", () => ({
  PdfPanel: ({ fileUrl }: { fileUrl: string }) => <div>pdf viewer: {fileUrl}</div>,
}));

const reading = vi.hoisted(() => ({
  current: null as ReadingDetail | null,
  error: null as unknown,
  refetch: vi.fn(),
}));

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
  title: "Recovery to the Bisector",
  description: null,
  class_name: "STSWENG - S11",
  class_id: "c1",
  content: "the extracted text",
  core_components: [],
  has_file: true,
};

function renderScreen(detail: ReadingDetail = base) {
  reading.current = detail;
  return render(
    <MemoryRouter>
      <ReadingStepScreen />
    </MemoryRouter>,
  );
}

const dismissIntro = () =>
  userEvent.click(screen.getByRole("button", { name: "Start" }));

beforeEach(() => {
  navigate.mockClear();
  reading.error = null;
  reading.refetch.mockClear();
  sessionStorage.clear();
});

describe("the reading step", () => {
  it("opens on the intro, and Start dismisses it", async () => {
    renderScreen();
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    await dismissIntro();

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    // dismissing the intro is not finishing the reading
    expect(navigate).not.toHaveBeenCalled();
  });

  it("shows the PDF when the reading has one", async () => {
    renderScreen();
    await dismissIntro();
    expect(screen.getByText(/pdf viewer: \/readings\/r1\/file/)).toBeInTheDocument();
  });

  it("falls back to the extracted text when it does not", async () => {
    renderScreen({ ...base, has_file: false });
    await dismissIntro();
    expect(screen.getByText("the extracted text")).toBeInTheDocument();
    expect(screen.queryByText(/pdf viewer/)).not.toBeInTheDocument();
  });

  it("enters the session only once the student presses Done and confirms", async () => {
    renderScreen();
    await dismissIntro();
    expect(navigate).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: "Done" }));
    expect(screen.getByText("Start the tutoring session?")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(navigate).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: "Done" }));
    await userEvent.click(screen.getByRole("button", { name: "Start session" }));
    expect(navigate).toHaveBeenCalledWith("/tutor/r1");
  });

  it("starts a new session from Done, not one this tab was in before", async () => {
    sessionStorage.setItem("senseei.session.r1", "old");
    renderScreen();
    await dismissIntro();
    await userEvent.click(screen.getByRole("button", { name: "Done" }));
    await userEvent.click(screen.getByRole("button", { name: "Start session" }));
    expect(sessionStorage.getItem("senseei.session.r1")).toBeNull();
  });

  it("says when the reading did not load, offers Try again, and has no Done", async () => {
    reading.error = new ApiError(500, "reading r1: 500");
    renderScreen();
    expect(screen.getByText("Couldn't load this reading.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Done" })).not.toBeInTheDocument();
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

  it("asks before going back, and stays put if the student declines", async () => {
    renderScreen();
    await dismissIntro();
    await userEvent.click(screen.getByRole("button", { name: "Back" }));

    expect(screen.getByRole("alertdialog")).toBeInTheDocument();
    expect(navigate).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: "Stay" }));
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(navigate).not.toHaveBeenCalled();
  });

  it("goes back to the reading's page once confirmed, without starting anything", async () => {
    renderScreen();
    await dismissIntro();
    await userEvent.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByText("Leave this reading?")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Leave" }));

    expect(navigate).toHaveBeenCalledWith("/classes/c1/readings/r1");
    expect(navigate).not.toHaveBeenCalledWith("/tutor/r1");
  });
});
