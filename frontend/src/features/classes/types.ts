/** Shapes returned by the class API. Mirror backend/schemas.py. */

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
