/** Domain types shared by the API client and the tutoring UI.
 *
 * These mirror what the backend sends. The stream event names and payloads are
 * documented on backend/services/session_service.py; the grade is deliberately
 * not among them — the student hears only the Tutor. */

export type SeeiStep = "State" | "Elaborate" | "Exemplify" | "Illustrate";
export type SessionStatus = "in_progress" | "complete" | "fallback";

/** The situation a tutor message was written for. `fallback` is the static copy. */
export type MessageKind =
  | "first_attempt"
  | "retry"
  | "final_fail"
  | "passed"
  | "fallback";

export interface SessionState {
  id: string;
  reading_id: string;
  reading_title: string;
  status: SessionStatus;
  current_step: SeeiStep;
  started_at: string;
  ended_at: string | null;
}

export interface TutorMessageRow {
  id: string;
  step: SeeiStep;
  attempt_id: string | null;
  moves: string[] | null;
  content: string;
  created_at: string;
}

// --- the streamed turn, as a discriminated union on `type` --------------------

export interface SessionEvent {
  type: "session";
  id: string;
  reading_id: string;
  reading_title: string;
  status: SessionStatus;
  current_step: SeeiStep;
  started_at: string;
  ended_at: string | null;
}

export interface MessageStartEvent {
  type: "message_start";
  step: SeeiStep;
  kind: MessageKind;
  moves: string[];
}

export interface DeltaEvent {
  type: "delta";
  text: string;
}

export interface MessageEndEvent {
  type: "message_end";
  id: string;
  content: string;
}

export interface StateEvent {
  type: "state";
  status: SessionStatus;
  current_step: SeeiStep;
  terminal: boolean;
  attempts_used: number;
  attempts_left: number;
}

export interface ErrorEvent {
  type: "error";
  detail: string;
}

export type StreamEvent =
  | SessionEvent
  | MessageStartEvent
  | DeltaEvent
  | MessageEndEvent
  | StateEvent
  | ErrorEvent;
