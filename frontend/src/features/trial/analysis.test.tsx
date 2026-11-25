/** The Analysis tab: the group comparison in full, the distributions, a batch at
 *  a time, only Finished IDs counted, and leaving an ID out by unticking it. */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AnalysisPage } from "./AnalysisPage";
import type { Analysis, AnalysisParticipant, AnalysisRow } from "./types";

vi.mock("../../components/AppTopBar", () => ({ AppTopBar: () => null }));
const api = vi.hoisted(() => ({ getAnalysis: vi.fn() }));
vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return { ...actual, ...api };
});

const person = (
  code: string,
  group: AnalysisParticipant["group"],
  { finished = true, flags = [] as string[] } = {},
): AnalysisParticipant => ({
  code, batch: "Sitting 1", group, finished, excluded: false, voided: false,
  status: group === "seei" ? "complete" : null, last_step: null, completed: group === "seei" ? true : null,
  pretest_score: 1, posttest_total: 18, posttest_max: 30, calibration: 0.5, sure_but_wrong: 2,
  pretest_minutes: 2, posttest_minutes: 20, pretest_ended_by: "submitted", posttest_ended_by: "submitted",
  reading_minutes: null, session_minutes: null, total_minutes: 25, minutes_to_done: null,
  turns: group === "seei" ? 8 : null, chat_questions: null, chat_words: null,
  pastes: 0, paste_chars: 0, test_pastes: code === "P-CHAT-0001" ? 1 : 0, test_tab_left: 0,
  thinking_seconds: null, turn_failed: 0, flags,
});

const stat = (key: string, label: string, measure: string, values: AnalysisRow["values"], format: AnalysisRow["format"] = "number"): AnalysisRow =>
  ({ key, label, format, section: "scores", measure, values });

function analysis(exclude: string[] = []): Analysis {
  const people = [
    person("P-SEEI-0001", "seei"),
    person("P-CHAT-0001", "chatbot", { flags: ["Pasted during a test"] }),
    person("P-READ-0001", "reading_only", { finished: false, flags: ["Not finished"] }),
  ].map((p) => ({ ...p, excluded: exclude.includes(p.code) }));
  const columns = [
    { key: "chatbot", label: "Chatbot", n: exclude.includes("P-CHAT-0001") ? 0 : 1 },
    { key: "reading_only", label: "Reading only", n: 0 },
    { key: "seei", label: "SEE-I all", n: 1 },
    { key: "seei_completed", label: "SEE-I completed", n: 1 },
    { key: "seei_not_completed", label: "SEE-I not completed", n: 0 },
  ];
  const post = "Post-test score (out of 30)";
  return {
    batches: [{ id: "b1", name: "Sitting 1" }, { id: "b2", name: "Dry run" }],
    batch_id: null,
    used: 3,
    unused: 3,
    finished: 2,
    included: 2 - exclude.length,
    comparison: {
      columns,
      posttest_max: 30,
      rows: [
        stat("posttest_total_mean", "Mean", post, { chatbot: exclude.length ? null : 14.6, reading_only: null, seei: 16.25, seei_completed: 15, seei_not_completed: null }),
        stat("posttest_total_sd", "SD", post, { chatbot: 4.71, reading_only: null, seei: 2.94, seei_completed: null, seei_not_completed: null }),
        stat("posttest_total_range", "Range", post, { chatbot: [7, 19], reading_only: null, seei: [12, 19], seei_completed: [12, 18], seei_not_completed: null }),
        stat("calibration_mean", "Mean", "Calibration", { chatbot: 0.444, reading_only: null, seei: 0.36, seei_completed: 0.214, seei_not_completed: null }, "share"),
        stat("calibration_range", "Range", "Calibration", { chatbot: [0.29, 0.6], reading_only: null, seei: null, seei_completed: null, seei_not_completed: null }, "share"),
        stat("sure_but_wrong_mean", "Mean", "Sure but wrong", { chatbot: 3.5, reading_only: null, seei: 4.14, seei_completed: 5.5, seei_not_completed: 3.6 }),
        stat("posttest_minutes_mean", "Mean", "Post-test time", { chatbot: 28.1, reading_only: null, seei: 22.9, seei_completed: 19.8, seei_not_completed: 24.1 }, "minutes"),
      ],
      distributions: [
        {
          key: "posttest_total", label: "Post-test score", format: "number", low: 0, high: 30,
          series: {
            chatbot: { values: [7, 12, 19], mean: 12.67, sd: 6.03 },
            reading_only: { values: [], mean: null, sd: null },
            seei: { values: [16], mean: 16, sd: null },
          },
        },
      ],
    },
    seei: {
      sessions: [], steps: [], criteria: [], fixes: [],
      fixed_overall: { criterion: "All", failed: 0, fixed: 0, rate: null },
    },
    participants: people,
  };
}

/** The Descriptive statistics card's table. */
async function statsTable(): Promise<HTMLElement> {
  const card = (await screen.findByText("Descriptive statistics")).closest("section")!;
  return card.querySelector("table")!;
}

