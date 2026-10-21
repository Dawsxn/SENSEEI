import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { getBatch, getBatches, getTrialStatus } from "../../lib/api";
import { useMe } from "../auth/useAuth";

/** Whether the signed-in user is a trial participant, signed in by ID. The
 *  server only lets a participant stay signed in while trial mode is on, so
 *  this needs nothing from the trial setting itself. */
export function useIsParticipant(): boolean {
  const { data: user } = useMe();
  return !!user?.participant;
}

/** The participant's own status: their mode, reading, session and time. Only
 *  asked for by a participant; everyone else gets `undefined`. */
export function useTrialStatus() {
  const participant = useIsParticipant();
  return useQuery({
    queryKey: ["trial"],
    queryFn: getTrialStatus,
    enabled: participant,
  });
}

export function useBatches() {
  return useQuery({ queryKey: ["batches"], queryFn: getBatches });
}

export function useBatch(batchId: string | undefined) {
  return useQuery({
    queryKey: ["batch", batchId],
    queryFn: () => getBatch(batchId!),
    enabled: !!batchId,
  });
}

/** Seconds left, counting down from what the server last said.
 *
 * The server holds the clock; this only draws it. It counts from the moment the
 * server's answer arrived rather than from a deadline in the browser's own
 * time, so a computer whose clock is wrong still shows the right time left. */
export function useCountdown(
  secondsLeft: number | null | undefined,
  receivedAt: number,
): number | null {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const tick = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(tick);
  }, []);
  if (secondsLeft === null || secondsLeft === undefined) return null;
  return Math.max(0, secondsLeft - Math.floor((now - receivedAt) / 1000));
}
