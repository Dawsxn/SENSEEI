/** Trial mode's sign-in: the participant ID, and nothing else.
 *
 * It replaces the Google button, which on the trial instance is the research
 * team's way in, and sits under the card as a link. */

import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "../../components/ui/button";
import { ApiError, participantSignIn } from "../../lib/api";

export function ParticipantSignIn({ notice }: { notice?: React.ReactNode }) {
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!code.trim() || busy) return;
    setBusy(true);
    setError(null);
    try {
      await participantSignIn(code.trim());
      await queryClient.resetQueries();
      navigate("/", { replace: true });
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 404
          ? "That ID doesn't exist."
          : err instanceof ApiError && err.status === 403
            ? "That ID is no longer active."
            : "That didn't work. Try again.",
      );
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit}>
      <h1 className="text-[16px] font-semibold">Sign in</h1>
      <p className="mt-1 text-[13px] text-muted-foreground">Enter your participant ID.</p>

      {(error || notice) && (
        <p
          role="alert"
          className="mt-3 rounded-md border border-fail-border bg-fail px-3 py-2 text-[13px] text-fail-foreground"
        >
          {error ?? notice}
        </p>
      )}

      <input
        autoFocus
        value={code}
        onChange={(e) => setCode(e.target.value)}
        placeholder="P-XXXX-XXXX"
        aria-label="Participant ID"
        autoComplete="off"
        autoCapitalize="characters"
        spellCheck={false}
        maxLength={40}
        className="mt-4 h-9 w-full rounded-md border bg-background px-3 font-mono text-[14px] tracking-wider outline-none placeholder:text-muted-foreground/70 focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/30"
      />
      <Button type="submit" className="mt-3 w-full" disabled={!code.trim() || busy}>
        Start
      </Button>
    </form>
  );
}
