/** The trial's pre-test and post-test screens, and the grading page. */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { GradingPage } from "./GradingPage";
import { PostTestScreen, PreTestScreen } from "./TestScreens";
import type { GradingDetail, TestItem, TestView } from "./types";

const api = vi.hoisted(() => ({
  getTest: vi.fn(),
  startTest: vi.fn(),
  saveTestAnswer: vi.fn(),
  submitTest: vi.fn(),
  getGradingList: vi.fn(),
  getGrading: vi.fn(),
  setScore: vi.fn(),
}));

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return { ...actual, ...api };
});
// The grading page's top bar asks who is signed in; it is not what is tested.
vi.mock("../../components/AppTopBar", () => ({ AppTopBar: () => null }));

function renderAt(path: string, element: React.ReactNode, route = path) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createMemoryRouter(
    [
      { path: route, element },
      { path: "/", element: <p>Home</p> },
      { path: "/finished", element: <p>Finished</p> },
    ],
    { initialEntries: [path] },
  );
  render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

const pre: TestView = {
  which: "pre",
  minutes: 5,
  started: true,
  seconds_left: 240,
  strategies: [],
  strategy_list_parts: [],
  items: [
    { id: "pre", kind: "text", part: "", question: "Define a strategic offensive.", options: [], points: 3, ticked: false },
  ],
  answers: [],
};

const item = (id: string, part: string, kind: TestItem["kind"] = "text"): TestItem => ({
  id,
  kind,
  part,
  question: `Question ${id}`,
  options: kind === "choice" ? [{ key: "a", text: "First" }, { key: "b", text: "Second" }] : [],
  points: kind === "choice" ? 1 : kind === "groups" ? 0 : 2,
  ticked: part !== "D",
});

const post: TestView = {
  which: "post",
  minutes: 30,
  started: true,
  seconds_left: 1500,
  strategies: ["Cutting prices", "Moving first"],
  strategy_list_parts: ["D"],
  items: [item("q1", "A", "choice"), item("q5", "B"), item("q12a", "D", "groups"), item("q12b", "D")],
  answers: [{ item: "q5", text: "Already typed", sure: true }],
};

beforeEach(() => {
  vi.clearAllMocks();
  api.saveTestAnswer.mockResolvedValue({});
});

describe("the pre-test", () => {
  it("saves the answer as it is typed and asks before submitting", async () => {
    api.getTest.mockResolvedValue(pre);
    api.submitTest.mockResolvedValue({ test_stage: "session" });
    renderAt("/pretest", <PreTestScreen />);

    await userEvent.type(await screen.findByLabelText("Define a strategic offensive."), "A move");
    await waitFor(() =>
      expect(api.saveTestAnswer).toHaveBeenLastCalledWith("pre", "pre", { text: "A move" }),
    );
    expect(screen.getByRole("timer")).toHaveTextContent(/[34]:\d\d left/);

    await userEvent.click(screen.getByRole("button", { name: "Submit" }));
    const dialog = screen.getByRole("alertdialog");
    expect(dialog).toHaveTextContent("You can't change your answer after submitting.");
    await userEvent.click(within(dialog).getByRole("button", { name: "Submit" }));
    expect(api.submitTest).toHaveBeenCalledWith("pre");
    expect(await screen.findByText("Home")).toBeInTheDocument();
  });

  it("starts its clock when it first opens", async () => {
    api.getTest.mockResolvedValue({ ...pre, started: false, seconds_left: null });
    api.startTest.mockResolvedValue(pre);
    renderAt("/pretest", <PreTestScreen />);
    await waitFor(() => expect(api.startTest).toHaveBeenCalledWith("pre"));
  });
});

