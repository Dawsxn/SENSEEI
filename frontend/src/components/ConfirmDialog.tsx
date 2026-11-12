/** A yes/no modal: a question, a sentence of consequence, and two ways out.
 *
 * Escape and a click on the overlay both cancel, so every accidental
 * interaction produces the safe outcome rather than the irreversible one. That
 * is also why cancelling is the autofocused button.
 *
 * `tone` picks the confirm button's weight. `danger` is for an action that
 * destroys something; it uses the design system's soft failure treatment rather
 * than a solid red fill. Leave it off when the action is merely a navigation.
 */

import { useEffect } from "react";

import { Button } from "./ui/button";

interface ConfirmDialogProps {
  title: string;
  children: React.ReactNode;
  confirmLabel: string;
  cancelLabel?: string;
  tone?: "default" | "danger";
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  title,
  children,
  confirmLabel,
  cancelLabel = "Stay",
  tone = "default",
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
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
        aria-labelledby="confirm-dialog-title"
        className="w-full max-w-[420px] rounded-t-lg bg-background p-6 shadow-lg sm:rounded-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="confirm-dialog-title" className="text-[16px] font-semibold">
          {title}
        </h2>
        <p className="mt-2 text-[14px] leading-[1.6] text-muted-foreground">{children}</p>

        <div className="mt-5 flex justify-end gap-2">
          <Button variant="secondary" size="sm" onClick={onCancel} autoFocus>
            {cancelLabel}
          </Button>
          <Button
            variant={tone === "danger" ? "danger" : "primary"}
            size="sm"
            onClick={onConfirm}
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
