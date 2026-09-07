/** Shapes returned by the reading API. Mirror backend/schemas.py. */

export type ReadingStatus = "not_started" | "complete" | "failed";

export interface ReadingListItem {
  id: string;
  title: string;
  description: string | null;
  class_name: string;
  status: ReadingStatus;
}

export interface ReadingDetail {
  id: string;
  title: string;
  description: string | null;
  class_name: string;
  content: string;
  core_components: string[];
}

export type SessionStatus = "in_progress" | "complete" | "fallback";

export interface ReadingSessionItem {
  id: string;
  index: number;
  status: SessionStatus;
  started_at: string;
  ended_at: string | null;
  attempt_count: number;
}
