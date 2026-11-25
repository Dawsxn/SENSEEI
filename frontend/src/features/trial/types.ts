/** Shapes for the trial, from backend/schemas.py. Only the trial instance
 *  serves these (docs/context/trial.md). */

import type { ClassMode } from "../classes/types";
import type { SessionStatus } from "../tutoring/types";

/** Where a participant is. The countdown is drawn from `seconds_left`. */
export interface TrialStatus {
  code: string;
  mode: ClassMode;
  /** Pressed Done: the chatbot and reading-only groups' way to finish early. */
  done: boolean;
  reading_id: string | null;
  minutes: number;
  /** Null until the reading first opens and the clock starts. */
  seconds_left: number | null;
  time_up: boolean;
  session: { id: string; status: SessionStatus } | null;
  /** With tests, where the participant is. Null for a class without them. */
  test_stage?: TestStage | null;
  /** With tests, each test's length in minutes. */
  test_minutes?: { pre: number; post: number } | null;
}

export type TestStage = "pretest" | "session" | "posttest_ready" | "posttest" | "done";
export type TestWhich = "pre" | "post";

export interface TestItem {
  id: string;
  /** truefalse: statements each marked True or False. steps: written in parts. */
  kind: "choice" | "truefalse" | "text" | "steps";
  part: string;
  question: string;
  options: { key: string; text: string }[];
  statements: { key: string; text: string }[];
  steps: { key: string; prompt: string }[];
  /** The first step locks once a later one has text. */
  lock_first: boolean;
  points: number;
  /** Ends with "Is this answer fully correct?". */
  ticked: boolean;
}

export interface SavedAnswer {
  item: string;
  choice?: string | null;
  text?: string | null;
  /** A true/false set's marks ({a: true}) or a question in steps ({a: "..."}). */
  parts?: Record<string, boolean | string> | null;
  sure?: boolean | null;
}

/** A test as its taker sees it: no answer key and no rubric. */
export interface TestView {
  which: TestWhich;
  minutes: number;
  started: boolean;
  /** Null until the test starts. */
  seconds_left: number | null;
  /** A line shown at the start of a part, under its heading. */
  part_intros: Record<string, string>;
  items: TestItem[];
  answers: SavedAnswer[];
}

export interface GradingListItem {
  code: string;
  /** Written answers still to grade. */
  left: number;
  posttest_ended: boolean;
  /** The sitting the ID was made for. Never the group. */
  batch_id: string;
  batch_name: string;
}

export interface GradingWritten {
  test: TestWhich;
  item: string;
  question: string;
  text: string | null;
  /** A question answered in steps: each part with its prompt. */
  parts?: { key: string; prompt: string; text: string | null }[] | null;
  sure: boolean | null;
  score: number | null;
  points: number;
  reference: string;
  criteria: { points: number; text: string }[];
}

export interface GradingSet {
  item: string;
  question: string;
  sure: boolean | null;
  score: number;
  points: number;
  statements: { key: string; text: string; answer: boolean; picked: boolean | null }[];
}

/** One participant's tests for the grader. Never their group. */
export interface GradingDetail {
  code: string;
  posttest_ended: boolean;
  left: number;
  pretest_score: number | null;
  posttest_total: number | null;
  calibration: number | null;
  sure_but_wrong: number | null;
  choices: {
    item: string;
    choice: string | null;
    answer: string;
    correct: boolean;
    sure: boolean | null;
  }[];
  /** True/false sets, scored automatically. */
  sets: GradingSet[];
  written: GradingWritten[];
}

export interface BatchListItem {
  id: string;
  name: string;
  created_at: string;
  closed_at: string | null;
  id_count: number;
  used_count: number;
}

export type ParticipantStatus = "not_used" | "signed_in" | "finished" | "voided";

export interface BatchParticipant {
  id: string;
  code: string;
  class_id: string;
  class_label: string;
  mode: ClassMode;
  status: ParticipantStatus;
}

