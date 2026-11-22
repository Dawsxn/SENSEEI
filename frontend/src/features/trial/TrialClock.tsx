/** The participant's session clock, on the reading and the session screens.
 *
 * It is not shown: a running countdown confused people in the user acceptance
 * test. It keeps time out of sight and shows the time pop-ups instead (15, 5
 * and 1 minute left, plus any `extra`). The same in every group, so no group is
 * treated differently. At zero it asks the server again, which is what ends the
 * session on the record, and the screens follow the answer. */

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo } from "react";

import { SESSION_NOTICES, TimeNotices, type TimeNotice } from "./TimeNotices";
import { useCountdown, useTrialStatus } from "./useTrial";

export function TrialClock({ extra }: { extra?: TimeNotice[] }) {
  const { data, dataUpdatedAt } = useTrialStatus();
  const left = useCountdown(data?.seconds_left, dataUpdatedAt);
  const queryClient = useQueryClient();

  const reachedZero = left === 0 && data !== undefined && !data.time_up;
  useEffect(() => {
    if (reachedZero) void queryClient.invalidateQueries({ queryKey: ["trial"] });
  }, [reachedZero, queryClient]);

  const notices = useMemo(() => [...SESSION_NOTICES, ...(extra ?? [])], [extra]);
  return <TimeNotices left={left} notices={notices} />;
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
