/** The two things a student can look up mid-session, from the top bar.
 *
 * Popovers rather than modals. Both are consulted *while* writing an answer, so
 * covering the reading or the composer would defeat the point. Escape and a
 * click outside close them, and only one is open at a time.
 *
 * Components repeats what the reading detail already showed before the session;
 * Rubric is the criteria the tags in the chat refer to, in the rubric's own
 * words. Between them they are why the tags need only carry names.
 */

import { useEffect, useState } from "react";
import { ChevronRight, X } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { getRubric } from "../../lib/api";
import { cn } from "../../lib/utils";
import type { SeeiStep } from "./types";

/** Where a panel opens. `bar`: under the live session's top bar, which does not
 *  scroll. `page`: on a page that scrolls, so it stays in view at the top right,
 *  and on a phone rises from the bottom over a dimmed page. */
export type PanelPlacement = "bar" | "page";

/** The shell: a card under the top bar, dismissed the same way either way. */
function Popover({
  title,
  onClose,
  placement = "bar",
  className,
  children,
}: {
  title: string;
  onClose: () => void;
  placement?: PanelPlacement;
  className?: string;
  children: React.ReactNode;
}) {
  const page = placement === "page";
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <>
      {/* Catches the click-away without dimming: the reading stays readable,
          which is the reason this is a popover and not a modal. */}
      <div
        className={cn("fixed inset-0 z-40", page && "bg-black/30 sm:bg-transparent")}
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-label={title}
        className={cn(
          "absolute right-2 top-[58px] z-50 w-[min(440px,calc(100vw-1rem))]",
          "overflow-hidden rounded-lg border bg-background shadow-lg sm:right-4",
          page &&
            "fixed inset-x-0 bottom-0 top-auto w-full rounded-b-none rounded-t-xl sm:inset-x-auto sm:bottom-auto sm:right-6 sm:top-[68px] sm:w-[440px] sm:rounded-lg",
          className,
        )}
      >
        <div className="flex items-center justify-between border-b px-4 py-3">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            {title}
          </span>
          <button
            onClick={onClose}
            aria-label="Close"
            className="text-muted-foreground transition-colors hover:text-foreground"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
        {children}
      </div>
    </>
  );
}

export function ComponentsPanel({
  components,
  onClose,
  placement,
}: {
  components: string[];
  onClose: () => void;
  placement?: PanelPlacement;
}) {
  return (
    <Popover title="Core components" onClose={onClose} placement={placement}>
      {components.length === 0 ? (
        <p className="px-4 py-4 text-[13px] text-muted-foreground">
          No core components available
        </p>
      ) : (
        <ul className="flex flex-col gap-2.5 px-4 py-3.5">
          {components.map((text, i) => (
            <li key={i} className="flex gap-2.5">
              <span className="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-muted-foreground/60" />
              <span className="text-[13px] leading-[1.55] text-[#3f3f46]">{text}</span>
            </li>
          ))}
        </ul>
      )}
    </Popover>
  );
}

export function RubricPanel({
  currentStep,
  unmet,
  onClose,
  placement,
}: {
  currentStep: SeeiStep | null;
  /** Criteria the last attempt missed, marked so the tags in the chat and the
   *  definitions here are visibly the same things. */
  unmet: string[];
  onClose: () => void;
  placement?: PanelPlacement;
}) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["rubric"],
    queryFn: getRubric,
  });

  // Opens on the step in question; the others are a tap away. The marks belong
  // to that step's answer, so they show only while it is the one in view.
  const home = currentStep ?? "State";
  const [step, setStep] = useState<SeeiStep>(home);
  useEffect(() => setStep(home), [home]);
  const current = data?.steps.find((s) => s.step === step);
  const others = data?.steps.filter((s) => s.step !== step) ?? [];
  const missed = new Set(step === home ? unmet : []);

  return (
    <Popover title={`Rubric · ${step}`} onClose={onClose} placement={placement}>
      {isLoading && <Notice>Loading the rubric…</Notice>}
      {isError && <Notice>Couldn&rsquo;t load the rubric.</Notice>}

      {current && (
        <>
          <div className="flex max-h-[380px] flex-col gap-3 overflow-y-auto px-4 py-3.5">
            {current.criteria.map((c) => (
              <div key={c.name} className="flex gap-3">
                {/* Fixed column, so every requirement starts on the same edge
                    however long the criterion's name is. */}
                <span className="flex w-[104px] shrink-0">
                  <Tag marked={missed.has(c.name)}>{c.name}</Tag>
                </span>
                <span className="text-[12px] leading-[1.55] text-[#52525b]">
                  {c.requirement}
                </span>
              </div>
            ))}
          </div>

          {others.map((s) => (
            <button
              key={s.step}
              type="button"
              onClick={() => setStep(s.step)}
              className="flex w-full items-center justify-between border-t px-4 py-2 text-left text-[12px] text-foreground/80 hover:bg-muted/50"
            >
              {s.step}
              <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
            </button>
          ))}
        </>
      )}
    </Popover>
  );
}

function Tag({ marked, children }: { marked: boolean; children: React.ReactNode }) {
  return (
    <span
      className={cn(
        "inline-flex h-5 items-center rounded-full border px-2 text-[11px] font-medium",
        marked
          ? "border-fail-border bg-fail text-fail-foreground"
          : "border-border bg-muted/50 text-[#3f3f46]",
      )}
    >
      {children}
    </span>
  );
}

function Notice({ children }: { children: React.ReactNode }) {
  return <p className="px-4 py-5 text-[13px] text-muted-foreground">{children}</p>;
}
