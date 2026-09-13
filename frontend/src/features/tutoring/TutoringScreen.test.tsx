/** The tutoring screen's two decisions: which reading pane, and what exit does.
 *
 * jsdom has no canvas, so the PDF viewer itself cannot be rendered here and is
 * stubbed. What is worth locking is the logic in front of it — a reading with a
 * stored file gets the viewer and one without falls back to its extracted text,
 * and leaving a running session asks first while leaving a finished one does
 * not.
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ReadingDetail } from "../readings/types";
import { TutoringScreen } from "./TutoringScreen";
import { initialState, type Phase, type TutoringState } from "./useTutoringSession";

const navigate = vi.hoisted(() => vi.fn());

vi.mock("react-router-dom", async () => ({
  ...(await vi.importActual<typeof import("react-router-dom")>("react-router-dom")),
  useParams: () => ({ readingId: "r1" }),
  useNavigate: () => navigate,
}));

vi.mock("./PdfPanel", () => ({
  PdfPanel: ({ fileUrl }: { fileUrl: string }) => <div>pdf viewer: {fileUrl}</div>,
}));

const session = vi.hoisted(() => ({ state: null as unknown as TutoringState }));
const reading = vi.hoisted(() => ({ current: null as ReadingDetail | null }));

vi.mock("./useTutoringSession", async () => {
  const actual =
    await vi.importActual<typeof import("./useTutoringSession")>("./useTutoringSession");
  return {
    ...actual,
    useTutoringSession: () => ({ state: session.state, submit: vi.fn() }),
  };
});

vi.mock("../readings/useReadings", () => ({
  useReading: () => ({ data: reading.current, isLoading: false, isError: false }),
}));

const base: ReadingDetail = {
  id: "r1",
  title: "Strategy",
  description: null,
  class_name: "STRAMA K31",
  content: "the extracted text",
  core_components: [],
  has_file: true,
};

function renderScreen(detail: ReadingDetail = base, phase: Phase = "awaiting_input") {
  reading.current = detail;
  session.state = { ...initialState, phase };
  return render(
    <MemoryRouter>
      <TutoringScreen />
    </MemoryRouter>,
  );
}

beforeEach(() => navigate.mockClear());

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
  });

  it("does not ask when the session has already ended", async () => {
    // a finished session is read-only, so there is no progress to discard and
    // the confirmation would have exactly one sensible answer
    renderScreen(base, "terminal");
    await userEvent.click(screen.getByRole("button", { name: "Leave session" }));

    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(navigate).toHaveBeenCalledWith("/");
  });
});
