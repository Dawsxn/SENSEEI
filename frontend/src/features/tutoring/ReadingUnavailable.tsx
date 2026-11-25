/** A reading that did not load, in place of the whole screen below the bar.
 *
 * Outside the trial only. A reading that does not exist, or that the student
 * can no longer see (the server answers both with the same 404), will not
 * appear by asking again, so it offers the way back instead of Try again. */

import { useNavigate } from "react-router-dom";

import { Button } from "../../components/ui/button";
import { ApiError } from "../../lib/api";

export function ReadingUnavailable({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const navigate = useNavigate();
  const missing = error instanceof ApiError && error.status === 404;
  return (
    <div role="alert" className="flex h-full flex-col items-center justify-center gap-3.5 p-6 text-center">
      <p className="text-[14px] text-muted-foreground">
        {missing ? "This reading isn't available." : "Couldn't load this reading."}
      </p>
      {missing ? (
        <Button className="h-10 w-full sm:h-9 sm:w-auto" onClick={() => navigate("/")}>
          Back to classes
        </Button>
      ) : (
        <Button variant="secondary" className="h-10 w-full sm:h-9 sm:w-auto" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}
