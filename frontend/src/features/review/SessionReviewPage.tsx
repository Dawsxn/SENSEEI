import { Check, ChevronLeft } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { SessionStatusBadge } from "../../components/SessionStatusBadge";
import { Button } from "../../components/ui/button";
import { cn } from "../../lib/utils";
import { formatDate, formatDuration } from "../../lib/format";
import { useReadingSessions } from "../readings/useReadings";
import type { SeeiStep } from "../tutoring/types";
import type { SessionTranscript, TranscriptEntry } from "./types";
import { useTranscript } from "./useTranscript";

export function SessionReviewPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const { data: t, isLoading, isError } = useTranscript(sessionId);
  const { data: sessions } = useReadingSessions(t?.reading_id);

  return (
    <div className="flex h-full flex-col">
      <header className="flex h-14 shrink-0 items-center justify-between border-b px-4 sm:px-6">
        <Link
          to="/"
          className="flex items-center gap-1 text-[14px] text-muted-foreground hover:text-foreground"
        >
          <ChevronLeft className="h-4 w-4" />
          Readings
        </Link>
        {t && (
          <Button size="sm" onClick={() => navigate(`/tutor/${t.reading_id}`)}>
            Start a new attempt
          </Button>
        )}
      </header>

      <main className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[820px] px-4 py-6 sm:px-6 sm:py-8">
          {isLoading && <Notice>Loading session…</Notice>}
          {isError && <Notice>Couldn't load this session.</Notice>}
          {t && (
            <>
              <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <div className="text-[12px] font-medium uppercase tracking-wide text-muted-foreground">
                    {t.class_name}
                  </div>
                  <h1 className="text-[24px] font-semibold tracking-[-0.02em]">
                    {t.reading_title}
                  </h1>
                </div>
                {sessions && sessions.length > 1 && (
                  <select
                    value={t.id}
                    onChange={(e) => navigate(`/review/${e.target.value}`)}
                    className="h-9 rounded-md border bg-background px-3 text-[14px] outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {sessions.map((s) => (
                      <option key={s.id} value={s.id}>
                        Attempt {s.index} · {formatDate(s.started_at)}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <SummaryCard t={t} />
              <Replay t={t} />
            </>
          )}
        </div>
      </main>
    </div>
  );
}

function SummaryCard({ t }: { t: SessionTranscript }) {
  const totalAttempts = t.steps.reduce((n, s) => n + s.attempts, 0);
  const duration = formatDuration(t.started_at, t.ended_at);
  return (
    <div className="mb-8 overflow-hidden rounded-lg border">
      <div className="flex items-center justify-between gap-3 bg-muted px-4 py-3">
        <SessionStatusBadge status={t.status} />
        <span className="text-[13px] text-muted-foreground">
          {duration && `${duration} · `}
          {totalAttempts} attempt{totalAttempts === 1 ? "" : "s"} across {t.steps.length}{" "}
          step{t.steps.length === 1 ? "" : "s"}
        </span>
      </div>
      {t.steps.map((s, i) => (
        <div
          key={s.step}
          className={cn(
            "flex items-center px-4 py-3 text-[14px]",
            i > 0 && "border-t",
          )}
        >
          <span className="font-medium">{s.step}</span>
          <span className={cn("ml-auto mr-6", s.passed ? "text-primary" : "text-fail-foreground")}>
            {s.passed ? "passed" : "not passed"}
          </span>
          <span className="w-20 text-right text-muted-foreground">
            {s.attempts} attempt{s.attempts === 1 ? "" : "s"}
          </span>
        </div>
      ))}
    </div>
  );
}

function Replay({ t }: { t: SessionTranscript }) {
  const passedSteps = new Set(t.steps.filter((s) => s.passed).map((s) => s.step));
  let lastStep: SeeiStep | null = null;

  return (
    <div>
      {t.timeline.map((e, i) => {
        const divider =
          e.step !== lastStep ? (
            <StepDivider key={`d-${i}`} step={e.step} passed={passedSteps.has(e.step)} />
          ) : null;
        lastStep = e.step;
        return (
          <div key={i}>
            {divider}
            <Entry entry={e} />
          </div>
        );
      })}
    </div>
  );
}

function StepDivider({ step, passed }: { step: SeeiStep; passed: boolean }) {
  return (
    <div className="mb-4 mt-6 flex items-center gap-3 first:mt-0">
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

function Entry({ entry }: { entry: TranscriptEntry }) {
  if (entry.role === "student") {
    return (
      <div className="my-4 flex justify-end">
        <div className="max-w-[85%] rounded-lg bg-[#f0fdf4] px-4 py-2.5 text-[14px] leading-relaxed text-[#3f3f46]">
          {entry.content}
        </div>
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
  return <div className="my-4 text-[14px] leading-relaxed">{entry.content}</div>;
}

function Notice({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed px-4 py-10 text-center text-[14px] text-muted-foreground">
      {children}
    </div>
  );
}
