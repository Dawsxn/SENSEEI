/** Confirms leaving a session that is still running.
 *
 * A session cannot be paused or resumed: leaving discards it, and the student
 * starts over from State next time. That is a real cost and an easy misclick, so
 * the exit asks first, but only while there is something to lose. A session that
 * has already ended is read-only, and confirming an exit from it would be a
 * question with one sensible answer.
 */

import { ConfirmDialog } from "../../components/ConfirmDialog";

interface LeaveSessionDialogProps {
  onConfirm: () => void;
  onCancel: () => void;
}

export function LeaveSessionDialog({ onConfirm, onCancel }: LeaveSessionDialogProps) {
  return (
    <ConfirmDialog
      title="Leave this session?"
      confirmLabel="Leave"
      tone="danger"
      onConfirm={onConfirm}
      onCancel={onCancel}
    >
      Your progress will not be saved. This session will be discarded and cannot be
      resumed, so you would start again from the beginning.
    </ConfirmDialog>
  );
}
