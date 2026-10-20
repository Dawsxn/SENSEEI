/** Shapes returned by the class API. Mirror backend/schemas.py. */

import type { SeeiStep } from "../tutoring/types";

/** What a class's students do with a reading. Only SEE-I outside trial mode. */
export type ClassMode = "seei" | "chatbot" | "reading_only";

export const MODE_LABEL: Record<ClassMode, string> = {
  seei: "SEE-I",
  chatbot: "Chatbot",
  reading_only: "Reading only",
};

export interface ClassListItem {
  id: string;
  name: string;
  section: string;
  /** How students see the class, `STRAMA K31`. */
  label: string;
  join_code: string;
  mode: ClassMode;
  student_count: number;
  reading_count: number;
}

export interface ClassStudent {
  id: string;
  name: string;
  email: string;
  enrolled_at: string;
  /** Trial mode: the participant ID this student is. */
  participant_code?: string | null;
  signed_in_at?: string | null;
}

export interface ClassReading {
  id: string;
  title: string;
  description: string | null;
}

export interface ClassDetail {
  id: string;
  name: string;
  section: string;
  label: string;
  join_code: string;
  mode: ClassMode;
  /** The mode is fixed once a participant has signed in. */
  mode_locked?: boolean;
  students: ClassStudent[];
  readings: ClassReading[];
}

export interface ClassFields {
  name: string;
  section: string;
  mode?: ClassMode;
}

export interface JoinResult {
  class_id: string;
  label: string;
  reading_count: number;
}

/** The three statistics, over a class or over one reading in it. */
export interface Statistics {
  /** Finished sessions the numbers cover. Zero means there is nothing to show. */
  session_count: number;
  pass_rates: { step: SeeiStep; passed: number; total: number; percent: number }[];
  failed_criteria: { criterion: string; failures: number }[];
  average_attempts: { step: SeeiStep; average: number }[];
}

export interface ClassReadingItem {
  id: string;
  title: string;
  description: string | null;
  session_count: number;
}

export interface ClassDashboard {
  statistics: Statistics;
  readings: ClassReadingItem[];
}

/** Where a student got to on one reading. */
export type ReadingProgress = "not_started" | "completed" | "stopped_early" | "timed_out";

export interface RosterStudent {
  id: string;
  name: string;
  email: string;
  status: ReadingProgress;
  steps_passed: number;
  /** The step they stopped on, out of attempts or out of time. */
  stopped_on: SeeiStep | null;
  /** Their latest finished session, which the row opens. */
  session_id: string | null;
  last_session_at: string | null;
}

export interface ClassReadingDetail {
  id: string;
  title: string;
  description: string | null;
  class_id: string;
  class_label: string;
  statistics: Statistics;
  students: RosterStudent[];
}
