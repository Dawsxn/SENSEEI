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
  getTrialStatus: vi.fn(),
  getReading: vi.fn(),
  getMe: vi.fn(),
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
  part_intros: {},
  items: [
    {
      id: "pre", kind: "text", part: "", question: "Define a strategic offensive.", options: [],
      statements: [], steps: [], lock_first: false, points: 3, ticked: false,
    },
  ],
  answers: [],
};

const item = (id: string, part: string, kind: TestItem["kind"] = "text"): TestItem => ({
  id,
  kind,
  part,
  question: `Question ${id}`,
  options: [],
  statements:
    kind === "truefalse"
      ? [{ key: "a", text: "First statement" }, { key: "b", text: "Second statement" }]
      : [],
  steps:
    kind === "steps"
      ? [{ key: "a", prompt: "Write a checklist." }, { key: "b", prompt: "Use it." }, { key: "c", prompt: "Check it." }]
      : [],
  lock_first: kind === "steps",
  points: kind === "truefalse" ? 2 : 3,
  ticked: part !== "D",
});

const post: TestView = {
  which: "post",
  minutes: 30,
  started: true,
  seconds_left: 1500,
  part_intros: { A: "For each statement, choose True or False." },
  items: [item("q1", "A", "truefalse"), item("q5", "B"), item("q8", "D", "steps")],
  answers: [{ item: "q5", text: "Already typed", sure: true }],
};

beforeEach(() => {
  vi.clearAllMocks();
  api.saveTestAnswer.mockResolvedValue({});
  api.getTrialStatus.mockResolvedValue({
    code: "P-7K3Q-9TXM", mode: "seei", done: false, reading_id: "r1", minutes: 35,
    seconds_left: null, time_up: false, session: null, test_stage: "pretest",
    test_minutes: { pre: 5, post: 30 },
  });
  api.getReading.mockResolvedValue({ id: "r1", title: "Strategic Offensives" });
  api.getMe.mockRejectedValue(new Error("not signed in"));
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
    // No countdown is shown, only pop-ups as time runs low.
    expect(screen.queryByRole("timer")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Submit" }));
    const dialog = screen.getByRole("alertdialog");
    expect(dialog).toHaveTextContent("You can't change your answer after submitting.");
    await userEvent.click(within(dialog).getByRole("button", { name: "Submit" }));
    expect(api.submitTest).toHaveBeenCalledWith("pre");
    expect(await screen.findByText("Home")).toBeInTheDocument();
  });

  it("waits for Start before its clock runs", async () => {
    api.getTest.mockResolvedValue({ ...pre, started: false, seconds_left: null });
    api.startTest.mockResolvedValue(pre);
    api.getMe.mockResolvedValue({ id: "u1", name: "P-7K3Q-9TXM", role: "student", participant: true });
    renderAt("/pretest", <PreTestScreen />);
    // Every group's welcome first, with their steps and times.
    expect(await screen.findByText("Good day!")).toBeInTheDocument();
    const steps = screen.getByRole("list", { name: "Your steps" });
    expect(steps).toHaveTextContent("About SENSEE-I");
    expect(steps).toHaveTextContent("Reading and tutoring session35 min");
    expect(screen.getByText("70 minutes in total")).toBeInTheDocument();
    // The group is named, plainly, as the consent form names it.
    expect(screen.getByText("SENSEE-I group")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(await screen.findByText("You have 5 minutes.")).toBeInTheDocument();
    expect(await screen.findByText(/already know about strategic offensives/)).toBeInTheDocument();
    expect(api.startTest).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Start" }));
    expect(api.startTest).toHaveBeenCalledWith("pre");
  });
});

