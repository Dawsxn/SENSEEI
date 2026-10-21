/** The trial's two control groups (docs/context/trial.md).
 *
 * - **Chatbot**: the reading beside a plain chat on the same model as SENSEE-I,
 *   with no instructions and no copy of the reading.
 * - **Reading only**: the reading, and nothing else.
 *
 * Both are built from the SEE-I screens' parts, so the groups differ only in
 * what the study means them to: the same top bar and countdown, the same PDF
 * pane, the same "Before you start", the same green Done, the same endings. Done
 * asks first, since it cannot be undone, and is recorded; for the reading-only
 * group it is the measure their exclusion rule uses. */

import { useQueryClient } from "@tanstack/react-query";
import { Suspense, lazy, useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { ConfirmDialog } from "../../components/ConfirmDialog";
import { Button } from "../../components/ui/button";
import { finishTrial, readingFileUrl } from "../../lib/api";
import { cn } from "../../lib/utils";
import { useReading } from "../readings/useReadings";
import { ReadingIntroDialog } from "../tutoring/ReadingIntroDialog";
import { ReadingPanel } from "../tutoring/ReadingPanel";
import { ChatText } from "./ChatText";
import { TrialClock, useTimeUp } from "./TrialClock";
import { logTrial, useTrialLogging } from "./trialLog";
import { useChatbot } from "./useChatbot";
import { useStartTrialClock, useTrialStatus } from "./useTrial";

const PdfPanel = lazy(() =>
  import("../tutoring/PdfPanel").then((m) => ({ default: m.PdfPanel })),
);

const INTRO = {
  chatbot:
    "Read the material. You can use the chatbot beside it however you like. Press Done when you're finished.",
  reading: "Read the material in its entirety. Press Done when you're finished.",
};

/** Seconds into the clock after which an open screen counts as a return, not a
 *  first visit. Long enough for a slow first load to still show the intro. */
const RELOAD_GRACE = 15;

const DONE_TEXT = "You're done. Please stay at your seat until time is up.";
const TIME_UP_TEXT = "Time's up. Please wait for the next instructions.";

/** What every control-group screen shares: the clock, logging, the intro, and
 *  Done with its confirmation. */
function useControlGroup() {
  const { readingId } = useParams<{ readingId: string }>();
  const reading = useReading(readingId);
  const { data: status } = useTrialStatus();
  const timeUp = useTimeUp();
  const [intro, setIntro] = useState(true);
  // "Before you start" is for the start. A participant reloading partway
  // through already started, so it stays closed for them.
  const underway =
    status?.seconds_left != null && status.seconds_left < status.minutes * 60 - RELOAD_GRACE;
  useEffect(() => {
    if (underway) setIntro(false);
  }, [underway]);
  const [confirming, setConfirming] = useState(false);
  const queryClient = useQueryClient();
  useStartTrialClock(true);
  useTrialLogging(true);

  const done = !!status?.done;
  async function finish() {
    setConfirming(false);
    queryClient.setQueryData(["trial"], await finishTrial());
  }
  return {
    reading,
    ended: done || timeUp,
    endText: timeUp && !done ? TIME_UP_TEXT : DONE_TEXT,
    intro,
    closeIntro: () => setIntro(false),
    confirming,
    askToFinish: () => setConfirming(true),
    cancelFinish: () => setConfirming(false),
    finish,
  };
}

function TopBar({ title, done }: { title: string; done?: React.ReactNode }) {
  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b px-4 sm:px-5">
      <span className="min-w-0 truncate text-[14px] font-medium">{title}</span>
      <div className="ml-auto flex shrink-0 items-center gap-2">
        <TrialClock />
        {done}
      </div>
    </header>
  );
}

function Reading({ state }: { state: ReturnType<typeof useReading> }) {
  const { data: reading, isLoading, isError } = state;
  if (isLoading) return <Notice>Loading reading…</Notice>;
  if (isError || !reading) return <Notice>Couldn&rsquo;t load this reading.</Notice>;
  return reading.has_file ? (
    <Suspense fallback={<Notice>Loading reading…</Notice>}>
      <PdfPanel
        fileUrl={readingFileUrl(reading.id)}
        fallback={<ReadingPanel content={reading.content} />}
      />
    </Suspense>
  ) : (
    <ReadingPanel content={reading.content} />
  );
}

function EndStrip({ children }: { children: React.ReactNode }) {
  return (
    <div className="shrink-0 border-t px-6 py-4 text-center text-[13px] text-muted-foreground">
      {children}
    </div>
  );
}

function FinishDialog({
  body,
  onConfirm,
  onCancel,
}: {
  body: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <ConfirmDialog
      title="Finish now?"
      confirmLabel="Finish"
      cancelLabel="Cancel"
      onConfirm={onConfirm}
      onCancel={onCancel}
    >
      {body}
    </ConfirmDialog>
  );
}

// --------------------------------------------------------------------------- //
// reading only

