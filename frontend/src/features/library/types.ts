/** Shapes returned by the instructor's reading API. Mirror backend/schemas.py. */

export interface ClassRef {
  id: string;
  label: string;
}

/** A class a reading is in, as the reading's page lists it. */
export interface LibraryClass extends ClassRef {
  student_count: number;
  /** Finished sessions on this reading by the class's students. */
  session_count: number;
}

export interface LibraryItem {
  id: string;
  title: string;
  description: string | null;
  /** Labels of the classes it is assigned to. Empty means no student sees it. */
  classes: string[];
  session_count: number;
  created_at: string;
}

export interface LibraryReading {
  id: string;
  title: string;
  description: string | null;
  content: string;
  core_components: string[];
  classes: LibraryClass[];
  session_count: number;
  has_file: boolean;
  created_at: string;
}

export interface ExtractResult {
  text: string;
  figures_described: number;
  figures_failed: boolean;
}

export interface NewReading {
  file: File;
  title: string;
  description: string;
  content: string;
  coreComponents: string[];
  classIds: string[];
}
