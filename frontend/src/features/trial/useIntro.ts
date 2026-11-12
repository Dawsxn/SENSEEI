import { useEffect, useState } from "react";

import { useTrialStatus } from "./useTrial";

/** Seconds into the clock after which an open screen counts as a return, not a
 *  first visit. Long enough for a slow first load to still show the intro. */
const RELOAD_GRACE = 15;

/** Whether "Before you start" is showing, and how to close it.
 *
 * It opens with the screen. For a trial participant who reloads partway, it
 * stays closed: they already started, and the clock is already running. Every
 * group's intro behaves the same way, so no group sees it more than another.
 * Outside the trial nothing changes: it opens each time. */
export function useIntro(participant: boolean): [boolean, () => void] {
  const [open, setOpen] = useState(true);
  const { data: status } = useTrialStatus();
  const underway =
    participant &&
    status?.seconds_left != null &&
    status.seconds_left < status.minutes * 60 - RELOAD_GRACE;
  useEffect(() => {
    if (underway) setOpen(false);
  }, [underway]);
  return [open, () => setOpen(false)];
}
