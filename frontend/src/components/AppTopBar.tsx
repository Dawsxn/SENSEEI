import { User } from "lucide-react";

import { Button } from "./ui/button";

/** The app shell's top bar, from the reading-list mockup: the wordmark, a Join a
 *  class action, and the signed-in student's avatar. Join a class and the avatar
 *  are placeholders until enrolment and auth exist. The tutoring screen has its
 *  own bar and does not use this one. */
export function AppTopBar() {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b px-4 sm:px-6">
      {/* SEE-I is set in the accent colour: the framework name sits inside the
          product name (design/README.md). */}
      <span className="text-[15px] font-semibold tracking-[-0.01em]">
        SEN<span className="text-primary">SEE-I</span>
      </span>

      <div className="flex items-center gap-3">
        <Button variant="secondary" size="sm">
          Join a class
        </Button>
        <span
          className="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-muted-foreground"
          aria-label="Account"
        >
          <User className="h-4 w-4" />
        </span>
      </div>
    </header>
  );
}
