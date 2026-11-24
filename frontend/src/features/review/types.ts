/** Shapes for the session review, from backend/schemas.py. */

import type { SeeiStep } from "../tutoring/types";
import type { SessionStatus } from "../readings/types";

export interface StepSummary {
  step: SeeiStep;
  attempts: number;
  passed: boolean;
}

/** How the Assessment Agent judged one answer. A student gets it with every
 *  `reason` empty; only the instructor sees why. */
export interface Judgment {
  verdict: "PASS" | "FAIL";
  /** Failed first, then in the rubric's order. */
  criteria: { criterion: string; passed: boolean; reason: string | null }[];
}

export interface TranscriptEntry {
  role: "tutor" | "student" | "fallback";
  step: SeeiStep;
  content: string;
  attempt_number: number | null;
  at: string;
  judgment?: Judgment | null;
}

export interface SessionTranscript {
  id: string;
  reading_id: string;
  reading_title: string;
  class_name: string;
  /** The class it is reviewed under, so an old `/review/:id` link can find it. */
  class_id: string;
  core_components: string[];
  /** Whose session it is. Shown when an instructor is reading it. */
  student_name: string;
  index: number;
  status: SessionStatus;
  started_at: string;
  ended_at: string | null;
  steps: StepSummary[];
  timeline: TranscriptEntry[];
}
