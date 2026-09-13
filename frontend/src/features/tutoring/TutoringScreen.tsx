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
 * largest thing the app ships, and no other screen needs it. */

import { Suspense, lazy, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { useReading } from "../readings/useReadings";
import { readingFileUrl } from "../../lib/api";
import { cn } from "../../lib/utils";
import { ChatPanel } from "./ChatPanel";
import { LeaveSessionDialog } from "./LeaveSessionDialog";
import { ReadingPanel } from "./ReadingPanel";
import { SessionTopBar } from "./SessionTopBar";
import { useTutoringSession } from "./useTutoringSession";

const PdfPanel = lazy(() =>
  import("./PdfPanel").then((m) => ({ default: m.PdfPanel })),
);

type Pane = "reading" | "chat";

export function TutoringScreen() {
  const { readingId } = useParams<{ readingId: string }>();
  const { data: reading, isLoading, isError } = useReading(readingId);
  const { state, submit } = useTutoringSession(readingId ?? "");
  const [pane, setPane] = useState<Pane>("chat");
  const [confirmingExit, setConfirmingExit] = useState(false);
  const navigate = useNavigate();

  const leave = () => navigate("/");

  // Only a running session has anything to lose. Once it has ended it is
  // read-only, so the exit just leaves rather than asking a question with one
  // sensible answer.
  const running = state.phase !== "terminal" && state.phase !== "idle";
  const onExit = () => (running ? setConfirmingExit(true) : leave());

  return (
    <div className="flex h-full flex-col">
      <SessionTopBar
        readingTitle={reading?.title ?? "…"}
        section={reading?.class_name ?? ""}
        currentStep={state.currentStep}
        status={state.status}
        phase={state.phase}
        onExit={onExit}
      />

      {confirmingExit && (
        <LeaveSessionDialog onConfirm={leave} onCancel={() => setConfirmingExit(false)} />
      )}

      <PaneToggle pane={pane} onChange={setPane} />

      {/* Not 50/50: the reading is the narrower column, matching the mockup's
          ~46/54 split. */}
      <div className="grid min-h-0 flex-1 grid-cols-1 overflow-hidden lg:grid-cols-[46fr_54fr]">
        <div className={cn("h-full min-h-0", pane === "reading" ? "block" : "hidden", "lg:block")}>
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
          <ChatPanel state={state} onSubmit={submit} />
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
