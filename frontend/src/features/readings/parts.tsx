import { ChevronRight } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { cn } from "../../lib/utils";
import type { ReadingStatus, SessionStatus } from "./types";

type Tone = "done" | "failed" | "neutral";

const TONES: Record<Tone, string> = {
  done: "border-accent-soft-border bg-accent-soft text-accent-soft-foreground",
  failed: "border-fail-border bg-fail text-fail-foreground",
  neutral: "border-border bg-background text-muted-foreground",
};

/** A status pill of one fixed width, so a column of them lines up. */
function Chip({ tone, children }: { tone: Tone; children: ReactNode }) {
  return (
    <span
      className={cn(
        "inline-flex h-[22px] w-24 shrink-0 items-center justify-center rounded-full border text-[12px] font-medium",
        TONES[tone],
      )}
    >
      {children}
    </span>
  );
}

const READING: Record<ReadingStatus, [Tone, string]> = {
  complete: ["done", "Complete"],
  failed: ["failed", "Failed"],
  not_started: ["neutral", "Not started"],
};

export function ReadingStatusChip({ status }: { status: ReadingStatus }) {
  const [tone, label] = READING[status];
  return <Chip tone={tone}>{label}</Chip>;
}

// Only the trial ends a session by time, so outside it a student sees Complete
// or Failed. The other labels are kept so nothing renders blank.
const SESSION: Record<SessionStatus, [Tone, string]> = {
  complete: ["done", "Complete"],
  fallback: ["failed", "Failed"],
  timed_out: ["failed", "Ran out of time"],
  in_progress: ["neutral", "In progress"],
  // Never listed, since neither is finished; here so nothing renders blank.
  left: ["neutral", "Left"],
  abandoned: ["neutral", "Not finished"],
};

export function SessionStatusChip({ status }: { status: SessionStatus }) {
  const [tone, label] = SESSION[status];
  return <Chip tone={tone}>{label}</Chip>;
}

/** Where a student is: the full trail from a tablet up, and on a phone just a
 *  link back to the page above, which is all there is room for. */
export function Breadcrumb({
  trail,
  current,
}: {
  trail: { label: string; to: string }[];
  current: string;
}) {
  const parent = trail[trail.length - 1];
  return (
    <>
      <nav aria-label="Breadcrumb" className="hidden items-center gap-1.5 text-[13px] text-muted-foreground sm:flex">
        {trail.map((t) => (
          <span key={t.to} className="flex items-center gap-1.5">
            <Link to={t.to} className="text-foreground/70 hover:text-foreground hover:underline">
              {t.label}
            </Link>
            <ChevronRight className="h-3.5 w-3.5" aria-hidden />
          </span>
        ))}
        <span className="text-foreground" aria-current="page">
          {current}
        </span>
      </nav>
      <Link
        to={parent.to}
        className="flex w-fit items-center gap-1 text-[13px] text-foreground/70 hover:text-foreground sm:hidden"
      >
        <ChevronRight className="h-4 w-4 rotate-180" aria-hidden />
        {parent.label}
      </Link>
    </>
  );
}

/** A progress bar in the accent colour. */
export function ProgressBar({ value, className }: { value: number; className?: string }) {
  return (
    <div
      role="progressbar"
      aria-valuenow={Math.round(value * 100)}
      aria-valuemin={0}
      aria-valuemax={100}
      className={cn("h-1.5 overflow-hidden rounded-full bg-muted", className)}
    >
      <div className="h-full rounded-full bg-primary" style={{ width: `${value * 100}%` }} />
    </div>
  );
}

/** A dashed box for loading, errors and empty lists. */
export function Notice({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed px-4 py-10 text-center text-[14px] text-muted-foreground">
      {children}
    </div>
  );
}
