/** The reading step: read the whole thing, then say so.
 *
 * It sits between choosing a reading and the session itself, and it is where
 * the session is created. Nothing is written until the student presses Done, so
 * opening a reading and thinking better of it leaves nothing behind.
 *
 * Lives beside the tutoring screen rather than the reading list because it is
 * the session's on-ramp and composes the same two reading panes.
 *
 * The Done button is never disabled. The page knows which PDF page is on screen
 * and could require the last one, but scrolling is not reading: it would stop
 * someone who read quickly and wave through someone who dragged the scrollbar.
 *
 * Going back still asks first. No session exists to discard, so the warning is
 * not the session one, but the student loses their place in the reading and the
 * back link sits next to nothing else, which makes it easy to hit by accident.
 *
 * For a trial participant this is where their time starts. They have no back
 * link, since they have nowhere else to go, and no class label, which could name
 * their group. The countdown takes the right of the bar.
 */

import { Suspense, lazy, useEffect, useMemo, useState } from "react";
import { ChevronLeft } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";

import { ConfirmDialog } from "../../components/ConfirmDialog";
import { Button } from "../../components/ui/button";
import { readingFileUrl } from "../../lib/api";
import { AboutSeei, SessionGuide, useConcept } from "../trial/Briefing";
import { useReading } from "../readings/useReadings";
import { TrialClock, useTimeUp } from "../trial/TrialClock";
import { setTrialContext, useTrialLogging } from "../trial/trialLog";
import { useIntro } from "../trial/useIntro";
import { TimeUpDialog } from "../trial/TimeUpDialog";
import {
  useIsParticipant,
  useStartTrialClock,
  useTestHandoff,
  useTrialStatus,
} from "../trial/useTrial";
import { ReadingIntroDialog } from "./ReadingIntroDialog";
import { ReadingPanel } from "./ReadingPanel";

const PdfPanel = lazy(() =>
  import("./PdfPanel").then((m) => ({ default: m.PdfPanel })),
);

/** When a participant is nudged that the session is waiting. */
const READING_NUDGE_SECONDS = 10 * 60;

