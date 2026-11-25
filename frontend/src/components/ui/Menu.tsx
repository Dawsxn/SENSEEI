/** A small drop-down of actions, opened from a button (a ⋯, or a labelled one).
 *
 * Closes on a pick, on Escape, and on a press anywhere outside it. Items marked
 * `danger` are red, for the ones that take something away. */

import { useEffect, useRef, useState, type ReactNode } from "react";

import { cn } from "../../lib/utils";

export interface MenuItem {
  label: string;
  onSelect: () => void;
  danger?: boolean;
}

export function Menu({
  trigger,
  label,
  items,
  align = "right",
  className,
}: {
  /** What the button shows. */
  trigger: ReactNode;
  /** The button's accessible name, for a trigger that is only an icon. */
  label?: string;
  items: MenuItem[];
  align?: "left" | "right";
  /** Classes for the button. */
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPress = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onPress);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPress);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className={className}
      >
        {trigger}
      </button>
      {open && (
        <div
          role="menu"
          className={cn(
            "absolute top-[calc(100%+6px)] z-40 min-w-[200px] rounded-lg border bg-card p-1 shadow-lg",
            align === "right" ? "right-0" : "left-0",
          )}
        >
          {items.map((item) => (
            <button
              key={item.label}
              type="button"
              role="menuitem"
              onClick={() => {
                setOpen(false);
                item.onSelect();
              }}
              className={cn(
                "block w-full rounded-md px-2.5 py-2 text-left text-[13px] hover:bg-muted focus-visible:bg-muted focus-visible:outline-none",
                item.danger && "text-fail-foreground",
              )}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
