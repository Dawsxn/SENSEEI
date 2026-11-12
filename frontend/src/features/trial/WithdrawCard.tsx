/** Withdraw a participant: type their ID, confirm, and everything recorded for
 *  it is deleted. It asks first and names the ID, because it cannot be undone. */

import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { ConfirmDialog } from "../../components/ConfirmDialog";
import { Button } from "../../components/ui/button";
import { ApiError, withdrawParticipant } from "../../lib/api";

export function WithdrawCard() {
  const [code, setCode] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [message, setMessage] = useState<{ text: string; failed: boolean } | null>(null);
  const queryClient = useQueryClient();
  const typed = code.trim().toUpperCase();

  async function withdraw() {
    setConfirming(false);
    try {
      await withdrawParticipant(typed);
      setMessage({ text: `Deleted ${typed}.`, failed: false });
      setCode("");
      // Batch counts and statuses no longer include them.
      await queryClient.invalidateQueries({ queryKey: ["batches"] });
      await queryClient.invalidateQueries({ queryKey: ["batch"] });
    } catch (err) {
      setMessage({
        text:
          err instanceof ApiError && err.status === 404
            ? "That ID doesn't exist."
            : "That didn't work. Try again.",
        failed: true,
      });
    }
  }

  return (
    <section className="mt-5 rounded-lg border">
      <div className="border-b px-4 py-3.5 text-[14px] font-semibold">Withdraw a participant</div>
      <form
        className="flex flex-col gap-3 p-4"
        onSubmit={(e) => {
          e.preventDefault();
          if (typed) setConfirming(true);
        }}
      >
        <span className="text-[13px] text-muted-foreground">
          Deletes everything recorded for an ID.
        </span>
        <div className="flex max-w-[420px] gap-2">
          <input
            value={code}
            onChange={(e) => {
              setCode(e.target.value);
              setMessage(null);
            }}
            placeholder="P-XXXX-XXXX"
            aria-label="Participant ID to withdraw"
            autoComplete="off"
            spellCheck={false}
            maxLength={40}
            className="h-9 min-w-0 flex-1 rounded-md border bg-background px-3 font-mono text-[14px] tracking-wider outline-none placeholder:text-muted-foreground/70 focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/30"
          />
          <Button type="submit" variant="danger" disabled={!typed}>
            Delete
          </Button>
        </div>
        {message && (
          <p
            role="status"
            className={`text-[13px] ${message.failed ? "text-fail-foreground" : "text-muted-foreground"}`}
          >
            {message.text}
          </p>
        )}
      </form>

      {confirming && (
        <ConfirmDialog
          title={`Delete ${typed}?`}
          confirmLabel="Delete"
          cancelLabel="Cancel"
          tone="danger"
          onConfirm={withdraw}
          onCancel={() => setConfirming(false)}
        >
          Everything recorded for this ID will be deleted. This can&rsquo;t be undone.
        </ConfirmDialog>
      )}
    </section>
  );
}