export interface Batch {
  id: string;
  name: string;
  created_at: string;
  closed_at: string | null;
  /** In the order drawn (shuffled); the batch page lists them by class. */
  participants: BatchParticipant[];
  /** After adding IDs: just the new ones. */
  added?: string[];
}

export interface NewBatch {
  name: string;
  classes: { class_id: string; count: number }[];
}

export interface ChatMessageRow {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

/** What the chatbot's reply stream sends. */
export type ChatEvent =
  | { type: "message_start" }
  | { type: "delta"; text: string }
  | { type: "message_end"; id: string; content: string }
  | { type: "error"; detail: string };

/** The Analysis tab, from AnalysisOut in backend/schemas.py. The research
 *  team only: it names each ID's group. */
export type AnalysisFormat =
  | "number"
  | "share"
  | "minutes"
  | "seconds"
  | "people"
  | "count";

export interface AnalysisColumn {
  key: string;
  label: string;
  n: number;
}

export interface AnalysisRow {
  key: string;
  label: string;
  format: AnalysisFormat;
  section: "scores" | "dimensions" | "behaviour";
  /** In scores, the measure this row describes; its rows are n, mean, SD... */
  measure: string | null;
  /** Quartiles and range are [low, high]. */
  values: Record<string, number | [number, number] | null>;
}

/** One measure's values per group, for the overlapping bell curves. */
export interface AnalysisDistribution {
  key: string;
  label: string;
  format: AnalysisFormat;
  low: number | null;
  high: number | null;
  series: Record<string, { values: number[]; mean: number | null; sd: number | null }>;
}

export interface AnalysisStep {
  step: string;
  attempts: number;
  pass_rate: number | null;
  passed: number;
  reached: number;
  attempts_to_pass: number | null;
  most_attempts: number | null;
}

export interface AnalysisSession {
  code: string;
  status: string | null;
  last_step: string | null;
  /** The session completed all four steps. */
  completed: boolean | null;
  reading_minutes: number | null;
  session_minutes: number | null;
  turns: number | null;
  pretest_score: number | null;
  posttest_total: number | null;
}

export interface AnalysisFix {
  criterion: string;
  failed: number;
  fixed: number;
  rate: number | null;
}

export interface AnalysisParticipant {
  code: string;
  batch: string;
  group: ClassMode;
  /** Finished as the batch page counts it. Only these are in the figures. */
  finished: boolean;
  excluded: boolean;
  voided: boolean;
  status: string | null;
  last_step: string | null;
  /** SEE-I only: the session completed all four steps. */
  completed: boolean | null;
  pretest_score: number | null;
  posttest_total: number | null;
  posttest_max: number | null;
  calibration: number | null;
  sure_but_wrong: number | null;
  pretest_minutes: number | null;
  posttest_minutes: number | null;
  pretest_ended_by: string | null;
  posttest_ended_by: string | null;
  reading_minutes: number | null;
  session_minutes: number | null;
  total_minutes: number | null;
  minutes_to_done: number | null;
  turns: number | null;
  chat_questions: number | null;
  chat_words: number | null;
  pastes: number;
  paste_chars: number;
  test_pastes: number;
  test_tab_left: number;
  thinking_seconds: number | null;
  turn_failed: number;
  flags: string[];
}

export interface Analysis {
  batches: { id: string; name: string }[];
  batch_id: string | null;
  used: number;
  unused: number;
  /** Signed in and Finished on the batch page. */
  finished: number;
  /** In the figures: Finished, after exclusions. */
  included: number;
  comparison: {
    columns: AnalysisColumn[];
    posttest_max: number | null;
    rows: AnalysisRow[];
    distributions: AnalysisDistribution[];
  };
  seei: {
    sessions: AnalysisSession[];
    steps: AnalysisStep[];
    criteria: { step: string; criterion: string; judged: number; failed: number; fail_rate: number }[];
    fixes: AnalysisFix[];
    fixed_overall: AnalysisFix;
  };
  participants: AnalysisParticipant[];
}
