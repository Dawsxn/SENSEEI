/** The trial's event log, from the browser's side (docs/context/trial.md).
 *
 * Anything can call `logTrial`; it does nothing unless a participant's screen
 * has switched logging on with `useTrialLogging`, so the shared tutoring
 * components log freely without knowing whether they are in a trial.
 *
 * Events wait in a queue and go to the server in batches every few seconds, and
 * once more when the page is hidden or closed, through `sendBeacon` so the last
 * batch survives the tab closing. Each carries the time it happened, so a late
 * batch keeps its true order. Nothing typed or pasted is ever sent: a paste is
 * its length. */

import { useEffect } from "react";

export type TrialEventKind =
  | "panel_opened"
  | "panel_closed"
  | "page_changed"
  | "reply_shown"
  | "first_keystroke"
  | "paste"
  | "tab_left"
  | "tab_returned";

interface QueuedEvent {
  kind: TrialEventKind;
  at: string;
  data?: Record<string, string | number | boolean>;
}

const FLUSH_MS = 5000;
const MAX_BATCH = 200;

let enabled = false;
let queue: QueuedEvent[] = [];

export function logTrial(
  kind: TrialEventKind,
  data?: Record<string, string | number | boolean>,
): void {
  if (!enabled) return;
  queue.push({ kind, at: new Date().toISOString(), ...(data ? { data } : {}) });
}

function take(): QueuedEvent[] {
  const batch = queue.slice(0, MAX_BATCH);
  queue = queue.slice(MAX_BATCH);
  return batch;
}

async function flush(): Promise<void> {
  while (queue.length) {
    const events = take();
    try {
      await fetch("/trial/events", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ events }),
        keepalive: true,
      });
    } catch {
      // Put them back for the next try; losing the network should not lose them.
      queue = [...events, ...queue];
      return;
    }
  }
}

/** The last batch, as the page goes away. A normal request may be cut off by the
 *  tab closing; a beacon is delivered anyway. */
function beacon(): void {
  while (queue.length) {
    const body = new Blob([JSON.stringify({ events: take() })], { type: "application/json" });
    navigator.sendBeacon?.("/trial/events", body);
  }
}

/** Switch the log on while a participant's screen is open. Also records leaving
 *  and returning to the tab, which only the page itself can see. */
export function useTrialLogging(on: boolean): void {
  useEffect(() => {
    if (!on) return;
    enabled = true;
    const tick = setInterval(() => void flush(), FLUSH_MS);
    const onVisibility = () => {
      if (document.visibilityState === "hidden") {
        logTrial("tab_left");
        beacon();
      } else {
        logTrial("tab_returned");
      }
    };
    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("pagehide", beacon);
    return () => {
      clearInterval(tick);
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("pagehide", beacon);
      void flush();
      enabled = false;
    };
  }, [on]);
}

/** For tests: what is waiting to be sent, and a clean slate. */
export const __queue = {
  peek: () => queue.slice(),
  reset: () => {
    queue = [];
    enabled = false;
  },
  enable: () => {
    enabled = true;
  },
};
