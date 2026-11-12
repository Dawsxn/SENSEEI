/** Upload a reading, in three steps: the PDF, its text, and its details.
 *
 * Nothing is saved until Save reading. Step one sends the PDF off to be turned
 * into text and have its figures described, and that comes back without being
 * stored. Step two is the instructor checking that text, which matters more than
 * anything else on the page: the tutor never sees the PDF, only this text, so a
 * mistake left here is one every student's answers are graded against.
 *
 * Going back a step keeps everything. The text is only fetched again if the
 * file itself changes, so corrections are never thrown away by a Back.
 *
 * Leaving midway asks first, since the work so far lives only in this page.
 *
 * Started from a class (`?class=`), it arrives with that class already ticked
 * and goes back there rather than to the readings list. Ticked, not locked: an
 * instructor teaching two sections of the same course wants both, and one who
 * started from the wrong class should not have to begin again.
 */

import { Suspense, lazy, useCallback, useEffect, useRef, useState } from "react";
import { Check, ChevronLeft, Info, Lock, Plus, Upload } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useBlocker, useNavigate, useSearchParams } from "react-router-dom";

import { AppTopBar } from "../../components/AppTopBar";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { Button } from "../../components/ui/button";
import { ApiError, createReading, extractReading } from "../../lib/api";
import { useClasses } from "../classes/useClasses";
import { ClassPicker } from "./ClassPicker";
import type { ExtractResult } from "./types";

const PdfPanel = lazy(() =>
  import("../tutoring/PdfPanel").then((m) => ({ default: m.PdfPanel })),
);

const MAX_BYTES = 20 * 1024 * 1024;
const STEPS = ["PDF", "Text", "Details"] as const;

type Step = "pdf" | "loading" | "text" | "details";

const INPUT =
  "h-9 w-full rounded-md border bg-background px-3 text-[14px] outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/30";

/** Words a title leaves lower case unless they start it. */
const MINOR = new Set(["a", "an", "and", "as", "at", "by", "for", "in", "of", "on", "or", "the", "to"]);

/** `recovery-to-the-bisector.pdf` -> `Recovery to the Bisector`. A starting point only. */
export function titleFromFilename(name: string): string {
  return name
    .replace(/\.pdf$/i, "")
    .replace(/[-_]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .split(" ")
    .map((w, i) =>
      i > 0 && MINOR.has(w.toLowerCase()) ? w.toLowerCase() : w.charAt(0).toUpperCase() + w.slice(1),
    )
    .join(" ");
}

function uploadError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.detail === "not_pdf") return "Not a PDF.";
    if (err.detail === "too_large") return "Over 20 MB.";
    if (err.detail === "no_text") return "No text found. The PDF may be a scanned image.";
  }
  return "That didn't work. Try again.";
}

