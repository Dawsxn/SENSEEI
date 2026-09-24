/** Shapes returned by the class API. Mirror backend/schemas.py. */

import type { SeeiStep } from "../tutoring/types";

export interface ClassListItem {
  id: string;
  name: string;
  section: string;
  /** How students see the class, `STRAMA K31`. */
  label: string;
  join_code: string;
  student_count: number;
  reading_count: number;
}

export interface ClassStudent {
  id: string;
  name: string;
  email: string;
  enrolled_at: string;
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
  students: ClassStudent[];
  readings: ClassReading[];
}

export interface ClassFields {
  name: string;
  section: string;
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
export type ReadingProgress = "not_started" | "completed" | "stopped_early";

export interface RosterStudent {
  id: string;
  name: string;
  email: string;
  status: ReadingProgress;
  steps_passed: number;
  /** The step they ran out of attempts on, when they stopped early. */
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
