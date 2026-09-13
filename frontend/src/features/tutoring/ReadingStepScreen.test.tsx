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

import type { ReadingDetail } from "../readings/types";
import { ReadingStepScreen } from "./ReadingStepScreen";

const navigate = vi.hoisted(() => vi.fn());

vi.mock("react-router-dom", async () => ({
  ...(await vi.importActual<typeof import("react-router-dom")>("react-router-dom")),
  useParams: () => ({ readingId: "r1" }),
  useNavigate: () => navigate,
}));

vi.mock("./PdfPanel", () => ({
  PdfPanel: ({ fileUrl }: { fileUrl: string }) => <div>pdf viewer: {fileUrl}</div>,
}));

const reading = vi.hoisted(() => ({ current: null as ReadingDetail | null }));

vi.mock("../readings/useReadings", () => ({
  useReading: () => ({ data: reading.current, isLoading: false, isError: false }),
}));

const base: ReadingDetail = {
  id: "r1",
  title: "Recovery to the Bisector",
  description: null,
  class_name: "STSWENG - S11",
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

beforeEach(() => navigate.mockClear());

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

  it("enters the session only when the student presses Done", async () => {
    renderScreen();
    await dismissIntro();
    expect(navigate).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: "Done" }));

    expect(navigate).toHaveBeenCalledWith("/tutor/r1");
  });

  it("asks before going back, and stays put if the student declines", async () => {
    renderScreen();
    await dismissIntro();
    await userEvent.click(screen.getByRole("button", { name: /Readings/ }));

    expect(screen.getByRole("alertdialog")).toBeInTheDocument();
    expect(navigate).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: "Stay" }));
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(navigate).not.toHaveBeenCalled();
  });

  it("goes back to the reading list once confirmed, without starting anything", async () => {
    renderScreen();
    await dismissIntro();
    await userEvent.click(screen.getByRole("button", { name: /Readings/ }));
    await userEvent.click(screen.getByRole("button", { name: "Go back" }));

    expect(navigate).toHaveBeenCalledWith("/");
    expect(navigate).not.toHaveBeenCalledWith("/tutor/r1");
  });
});
