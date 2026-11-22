/** The trial's time pop-ups, in place of a visible countdown.
 *
 * In the user acceptance test a running clock confused people, so no timer is
 * shown. Instead a small card appears at set points ("5 minutes left") and
 * stays until closed. It never takes the cursor, so it cannot swallow an Enter
 * meant for the answer box. A point already passed when the screen opens (a
 * reload) is not shown late. */

import { Clock, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

export interface TimeNotice {
  /** Shown once the seconds left reach this. */
  at: number;
  title: string;
  body?: string;
}

export const minutesLeft = (minutes: number[], body?: string): TimeNotice[] =>
  minutes.map((m) => ({ at: m * 60, title: m === 1 ? "1 minute left" : `${m} minutes left`, body }));

/** The session's (reading and tutoring, or a control group's screen). */
export const SESSION_NOTICES = minutesLeft([15, 5, 1]);
export const PRETEST_NOTICES = minutesLeft([1], "Your answer saves as you type.");
export const POSTTEST_NOTICES = minutesLeft([10, 5, 1], "Your answers save as you go.");

/** The latest notice due by `left` seconds, until it is closed or replaced. */
export function useTimeNotices(left: number | null, notices: TimeNotice[]) {
  const fired = useRef<Set<number> | null>(null);
  const [current, setCurrent] = useState<TimeNotice | null>(null);

  useEffect(() => {
    if (left === null || left <= 0) return;
    const due = notices.filter((n) => left <= n.at);
    if (fired.current === null) {
      // The first reading: anything already due was missed, not new.
      fired.current = new Set(due.map((n) => n.at));
      return;
    }
    const fresh = due.filter((n) => !fired.current!.has(n.at));
    if (!fresh.length) return;
    fresh.forEach((n) => fired.current!.add(n.at));
    setCurrent(fresh.reduce((a, b) => (b.at < a.at ? b : a)));
  }, [left, notices]);

  return [current, () => setCurrent(null)] as const;
}

export function TimeNoticeCard({ notice, onClose }: { notice: TimeNotice; onClose: () => void }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed left-1/2 top-[68px] z-40 flex w-[420px] max-w-[calc(100%-32px)] -translate-x-1/2 items-start gap-3 rounded-lg border bg-background px-4 py-3.5 shadow-lg"
    >
      <Clock className="mt-px h-[18px] w-[18px] shrink-0 text-primary" aria-hidden />
      <div className="min-w-0 flex-1">
        <div className="text-[14px] font-semibold">{notice.title}</div>
        {notice.body && (
          <div className="mt-1 text-[13px] leading-[1.55] text-muted-foreground">{notice.body}</div>
        )}
      </div>
      <button
        onClick={onClose}
        aria-label="Close"
        tabIndex={-1}
        className="shrink-0 text-muted-foreground hover:text-foreground"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

/** Both together, for a screen that only needs to show them. */
export function TimeNotices({ left, notices }: { left: number | null; notices: TimeNotice[] }) {
  const [current, close] = useTimeNotices(left, notices);
  return current ? <TimeNoticeCard notice={current} onClose={close} /> : null;
}
