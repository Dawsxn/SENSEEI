import { cn } from "../lib/utils";
import type { SessionStatus } from "../features/readings/types";

/** A pill for a session's outcome, shared by the dialog and the review header.
 *  Complete is the success green; fallback is the soft failure; in-progress is
 *  neutral (a session is not resumable, so it reads as unfinished). */
export function SessionStatusBadge({ status }: { status: SessionStatus }) {
  const styles: Record<SessionStatus, string> = {
    complete: "border-[#bbf7d0] bg-[#f0fdf4] text-[#15803d]",
    fallback: "border-fail-border bg-fail text-fail-foreground",
    in_progress: "border-border text-muted-foreground",
  };
  const label: Record<SessionStatus, string> = {
    complete: "Complete",
    fallback: "Failed",
    in_progress: "In progress",
  };
  return (
    <span
      className={cn(
        "inline-flex rounded-full border px-2.5 py-0.5 text-[12px] font-medium",
        styles[status],
      )}
    >
      {label[status]}
    </span>
  );
}
