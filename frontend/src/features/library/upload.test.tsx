/** The upload flow: what it sends, what it keeps, and when it asks first.
 *
 * Rendered under a memory data router, because the leave guard only works
 * under a data router and is part of what is tested.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../../lib/api";
import { UploadReadingPage, titleFromFilename } from "./UploadReadingPage";

const api = vi.hoisted(() => ({
  extractReading: vi.fn(),
  createReading: vi.fn(),
  getClasses: vi.fn(),
  getMe: vi.fn(),
}));

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return { ...actual, ...api };
});

// The viewer pulls in pdf.js, which jsdom cannot run and this test does not need.
vi.mock("../tutoring/PdfPanel", () => ({ PdfPanel: () => <div>pdf</div> }));

api.getClasses.mockResolvedValue([
  { id: "k31", label: "STRAMA K31", name: "STRAMA", section: "K31", join_code: "", student_count: 0, reading_count: 0 },
]);
api.getMe.mockResolvedValue({ id: "p", name: "Prof", email: "p@dlsu.edu.ph", role: "instructor" });
URL.createObjectURL = vi.fn(() => "blob:pdf");
URL.revokeObjectURL = vi.fn();

function renderUpload() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createMemoryRouter(
    [
      { path: "/library/new", element: <UploadReadingPage /> },
      { path: "/library", element: <p>Readings list</p> },
      { path: "/library/:id", element: <p>Saved reading</p> },
    ],
    { initialEntries: ["/library/new"] },
  );
  render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return router;
}

const pdf = () => new File(["%PDF-1.4"], "porters-five-forces.pdf", { type: "application/pdf" });

describe("a title from the filename", () => {
  it("turns the file's name into words", () => {
    expect(titleFromFilename("porters-five-forces.pdf")).toBe("Porters Five Forces");
    expect(titleFromFilename("chapter_3  notes.PDF")).toBe("Chapter 3 Notes");
    expect(titleFromFilename("the-recovery-to-the-bisector.pdf")).toBe("The Recovery to the Bisector");
  });
});

describe("uploading a reading", () => {
  it("sends the text as corrected, with its components and classes", async () => {
    api.extractReading.mockResolvedValue({
      text: "Extracted text.\n\n[Figure 1: Five boxes.]",
      figures_described: 1,
      figures_failed: false,
    });
    api.createReading.mockResolvedValue({ id: "r1" });
    renderUpload();

    await userEvent.upload(screen.getByLabelText("PDF file"), pdf());
    expect(screen.getByLabelText("Title")).toHaveValue("Porters Five Forces");
    await userEvent.click(screen.getByRole("button", { name: "Next" }));

    const text = await screen.findByLabelText("Reading text");
    expect(screen.getByText("1 figure described. Please verify.")).toBeInTheDocument();
    await userEvent.type(text, " Fixed.");
    await userEvent.click(screen.getByRole("button", { name: "Next" }));

    const save = screen.getByRole("button", { name: "Save reading" });
    expect(save).toBeDisabled();
    expect(screen.getByText(/Students won.t see this/)).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Core component 1"), "Five forces shape profit.");
    await userEvent.click(await screen.findByLabelText("STRAMA K31"));
    await userEvent.click(save);

    expect(api.createReading).toHaveBeenLastCalledWith(
      expect.objectContaining({
        title: "Porters Five Forces",
        content: "Extracted text.\n\n[Figure 1: Five boxes.] Fixed.",
        coreComponents: ["Five forces shape profit."],
        classIds: ["k31"],
      }),
    );
    expect(await screen.findByText("Saved reading")).toBeInTheDocument();
  });

  it("keeps the instructor's edits when they go back and forward again", async () => {
    api.extractReading.mockResolvedValue({ text: "Original.", figures_described: 0, figures_failed: false });
    // Mocks are not reset between tests (see classes.test.tsx), so count from here.
    const before = api.extractReading.mock.calls.length;
    renderUpload();

    await userEvent.upload(screen.getByLabelText("PDF file"), pdf());
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    await userEvent.type(await screen.findByLabelText("Reading text"), " Edited.");
    await userEvent.click(screen.getByRole("button", { name: "Back" }));
    await userEvent.click(screen.getByRole("button", { name: "Next" }));

    expect(await screen.findByLabelText("Reading text")).toHaveValue("Original. Edited.");
    expect(api.extractReading.mock.calls.length - before).toBe(1);
  });

  it("says when a PDF has no text, and asks for another", async () => {
    api.extractReading.mockImplementation(async () => {
      throw new ApiError(422, "no text", "no_text");
    });
    renderUpload();

    await userEvent.upload(screen.getByLabelText("PDF file"), pdf());
    await userEvent.click(screen.getByRole("button", { name: "Next" }));

    expect(
      await screen.findByText("No text found. The PDF may be a scanned image."),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("PDF file")).toBeInTheDocument();
  });

  it("says when the figures could not be described", async () => {
    api.extractReading.mockResolvedValue({ text: "Text.", figures_described: 0, figures_failed: true });
    renderUpload();

    await userEvent.upload(screen.getByLabelText("PDF file"), pdf());
    await userEvent.click(screen.getByRole("button", { name: "Next" }));

    expect(
      await screen.findByText("Couldn't describe the figures. Add them by hand if needed."),
    ).toBeInTheDocument();
  });

  it("asks before leaving with a file chosen, and stays if told to", async () => {
    const router = renderUpload();

    await userEvent.upload(screen.getByLabelText("PDF file"), pdf());
    await userEvent.click(screen.getByRole("button", { name: "Readings" }));
    expect(screen.getByText("Leave this upload?")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Stay" }));
    expect(router.state.location.pathname).toBe("/library/new");

    await userEvent.click(screen.getByRole("button", { name: "Readings" }));
    await userEvent.click(screen.getByRole("button", { name: "Leave" }));
    expect(await screen.findByText("Readings list")).toBeInTheDocument();
  });

  it("leaves without asking when nothing has been chosen", async () => {
    renderUpload();
    await userEvent.click(screen.getByRole("button", { name: "Readings" }));
    expect(await screen.findByText("Readings list")).toBeInTheDocument();
  });
});
