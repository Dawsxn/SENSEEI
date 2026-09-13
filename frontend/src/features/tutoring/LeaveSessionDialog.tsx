/** Confirms leaving a session that is still running.
 *
 * A session cannot be paused or resumed: leaving discards it, and the student
 * starts over from State next time. That is a real cost and an easy misclick, so
 * the exit asks first — but only while there is something to lose. A session
 * that has already ended is read-only, and confirming an exit from it would be
 * a question with one sensible answer.
 *
 * Follows the reading dialog's pattern: a plain modal, dismissed by Escape or a
 * click on the overlay. Dismissing means staying, so the safe outcome is the one
 * every accidental interaction produces.
 */

import { useEffect } from "react";

import { Button } from "../../components/ui/button";

interface LeaveSessionDialogProps {
  onConfirm: () => void;
  onCancel: () => void;
}

export function LeaveSessionDialog({ onConfirm, onCancel }: LeaveSessionDialogProps) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onCancel();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onCancel]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/30 p-0 sm:items-center sm:p-4"
      onClick={onCancel}
    >
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="leave-session-title"
        className="w-full max-w-[420px] rounded-t-lg bg-background p-6 shadow-lg sm:rounded-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="leave-session-title" className="text-[16px] font-semibold">
          Leave this session?
        </h2>
        <p className="mt-2 text-[14px] leading-[1.6] text-muted-foreground">
          Your progress will not be saved. This session will be discarded and cannot be
          resumed, so you would start again from the beginning.
        </p>

        <div className="mt-5 flex justify-end gap-2">
          <Button variant="secondary" size="sm" onClick={onCancel} autoFocus>
            Stay
          </Button>
          <Button variant="danger" size="sm" onClick={onConfirm}>
            Leave
          </Button>
        </div>
      </div>
    </div>
  );
}