describe("the post-test", () => {
  it("waits for Start before its clock runs", async () => {
    api.getTest.mockResolvedValue({ ...post, started: false, seconds_left: null });
    api.startTest.mockResolvedValue(post);
    api.getMe.mockResolvedValue({ id: "u1", name: "P-7K3Q-9TXM", role: "student", participant: true });
    renderAt("/posttest", <PostTestScreen />);
    expect(await screen.findByText("You have 30 minutes.")).toBeInTheDocument();
    expect(screen.getByText(/Only choose .Yes, I.m sure. if you expect full marks/)).toBeInTheDocument();
    expect(screen.getByText(/as the reading describes them/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Start" }));
    expect(api.startTest).toHaveBeenCalledWith("post");
    expect(await screen.findByText("Question q1")).toBeInTheDocument();
  });

  it("shows the parts, marks true/false statements, and what is answered", async () => {
    api.getTest.mockResolvedValue(post);
    renderAt("/posttest", <PostTestScreen />);

    expect(await screen.findByRole("heading", { name: "Part D" })).toBeInTheDocument();
    expect(screen.getByText("For each statement, choose True or False.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Question 5, answered" })).toBeInTheDocument();
    expect(screen.getByText("1 of 3 answered")).toBeInTheDocument();

    // Each statement is marked on its own, and the whole set is sent.
    const a = screen.getByRole("radiogroup", { name: "Statement a" });
    await userEvent.click(within(a).getByLabelText("True"));
    const b = screen.getByRole("radiogroup", { name: "Statement b" });
    await userEvent.click(within(b).getByLabelText("False"));
    await waitFor(() =>
      expect(api.saveTestAnswer).toHaveBeenLastCalledWith("post", "q1", { parts: { a: true, b: false } }),
    );
    // Answered but not yet ticked: the tick is required.
    expect(screen.getByRole("button", { name: "Question 1, needs how sure" })).toBeInTheDocument();
    expect(screen.getByText("Required")).toBeInTheDocument();
    await userEvent.click(screen.getByLabelText(/No, I.m not sure/, { selector: "input[name='q1-sure']" }));
    expect(screen.getByRole("button", { name: "Question 1, answered" })).toBeInTheDocument();
    expect(screen.queryByText("Required")).not.toBeInTheDocument();
    expect(screen.getByLabelText(/Yes, I.m sure/, { selector: "input[name='q5-sure']" })).toBeChecked();
  });

  it("locks the first part of a question in steps once a later part is started", async () => {
    api.getTest.mockResolvedValue(post);
    renderAt("/posttest", <PostTestScreen />);

    const first = await screen.findByLabelText("Answer to question 8, part a");
    await userEvent.type(first, "Does a rival lose?");
    expect(first).toBeEnabled();
    await userEvent.type(screen.getByLabelText("Answer to question 8, part b"), "No.");
    expect(first).toBeDisabled();
    expect(screen.getByText(/Locked, since you.ve started part \(b\)/)).toBeInTheDocument();
  });

  it("asks for the ticks on answered questions before submitting, not on blank ones", async () => {
    Element.prototype.scrollIntoView = vi.fn();
    api.getTest.mockResolvedValue({
      ...post,
      answers: [{ item: "q5", text: "Typed, no tick" }],
    });
    api.submitTest.mockResolvedValue({ test_stage: "done" });
    renderAt("/posttest", <PostTestScreen />);

    await userEvent.click((await screen.findAllByRole("button", { name: "Submit" }))[0]);
    const ask = screen.getByRole("alertdialog");
    expect(ask).toHaveTextContent("Choose Yes or No under every question you answered.");
    await userEvent.click(within(ask).getByRole("button", { name: "Show me" }));
    expect(Element.prototype.scrollIntoView).toHaveBeenCalled();
    expect(api.submitTest).not.toHaveBeenCalled();

    await userEvent.click(screen.getByLabelText(/Yes, I.m sure/, { selector: "input[name='q5-sure']" }));
    await userEvent.click(screen.getAllByRole("button", { name: "Submit" })[0]);
    // q1 and q8 are blank, so they need no tick: straight to the usual confirmation.
    expect(screen.getByRole("alertdialog")).toHaveTextContent("2 questions have no answer");
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
    choices: [],
    sets: [
      {
        item: "q1",
        question: "Which of these are true of a strategic offensive?",
        sure: true,
        score: 1,
        points: 2,
        statements: [
          { key: "a", text: "It takes from rivals.", answer: true, picked: true },
          { key: "b", text: "Any growth counts.", answer: false, picked: null },
        ],
      },
    ],
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
        points: 3,
        reference: "Strength meets weakness.",
        criteria: [
          { points: 3, text: "Explains the link and the goal." },
          { points: 2, text: "Explains the link." },
          { points: 1, text: "States it." },
          { points: 0, text: "No link." },
        ],
      },
    ],
  };

  it("shows a participant by ID, with scores, ticks and the rubric, and saves a score", async () => {
    api.getGradingList.mockResolvedValue([
      { code: "P-7K3Q-9TXM", left: 1, posttest_ended: true, batch_id: "b1", batch_name: "Sitting 1" },
    ]);
    api.getGrading.mockResolvedValue(detail);
    api.setScore.mockResolvedValue({ ...detail, left: 0 });
    renderAt("/grading", <GradingPage />);

    expect(await screen.findByText("1 left")).toBeInTheDocument();
    // A true/false set: each statement, what they marked, and the key.
    expect(await screen.findByText("True · Correct")).toBeInTheDocument();
    expect(screen.getByText("Blank · Answer is False")).toBeInTheDocument();
    expect(screen.getByText("1 / 3")).toBeInTheDocument();
    expect(screen.getAllByText("Not graded yet")).toHaveLength(2);
    expect(screen.getByText("No answer")).toBeInTheDocument();
    // The rubric follows the first answer still to grade.
    expect(screen.getByText("Strength meets weakness.")).toBeInTheDocument();

    const q5 = screen.getByText("How does the rule help?").closest("div[class*='rounded-lg']") as HTMLElement;
    await userEvent.click(within(q5).getByRole("button", { name: "Score 0" }));
    expect(api.setScore).toHaveBeenCalledWith("P-7K3Q-9TXM", "post", "q5", 0);
  });

  it("shows one batch at a time, so a dry run can be left out", async () => {
    api.getGradingList.mockResolvedValue([
      { code: "P-DRYR-UN01", left: 6, posttest_ended: true, batch_id: "dry", batch_name: "Dry run" },
      { code: "P-7K3Q-9TXM", left: 1, posttest_ended: true, batch_id: "s1", batch_name: "Sitting 1" },
    ]);
    api.getGrading.mockResolvedValue(detail);
    renderAt("/grading", <GradingPage />);

    expect(await screen.findByText("P-DRYR-UN01")).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Batch"), "Sitting 1");
    expect(screen.queryByText("P-DRYR-UN01")).not.toBeInTheDocument();
    expect(screen.getAllByText("P-7K3Q-9TXM").length).toBeGreaterThan(0);
    expect(screen.getByText("0 of 1 participants graded")).toBeInTheDocument();
  });
});
