/** The split-screen tutoring view: reading on the left, chat on the right.
 *
 * The reading is a hard-coded placeholder for now (placeholderReading.ts); when
 * the Reading API exists it becomes a fetch and nothing else here changes. The
 * session itself is real: it starts against the seeded reading's stable id and
 * streams from the backend.
 *
 * Responsive: two panes side by side from `lg` up. Below that a split does not
 * fit, so one pane shows at a time behind a Reading / Chat toggle, defaulting to
 * the chat since that is where the work happens. */

import { useState } from "react";

import { cn } from "../../lib/utils";
import { ChatPanel } from "./ChatPanel";
import { DEV_READING } from "./placeholderReading";
import { ReadingPanel } from "./ReadingPanel";
import { SessionTopBar } from "./SessionTopBar";
import { useTutoringSession } from "./useTutoringSession";

type Pane = "reading" | "chat";

export function TutoringScreen() {
  const { state, submit } = useTutoringSession(DEV_READING.id);
  const [pane, setPane] = useState<Pane>("chat");

  return (
    <div className="flex h-full flex-col">
      <SessionTopBar
        readingTitle={DEV_READING.title}
        section={DEV_READING.section}
        currentStep={state.currentStep}
        status={state.status}
        phase={state.phase}
      />

      <PaneToggle pane={pane} onChange={setPane} />

      {/* Not 50/50: the reading is the narrower column, matching the mockup's
          ~46/54 split. */}
      <div className="grid min-h-0 flex-1 grid-cols-1 overflow-hidden lg:grid-cols-[46fr_54fr]">
        <div className={cn("h-full min-h-0", pane === "reading" ? "block" : "hidden", "lg:block")}>
          <ReadingPanel content={DEV_READING.content} />
        </div>
        <div className={cn("h-full min-h-0", pane === "chat" ? "block" : "hidden", "lg:block")}>
          <ChatPanel state={state} onSubmit={submit} />
        </div>
      </div>
    </div>
  );
}

/** Reading / Chat switch, shown only below the `lg` breakpoint. */
function PaneToggle({ pane, onChange }: { pane: Pane; onChange: (p: Pane) => void }) {
  return (
    <div className="flex shrink-0 gap-1 border-b p-1.5 lg:hidden">
      {(["reading", "chat"] as const).map((p) => (
        <button
          key={p}
          onClick={() => onChange(p)}
          className={cn(
            "flex-1 rounded-md py-1.5 text-[13px] font-medium capitalize transition-colors",
            pane === p ? "bg-muted text-foreground" : "text-muted-foreground",
          )}
        >
          {p}
        </button>
      ))}
    </div>
  );
}