export function ReadingStepScreen() {
  const { readingId } = useParams<{ readingId: string }>();
  const { data: reading, isLoading, isError } = useReading(readingId);
  const navigate = useNavigate();
  const participant = useIsParticipant();
  const [showIntro, closeIntro] = useIntro(participant);
  const [confirmingLeave, setConfirmingLeave] = useState(false);
  const timeUp = useTimeUp();
  const moveOn = useTestHandoff(participant && timeUp, false);
  const { data: status } = useTrialStatus();
  const timeUpPopup = participant && timeUp && status?.test_stage != null;
  // A participant first reads what SENSEE-I is and how its screen works, before
  // the reading and its clock. Not timed; a reload before Start shows it again.
  const [guide, setGuide] = useState<"about" | "screen" | "done">("about");
  const briefing = participant && showIntro && guide !== "done";
  const [confirmingDone, setConfirmingDone] = useState(false);
  const concept = useConcept();
  // Ten minutes into the clock: a nudge that the session is waiting.
  const nudge = useMemo(
    () =>
      status
        ? [{
            at: status.minutes * 60 - READING_NUDGE_SECONDS,
            title: "You've been reading for 10 minutes",
            body:
              "When you're confident you understand the concept, press Done to start the tutoring session. The reading stays open beside it.",
          }]
        : [],
    [status],
  );
  // Their time starts when they press Start in Before you start.
  useStartTrialClock(participant && !showIntro);
  useTrialLogging(participant);
  // Page changes here happen before the session: reading, not a SEE-I step.
  useEffect(() => {
    setTrialContext({ step: "Reading" });
    return () => setTrialContext({});
  }, []);

  if (briefing && guide === "about") return <AboutSeei onContinue={() => setGuide("screen")} />;
  if (briefing) return <SessionGuide onContinue={() => setGuide("done")} />;

  return (
    <div className="flex h-full flex-col">
      <header className="flex h-14 shrink-0 items-center gap-3 border-b px-3 sm:px-5">
        {!participant && (
          <>
            <button
              onClick={() => setConfirmingLeave(true)}
              className="flex items-center gap-1.5 text-[13px] text-muted-foreground transition-colors hover:text-foreground"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
              Readings
            </button>
            <div className="h-4 w-px shrink-0 bg-border" />
          </>
        )}
        <div className="flex min-w-0 items-baseline gap-2">
          <span className="truncate text-[14px] font-medium">
            {reading?.title ?? "…"}
          </span>
          {!participant && (
            <span className="hidden shrink-0 text-[13px] text-muted-foreground sm:inline">
              {reading?.class_name ?? ""}
            </span>
          )}
        </div>
        {participant && (
          <div className="ml-auto">
            <TrialClock extra={nudge} />
          </div>
        )}
      </header>

      <div className="min-h-0 flex-1">
        {isLoading && <Notice>Loading reading…</Notice>}
        {isError && <Notice>Couldn't load this reading.</Notice>}
        {reading &&
          (reading.has_file ? (
            <Suspense fallback={<Notice>Loading reading…</Notice>}>
              <PdfPanel
                fileUrl={readingFileUrl(reading.id)}
                fallback={<ReadingPanel content={reading.content} />}
              />
            </Suspense>
          ) : (
            <ReadingPanel content={reading.content} />
          ))}
      </div>

      {/* Pinned, so finishing does not require scrolling back to anywhere. */}
      {participant && timeUp ? (
        <footer className="shrink-0 border-t px-6 py-4 text-center text-[13px] text-muted-foreground">
          {timeUpPopup ? "Time's up." : "Time's up. Please wait for the next instructions."}
        </footer>
      ) : (
        <footer className="flex shrink-0 items-center justify-end border-t px-4 py-3 sm:px-6">
          <Button
            onClick={() =>
              participant ? setConfirmingDone(true) : navigate(`/tutor/${readingId}`)
            }
          >
            Done
          </Button>
        </footer>
      )}

      {showIntro && !participant && <ReadingIntroDialog onStart={closeIntro} />}
      {showIntro && participant && (
        <ReadingIntroDialog onStart={closeIntro}>
          <div className="text-[14px] leading-[1.6] text-muted-foreground">
            <p className="mt-2">You have {status?.minutes ?? 35} minutes for two parts:</p>
            <ol className="mt-2 list-decimal space-y-1.5 pl-5">
              <li>
                <span className="font-medium text-foreground">Reading.</span> Read the material on
                this screen until you understand the concept of {concept}. We suggest about 10
                minutes.
              </li>
              <li>
                <span className="font-medium text-foreground">Tutoring session.</span> When you
                press Done, the screen splits: the reading stays on one side, and the learning tool
                opens on the other. There you explain the concept through the four SEE-I steps.
              </li>
            </ol>
            <p className="mt-2">
              You can still look at the reading during the session, but press Done only once
              you&rsquo;re confident you understand the concept.
            </p>
          </div>
        </ReadingIntroDialog>
      )}
      {confirmingDone && (
        <ConfirmDialog
          title="Start the tutoring session?"
          confirmLabel="Start session"
          cancelLabel="Cancel"
          onConfirm={() => navigate(`/tutor/${readingId}`)}
          onCancel={() => setConfirmingDone(false)}
        >
          Only continue if you&rsquo;re confident you understand the concept of {concept}. The
          reading stays open beside the session.
        </ConfirmDialog>
      )}
      {timeUpPopup && <TimeUpDialog onContinue={() => void moveOn()} />}

      {confirmingLeave && (
        <ConfirmDialog
          title="Go back to readings?"
          confirmLabel="Go back"
          onConfirm={() => navigate("/")}
          onCancel={() => setConfirmingLeave(false)}
        >
          You have not started the session yet, so there is nothing to discard. You
          will lose your place in the reading.
        </ConfirmDialog>
      )}
    </div>
  );
}

function Notice({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-full items-center justify-center p-6 text-[14px] text-muted-foreground">
      {children}
    </div>
  );
}
