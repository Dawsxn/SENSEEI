import { Check } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "../../components/ui/button";
import { cn } from "../../lib/utils";
import type { ChatMessage, TutoringState } from "./useTutoringSession";
import type { SeeiStep } from "./types";
import { useSmoothText } from "./useSmoothText";

const STEPS: SeeiStep[] = ["State", "Elaborate", "Exemplify", "Illustrate"];

const PLACEHOLDER: Record<SeeiStep, string> = {
  State: "Write your statement…",
  Elaborate: "Write your elaboration…",
  Exemplify: "Write your example…",
  Illustrate: "Write your illustration…",
};

interface ChatPanelProps {
  state: TutoringState;
  onSubmit: (text: string) => void;
}

/** Is a tutor reply expected but not yet producing text? Covers both the opening
 *  question and the gap after a submit while grading runs, so the wait looks the
 *  same every time rather than a placeholder once and a bare caret after. */
function awaitingReply(state: TutoringState): boolean {
  const last = state.messages[state.messages.length - 1];
  if (state.phase === "starting") return true;
  if (state.phase !== "streaming") return false;
  if (!last || last.role === "student") return true;
  const tutor = last.role === "tutor" || last.role === "fallback";
  return tutor && last.streaming && last.content === "";
}

export function ChatPanel({ state, onSubmit }: ChatPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const waiting = awaitingReply(state);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [state.messages, waiting]);

  const currentIndex = state.currentStep ? STEPS.indexOf(state.currentStep) : 0;
  const stepPassed = (step: SeeiStep) =>
    state.status === "complete" || STEPS.indexOf(step) < currentIndex;

  let lastStep: SeeiStep | null = null;

  return (
    <div className="flex h-full flex-col">
      <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto px-5 py-5 sm:px-6">
        {state.messages.map((m) => {
          // A message that has started but has no text yet is represented by the
          // typing indicator instead, so it is not rendered as an empty line.
          if (m.streaming && m.content === "") return null;

          const passed = m.step ? stepPassed(m.step) : false;
          const isCurrent =
            !!m.step &&
            STEPS.indexOf(m.step) === currentIndex &&
            !passed &&
            state.phase !== "terminal";
          const divider =
            m.step && m.step !== lastStep ? (
              <StepDivider
                key={`d-${m.key}`}
                step={m.step}
                passed={passed}
                current={isCurrent}
                attemptsUsed={state.attemptsUsed}
              />
            ) : null;
          if (m.step) lastStep = m.step;

          return (
            <div key={m.key}>
              {divider}
              <Message message={m} />
            </div>
          );
        })}
        {waiting && <TypingIndicator />}
      </div>

      <Composer state={state} onSubmit={onSubmit} />
    </div>
  );
}

function StepDivider({
  step,
  passed,
  current,
  attemptsUsed,
}: {
  step: SeeiStep;
  passed: boolean;
  current: boolean;
  attemptsUsed: number;
}) {
  return (
    <div className="mb-4 mt-6 flex items-center gap-3 first:mt-0">
      <span
        className={cn(
          "text-[12px] font-medium uppercase tracking-wide",
          passed ? "text-primary" : "text-muted-foreground",
        )}
      >
        {step}
      </span>
      <span className="h-px flex-1 bg-border" />
      {passed ? (
        <Check className="h-4 w-4 text-primary" />
      ) : current ? (
        <AttemptDots used={attemptsUsed} />
      ) : null}
    </div>
  );
}

/** Three dots marking attempt progress within the current step; the filled dot
 *  is the attempt now being made (0-based `used`), matching the design mockup. */
function AttemptDots({ used }: { used: number }) {
  const active = Math.min(used, 2);
  return (
    <span
      className="flex items-center gap-1"
      aria-label={`Attempt ${active + 1} of 3`}
    >
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className={cn(
            "h-1.5 w-1.5 rounded-full",
            i === active ? "bg-foreground" : "bg-border",
          )}
        />
      ))}
    </span>
  );
}

function Message({ message }: { message: ChatMessage }) {
  if (message.role === "student") {
    return (
      <div className="my-4 flex justify-end">
        {/* Student bubble uses the success-tint green (#f0fdf4), per the
            Tutoring chat pattern in design-system.md. */}
        <div className="max-w-[85%] rounded-lg bg-[#f0fdf4] px-4 py-2.5 text-[14px] leading-relaxed text-[#3f3f46]">
          {message.content}
        </div>
      </div>
    );
  }

  if (message.role === "fallback") {
    return (
      <div className="my-4 rounded-lg border border-fail-border bg-fail px-4 py-3 text-[14px] leading-relaxed text-fail-foreground">
        {message.content}
      </div>
    );
  }

  return <TutorText message={message} />;
}

/** A tutor message, revealed smoothly while it streams. */
function TutorText({ message }: { message: ChatMessage }) {
  const text = useSmoothText(message.content, !message.streaming);
  return (
    <div className="my-4 text-[14px] leading-relaxed">
      {text}
      {message.streaming && (
        <span className="ml-0.5 inline-block h-[1em] w-[2px] translate-y-[2px] animate-pulse bg-foreground align-middle" />
      )}
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="my-4 flex gap-1" aria-label="Tutor is thinking">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/60"
          style={{ animationDelay: `${i * 150}ms` }}
        />
      ))}
    </div>
  );
}

function Composer({ state, onSubmit }: ChatPanelProps) {
  const [text, setText] = useState("");
  const canSubmit = state.phase === "awaiting_input" && text.trim().length > 0;

  function send() {
    if (!canSubmit) return;
    onSubmit(text.trim());
    setText("");
  }

  if (state.phase === "terminal") {
    return (
      <div className="shrink-0 border-t px-6 py-4 text-center text-[13px] text-muted-foreground">
        {state.status === "complete"
          ? "You've completed all four steps for this reading."
          : "This session has ended. Your instructor has been notified."}
      </div>
    );
  }

  if (state.phase === "error") {
    return (
      <div className="shrink-0 border-t border-fail-border bg-fail px-6 py-4 text-[13px] text-fail-foreground">
        Something went wrong: {state.error}. Your attempts are unaffected — reload
        to continue.
      </div>
    );
  }

  const disabled = state.phase !== "awaiting_input";
  const placeholder = disabled
    ? "Waiting for the tutor…"
    : PLACEHOLDER[state.currentStep ?? "State"];

  return (
    <div className="shrink-0 border-t p-4">
      <div className="flex items-end gap-2 rounded-md border px-3 py-2 focus-within:ring-2 focus-within:ring-ring">
        <textarea
          value={text}
          disabled={disabled}
          rows={1}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
          placeholder={placeholder}
          className="max-h-40 flex-1 resize-none bg-transparent py-1 text-[14px] outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed"
        />
        <Button size="sm" onClick={send} disabled={!canSubmit}>
          Submit
        </Button>
      </div>
    </div>
  );
}