export function UploadReadingPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [params] = useSearchParams();
  const fromClass = params.get("class");
  const { data: classes } = useClasses();
  const origin = fromClass
    ? {
        path: `/classes/${fromClass}`,
        label: classes?.find((c) => c.id === fromClass)?.label ?? "Class",
      }
    : { path: "/library", label: "Readings" };

  const [step, setStep] = useState<Step>("pdf");
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  // The file the current text was extracted from. A different file means the
  // text is stale; the same file means the instructor's edits are kept.
  const [extractedFrom, setExtractedFrom] = useState<File | null>(null);
  const [extracted, setExtracted] = useState<ExtractResult | null>(null);
  const [text, setText] = useState("");
  const [components, setComponents] = useState<string[]>([""]);
  const [classIds, setClassIds] = useState<string[]>(fromClass ? [fromClass] : []);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Set just before leaving on purpose, so the guard lets that one through.
  const leaving = useRef(false);
  const dirty = file !== null;
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      dirty && !leaving.current && currentLocation.pathname !== nextLocation.pathname,
  );

  // A refresh or a closed tab cannot show our dialog; the browser's own will do.
  useEffect(() => {
    if (!dirty) return;
    const warn = (e: BeforeUnloadEvent) => {
      if (leaving.current) return;
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  function choose(picked: File | undefined) {
    if (!picked) return;
    const isPdf = picked.type === "application/pdf" || /\.pdf$/i.test(picked.name);
    if (!isPdf) return setFileError("Not a PDF.");
    if (picked.size > MAX_BYTES) return setFileError("Over 20 MB.");
    setFileError(null);
    setFile(picked);
    if (!title.trim()) setTitle(titleFromFilename(picked.name));
  }

  async function toText() {
    if (!file || !title.trim()) return;
    if (extractedFrom === file) return setStep("text");
    setStep("loading");
    try {
      const result = await extractReading(file);
      setExtracted(result);
      setText(result.text);
      setExtractedFrom(file);
      setStep("text");
    } catch (err) {
      setFile(null);
      setFileError(uploadError(err));
      setStep("pdf");
    }
  }

  async function save() {
    const kept = components.map((c) => c.trim()).filter(Boolean);
    if (!file || !kept.length || saving) return;
    setSaving(true);
    setSaveError(null);
    try {
      const { id } = await createReading({
        file,
        title: title.trim(),
        description: description.trim(),
        content: text,
        coreComponents: kept,
        classIds,
      });
      await queryClient.invalidateQueries({ queryKey: ["library"] });
      await queryClient.invalidateQueries({ queryKey: ["classes"] });
      leaving.current = true;
      navigate(`/library/${id}`, { replace: true });
    } catch (err) {
      setSaveError(uploadError(err));
      setSaving(false);
    }
  }

  const stepIndex = step === "text" ? 1 : step === "details" ? 2 : 0;

  return (
    <div className="flex h-full flex-col">
      <AppTopBar />
      <main className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex max-w-[1360px] flex-col px-4 py-5 sm:px-6 sm:py-6">
          <button
            onClick={() => navigate(origin.path)}
            className="mb-4 flex w-fit items-center gap-1.5 text-[13px] text-muted-foreground hover:text-foreground"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
            {origin.label}
          </button>

          <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
            <h1 className="text-[22px] font-semibold tracking-[-0.02em] sm:text-[24px]">
              Upload a reading
            </h1>
            <Stepper current={stepIndex} />
          </div>

          {step === "pdf" && (
            <PdfStep
              file={file}
              error={fileError}
              title={title}
              description={description}
              onFile={choose}
              onRemove={() => setFile(null)}
              onTitle={setTitle}
              onDescription={setDescription}
              onNext={toText}
            />
          )}

          {step === "loading" && (
            <div className="flex flex-col items-center gap-3.5 py-24" role="status">
              <span className="h-7 w-7 animate-spin rounded-full border-[2.5px] border-muted border-t-primary" />
              <span className="text-[14px] font-medium">Reading your PDF&hellip;</span>
            </div>
          )}

          {step === "text" && file && extracted && (
            <TextStep
              file={file}
              extracted={extracted}
              text={text}
              onText={setText}
              onBack={() => setStep("pdf")}
              onNext={() => text.trim() && setStep("details")}
            />
          )}

          {step === "details" && (
            <DetailsStep
              components={components}
              onComponents={setComponents}
              classIds={classIds}
              onClassIds={setClassIds}
              saving={saving}
              error={saveError}
              onBack={() => setStep("text")}
              onSave={save}
            />
          )}
        </div>
      </main>

      {blocker.state === "blocked" && (
        <ConfirmDialog
          title="Leave this upload?"
          confirmLabel="Leave"
          cancelLabel="Stay"
          tone="danger"
          onConfirm={() => blocker.proceed()}
          onCancel={() => blocker.reset()}
        >
          Nothing is saved yet.
        </ConfirmDialog>
      )}
    </div>
  );
}

// --------------------------------------------------------------------------- //

function Stepper({ current }: { current: number }) {
  return (
    <ol className="flex items-center gap-2.5" aria-label="Steps">
      {STEPS.map((label, i) => {
        const done = i < current;
        const on = i === current;
        return (
          <li key={label} className="flex items-center gap-2" aria-current={on ? "step" : undefined}>
            <span
              className={`flex h-[22px] w-[22px] items-center justify-center rounded-full text-[12px] font-semibold ${
                done || on ? "bg-primary text-primary-foreground" : "border text-muted-foreground"
              }`}
            >
              {done ? <Check className="h-3 w-3" strokeWidth={3} /> : i + 1}
            </span>
            <span
              className={`hidden text-[13px] font-medium sm:inline ${
                done || on ? "text-foreground" : "text-muted-foreground"
              }`}
            >
              {label}
            </span>
            {i < STEPS.length - 1 && <span className="h-px w-3 bg-border sm:w-7" />}
          </li>
        );
      })}
    </ol>
  );
}

interface PdfStepProps {
  file: File | null;
  error: string | null;
  title: string;
  description: string;
  onFile: (file: File | undefined) => void;
  onRemove: () => void;
  onTitle: (value: string) => void;
  onDescription: (value: string) => void;
  onNext: () => void;
}

function PdfStep(props: PdfStepProps) {
  const { file, error, title, description, onFile, onRemove, onTitle, onDescription, onNext } =
    props;
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const ready = file !== null && title.trim() !== "";

  return (
    <form
      className="mx-auto flex w-full max-w-[560px] flex-col gap-5 pt-2"
      onSubmit={(e) => {
        e.preventDefault();
        if (ready) onNext();
      }}
    >
      {file ? (
        <div className="flex items-center gap-3 rounded-lg border px-3.5 py-3">
          <span className="flex h-9 w-8 shrink-0 items-center justify-center rounded bg-fail text-[9px] font-semibold text-fail-foreground">
            PDF
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-[14px] font-medium">{file.name}</span>
            <span className="block text-[12px] text-muted-foreground">{formatSize(file.size)}</span>
          </span>
          <button
            type="button"
            onClick={onRemove}
            className="text-[13px] text-muted-foreground hover:text-foreground"
          >
            Remove
          </button>
        </div>
      ) : (
        <div>
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setOver(true);
            }}
            onDragLeave={() => setOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setOver(false);
              onFile(e.dataTransfer.files[0]);
            }}
            className={`flex flex-col items-center gap-2 rounded-lg border border-dashed px-6 py-12 text-center ${
              over ? "border-primary bg-primary/5" : error ? "border-fail-border bg-muted/40" : "border-[#d4d4d8] bg-muted/40"
            }`}
          >
            <Upload className="h-7 w-7 text-muted-foreground/70" strokeWidth={1.6} />
            <span className="mt-1 text-[14px] font-medium">
              Drop a PDF or{" "}
              <button
                type="button"
                onClick={() => input.current?.click()}
                className="text-primary hover:underline"
              >
                choose a file
              </button>
            </span>
            <span className="text-[13px] text-muted-foreground">Up to 20 MB</span>
            <input
              ref={input}
              type="file"
              accept="application/pdf,.pdf"
              aria-label="PDF file"
              className="hidden"
              onChange={(e) => {
                onFile(e.target.files?.[0]);
                e.target.value = "";
              }}
            />
          </div>
          {error && <p className="mt-2 text-[13px] text-fail-foreground">{error}</p>}
        </div>
      )}

      <label className="text-[13px] font-medium">
        Title
        <input
          value={title}
          onChange={(e) => onTitle(e.target.value)}
          maxLength={200}
          className={`${INPUT} mt-1.5`}
        />
      </label>
      <label className="text-[13px] font-medium">
        Description (optional)
        <input
          value={description}
          onChange={(e) => onDescription(e.target.value)}
          maxLength={200}
          className={`${INPUT} mt-1.5`}
        />
      </label>

      <div className="flex justify-end">
        <Button type="submit" disabled={!ready}>
          Next
        </Button>
      </div>
    </form>
  );
}

