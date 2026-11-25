/** Small pieces the instructor's class pages share: the flag, where a student
 *  got to on a reading, and their initials.
 *
 * A student is flagged on a reading while their latest finished session there
 * ran out of tries, and no longer once a later one passes. The flag is red and
 * says Flagged wherever it appears, so it is never a matter of reading between
 * the lines; the student, for their part, sees Failed. */

import { Flag } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "../../lib/utils";
import { Chip } from "../readings/parts";
import type { ReadingProgress } from "./types";

/** A red pill with a flag: "Flagged", or a count of flagged students. */
export function FlagPill({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex h-[22px] shrink-0 items-center gap-1 whitespace-nowrap rounded-full border border-fail-border bg-fail px-2.5 text-[12px] font-medium text-fail-foreground">
      <Flag className="h-3 w-3" aria-hidden />
      {children}
    </span>
  );
}

/** Where a student got to on a reading, as its chip. */
export function ProgressChip({ status }: { status: ReadingProgress }) {
  switch (status) {
    case "completed":
      return <Chip tone="done">Complete</Chip>;
    case "stopped_early":
      return (
        <Chip tone="failed">
          <Flag className="mr-1 h-3 w-3" aria-hidden />
          Flagged
        </Chip>
      );
    case "timed_out":
      return <Chip tone="failed">Ran out of time</Chip>;
    default:
      return <Chip tone="neutral">Not started</Chip>;
  }
}

/** One mark per SEE-I step, filled for each step passed. A stopped session's
 *  marks are pale red, so a row that needs attention reads as one at a glance. */
export function StepBar({
  passed,
  stopped,
  className,
}: {
  passed: number;
  stopped: boolean;
  className?: string;
}) {
  return (
    <span className={cn("flex gap-1", className)} aria-label={`${passed} of 4 steps passed`}>
      {[0, 1, 2, 3].map((i) => (
        <span
          key={i}
          className={cn(
            "h-1 flex-1 rounded-sm",
            i < passed ? (stopped ? "bg-fail-border" : "bg-primary") : "bg-border",
          )}
        />
      ))}
    </span>
  );
}

export function Initials({ name }: { name: string }) {
  const text = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]!.toUpperCase())
    .join("");
  return (
    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted text-[11px] font-medium text-muted-foreground">
      {text}
    </span>
  );
}
