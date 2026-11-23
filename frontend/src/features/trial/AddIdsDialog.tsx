/** Add IDs to an open batch (design/TrialBatchGroups.dc.html, "Add IDs").
 *
 * The batch's own classes are listed, each starting at 1. Any other class can
 * be brought in from "Add another class", starting at 0, so the dialog only
 * ever shows the classes that matter however many exist. Counts can differ:
 * the hint suggests keeping the groups even but nothing enforces it. */

import { X } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "../../components/ui/button";
import { MODE_LABEL } from "../classes/types";
import { useClasses } from "../classes/useClasses";
import type { Batch } from "./types";

const INPUT =
  "h-9 w-full rounded-md border bg-background px-3 text-[14px] outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/30";

export function AddIdsDialog({
  batch,
  onSubmit,
  onCancel,
}: {
  batch: Batch;
  onSubmit: (classes: { class_id: string; count: number }[]) => Promise<void>;
  onCancel: () => void;
}) {
  const { data: classes } = useClasses();
  const inBatch = [...new Set(batch.participants.map((p) => p.class_id))];
  const [extra, setExtra] = useState<string[]>([]);
  const [counts, setCounts] = useState<Record<string, string>>(() =>
    Object.fromEntries(inBatch.map((id) => [id, "1"])),
  );
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onCancel();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onCancel]);

  const byId = new Map((classes ?? []).map((c) => [c.id, c]));
  // The batch's classes, by their label in the batch; the others from the class list.
  const label = (id: string) => {
    const p = batch.participants.find((x) => x.class_id === id);
    const c = byId.get(id);
    return { label: p?.class_label ?? c?.label ?? "", mode: p?.mode ?? c?.mode };
  };
  const rows = [...inBatch, ...extra];
  const others = (classes ?? []).filter((c) => !rows.includes(c.id));
  const count = (id: string) => Math.max(0, Math.floor(Number(counts[id] || 0)) || 0);
  const total = rows.reduce((sum, id) => sum + count(id), 0);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (total === 0 || saving) return;
    setSaving(true);
    setError(null);
    try {
      await onSubmit(rows.filter((id) => count(id) > 0).map((id) => ({ class_id: id, count: count(id) })));
    } catch {
      setError("That didn't save. Try again.");
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/30 p-0 sm:items-center sm:p-4">
      <form
        role="dialog"
        aria-modal="true"
        aria-labelledby="add-ids-title"
        onSubmit={submit}
        className="flex max-h-[90vh] w-full max-w-[420px] flex-col rounded-t-lg bg-background p-6 shadow-lg sm:rounded-lg"
      >
        <h2 id="add-ids-title" className="text-[16px] font-semibold">
          Add IDs to {batch.name}
        </h2>
        <p className="mt-4 text-[13px] font-medium">IDs to add per class</p>
        {/* Scrolls inside itself if it ever gets long, so the buttons stay on screen. */}
        <div className="mt-1.5 flex min-h-0 flex-col gap-2 overflow-y-auto">
          {rows.map((id) => {
            const { label: name, mode } = label(id);
            const added = extra.includes(id);
            return (
              <div key={id} className="grid grid-cols-[1fr_72px_20px] items-center gap-2">
                <span className="min-w-0 truncate text-[14px]">
                  {name} {mode && <span className="text-muted-foreground">· {MODE_LABEL[mode]}</span>}
                </span>
                <input
                  type="number"
                  inputMode="numeric"
                  min={0}
                  max={300}
                  value={counts[id] ?? ""}
                  placeholder="0"
                  aria-label={`IDs to add for ${name}`}
                  onChange={(e) => setCounts((all) => ({ ...all, [id]: e.target.value }))}
                  className={`${INPUT} text-center`}
                />
                {added ? (
                  <button
                    type="button"
                    aria-label={`Remove ${name}`}
                    onClick={() => setExtra((all) => all.filter((x) => x !== id))}
                    className="flex justify-center text-muted-foreground hover:text-foreground"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                ) : (
                  <span />
                )}
              </div>
            );
          })}
        </div>
        {others.length > 0 && (
          <select
            aria-label="Add another class"
            value=""
            onChange={(e) => {
              const id = e.target.value;
              if (!id) return;
              setExtra((all) => [...all, id]);
              setCounts((all) => ({ ...all, [id]: all[id] ?? "" }));
            }}
            className={`${INPUT} mt-3 text-muted-foreground`}
          >
            <option value="">Add another class</option>
            {others.map((c) => (
              <option key={c.id} value={c.id}>
                {c.label} · {MODE_LABEL[c.mode]}
              </option>
            ))}
          </select>
        )}

        <p className="mt-3 text-[12px] text-muted-foreground">
          {total} new {total === 1 ? "ID" : "IDs"}. Add the same number to each class to keep the
          groups even.
        </p>
        {error && <p className="mt-1 text-[13px] text-fail-foreground">{error}</p>}

        <div className="mt-5 flex justify-end gap-2">
          <Button type="button" variant="secondary" size="sm" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit" size="sm" disabled={total === 0 || saving}>
            Add IDs
          </Button>
        </div>
      </form>
    </div>
  );
}
