/** A class as a card: a coloured band, the name with the section under it, and
 *  one line about it. Both homes use it, the student's and the instructor's, so
 *  the two read as the same app; only the line differs.
 *
 * The band's colour is the viewer's own choice, from the ⋯ button on it, and is
 * kept in this browser only (classColours.ts). */

import { MoreHorizontal } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { cn } from "../../lib/utils";
import { CLASS_COLOURS, classColour, saveClassColour } from "./classColours";

interface CardClass {
  id: string;
  name: string;
  section: string;
  /** Name and section joined, for the colour button's label. */
  label: string;
}

export function ClassCard({ klass, index, meta }: { klass: CardClass; index: number; meta: string }) {
  const [colour, setColour] = useState(() => classColour(klass.id, index));

  return (
    <div className="relative rounded-lg border bg-card shadow-raised transition-shadow hover:shadow-md">
      {/* The whole card opens the class; the colour button sits above the link. */}
      <Link
        to={`/classes/${klass.id}`}
        className="block rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <div className="mx-2 mt-2 h-16 rounded-md sm:h-24" style={{ background: colour }} />
        <div className="flex flex-col gap-2.5 px-4 pb-[18px] pt-3.5">
          <div className="min-w-0">
            <div className="truncate text-[16px] font-semibold tracking-[-0.01em]">
              {klass.name}
            </div>
            {klass.section && (
              <div className="mt-0.5 truncate text-[13px] font-medium text-foreground/70">
                {klass.section}
              </div>
            )}
          </div>
          <div className="text-[13px] text-muted-foreground">{meta}</div>
        </div>
      </Link>
      <ColourPicker
        label={klass.label}
        value={colour}
        onChange={(value) => {
          setColour(value);
          saveClassColour(klass.id, value);
        }}
      />
    </div>
  );
}

function ColourPicker({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={ref} className="absolute right-4 top-4">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={`Change the colour of ${label}`}
        aria-expanded={open}
        className="flex h-7 w-7 items-center justify-center rounded-md bg-card/70 text-foreground/75 hover:bg-card"
      >
        <MoreHorizontal className="h-4 w-4" />
      </button>
      {open && (
        <div className="absolute right-0 top-[34px] z-10 flex gap-2 rounded-lg border bg-card p-3 shadow-lg">
          {CLASS_COLOURS.map((c) => (
            <button
              key={c.value}
              type="button"
              aria-label={c.name}
              aria-pressed={c.value === value}
              onClick={() => {
                onChange(c.value);
                setOpen(false);
              }}
              className={cn(
                "h-6 w-6 rounded-full",
                c.value === value && "ring-2 ring-foreground ring-offset-2 ring-offset-background",
              )}
              style={{ background: c.value }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
