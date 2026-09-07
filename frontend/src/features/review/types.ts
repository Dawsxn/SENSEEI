/** Shapes for the session review, from backend/schemas.py. */

import type { SeeiStep } from "../tutoring/types";
import type { SessionStatus } from "../readings/types";

export interface StepSummary {
  step: SeeiStep;
  attempts: number;
  passed: boolean;
}

export interface TranscriptEntry {
  role: "tutor" | "student" | "fallback";
  step: SeeiStep;
  content: string;
  attempt_number: number | null;
  at: string;
}

export interface SessionTranscript {
  id: string;
  reading_id: string;
  reading_title: string;
  class_name: string;
  index: number;
  status: SessionStatus;
  started_at: string;
  ended_at: string | null;
  steps: StepSummary[];
  timeline: TranscriptEntry[];
}
