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

import { useQueryClient } from "@tanstack/react-query";
import { Suspense, lazy, useEffect, useRef, useState } from "react";
import { ChevronLeft } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";

import { ConfirmDialog } from "../../components/ConfirmDialog";
import { Button } from "../../components/ui/button";
import { readingFileUrl, startTrialClock } from "../../lib/api";
import { useReading } from "../readings/useReadings";
import { TrialClock, useTimeUp } from "../trial/TrialClock";
import { useIsParticipant } from "../trial/useTrial";
import { ReadingIntroDialog } from "./ReadingIntroDialog";
import { ReadingPanel } from "./ReadingPanel";

const PdfPanel = lazy(() =>
  import("./PdfPanel").then((m) => ({ default: m.PdfPanel })),
);

export function ReadingStepScreen() {
  const { readingId } = useParams<{ readingId: string }>();
  const { data: reading, isLoading, isError } = useReading(readingId);
  const navigate = useNavigate();
  const [showIntro, setShowIntro] = useState(true);
  const [confirmingLeave, setConfirmingLeave] = useState(false);
  const participant = useIsParticipant();
  const timeUp = useTimeUp();
  useStartTrialClock(participant);

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
            <TrialClock />
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
          Time&rsquo;s up. Please wait for the next instructions.
        </footer>
      ) : (
        <footer className="flex shrink-0 items-center justify-end border-t px-4 py-3 sm:px-6">
          <Button onClick={() => navigate(`/tutor/${readingId}`)}>Done</Button>
        </footer>
      )}

      {showIntro && <ReadingIntroDialog onStart={() => setShowIntro(false)} />}

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

/** A participant's time starts when their reading opens. Asked once; the server
 *  ignores the ask after the first, so a reload does not restart the clock. */
function useStartTrialClock(participant: boolean) {
  const queryClient = useQueryClient();
  const asked = useRef(false);
  useEffect(() => {
    if (!participant || asked.current) return;
    asked.current = true;
    void startTrialClock().then((status) => queryClient.setQueryData(["trial"], status));
  }, [participant, queryClient]);
}

function Notice({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-full items-center justify-center p-6 text-[14px] text-muted-foreground">
      {children}
    </div>
  );
}