describe("the post-test", () => {
  it("waits for Start before its clock runs", async () => {
    api.getTest.mockResolvedValue({ ...post, started: false, seconds_left: null });
    api.startTest.mockResolvedValue(post);
    renderAt("/posttest", <PostTestScreen />);
    expect(await screen.findByText(/You have 30 minutes, and the reading won.t be shown\./)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Start" }));
    expect(api.startTest).toHaveBeenCalledWith("post");
    expect(await screen.findByText("Question q1")).toBeInTheDocument();
  });

  it("shows the parts, the strategy list, and what is answered", async () => {
    api.getTest.mockResolvedValue(post);
    renderAt("/posttest", <PostTestScreen />);

    expect(await screen.findByRole("heading", { name: "Part D" })).toBeInTheDocument();
    expect(screen.getByText(/Cutting prices/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Question 5, answered" })).toBeInTheDocument();
    expect(screen.getByText("1 of 3 answered")).toBeInTheDocument();

    await userEvent.click(screen.getByLabelText(/a\. First/));
    await waitFor(() =>
      expect(api.saveTestAnswer).toHaveBeenCalledWith("post", "q1", { choice: "a" }),
    );
    expect(screen.getByRole("button", { name: "Question 1, answered" })).toBeInTheDocument();
    expect(screen.getByLabelText(/I.m sure/, { selector: "input[name='q5-sure']" })).toBeChecked();
  });

  it("says how many questions are blank before submitting", async () => {
    api.getTest.mockResolvedValue(post);
    api.submitTest.mockResolvedValue({ test_stage: "done" });
    renderAt("/posttest", <PostTestScreen />);

    await userEvent.click((await screen.findAllByRole("button", { name: "Submit" }))[0]);
    const dialog = screen.getByRole("alertdialog");
    expect(dialog).toHaveTextContent(
      "2 questions have no answer, and you can't change your answers after submitting.",
    );
    await userEvent.click(within(dialog).getByRole("button", { name: "Submit" }));
    expect(api.submitTest).toHaveBeenCalledWith("post");
    expect(await screen.findByText("Finished")).toBeInTheDocument();
  });
});

describe("grading", () => {
  const detail: GradingDetail = {
    code: "P-7K3Q-9TXM",
    posttest_ended: true,
    left: 1,
    pretest_score: 1,
    posttest_total: null,
    calibration: null,
    sure_but_wrong: null,
    choices: [{ item: "q1", choice: "b", answer: "a", correct: false, sure: true }],
    groups: null,
    written: [
      {
        test: "pre",
        item: "pre",
        question: "Define a strategic offensive.",
        text: "A move",
        sure: null,
        score: 1,
        points: 3,
        reference: "An aggressive move.",
        criteria: [{ points: 3, text: "Complete and accurate." }],
      },
      {
        test: "post",
        item: "q5",
        question: "How does the rule help?",
        text: "",
        sure: false,
        score: null,
        points: 2,
        reference: "Strength meets weakness.",
        criteria: [
          { points: 2, text: "Explains the link." },
          { points: 1, text: "States it." },
          { points: 0, text: "No link." },
        ],
      },
    ],
  };

  it("shows a participant by ID, with scores, ticks and the rubric, and saves a score", async () => {
    api.getGradingList.mockResolvedValue([{ code: "P-7K3Q-9TXM", left: 1, posttest_ended: true }]);
    api.getGrading.mockResolvedValue(detail);
    api.setScore.mockResolvedValue({ ...detail, left: 0 });
    renderAt("/grading", <GradingPage />);

    expect(await screen.findByText("1 left")).toBeInTheDocument();
    expect(await screen.findByText("Picked b · Answer is a")).toBeInTheDocument();
    expect(screen.getByText("1 / 3")).toBeInTheDocument();
    expect(screen.getAllByText("Not graded yet")).toHaveLength(2);
    expect(screen.getByText("No answer")).toBeInTheDocument();
    // The rubric follows the first answer still to grade.
    expect(screen.getByText("Strength meets weakness.")).toBeInTheDocument();

    const q5 = screen.getByText("How does the rule help?").closest("div[class*='rounded-lg']") as HTMLElement;
    await userEvent.click(within(q5).getByRole("button", { name: "Score 0" }));
    expect(api.setScore).toHaveBeenCalledWith("P-7K3Q-9TXM", "post", "q5", 0);
  });
});
