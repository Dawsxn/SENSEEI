/** The two things an instructor can change about a saved reading: how it is
 *  labelled, and which classes see it. Its text and core components are not
 *  among them, which is why neither dialog offers them. */

import { useEffect, useState } from "react";

import { Button } from "../../components/ui/button";
import { ClassPicker } from "./ClassPicker";

const INPUT =
  "h-9 w-full rounded-md border bg-background px-3 text-[14px] outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/30";

function useEscape(onCancel: () => void) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onCancel();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onCancel]);
}

function Shell({
  title,
  onCancel,
  onSubmit,
  children,
}: {
  title: string;
  onCancel: () => void;
  onSubmit: () => void;
  children: React.ReactNode;
}) {
  useEscape(onCancel);
  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/30 p-0 sm:items-center sm:p-4"
      onClick={onCancel}
    >
      <form
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit();
        }}
        className="w-full max-w-[440px] rounded-t-lg bg-background p-6 shadow-lg sm:rounded-lg"
      >
        <h2 className="text-[16px] font-semibold">{title}</h2>
        {children}
      </form>
    </div>
  );
}

function Actions({ onCancel, disabled }: { onCancel: () => void; disabled: boolean }) {
  return (
    <div className="mt-5 flex justify-end gap-2">
      <Button type="button" variant="secondary" size="sm" onClick={onCancel}>
        Cancel
      </Button>
      <Button type="submit" size="sm" disabled={disabled}>
        Save
      </Button>
    </div>
  );
}

export function EditReadingDialog({
  initial,
  onSubmit,
  onCancel,
}: {
  initial: { title: string; description: string | null };
  onSubmit: (fields: { title: string; description: string | null }) => Promise<void>;
  onCancel: () => void;
}) {
  const [title, setTitle] = useState(initial.title);
  const [description, setDescription] = useState(initial.description ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(false);

  async function submit() {
    if (!title.trim() || saving) return;
    setSaving(true);
    setError(false);
    try {
      await onSubmit({ title: title.trim(), description: description.trim() || null });
    } catch {
      setError(true);
      setSaving(false);
    }
  }

  return (
    <Shell title="Edit reading" onCancel={onCancel} onSubmit={submit}>
      <label className="mt-4 block text-[13px] font-medium">
        Title
        <input
          autoFocus
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          maxLength={200}
          className={`${INPUT} mt-1.5`}
        />
      </label>
      <label className="mt-3.5 block text-[13px] font-medium">
        Description (optional)
        <input
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          maxLength={200}
          className={`${INPUT} mt-1.5`}
        />
      </label>
      {error && <p className="mt-3 text-[13px] text-fail-foreground">That didn&rsquo;t save. Try again.</p>}
      <Actions onCancel={onCancel} disabled={!title.trim() || saving} />
    </Shell>
  );
}

export function ReadingClassesDialog({
  initial,
  onSubmit,
  onCancel,
}: {
  initial: string[];
  onSubmit: (classIds: string[]) => Promise<void>;
  onCancel: () => void;
}) {
  const [selected, setSelected] = useState(initial);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(false);

  async function submit() {
    if (saving) return;
    setSaving(true);
    setError(false);
    try {
      await onSubmit(selected);
    } catch {
      setError(true);
      setSaving(false);
    }
  }

  return (
    <Shell title="Classes" onCancel={onCancel} onSubmit={submit}>
      <div className="mt-4">
        <ClassPicker selected={selected} onChange={setSelected} />
      </div>
      {error && <p className="mt-3 text-[13px] text-fail-foreground">That didn&rsquo;t save. Try again.</p>}
      <Actions onCancel={onCancel} disabled={saving} />
    </Shell>
  );
}
