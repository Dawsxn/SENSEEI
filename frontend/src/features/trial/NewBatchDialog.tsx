/** Make a batch: a name, and how many IDs each class gets.
 *
 * The counts start at zero rather than at some guess, so a class that has no
 * part in this sitting gets no IDs unless someone types a number for it. The
 * server draws the IDs in a shuffled order, which is what the line under the
 * counts says. */

import { useEffect, useState } from "react";

import { Button } from "../../components/ui/button";
import { MODE_LABEL } from "../classes/types";
import { useClasses } from "../classes/useClasses";
import type { NewBatch } from "./types";

const INPUT =
  "h-9 w-full rounded-md border bg-background px-3 text-[14px] outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/30";

interface NewBatchDialogProps {
  defaultName: string;
  onSubmit: (batch: NewBatch) => Promise<void>;
  onCancel: () => void;
}

export function NewBatchDialog({ defaultName, onSubmit, onCancel }: NewBatchDialogProps) {
  const { data: classes } = useClasses();
  const [name, setName] = useState(defaultName);
  const [counts, setCounts] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onCancel();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onCancel]);

  const count = (id: string) => Math.max(0, Math.floor(Number(counts[id] || 0)) || 0);
  const total = (classes ?? []).reduce((sum, c) => sum + count(c.id), 0);
  const ready = name.trim() !== "" && total > 0;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!ready || saving) return;
    setSaving(true);
    setError(null);
    try {
      await onSubmit({
        name: name.trim(),
        classes: (classes ?? [])
          .filter((c) => count(c.id) > 0)
          .map((c) => ({ class_id: c.id, count: count(c.id) })),
      });
    } catch {
      setError("That didn't save. Try again.");
      setSaving(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/30 p-0 sm:items-center sm:p-4"
      onClick={onCancel}
    >
      <form
        role="dialog"
        aria-modal="true"
        aria-labelledby="new-batch-title"
        onSubmit={submit}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-[420px] rounded-t-lg bg-background p-6 shadow-lg sm:rounded-lg"
      >
        <h2 id="new-batch-title" className="text-[16px] font-semibold">
          New batch
        </h2>

        <label className="mt-4 block text-[13px] font-medium">
          Name
          <input
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={60}
            className={`${INPUT} mt-1.5`}
          />
        </label>

        <p className="mt-4 text-[13px] font-medium">IDs per class</p>
        <div className="mt-1.5 flex flex-col gap-2">
          {(classes ?? []).map((c) => (
            <label key={c.id} className="grid grid-cols-[1fr_72px] items-center gap-3">
              <span className="min-w-0 truncate text-[14px]">
                {c.label} <span className="text-muted-foreground">· {MODE_LABEL[c.mode]}</span>
              </span>
              <input
                type="number"
                inputMode="numeric"
                min={0}
                max={300}
                value={counts[c.id] ?? ""}
                placeholder="0"
                aria-label={`IDs for ${c.label}`}
                onChange={(e) => setCounts((all) => ({ ...all, [c.id]: e.target.value }))}
                className={`${INPUT} text-center`}
              />
            </label>
          ))}
          {classes?.length === 0 && (
            <p className="text-[13px] text-muted-foreground">Make the classes first.</p>
          )}
        </div>

        <p className="mt-2 min-h-[18px] text-[12px] text-muted-foreground">
          {total > 0 && `${total} IDs, mixed so the slips don't show the class.`}
        </p>
        {error && <p className="mt-1 text-[13px] text-fail-foreground">{error}</p>}

        <div className="mt-5 flex justify-end gap-2">
          <Button type="button" variant="secondary" size="sm" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit" size="sm" disabled={!ready || saving}>
            Create batch
          </Button>
        </div>
      </form>
    </div>
  );
}
