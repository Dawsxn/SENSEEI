import { BookOpen, Component, X } from "lucide-react";

import { Button } from "../../components/ui/button";
import { cn } from "../../lib/utils";
import type { SeeiStep, SessionStatus } from "./types";
import type { Phase } from "./useTutoringSession";

const STEPS: SeeiStep[] = ["State", "Elaborate", "Exemplify", "Illustrate"];

interface SessionTopBarProps {
  readingTitle: string;
  section: string;
  currentStep: SeeiStep | null;
  status: SessionStatus | null;
  phase: Phase;
}

/** The tutoring screen's own top bar: exit, the reading, step progress, rubric.
 *
 * Progress is a four-segment bar rather than a row of labels — the steps are
 * named inline in the chat, so up here they only need to show how far along the
 * session is. */
export function SessionTopBar({
  readingTitle,
  section,
  currentStep,
  status,
  phase,
}: SessionTopBarProps) {
  const currentIndex = currentStep ? STEPS.indexOf(currentStep) : 0;
  const complete = status === "complete" || phase === "terminal";

  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b px-2 sm:px-4">
      <Button variant="ghost" size="icon" aria-label="Leave session">
        <X className="h-[18px] w-[18px] text-muted-foreground" />
      </Button>

      {/* Title, class and progress cluster together on the left, as in the
          mockup; the reference buttons are pushed to the right. */}
      <div className="flex min-w-0 items-baseline gap-2">
        <span className="truncate text-[14px] font-medium">{readingTitle}</span>
        <span className="hidden shrink-0 text-[13px] text-muted-foreground sm:inline">
          {section}
        </span>
      </div>

      <div className="hidden shrink-0 items-center gap-1.5 sm:flex" aria-label="Progress">
        {STEPS.map((step, i) => {
          const done = complete || i < currentIndex;
          const active = !complete && i === currentIndex;
          return (
            <span
              key={step}
              className={cn(
                "h-1 w-8 rounded-full",
                done && "bg-primary",
                active && "bg-foreground",
                !done && !active && "bg-border",
              )}
            />
          );
        })}
      </div>

      {/* Reference panels the student can open on demand, like the rubric. Both
          are visual only for now; their panels land in a later PR. */}
      <div className="ml-auto flex shrink-0 items-center gap-2">
        <Button variant="secondary" size="sm" aria-label="View core components">
          <Component className="h-[15px] w-[15px]" />
          <span className="hidden sm:inline">Components</span>
        </Button>

        <Button variant="secondary" size="sm" aria-label="View rubric">
          <BookOpen className="h-[15px] w-[15px]" />
          <span className="hidden sm:inline">Rubric</span>
        </Button>
      </div>
    </header>
  );
}
