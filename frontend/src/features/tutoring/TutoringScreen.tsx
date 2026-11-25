/** The split-screen tutoring view: reading on the left, chat on the right.
 *
 * The reading id comes from the route; the reading's text and class are fetched
 * for display while the session itself starts and streams in parallel (the
 * backend already has the reading, so the chat does not wait on the fetch).
 *
 * Responsive: two panes side by side from `lg` up. Below that a split does not
 * fit, so one pane shows at a time behind a Reading / Chat toggle, defaulting to
 * the chat since that is where the work happens.
 *
 * The reading shows as its original PDF when one is stored, and as the extracted
 * text when it is not. The viewer is loaded lazily because pdfjs is by far the
 * largest thing the app ships, and no other screen needs it.
 *
 * A reload picks the same session back up, for everyone: a trial participant's
 * from the server, anyone else's from what the tab remembers. Leaving is the
 * exit, or the browser's back, and both ask first while the session runs; a
 * session left that way is kept on the server as `left` and never offered back.
 *
 * Outside the trial the session waits for the reading, so a reading that fails
 * to load starts nothing behind its notice.
 *
 * A trial participant gets the same screen with a countdown, no way out, and an
 * ending in the trial's words. */

import { Suspense, lazy, useEffect, useRef, useState } from "react";
import { useBlocker, useNavigate, useParams } from "react-router-dom";

import { useReading } from "../readings/useReadings";
import { TrialClock, useTimeUp } from "../trial/TrialClock";
import { logTrial, setTrialContext, useTrialLogging } from "../trial/trialLog";
import { useIsParticipant, useTestHandoff, useTrialStatus } from "../trial/useTrial";
import { leaveSession, readingFileUrl } from "../../lib/api";
import { cn } from "../../lib/utils";
import { ChatPanel } from "./ChatPanel";
import { LeaveSessionDialog } from "./LeaveSessionDialog";
import { ComponentsPanel, RubricPanel } from "./ReferencePanel";
import { ReadingPanel } from "./ReadingPanel";
import { ReadingUnavailable } from "./ReadingUnavailable";
import { SessionTopBar } from "./SessionTopBar";
import { forgetSession, useTutoringSession } from "./useTutoringSession";

const PdfPanel = lazy(() =>
  import("./PdfPanel").then((m) => ({ default: m.PdfPanel })),
);

type Pane = "reading" | "chat";