function formatSize(bytes: number): string {
  return bytes >= 1024 * 1024
    ? `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

interface TextStepProps {
  file: File;
  extracted: ExtractResult;
  text: string;
  onText: (value: string) => void;
  onBack: () => void;
  onNext: () => void;
}

function TextStep({ file, extracted, text, onText, onBack, onNext }: TextStepProps) {
  // Below `lg` the PDF and the text cannot sit side by side, so they take turns.
  const [pane, setPane] = useState<"pdf" | "text">("text");
  // Made and revoked in one effect. A memoised URL revoked by an effect's
  // cleanup breaks under StrictMode, which runs the cleanup once on mount and
  // leaves the viewer holding a URL that no longer points at anything.
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    const made = URL.createObjectURL(file);
    setUrl(made);
    return () => URL.revokeObjectURL(made);
  }, [file]);

  const n = extracted.figures_described;
  const note = extracted.figures_failed
    ? { tone: "warn", text: "Couldn't describe the figures. Add them by hand if needed." }
    : n > 0
      ? {
          tone: "ok",
          text: n === 1 ? "1 figure described. Please verify." : `${n} figures described. Check each one.`,
        }
      : null;

  return (
    <div className="flex flex-col gap-3.5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h2 className="text-[16px] font-semibold">Check the text</h2>
          <p className="text-[13px] text-muted-foreground">
            The tutor only reads this text. Fix any mistakes.
          </p>
        </div>
        {note && (
          <p
            className={`flex items-center gap-2 rounded-md border px-3 py-2 text-[13px] ${
              note.tone === "warn"
                ? "border-[#fde68a] bg-[#fffbeb] text-[#92400e]"
                : "border-[#bbf7d0] bg-[#f0fdf4] text-[#166534]"
            }`}
          >
            <Info className="h-3.5 w-3.5 shrink-0" />
            {note.text}
          </p>
        )}
      </div>

      <div className="flex gap-0.5 rounded-md bg-muted p-[3px] lg:hidden">
        {(["pdf", "text"] as const).map((p) => (
          <button
            key={p}
            onClick={() => setPane(p)}
            className={`h-[30px] flex-1 rounded text-[13px] font-medium ${
              pane === p ? "bg-background text-foreground shadow-sm" : "text-muted-foreground"
            }`}
          >
            {p === "pdf" ? "PDF" : "Text"}
          </button>
        ))}
      </div>

      <div className="grid h-[calc(100vh-300px)] min-h-[420px] gap-4 lg:grid-cols-2">
        <div
          className={`min-h-0 overflow-hidden rounded-lg border ${pane === "pdf" ? "block" : "hidden"} lg:block`}
        >
          <Suspense fallback={<p className="p-6 text-[13px] text-muted-foreground">Loading the PDF…</p>}>
            {url && <PdfPanel fileUrl={url} fallback={null} />}
          </Suspense>
        </div>
        <textarea
          aria-label="Reading text"
          value={text}
          onChange={(e) => onText(e.target.value)}
          spellCheck
          className={`${pane === "text" ? "block" : "hidden"} min-h-0 w-full resize-none rounded-lg border bg-background px-4 py-3.5 text-[14px] leading-[1.65] outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/30 lg:block`}
        />
      </div>

      <div className="flex justify-end gap-2">
        <Button variant="secondary" onClick={onBack}>
          Back
        </Button>
        <Button onClick={onNext} disabled={!text.trim()}>
          Next
        </Button>
      </div>
    </div>
  );
}

interface DetailsStepProps {
  components: string[];
  onComponents: (value: string[]) => void;
  classIds: string[];
  onClassIds: (value: string[]) => void;
  saving: boolean;
  error: string | null;
  onBack: () => void;
  onSave: () => void;
}

function DetailsStep(props: DetailsStepProps) {
  const { components, onComponents, classIds, onClassIds, saving, error, onBack, onSave } = props;
  const ready = components.some((c) => c.trim());
  const [focusLast, setFocusLast] = useState(false);
  const lastRef = useCallback(
    (el: HTMLInputElement | null) => {
      if (el && focusLast) {
        el.focus();
        setFocusLast(false);
      }
    },
    [focusLast],
  );

  const set = (i: number, value: string) =>
    onComponents(components.map((c, j) => (j === i ? value : c)));

  return (
    <div className="mx-auto flex w-full max-w-[640px] flex-col gap-7 pt-1">
      <section className="flex flex-col gap-2.5">
        <h2 className="text-[16px] font-semibold">Core components</h2>
        {components.map((c, i) => (
          <div key={i} className="flex items-center gap-2.5">
            <span className="w-4 shrink-0 text-right text-[13px] text-muted-foreground">{i + 1}</span>
            <input
              ref={i === components.length - 1 ? lastRef : undefined}
              aria-label={`Core component ${i + 1}`}
              value={c}
              onChange={(e) => set(i, e.target.value)}
              className={INPUT}
            />
            {components.length > 1 && (
              <button
                onClick={() => onComponents(components.filter((_, j) => j !== i))}
                className="shrink-0 text-[13px] text-muted-foreground hover:text-foreground"
              >
                Remove
              </button>
            )}
          </div>
        ))}
        <div className="pl-[26px]">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              onComponents([...components, ""]);
              setFocusLast(true);
            }}
          >
            <Plus className="h-3.5 w-3.5 text-muted-foreground" />
            Add a core component
          </Button>
        </div>
      </section>

      <section className="flex flex-col gap-2.5">
        <h2 className="text-[16px] font-semibold">Classes</h2>
        <ClassPicker selected={classIds} onChange={onClassIds} />
      </section>

      <div className="flex flex-col gap-3 border-t pt-[18px] sm:flex-row sm:items-center sm:justify-between">
        <p className="flex items-center gap-2 text-[13px] text-muted-foreground">
          <Lock className="h-3.5 w-3.5 shrink-0" />
          Text and core components can&rsquo;t be changed after saving.
        </p>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onBack}>
            Back
          </Button>
          <Button onClick={onSave} disabled={!ready || saving}>
            Save reading
          </Button>
        </div>
      </div>
      {error && <p className="-mt-4 text-right text-[13px] text-fail-foreground">{error}</p>}
    </div>
  );
}
