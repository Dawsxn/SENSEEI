/** The participant's countdown, in the top bar of the reading and the session.
 *
 * The same in every group, so no group is treated differently. In the last five
 * minutes it turns amber; at zero it asks the server again, which is what ends
 * the session on the record, and the screens follow the answer. */

import { useQueryClient } from "@tanstack/react-query";
import { Clock } from "lucide-react";
import { useEffect } from "react";

import { cn } from "../../lib/utils";
import { useCountdown, useTrialStatus } from "./useTrial";

/** When the countdown turns amber. */
const LATE_SECONDS = 5 * 60;

export function TrialClock() {
  const { data, dataUpdatedAt } = useTrialStatus();
  const left = useCountdown(data?.seconds_left, dataUpdatedAt);
  const queryClient = useQueryClient();

  const reachedZero = left === 0 && data !== undefined && !data.time_up;
  useEffect(() => {
    if (reachedZero) void queryClient.invalidateQueries({ queryKey: ["trial"] });
  }, [reachedZero, queryClient]);

  if (left === null) return null;
  const late = left <= LATE_SECONDS;
  return (
    <div
      role="timer"
      aria-label="Time left"
      className={cn(
        "flex h-8 shrink-0 items-center gap-1.5 rounded-md px-2.5",
        late && "bg-[#fffbeb]",
      )}
    >
      <Clock className={cn("h-[15px] w-[15px]", late ? "text-[#92400e]" : "text-muted-foreground")} />
      <span
        className={cn(
          "text-[13px] font-medium tabular-nums",
          late ? "text-[#92400e]" : "text-[#3f3f46]",
        )}
      >
        {formatClock(left)} left
      </span>
    </div>
  );
}

/** `32:10`, or `4:58` under ten minutes. */
export function formatClock(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

/** Whether the participant's time is up, by the server's word or the countdown's. */
export function useTimeUp(): boolean {
  const { data, dataUpdatedAt } = useTrialStatus();
  const left = useCountdown(data?.seconds_left, dataUpdatedAt);
  return !!data?.time_up || left === 0;
}
