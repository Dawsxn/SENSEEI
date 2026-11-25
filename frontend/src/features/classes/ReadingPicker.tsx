/** Add readings the instructor already has to this class, from the class page.
 *
 * Lists only the readings this class does not have yet; ticking one and
 * pressing Add gives the class that reading, as its own page's Change would.
 * A reading's other classes are untouched. */

import { useEffect, useState } from "react";

import { Button } from "../../components/ui/button";
import { ApiError, addReadingsToClass } from "../../lib/api";
import { cn } from "../../lib/utils";
import { useLibrary } from "../library/useLibrary";

export function ReadingPicker({
  classId,
  classLabel,
  onDone,
  onCancel,
}: {
  classId: string;
  classLabel: string;
  onDone: () => void;
  onCancel: () => void;
}) {
  const { data, isLoading, isError } = useLibrary();
  const [chosen, setChosen] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onCancel();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onCancel]);

  // The library lists each reading's classes by label, which is unique among
  // one instructor's classes.
  const available = (data ?? []).filter((r) => !r.classes.includes(classLabel));

  async function add() {
    setSaving(true);
    setError(null);
    try {
      await addReadingsToClass(classId, chosen);
      onDone();
    } catch (e) {
      setError(
        e instanceof ApiError && e.detail === "class_has_reading"
          ? "A trial class can only have one reading."
          : "That didn't save. Try again.",
      );
      setSaving(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/30 p-0 sm:items-center sm:p-4"
      onClick={onCancel}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="picker-title"
        onClick={(e) => e.stopPropagation()}
        className="flex max-h-[85vh] w-full max-w-[480px] flex-col rounded-t-lg bg-card p-6 shadow-lg sm:rounded-lg"
      >
        <h2 id="picker-title" className="text-[16px] font-semibold">
          Choose from your readings
        </h2>

        <div className="mt-4 min-h-0 overflow-y-auto">
          {isLoading && <p className="py-6 text-center text-[13px] text-muted-foreground">Loading your readings…</p>}
          {isError && <p className="py-6 text-center text-[13px] text-muted-foreground">Couldn't load your readings. Try again.</p>}
          {data && available.length === 0 && (
            <p className="rounded-lg border border-dashed px-4 py-8 text-center text-[13px] text-muted-foreground">
              All your readings are already in this class.
            </p>
          )}
          {available.length > 0 && (
            <div className="overflow-hidden rounded-lg border bg-card">
              {available.map((r, i) => {
                const on = chosen.includes(r.id);
                return (
                  <label
                    key={r.id}
                    className={cn("flex cursor-pointer items-start gap-3 px-4 py-3 hover:bg-muted/40", i > 0 && "border-t")}
                  >
                    <input
                      type="checkbox"
                      checked={on}
                      onChange={() =>
                        setChosen((c) => (on ? c.filter((id) => id !== r.id) : [...c, r.id]))
                      }
                      className="mt-0.5 h-4 w-4 accent-primary"
                    />
                    <span className="min-w-0">
                      <span className="block text-[14px] font-medium">{r.title}</span>
                      {r.description && (
                        <span className="mt-0.5 block text-[13px] text-muted-foreground">{r.description}</span>
                      )}
                    </span>
                  </label>
                );
              })}
            </div>
          )}
        </div>

        {error && <p className="mt-3 text-[13px] text-fail-foreground">{error}</p>}
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="secondary" size="sm" className="flex-1 sm:flex-none" onClick={onCancel}>
            Cancel
          </Button>
          <Button size="sm" className="flex-1 sm:flex-none" disabled={chosen.length === 0 || saving} onClick={add}>
            Add
          </Button>
        </div>
      </div>
    </div>
  );
}
