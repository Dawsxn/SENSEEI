/** Shown when a participant's session time runs out on a screen with nothing
 * left to read first: the reading, or a control group's screen. It cannot be
 * dismissed, since the time is up either way; its one button moves them on to
 * the post-test. The SEE-I chat ends with a strip instead (ChatPanel), so the
 * tutor's last feedback stays readable. */

import { Button } from "../../components/ui/button";

export function TimeUpDialog({ onContinue }: { onContinue: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/30 sm:items-center sm:p-4">
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="time-up-title"
        className="w-full max-w-[420px] rounded-t-lg bg-card p-6 shadow-lg sm:rounded-lg"
      >
        <h2 id="time-up-title" className="text-[16px] font-semibold">
          Time&rsquo;s up
        </h2>
        <p className="mt-2 text-[14px] leading-[1.6] text-muted-foreground">
          Your session has ended.
        </p>
        <div className="mt-5 flex justify-end">
          <Button size="sm" onClick={onContinue} autoFocus>
            Continue to post-test
          </Button>
        </div>
      </div>
    </div>
  );
}
