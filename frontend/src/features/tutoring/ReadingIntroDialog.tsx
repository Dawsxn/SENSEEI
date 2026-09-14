/** What the student sees first on the reading step.
 *
 * It says what the session will ask of them and why reading the whole thing
 * matters, which is the one thing they cannot work out from the screen itself.
 *
 * Escape and a click on the overlay dismiss it, unlike the leave-session
 * dialog: this one informs rather than asks, so there is no wrong way to close
 * it and nothing is lost by closing it early.
 */

import { useEffect } from "react";

import { Button } from "../../components/ui/button";

export function ReadingIntroDialog({ onStart }: { onStart: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onStart();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onStart]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/30 p-0 sm:items-center sm:p-4"
      onClick={onStart}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="reading-intro-title"
        className="w-full max-w-[420px] rounded-t-lg bg-background p-6 shadow-lg sm:rounded-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="reading-intro-title" className="text-[16px] font-semibold">
          Before you start
        </h2>
        <p className="mt-2 text-[14px] leading-[1.6] text-muted-foreground">
          This session will take you through SEE-I one step at a time. Read the material
          in its entirety first, as the session will test your conceptual understanding
          of it. Press Done when you are finished.
        </p>

        <div className="mt-5 flex justify-end">
          <Button size="sm" onClick={onStart} autoFocus>
            Start
          </Button>
        </div>
      </div>
    </div>
  );
}
