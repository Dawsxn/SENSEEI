/** Shapes returned by the reading API. Mirror backend/schemas.py. */

export type ReadingStatus = "not_started" | "complete" | "failed";

export interface ReadingListItem {
  id: string;
  title: string;
  description: string | null;
  class_name: string;
  status: ReadingStatus;
}

/** A class on the student's home page. */
export interface StudentClassItem {
  id: string;
  name: string;
  section: string;
  /** Name and section joined, `STRAMA K31`. */
  label: string;
  reading_count: number;
  /** Readings whose latest finished session passed or failed. */
  finished_count: number;
}

/** One of the student's classes, with its readings, oldest first. */
export interface StudentClassDetail {
  id: string;
  name: string;
  section: string;
  label: string;
  readings: ReadingListItem[];
}

export interface ReadingDetail {
  id: string;
  title: string;
  description: string | null;
  class_name: string;
  content: string;
  core_components: string[];
  /** Whether the original upload is stored. False falls back to `content`. */
  has_file: boolean;
}

export type SessionStatus = "in_progress" | "complete" | "fallback" | "timed_out";

export interface ReadingSessionItem {
  id: string;
  index: number;
  status: SessionStatus;
  started_at: string;
  ended_at: string | null;
  attempt_count: number;
}
