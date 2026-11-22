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
