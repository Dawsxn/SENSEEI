/** What the student sees first on the reading step.
 *
 * It says what the session will ask of them and why reading the whole thing
 * matters, which is the one thing they cannot work out from the screen itself.
 *
 * Outside the trial, Escape and a click on the overlay dismiss it, unlike the
 * leave-session dialog: this one informs rather than asks, so there is no wrong
 * way to close it. A click only counts if the press also began on the overlay,
 * so selecting text and letting go outside the box doesn't close it.
 *
 * In the trial (`startOnly`) closing it starts the participant's clock, so only
 * the Start button does: no Escape, no overlay click.
 */

import { useEffect, useRef } from "react";

import { Button } from "../../components/ui/button";

/** `body` is what it says: the goal of the session outside the trial, and the
 *  trial's own wording for its control groups. Each string in a list is its own
 *  paragraph. `children`, when given, replaces it all (the trial's SEE-I
 *  wording, which has a list). */
export function ReadingIntroDialog({
  onStart,
  body = "",
  children,
  startOnly = false,
}: {
  onStart: () => void;
  body?: string | string[];
  children?: React.ReactNode;
  startOnly?: boolean;
}) {
  // Where the press began: a click on the overlay only counts if it did too.
  const pressedOnOverlay = useRef(false);

  useEffect(() => {
    if (startOnly) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onStart();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onStart, startOnly]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/30 p-0 sm:items-center sm:p-4"
      onMouseDown={(e) => {
        pressedOnOverlay.current = e.target === e.currentTarget;
      }}
      onClick={(e) => {
        if (!startOnly && pressedOnOverlay.current && e.target === e.currentTarget) onStart();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="reading-intro-title"
        className="w-full max-w-[460px] rounded-t-lg bg-card p-6 shadow-lg sm:rounded-lg"
      >
        <h2 id="reading-intro-title" className="text-[16px] font-semibold">
          Before you start
        </h2>
        {children ??
          (Array.isArray(body) ? body : [body]).map((p) => (
            <p key={p} className="mt-2 text-[14px] leading-[1.6] text-muted-foreground">
              {p}
            </p>
          ))}

        <div className="mt-5 flex justify-end">
          <Button size="sm" onClick={onStart} autoFocus>
            Start
          </Button>
        </div>
      </div>
    </div>
  );
}
