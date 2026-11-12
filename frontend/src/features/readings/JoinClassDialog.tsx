/** A student joins a class by typing its code.
 *
 * The code is forgiving: case, spaces and a missing hyphen are all fine, since
 * the server normalises it. A wrong code stays in the dialog with an inline
 * error, so the student can fix one character rather than start again.
 */

import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { Button } from "../../components/ui/button";
import { ApiError, joinClass } from "../../lib/api";
import type { JoinResult } from "../classes/types";

export function JoinClassDialog({ onClose }: { onClose: () => void }) {
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [joining, setJoining] = useState(false);
  const [joined, setJoined] = useState<JoinResult | null>(null);
  const queryClient = useQueryClient();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!code.trim() || joining) return;
    setJoining(true);
    setError(null);
    try {
      const result = await joinClass(code);
      // The new class's readings belong in the list behind this dialog.
      await queryClient.invalidateQueries({ queryKey: ["readings"] });
      setJoined(result);
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 404
          ? "That code doesn't match a class. Check it with your instructor."
          : "That didn't work. Try again.",
      );
    } finally {
      setJoining(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/30 p-0 sm:items-center sm:p-4"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="join-title"
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-[420px] rounded-t-lg bg-background p-6 shadow-lg sm:rounded-lg"
      >
        {joined ? (
          <>
            <h2 id="join-title" className="text-[16px] font-semibold">
              You joined {joined.label}
            </h2>
            <p className="mt-1.5 text-[14px] text-muted-foreground">
              {joined.reading_count > 0
                ? "Its readings are now in your list."
                : "It has no readings yet. They will appear in your list once added."}
            </p>
            <div className="mt-5 flex justify-end">
              <Button size="sm" onClick={onClose} autoFocus>
                Done
              </Button>
            </div>
          </>
        ) : (
          <form onSubmit={submit}>
            <h2 id="join-title" className="text-[16px] font-semibold">
              Join a class
            </h2>
            <p className="mt-1.5 text-[14px] text-muted-foreground">
              Enter the code your instructor gave you.
            </p>
            <input
              autoFocus
              value={code}
              onChange={(e) => {
                setCode(e.target.value.toUpperCase());
                setError(null);
              }}
              placeholder="XXXX-XXXX"
              aria-label="Join code"
              aria-invalid={!!error}
              maxLength={20}
              autoComplete="off"
              spellCheck={false}
              className={
                "mt-4 h-10 w-full rounded-md border bg-background px-3 font-mono text-[16px] tracking-[0.08em] outline-none focus-visible:ring-2 " +
                (error
                  ? "border-fail-border focus-visible:ring-fail-border/60"
                  : "focus-visible:border-ring focus-visible:ring-ring/30")
              }
            />
            {error && <p className="mt-1.5 text-[13px] text-fail-foreground">{error}</p>}
            <div className="mt-5 flex justify-end gap-2">
              <Button type="button" variant="secondary" size="sm" onClick={onClose}>
                Cancel
              </Button>
              <Button type="submit" size="sm" disabled={!code.trim() || joining}>
                Join
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
