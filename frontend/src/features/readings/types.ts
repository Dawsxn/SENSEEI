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