function renderPage(path = "/analysis") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <AnalysisPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("the Analysis tab", () => {
  beforeEach(() => {
    api.getAnalysis.mockReset();
    api.getAnalysis.mockImplementation(async (_batch: string | null, exclude: string[]) => analysis(exclude));
  });

  it("describes every measure in full, grouped under its name, with each column's size", async () => {
    renderPage();
    const table = await statsTable();
    expect(within(table).getByText("Calibration")).toBeInTheDocument();
    expect(within(table).getAllByText("SD")).toHaveLength(1);
    expect(within(table).getByText("SEE-I not completed")).toBeInTheDocument();
    expect(within(table).getAllByText("n = 1")).toHaveLength(3);
    expect(within(table).getByText("16.25")).toBeInTheDocument();
    expect(within(table).getByText("44%")).toBeInTheDocument();
    // Each end of a range in the measure's own format.
    expect(within(table).getByText("7–19")).toBeInTheDocument();
    expect(within(table).getByText("29%–60%")).toBeInTheDocument();
  });

  it("marks the best of the three groups in green on mean rows, and never on SD or range", async () => {
    renderPage();
    const table = await statsTable();
    const best = (text: string) => within(table).getByText(text).closest("td")!.getAttribute("title");
    // Post-test mean: SEE-I 16.25 over Chatbot 14.6. Calibration: Chatbot 44% over SEE-I 36%.
    expect(best("16.25")).toMatch(/^Best of .* \(highest\)$/);
    expect(best("44%")).toMatch(/\(highest\)$/);
    expect(within(table).getByText("16.25")).toHaveClass("text-[#15803d]");
    expect(best("14.6")).toBeNull();
    // Sure but wrong: lower is better, so Chatbot's 3.5 is best, not SEE-I's 4.14.
    expect(best("3.5")).toMatch(/\(lowest\)$/);
    expect(best("4.14")).toBeNull();
    expect(within(table).getByText(/lower is better/)).toBeInTheDocument();
    // Time has no better direction, so neither 28.1 nor 22.9 minutes is marked.
    expect(best("28.1 min")).toBeNull();
    expect(best("22.9 min")).toBeNull();
    // SEE-I completed's 15 is not in the running: its columns are parts of SEE-I.
    expect(best("15")).toBeNull();
    // Rows where a best means nothing are never marked.
    expect(best("4.71")).toBeNull();
    expect(best("12–19")).toBeNull();
    expect(within(table).getAllByTitle(/^Best of/)).toHaveLength(3);
  });

  it("counts only Finished IDs and says what it left out", async () => {
    renderPage();
    expect(await screen.findByText("2 of 2 finished participants included")).toBeInTheDocument();
    expect(screen.getByText(/not counted: 1 signed in but didn.t finish, 3 IDs were never used/)).toBeInTheDocument();
  });

  it("draws the distributions, and says when a group is too small to fit a curve", async () => {
    renderPage();
    const legend = await screen.findByRole("list", { name: "Legend" });
    expect(within(legend).getByText("Chatbot")).toBeInTheDocument();
    expect(within(legend).getByText(/n = 3 · mean 12.67 · SD 6.03/)).toBeInTheDocument();
    expect(within(legend).getByText(/n = 1 · mean 16 · too few to fit a curve/)).toBeInTheDocument();
    const chart = screen.getByRole("img", { name: /Post-test score: fitted normal curves/ });
    // One dot per value, and a curve only where there is a spread to fit.
    expect(chart.querySelectorAll("circle")).toHaveLength(4);
    expect(chart.querySelectorAll('path[stroke="#2a78d6"]')).toHaveLength(1);
    expect(chart.querySelectorAll('path[stroke="#1baf7a"]')).toHaveLength(0);
  });

  it("asks for one batch when it is picked", async () => {
    renderPage();
    await userEvent.selectOptions(await screen.findByLabelText("Batch"), "b2");
    expect(api.getAnalysis).toHaveBeenLastCalledWith("b2", []);
  });

  it("reads the batch from the URL", async () => {
    renderPage("/analysis?batch=b1");
    await statsTable();
    expect(api.getAnalysis).toHaveBeenCalledWith("b1", []);
  });

  it("leaves an unticked ID out of the figures, and puts everyone back", async () => {
    renderPage("/analysis?tab=participants");
    await userEvent.click(await screen.findByLabelText("Include P-CHAT-0001"));
    expect(api.getAnalysis).toHaveBeenLastCalledWith(null, ["P-CHAT-0001"]);
    expect(await screen.findByText(/1 of 2 finished participants included/)).toBeInTheDocument();
    expect(screen.getByLabelText("Include P-CHAT-0001")).not.toBeChecked();

    await userEvent.click(screen.getByRole("button", { name: "Include everyone" }));
    expect(api.getAnalysis).toHaveBeenLastCalledWith(null, []);
  });

  it("lists an ID that has not finished, but never counts it", async () => {
    renderPage("/analysis?tab=participants");
    const box = await screen.findByLabelText("Include P-READ-0001");
    expect(box).not.toBeChecked();
    expect(box).toBeDisabled();
  });

  it("flags what is worth a second look", async () => {
    renderPage("/analysis?tab=behaviour");
    const card = (await screen.findByText("Worth a second look")).closest("section")!;
    expect(within(card).getByText("P-CHAT-0001")).toBeInTheDocument();
    expect(within(card).getByText("Pasted during a test")).toBeInTheDocument();
    expect(within(card).getByText("Not finished")).toBeInTheDocument();
    expect(within(card).queryByText("P-SEEI-0001")).not.toBeInTheDocument();
  });
});
