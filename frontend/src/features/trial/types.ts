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
  /** In slip order: shuffled, so the classes are mixed. */
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