export function ReadingOnlyScreen() {
  const g = useControlGroup();
  return (
    <div className="flex h-full flex-col">
      <TopBar title={g.reading.data?.title ?? "…"} />
      <div className="min-h-0 flex-1">
        <Reading state={g.reading} />
      </div>
      {g.ended ? (
        <EndStrip>{g.endText}</EndStrip>
      ) : (
        <footer className="flex shrink-0 items-center justify-end border-t px-4 py-3 sm:px-6">
          <Button onClick={g.askToFinish}>Done</Button>
        </footer>
      )}
      {g.intro && <ReadingIntroDialog body={INTRO.reading} onStart={g.closeIntro} />}
      {g.confirming && (
        <FinishDialog body="You can't undo this." onConfirm={g.finish} onCancel={g.cancelFinish} />
      )}
    </div>
  );
}

// --------------------------------------------------------------------------- //
// chatbot

type Pane = "reading" | "chat";

export function ChatbotScreen() {
  const g = useControlGroup();
  const { state, send } = useChatbot(true);
  const [pane, setPane] = useState<Pane>("chat");

  return (
    <div className="flex h-full flex-col">
      <TopBar
        title={g.reading.data?.title ?? "…"}
        done={
          !g.ended && (
            <Button size="sm" onClick={g.askToFinish}>
              Done
            </Button>
          )
        }
      />

      {/* One pane at a time on a narrow screen, as in the SEE-I session. */}
      <div className="flex shrink-0 gap-1 border-b p-1.5 lg:hidden">
        {(["reading", "chat"] as const).map((p) => (
          <button
            key={p}
            onClick={() => setPane(p)}
            className={cn(
              "flex-1 rounded-md py-1.5 text-[13px] font-medium capitalize transition-colors",
              pane === p ? "bg-muted text-foreground" : "text-muted-foreground",
            )}
          >
            {p}
          </button>
        ))}
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-1 overflow-hidden lg:grid-cols-[46fr_54fr]">
        <div className={cn("h-full min-h-0", pane === "reading" ? "block" : "hidden", "lg:block lg:border-r")}>
          <Reading state={g.reading} />
        </div>
        <div className={cn("flex h-full min-h-0 flex-col", pane === "chat" ? "flex" : "hidden", "lg:flex")}>
          <Conversation lines={state.lines} />
          {state.phase === "error" && !g.ended && (
            <p className="shrink-0 border-t border-fail-border bg-fail px-6 py-3 text-[13px] text-fail-foreground">
              That didn&rsquo;t send. Try again.
            </p>
          )}
          {g.ended ? (
            <EndStrip>{g.endText}</EndStrip>
          ) : (
            <Composer
              disabled={state.phase === "loading" || state.phase === "streaming"}
              onSend={send}
            />
          )}
        </div>
      </div>

      {g.intro && <ReadingIntroDialog body={INTRO.chatbot} onStart={g.closeIntro} />}
      {g.confirming && (
        <FinishDialog
          body="You won't be able to send more messages."
          onConfirm={g.finish}
          onCancel={g.cancelFinish}
        />
      )}
    </div>
  );
}

function Conversation({ lines }: { lines: ReturnType<typeof useChatbot>["state"]["lines"] }) {
  if (lines.length === 0) {
    return (
      <div className="flex min-h-0 flex-1 items-center justify-center text-[14px] text-muted-foreground">
        Ask anything.
      </div>
    );
  }
  return (
    <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5 sm:px-6">
      {lines.map((line) =>
        line.role === "user" ? (
          <div key={line.key} className="my-4 flex justify-end first:mt-0">
            <div className="max-w-[85%] whitespace-pre-wrap rounded-lg bg-muted px-4 py-2.5 text-[14px] leading-relaxed text-[#3f3f46]">
              {line.content}
            </div>
          </div>
        ) : (
          <div key={line.key} className="my-4">
            {line.content ? (
              <ChatText text={line.content} />
            ) : (
              <span className="flex gap-1" aria-label="Chatbot is replying">
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/60"
                    style={{ animationDelay: `${i * 150}ms` }}
                  />
                ))}
              </span>
            )}
          </div>
        ),
      )}
    </div>
  );
}

function Composer({ disabled, onSend }: { disabled: boolean; onSend: (text: string) => void }) {
  const [text, setText] = useState("");
  const [typed, setTyped] = useState(false);
  const ready = !disabled && text.trim().length > 0;

  function send() {
    if (!ready) return;
    onSend(text.trim());
    setText("");
    setTyped(false); // the next first keystroke comes after this reply
  }

  return (
    <div className="shrink-0 border-t p-4">
      <div className="flex items-end gap-2 rounded-md border px-3 py-2 focus-within:ring-2 focus-within:ring-ring">
        <textarea
          value={text}
          rows={1}
          placeholder="Message…"
          aria-label="Message"
          onChange={(e) => {
            if (!typed && e.target.value) {
              setTyped(true);
              logTrial("first_keystroke");
            }
            setText(e.target.value);
          }}
          onPaste={(e) => logTrial("paste", { length: e.clipboardData.getData("text").length })}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
          className="max-h-40 flex-1 resize-none bg-transparent py-1 text-[14px] outline-none placeholder:text-muted-foreground"
        />
        <Button size="sm" onClick={send} disabled={!ready}>
          Send
        </Button>
      </div>
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
