/** The instructor's replay shows how each answer was judged. */
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { SessionReviewPage } from "./SessionReviewPage";
import type { SessionTranscript } from "./types";

const transcript: SessionTranscript = {
  id: "s1",
  reading_id: "r1",
  reading_title: "Strategic Offensives",
  class_name: "SEE-I",
  student_name: "P-7K3Q-9TXM",
  index: 1,
  status: "timed_out",
  started_at: "2026-11-22T01:00:00Z",
  ended_at: "2026-11-22T01:35:00Z",
  steps: [{ step: "Elaborate", attempts: 1, passed: false }],
  timeline: [
    { role: "tutor", step: "Elaborate", content: "Now elaborate.", attempt_number: null, at: "2026-11-22T01:01:00Z" },
    {
      role: "student",
      step: "Elaborate",
      content: "It is an attack on rivals.",
      attempt_number: 1,
      at: "2026-11-22T01:02:00Z",
      judgment: {
        verdict: "FAIL",
        criteria: [
          { criterion: "Completeness", passed: false, reason: "Leaves out strengths and weaknesses." },
          { criterion: "Own Words", passed: true, reason: "ok" },
          { criterion: "Accuracy", passed: true, reason: "ok" },
        ],
      },
    },
  ],
};

const role = vi.hoisted(() => ({ value: "instructor" }));
vi.mock("./useTranscript", () => ({ useTranscript: () => ({ data: transcript }) }));
vi.mock("../auth/useAuth", () => ({ useMe: () => ({ data: { role: role.value } }) }));
vi.mock("../readings/useReadings", () => ({ useReadingSessions: () => ({ data: [] }) }));

describe("the instructor's session replay", () => {
  it("shows each answer's verdict, the failed criteria with reasons, and the passed ones", () => {
    render(
      <MemoryRouter>
        <SessionReviewPage />
      </MemoryRouter>,
    );
    expect(screen.getByText("Not passed")).toBeInTheDocument();
    expect(screen.getByText("Completeness")).toBeInTheDocument();
    expect(screen.getByText("Leaves out strengths and weaknesses.")).toBeInTheDocument();
    expect(screen.getByText("Own Words, Accuracy")).toBeInTheDocument();
  });
});
