/** A student's home: the classes they are in, as cards.
 *
 * Each card shows how many readings the class has, and opens it; how far the
 * student is through them is on the class page, in its To do and Finished
 * counts. The
 * card's colour is the student's own choice, from the ⋯ button on its band.
 * Join a class sits beside the heading, in the same place however many classes
 * there are.
 */

import { MoreHorizontal } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { AppTopBar } from "../../components/AppTopBar";
import { Button } from "../../components/ui/button";
import { cn } from "../../lib/utils";
import { CLASS_COLOURS, classColour, saveClassColour } from "./classColours";
import { JoinClassDialog } from "./JoinClassDialog";
import { Notice } from "./parts";
import { ClassesSkeleton } from "./skeletons";
import type { StudentClassItem } from "./types";
import { useMyClasses } from "./useReadings";

export function StudentClassesPage() {
  const { data, isLoading, isError } = useMyClasses();
  const [joining, setJoining] = useState(false);

  return (
    <div className="flex h-full flex-col">
      <AppTopBar />
      <main className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex max-w-[1148px] flex-col gap-5 px-4 py-5 sm:gap-6 sm:px-8 sm:py-7 lg:px-6 lg:py-8">
          <div className="flex items-center justify-between gap-4">
            <h1 className="text-[22px] font-semibold tracking-[-0.02em] sm:text-[24px]">
              Classes
            </h1>
            <Button variant="secondary" size="sm" onClick={() => setJoining(true)}>
              + Join a class
            </Button>
          </div>

          {isLoading && <ClassesSkeleton />}
          {isError && <Notice>Couldn't load your classes. Try again.</Notice>}
          {data && data.length === 0 && (
            <Notice>No classes available</Notice>
          )}

          {data && data.length > 0 && (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 lg:grid-cols-4 lg:gap-5">
              {data.map((c, i) => (
                <ClassCard key={c.id} klass={c} index={i} />
              ))}
            </div>
          )}
        </div>
      </main>
      {joining && <JoinClassDialog onClose={() => setJoining(false)} />}
    </div>
  );
}

function ClassCard({ klass, index }: { klass: StudentClassItem; index: number }) {
  const [colour, setColour] = useState(() => classColour(klass.id, index));

  return (
    <div className="relative rounded-lg border bg-background shadow-raised transition-shadow hover:shadow-md">
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
          <div className="text-[13px] text-muted-foreground">
            {klass.reading_count} {klass.reading_count === 1 ? "reading" : "readings"}
          </div>
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
        className="flex h-7 w-7 items-center justify-center rounded-md bg-background/70 text-foreground/75 hover:bg-background"
      >
        <MoreHorizontal className="h-4 w-4" />
      </button>
      {open && (
        <div className="absolute right-0 top-[34px] z-10 flex gap-2 rounded-lg border bg-background p-3 shadow-lg">
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
