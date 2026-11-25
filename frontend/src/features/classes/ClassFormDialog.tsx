/** Create a class, or edit one. The same two fields either way, left empty
 *  rather than holding example values that read as if they were filled in.
 *
 * On the trial instance a class is one of the study's groups, so it also has a
 * mode, and can take the pre-test and post-test written for its reading. The
 * mode and the tests are fixed once a participant has signed in.
 */

import { useEffect, useState } from "react";

import { Button } from "../../components/ui/button";
import { ApiError } from "../../lib/api";
import { cn } from "../../lib/utils";
import { useTrialMode } from "../auth/useAuth";
import { MODE_LABEL, type ClassFields, type ClassMode } from "./types";

const MODES: ClassMode[] = ["seei", "chatbot", "reading_only"];

interface ClassFormDialogProps {
  mode: "new" | "edit";
  initial?: ClassFields;
  /** The mode and tests can no longer change: a participant has signed in. */
  modeLocked?: boolean;
  /** Trial mode: the tests this class could take. A new class has none, since
   *  it has no reading yet. */
  tests?: { key: string; title: string }[];
  onSubmit: (fields: ClassFields) => Promise<void>;
  onCancel: () => void;
}

const INPUT =
  "h-9 w-full rounded-md border bg-card px-3 text-[14px] outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/30";

export function ClassFormDialog({
  mode,
  initial,
  modeLocked = false,
  tests = [],
  onSubmit,
  onCancel,
}: ClassFormDialogProps) {
  const trial = useTrialMode();
  const [name, setName] = useState(initial?.name ?? "");
  const [section, setSection] = useState(initial?.section ?? "");
  const [classMode, setClassMode] = useState<ClassMode>(initial?.mode ?? "seei");
  const [testKey, setTestKey] = useState<string>(initial?.test_key ?? "");
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
      await onSubmit({
        name: name.trim(),
        section: section.trim(),
        ...(trial ? { mode: classMode, test_key: testKey || null } : {}),
      });
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 409 && err.detail.includes("mode")
          ? "A participant has signed in, so the mode can't change."
          : err instanceof ApiError && err.status === 409
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
        className="w-full max-w-[420px] rounded-t-lg bg-card p-6 shadow-lg sm:rounded-lg"
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
              maxLength={60}
              className={`${INPUT} mt-1.5`}
            />
          </label>
          <label className="text-[13px] font-medium">
            Section
            <input
              value={section}
              onChange={(e) => setSection(e.target.value)}
              maxLength={20}
              className={`${INPUT} mt-1.5`}
            />
          </label>
        </div>

        {trial ? (
          <>
            <p className="mt-4 text-[13px] font-medium">Mode</p>
            <div
              role="radiogroup"
              aria-label="Mode"
              className="mt-1.5 flex gap-0.5 rounded-md bg-muted p-[3px]"
            >
              {MODES.map((m) => (
                <button
                  key={m}
                  type="button"
                  role="radio"
                  aria-checked={classMode === m}
                  disabled={modeLocked}
                  onClick={() => setClassMode(m)}
                  className={cn(
                    "h-[30px] flex-1 rounded text-[13px] font-medium transition-colors disabled:cursor-not-allowed",
                    classMode === m
                      ? "bg-card shadow-sm"
                      : "text-muted-foreground enabled:hover:text-foreground",
                  )}
                >
                  {MODE_LABEL[m]}
                </button>
              ))}
            </div>
            <label className="mt-4 block text-[13px] font-medium">
              Pre-test and post-test
              <select
                value={testKey}
                onChange={(e) => setTestKey(e.target.value)}
                disabled={modeLocked || tests.length === 0}
                className={`${INPUT} mt-1.5 disabled:cursor-not-allowed disabled:bg-muted/50 disabled:text-muted-foreground`}
              >
                <option value="">Off</option>
                {tests.map((t) => (
                  <option key={t.key} value={t.key}>
                    {t.title}
                  </option>
                ))}
              </select>
            </label>
            <p className="mt-2 text-[12px] text-muted-foreground">
              {tests.length === 0 && !initial?.test_key
                ? "Add a reading to this class first."
                : "Mode and tests can’t be changed once a participant signs in."}
            </p>
          </>
        ) : null}
        {error && <p className="mt-2 text-[13px] text-fail-foreground">{error}</p>}

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