export function TutoringScreen() {
  const { readingId } = useParams<{ readingId: string }>();
  const { data: reading, isLoading, isError, error, refetch } = useReading(readingId);
  const participant = useIsParticipant();
  const trial = useTrialStatus();
  const timeUp = useTimeUp();
  const { state, submit, retry } = useTutoringSession(readingId ?? "", {
    resumeId: trial.data?.session?.id ?? null,
    // A participant's session may already exist; find out before starting one.
    // Anyone else's waits for the reading, so a broken one starts nothing.
    wait: participant ? !trial.data : !reading,
    remember: !participant,
  });
  const [pane, setPane] = useState<Pane>("chat");
  const [confirmingExit, setConfirmingExit] = useState(false);
  const [panel, setPanel] = useState<"components" | "rubric" | null>(null);
  const navigate = useNavigate();
  useTrialLogging(participant);
  // The end strip's button moves them on, so they can read how it ended first.
  const continueToPostTest = useTestHandoff(
    participant && (timeUp || state.phase === "terminal"),
    false,
  );
  const hasTests = trial.data?.test_stage != null;

  // Every event from this screen says which step, and which attempt at it, the
  // participant was on. The attempt is the one they are making next.
  // Not cleared between turns, only when the screen closes: a reply is logged
  // as it lands, against the attempt it answered, before this moves on.
  useEffect(() => {
    if (!state.currentStep) return;
    setTrialContext({ step: state.currentStep, attempt: state.attemptsUsed + 1 });
  }, [state.currentStep, state.attemptsUsed]);
  useEffect(() => () => setTrialContext({}), []);

  // Every open and close is recorded, including the close that comes from
  // switching straight to the other panel.
  const togglePanel = (p: "components" | "rubric") => {
    if (panel) logTrial("panel_closed", { panel });
    if (panel !== p) logTrial("panel_opened", { panel: p });
    setPanel(panel === p ? null : p);
  };
  const closePanel = () => {
    if (panel) logTrial("panel_closed", { panel });
    setPanel(null);
  };

  // Only a running session has anything to lose. Once it has ended it is
  // read-only, so the exit just leaves rather than asking a question with one
  // sensible answer.
  const running = state.phase !== "terminal" && state.phase !== "idle";

  /** Done with this session for good: the server keeps it as `left` if it was
   *  still running, and the tab forgets it, so coming back starts a new one. */
  const forget = () => {
    if (running && state.sessionId) void leaveSession(state.sessionId).catch(() => {});
    if (readingId) forgetSession(readingId);
  };

  // Set just before leaving on purpose, so the back guard lets that one through.
  const leaving = useRef(false);
  const leave = () => {
    forget();
    leaving.current = true;
    navigate("/");
  };
  const onExit = () => (running ? setConfirmingExit(true) : leave());

  // The browser's back (or a phone's back gesture) asks the same question as
  // the exit. A participant has no way out to guard.
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      !participant &&
      running &&
      !leaving.current &&
      currentLocation.pathname !== nextLocation.pathname,
  );

  // The criteria the newest tutor message reported, so the rubric panel can
  // mark the same ones the chat tagged.
  const unmet = [...state.messages].reverse().find((m) => m.unmet.length > 0)?.unmet ?? [];

  // Outside the trial, a reading that failed takes the whole screen: nothing
  // has started, so there is no progress or reference to show.
  if (!participant && isError) {
    return (
      <div className="relative flex h-full flex-col">
        <SessionTopBar
          readingTitle=""
          section=""
          currentStep={null}
          status={null}
          phase="idle"
          onExit={leave}
          panel={null}
          onTogglePanel={() => {}}
          bare
        />
        <div className="min-h-0 flex-1">
          <ReadingUnavailable error={error} onRetry={() => void refetch()} />
        </div>
      </div>
    );
  }

  return (
    <div className="relative flex h-full flex-col">
      <SessionTopBar
        readingTitle={reading?.title ?? "…"}
        section={reading?.class_name ?? ""}
        currentStep={state.currentStep}
        status={state.status}
        phase={state.phase}
        onExit={onExit}
        panel={panel}
        onTogglePanel={togglePanel}
        clock={participant ? <TrialClock /> : undefined}
      />

      {panel === "components" && (
        <ComponentsPanel
          components={reading?.core_components ?? []}
          onClose={closePanel}
        />
      )}
      {panel === "rubric" && (
        <RubricPanel
          currentStep={state.currentStep}
          unmet={unmet}
          onClose={closePanel}
        />
      )}

      {confirmingExit && (
        <LeaveSessionDialog onConfirm={leave} onCancel={() => setConfirmingExit(false)} />
      )}
      {blocker.state === "blocked" && (
        <LeaveSessionDialog
          onConfirm={() => {
            forget();
            blocker.proceed();
          }}
          onCancel={() => blocker.reset()}
        />
      )}

      <PaneToggle pane={pane} onChange={setPane} />

      {/* Not 50/50: the reading is the narrower column, matching the mockup's
          ~46/54 split. */}
      <div className="grid min-h-0 flex-1 grid-cols-1 overflow-hidden lg:grid-cols-[46fr_54fr]">
        <div className={cn("h-full min-h-0", pane === "reading" ? "block" : "hidden", "lg:block lg:border-r")}>
          {isLoading && <PaneNotice>Loading reading…</PaneNotice>}
          {isError && <PaneNotice>Couldn't load this reading.</PaneNotice>}
          {reading &&
            (reading.has_file ? (
              <Suspense fallback={<PaneNotice>Loading reading…</PaneNotice>}>
                <PdfPanel
                  fileUrl={readingFileUrl(reading.id)}
                  fallback={<ReadingPanel content={reading.content} />}
                />
              </Suspense>
            ) : (
              <ReadingPanel content={reading.content} />
            ))}
        </div>
        <div className={cn("h-full min-h-0", pane === "chat" ? "block" : "hidden", "lg:block")}>
          <ChatPanel
            state={state}
            onSubmit={submit}
            trial={
              participant
                ? { timeUp, onContinue: hasTests ? continueToPostTest : undefined }
                : undefined
            }
            onRetry={participant ? undefined : () => void retry()}
            links={
              reading
                ? {
                    reading: `/classes/${reading.class_id}/readings/${reading.id}`,
                    review: state.sessionId
                      ? `/classes/${reading.class_id}/readings/${reading.id}/sessions/${state.sessionId}`
                      : null,
                  }
                : undefined
            }
          />
        </div>
      </div>
    </div>
  );
}

function PaneNotice({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-full items-center justify-center p-6 text-[14px] text-muted-foreground">
      {children}
    </div>
  );
}

/** Reading / Chat switch, shown only below the `lg` breakpoint. */
function PaneToggle({ pane, onChange }: { pane: Pane; onChange: (p: Pane) => void }) {
  return (
    <div className="flex shrink-0 gap-1 border-b p-1.5 lg:hidden">
      {(["reading", "chat"] as const).map((p) => (
        <button
          key={p}
          onClick={() => onChange(p)}
          className={cn(
            "flex-1 rounded-md py-1.5 text-[13px] font-medium capitalize transition-colors",
            pane === p ? "bg-muted text-foreground" : "text-muted-foreground",
          )}
        >
          {p}
        </button>
      ))}
    </div>
  );
}
