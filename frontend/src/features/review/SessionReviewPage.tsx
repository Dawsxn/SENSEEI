/** One finished session, read back: a summary of how far it got, then the
 *  conversation as it happened.
 *
 * It lives under the reading it was a session on, so the breadcrumb leads back
 * to that reading and its class. The student sees the criteria each answer
 * missed, as tags under the tutor's reply, the same as during the session. The
 * instructor sees, under each answer, every criterion with the Assessment
 * Agent's reason. Both can open the reading's core components and the rubric;
 * tapping a tag opens the rubric on that step with that answer's misses marked.
 */

import { BookOpen, Check, Component, Minus, X } from "lucide-react";
import { useState } from "react";
import { Navigate, useParams } from "react-router-dom";

import { AppTopBar } from "../../components/AppTopBar";
import { Button } from "../../components/ui/button";
import { Loading, Skeleton } from "../../components/ui/Skeleton";
import { cn } from "../../lib/utils";
import { formatDateTime, formatDuration } from "../../lib/format";
import { useMe } from "../auth/useAuth";
import { useClass } from "../classes/useClasses";
import { Breadcrumb, Notice, SessionStatusChip } from "../readings/parts";
import { useMyClass } from "../readings/useReadings";
import { ComponentsPanel, RubricPanel } from "../tutoring/ReferencePanel";
import type { SeeiStep } from "../tutoring/types";
import type { Judgment, SessionTranscript, StepSummary, TranscriptEntry } from "./types";
import { useTranscript } from "./useTranscript";

const STEPS: SeeiStep[] = ["State", "Elaborate", "Exemplify", "Illustrate"];

type Panel =
  | { kind: "components" }
  | { kind: "rubric"; step: SeeiStep | null; unmet: string[]; from: number | null };

