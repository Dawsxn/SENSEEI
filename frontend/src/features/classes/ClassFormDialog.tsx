/** Create a class, or edit one. The same two fields either way.
 *
 * Name and section are stored apart but students only ever see them joined, so
 * the dialog shows the joined label as it is typed. That line is the only place
 * an instructor sees what their students will.
 */

import { useEffect, useState } from "react";

import { Button } from "../../components/ui/button";
import { ApiError } from "../../lib/api";
import type { ClassFields } from "./types";

interface ClassFormDialogProps {
  mode: "new" | "edit";
  initial?: ClassFields;
  onSubmit: (fields: ClassFields) => Promise<void>;
  onCancel: () => void;
}

const INPUT =
  "h-9 w-full rounded-md border bg-background px-3 text-[14px] outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/30";

export function ClassFormDialog({ mode, initial, onSubmit, onCancel }: ClassFormDialogProps) {
  const [name, setName] = useState(initial?.name ?? "");
  const [section, setSection] = useState(initial?.section ?? "");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onCancel();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onCancel]);

  const label = `${name.trim()} ${section.trim()}`.trim();
  const ready = name.trim() !== "" && section.trim() !== "";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!ready || saving) return;
    setSaving(true);
    setError(null);
    try {
      await onSubmit({ name: name.trim(), section: section.trim() });
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 409
          ? `You already have ${label}.`
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
      <form
        role="dialog"
        aria-modal="true"
        aria-labelledby="class-form-title"
        onSubmit={submit}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-[420px] rounded-t-lg bg-background p-6 shadow-lg sm:rounded-lg"
      >
        <h2 id="class-form-title" className="text-[16px] font-semibold">
          {mode === "new" ? "New class" : "Edit class"}
        </h2>

        <div className="mt-4 grid grid-cols-[1fr_120px] gap-3">
          <label className="text-[13px] font-medium">
            Name
            <input
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="STRAMA"
              maxLength={60}
              className={`${INPUT} mt-1.5`}
            />
          </label>
          <label className="text-[13px] font-medium">
            Section
            <input
              value={section}
              onChange={(e) => setSection(e.target.value)}
              placeholder="K31"
              maxLength={20}
              className={`${INPUT} mt-1.5`}
            />
          </label>
        </div>

        <p className="mt-2 min-h-[18px] text-[12px] text-muted-foreground">
          {label && `Students see this as ${label}.`}
        </p>
        {error && <p className="mt-1 text-[13px] text-fail-foreground">{error}</p>}

        <div className="mt-5 flex justify-end gap-2">
          <Button type="button" variant="secondary" size="sm" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit" size="sm" disabled={!ready || saving}>
            {mode === "new" ? "Create class" : "Save"}
          </Button>
        </div>
      </form>
    </div>
  );
}