export function SessionReviewPage() {
  const { classId, readingId, sessionId } = useParams();
  const { data: t, isLoading, isError } = useTranscript(sessionId);
  const { data: user } = useMe();
  const instructor = user?.role === "instructor";
  // The class's name for the breadcrumb, from whichever side is looking.
  const studentClass = useMyClass(instructor ? undefined : classId);
  const ownClass = useClass(instructor ? classId : undefined);
  const classLabel = (instructor ? ownClass.data?.label : studentClass.data?.label) ?? t?.class_name;
  const [panel, setPanel] = useState<Panel | null>(null);

  // The address must name this session's own reading, and for a student a
  // class that holds it, or the breadcrumb would point somewhere else.
  const wrongPlace =
    (t && t.reading_id !== readingId) ||
    (studentClass.data && !studentClass.data.readings.some((r) => r.id === readingId));

  const toggle = (kind: "components" | "rubric") =>
    setPanel((p) =>
      p?.kind === kind
        ? null
        : kind === "components"
          ? { kind }
          : { kind, step: lastStep(t?.steps ?? []), unmet: [], from: null },
    );

  return (
    <div className="flex h-full flex-col">
      <AppTopBar />
      <main className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex max-w-[868px] flex-col gap-5 px-4 pb-8 pt-4 sm:gap-6 sm:px-6 sm:pb-12 sm:pt-6">
          {isLoading && <ReviewSkeleton />}
          {(isError || wrongPlace) && <Notice>Couldn't load this session.</Notice>}

          {t && !wrongPlace && (
            <>
              <div className="flex flex-col gap-2.5">
                <Breadcrumb
                  trail={[
                    { label: "Classes", to: instructor ? "/classes" : "/" },
                    { label: classLabel ?? "Class", to: `/classes/${classId}` },
                    { label: t.reading_title, to: `/classes/${classId}/readings/${readingId}` },
                    // The instructor goes back to this student's sessions on the reading.
                    ...(instructor
                      ? [
                          {
                            label: t.student_name,
                            to: `/classes/${classId}/readings/${readingId}/students/${t.student_id}`,
                          },
                        ]
                      : []),
                  ]}
                  current={`Attempt ${t.index}`}
                />
                <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between sm:gap-4">
                  <div className="min-w-0">
                    <h1 className="text-[22px] font-semibold tracking-[-0.02em] sm:text-[24px]">
                      {instructor ? t.student_name : t.reading_title}
                    </h1>
                    <div className="mt-2 flex flex-wrap items-center gap-x-2.5 gap-y-1.5 text-[14px] text-muted-foreground">
                      <SessionStatusChip status={t.status} instructor={instructor} />
                      <span>
                        {[
                          instructor && t.reading_title,
                          `Attempt ${t.index}`,
                          formatDateTime(t.started_at),
                          formatDuration(t.started_at, t.ended_at),
                        ]
                          .filter(Boolean)
                          .join(" · ")}
                      </span>
                    </div>
                  </div>
                  <div className="flex shrink-0 gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      aria-expanded={panel?.kind === "components"}
                      className={cn("flex-1 sm:flex-none", panel?.kind === "components" && "bg-muted")}
                      onClick={() => toggle("components")}
                    >
                      <Component className="h-[15px] w-[15px]" />
                      Components
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      aria-expanded={panel?.kind === "rubric"}
                      className={cn("flex-1 sm:flex-none", panel?.kind === "rubric" && "bg-muted")}
                      onClick={() => toggle("rubric")}
                    >
                      <BookOpen className="h-[15px] w-[15px]" />
                      Rubric
                    </Button>
                  </div>
                </div>
              </div>

              <Summary t={t} />
              <Replay
                t={t}
                instructor={instructor}
                tapped={panel?.kind === "rubric" ? panel.from : null}
                onTag={(step, unmet, from) => setPanel({ kind: "rubric", step, unmet, from })}
              />
            </>
          )}
        </div>
      </main>

      {t && panel?.kind === "components" && (
        <ComponentsPanel
          components={t.core_components}
          placement="page"
          onClose={() => setPanel(null)}
        />
      )}
      {panel?.kind === "rubric" && (
        <RubricPanel
          currentStep={panel.step}
          unmet={panel.unmet}
          placement="page"
          onClose={() => setPanel(null)}
        />
      )}
    </div>
  );
}

/** An old `/review/:id` link: find the session's reading and class, and go there. */
export function OldReviewLink() {
  const { sessionId } = useParams();
  const { data: t, isError } = useTranscript(sessionId);
  if (isError) return <Navigate to="/" replace />;
  if (!t) return null;
  return (
    <Navigate to={`/classes/${t.class_id}/readings/${t.reading_id}/sessions/${t.id}`} replace />
  );
}

/** The header, the step card and the start of the conversation, in grey. */
function ReviewSkeleton() {
  return (
    <Loading label="Loading the session" className="flex flex-col gap-5 sm:gap-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex flex-col gap-3">
          <Skeleton className="h-3.5 w-64 max-w-full" />
          <Skeleton className="h-7 w-48" />
          <div className="flex items-center gap-2.5">
            <Skeleton className="h-[22px] w-24 rounded-full" />
            <Skeleton className="h-4 w-56 max-w-[60%]" />
          </div>
        </div>
        <div className="flex gap-2">
          <Skeleton className="h-8 flex-1 sm:w-[118px] sm:flex-none" />
          <Skeleton className="h-8 flex-1 sm:w-[86px] sm:flex-none" />
        </div>
      </div>
      <div className="grid grid-cols-2 overflow-hidden rounded-lg border sm:grid-cols-4">
        {STEPS.map((step, i) => (
          <div
            key={step}
            className={cn(
              "flex flex-col gap-2 px-4 py-3.5",
              i % 2 === 1 && "border-l",
              i >= 2 && "border-t sm:border-t-0",
              i === 2 && "sm:border-l",
            )}
          >
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-3.5 w-12" />
          </div>
        ))}
      </div>
      <div className="flex flex-col gap-4">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="ml-auto h-16 w-[85%] rounded-lg" />
        <Skeleton className="h-4 w-2/3" />
      </div>
    </Loading>
  );
}

function lastStep(steps: StepSummary[]): SeeiStep | null {
  return steps.length ? steps[steps.length - 1].step : null;
}

/** Each SEE-I step: passed, not passed, or never reached, and how many tries. */
function Summary({ t }: { t: SessionTranscript }) {
  return (
    <div className="overflow-hidden rounded-lg border">
      <div className="grid grid-cols-2 sm:grid-cols-4">
        {STEPS.map((step, i) => {
          const s = t.steps.find((x) => x.step === step);
          return (
            <div
              key={step}
              className={cn(
                "flex flex-col gap-1 px-4 py-3",
                i % 2 === 1 && "border-l",
                i >= 2 && "border-t sm:border-t-0",
                i === 2 && "sm:border-l",
              )}
            >
              <span
                className={cn(
                  "flex items-center gap-1.5 text-[14px] font-medium",
                  !s && "text-muted-foreground/70",
                )}
              >
                {!s ? (
                  <Minus className="h-3.5 w-3.5" aria-hidden />
                ) : s.passed ? (
                  <Check className="h-3.5 w-3.5 text-primary" aria-hidden />
                ) : (
                  <X className="h-3.5 w-3.5 text-fail-foreground" aria-hidden />
                )}
                {step}
              </span>
              <span className="text-[13px] text-muted-foreground">
                {!s ? "Not reached" : `${s.attempts} ${s.attempts === 1 ? "try" : "tries"}`}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Replay({
  t,
  instructor,
  tapped,
  onTag,
}: {
  t: SessionTranscript;
  instructor: boolean;
  tapped: number | null;
  onTag: (step: SeeiStep, unmet: string[], from: number) => void;
}) {
  const passedSteps = new Set(t.steps.filter((s) => s.passed).map((s) => s.step));
  let lastStep: SeeiStep | null = null;
  // The criteria the latest answer missed, waiting for the tutor's reply to it:
  // that reply is where the student saw them during the session.
  let pending: string[] = [];

  return (
    <div>
      {t.timeline.map((e, i) => {
        const divider =
          e.step !== lastStep ? (
            <StepDivider key={`d-${i}`} step={e.step} passed={passedSteps.has(e.step)} />
          ) : null;
        lastStep = e.step;

        let unmet: string[] = [];
        if (e.role === "student") {
          pending = missed(e.judgment);
        } else {
          if (e.role === "tutor") unmet = pending;
          pending = [];
        }

        return (
          <div key={i}>
            {divider}
            <Entry
              entry={e}
              instructor={instructor}
              unmet={instructor ? [] : unmet}
              tapped={tapped === i}
              onTag={() => onTag(e.step, unmet, i)}
            />
          </div>
        );
      })}
    </div>
  );
}

function missed(j: Judgment | null | undefined): string[] {
  return j ? j.criteria.filter((c) => !c.passed).map((c) => c.criterion) : [];
}

function StepDivider({ step, passed }: { step: SeeiStep; passed: boolean }) {
  return (
    <div className="mb-4 mt-7 flex items-center gap-3 first:mt-0">
      <span
        className={cn(
          "text-[12px] font-medium uppercase tracking-wide",
          passed ? "text-primary" : "text-muted-foreground",
        )}
      >
        {step}
      </span>
      <span className="h-px flex-1 bg-border" />
      {passed && <Check className="h-4 w-4 text-primary" />}
    </div>
  );
}

function Entry({
  entry,
  instructor,
  unmet,
  tapped,
  onTag,
}: {
  entry: TranscriptEntry;
  instructor: boolean;
  unmet: string[];
  tapped: boolean;
  onTag: () => void;
}) {
  if (entry.role === "student") {
    return (
      <div className="my-4 flex flex-col items-end gap-2">
        <div className="max-w-[92%] rounded-lg bg-accent-soft px-4 py-2.5 text-[14px] leading-relaxed text-foreground/80 sm:max-w-[85%]">
          {entry.content}
        </div>
        {instructor && entry.judgment && (
          <JudgmentCard judgment={entry.judgment} n={entry.attempt_number} />
        )}
      </div>
    );
  }
  if (entry.role === "fallback") {
    return (
      <div className="my-4 rounded-lg border border-fail-border bg-fail px-4 py-3 text-[14px] leading-relaxed text-fail-foreground">
        {entry.content}
      </div>
    );
  }
  return (
    <div className="my-4 text-[14px] leading-relaxed">
      {entry.content}
      {unmet.length > 0 && (
        <div className="mt-2.5 flex flex-wrap gap-1.5" aria-label="Criteria not met">
          {unmet.map((name) => (
            <button
              key={name}
              type="button"
              onClick={onTag}
              className={cn(
                "inline-flex h-[22px] items-center rounded-full border border-fail-border bg-fail px-2.5 text-[12px] font-medium text-fail-foreground hover:bg-fail-border/40",
                tapped && "ring-2 ring-fail-border ring-offset-2 ring-offset-background",
              )}
            >
              {name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/** Under each try, for the instructor: the verdict, every failed criterion
 *  with the Assessment Agent's reason, and the passed ones on one line. Tries
 *  are numbered within their step, as they are stored. */
function JudgmentCard({ judgment, n }: { judgment: Judgment; n: number | null }) {
  const failed = judgment.criteria.filter((c) => !c.passed);
  const passed = judgment.criteria.filter((c) => c.passed);
  const pass = judgment.verdict === "PASS";
  return (
    <div className="w-full max-w-[92%] rounded-lg border text-[13px] sm:max-w-[85%]">
      <div className="flex items-center justify-between rounded-t-lg border-b bg-muted/40 px-3 py-2">
        <span className="font-medium">Try {n}</span>
        <span
          className={cn(
            "rounded-full px-2 py-px text-[12px] font-medium",
            pass ? "bg-accent-soft text-accent-soft-foreground" : "bg-fail text-fail-foreground",
          )}
        >
          {pass ? "Passed" : "Not passed"}
        </span>
      </div>
      {failed.map((c) => (
        <div
          key={c.criterion}
          className="flex flex-col gap-0.5 border-b border-border/60 px-3 py-2 leading-[1.55] last:border-b-0 sm:flex-row sm:gap-2.5"
        >
          <span className="flex shrink-0 items-start gap-1.5 font-medium text-fail-foreground sm:w-[130px]">
            <X className="mt-[3px] h-3.5 w-3.5 shrink-0" aria-hidden />
            {c.criterion}
          </span>
          <span className="text-foreground/80">{c.reason || "No reason given."}</span>
        </div>
      ))}
      {passed.length > 0 && (
        <div className="flex flex-col gap-0.5 px-3 py-2 leading-[1.55] text-muted-foreground sm:flex-row sm:gap-2.5">
          <span className="flex shrink-0 items-start gap-1.5 font-medium text-primary sm:w-[130px]">
            <Check className="mt-[3px] h-3.5 w-3.5 shrink-0" aria-hidden />
            Passed
          </span>
          <span>{passed.map((c) => c.criterion).join(", ")}</span>
        </div>
      )}
    </div>
  );
}
