/** One batch: its IDs, what each has done, and the slips to print.
 *
 * The IDs are listed by class (SEE-I, then chatbot, then reading only), and a
 * filter narrows the list to one class. Printing follows the filter: the page is
 * swapped for a sheet of slips, with a line above each class's slips naming it,
 * to be cut off before the slips go into the bowl. A slip itself only ever shows
 * the ID and where to enter it, so a participant learns their group on signing
 * in. The fishbowl does the randomizing (docs/context/trial.md).
 *
 * Closing the batch ends the sitting; voiding one ID handles a spoiled slip or
 * someone who left. A closed batch can be deleted with everything recorded for
 * its IDs, to clear out a dry run. All three ask first, because none can be
 * undone. Each ID links to its answers on the grading page. */

import { useEffect, useMemo, useState } from "react";
import { Ban, Check, ChevronLeft, Copy, Download, Lock, Plus, Printer, Trash2 } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";

import { AppTopBar } from "../../components/AppTopBar";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { Tooltip } from "../../components/ui/Tooltip";
import { Button } from "../../components/ui/button";
import { addBatchIds, batchExportUrl, closeBatch, deleteBatch, voidParticipant } from "../../lib/api";
import { AddIdsDialog } from "./AddIdsDialog";
import { cn } from "../../lib/utils";
import { MODE_LABEL, type ClassMode } from "../classes/types";
import type { Batch, BatchParticipant, ParticipantStatus } from "./types";
import { useBatch } from "./useTrial";

const STATUS: Record<ParticipantStatus, { label: string; tone: string }> = {
  not_used: { label: "Not used", tone: "text-muted-foreground/70" },
  signed_in: { label: "Signed in", tone: "" },
  finished: { label: "Finished", tone: "" },
  voided: { label: "Voided", tone: "text-fail-foreground" },
};

/** The order the groups are listed and printed in. */
const MODE_ORDER: ClassMode[] = ["seei", "chatbot", "reading_only"];

/** One class's IDs within a batch. `name` is its group, with the class added
 *  when two classes in the batch share a group. */
interface Group {
  classId: string;
  name: string;
  classLabel: string;
  participants: BatchParticipant[];
}

function groupsOf(batch: Batch): Group[] {
  const byClass = new Map<string, BatchParticipant[]>();
  for (const p of batch.participants) byClass.set(p.class_id, [...(byClass.get(p.class_id) ?? []), p]);
  const groups = [...byClass.values()].map((ps) => ps.sort((a, b) => a.code.localeCompare(b.code)));
  groups.sort(
    (a, b) =>
      MODE_ORDER.indexOf(a[0].mode) - MODE_ORDER.indexOf(b[0].mode) ||
      a[0].class_label.localeCompare(b[0].class_label),
  );
  const modes = groups.map((ps) => ps[0].mode);
  return groups.map((ps) => {
    const shared = modes.filter((m) => m === ps[0].mode).length > 1;
    return {
      classId: ps[0].class_id,
      name: MODE_LABEL[ps[0].mode] + (shared ? ` (${ps[0].class_label})` : ""),
      classLabel: ps[0].class_label,
      participants: ps,
    };
  });
}

type Dialog =
  | { kind: "close" }
  | { kind: "delete" }
  | { kind: "add" }
  | { kind: "void"; participant: BatchParticipant }
  | null;

export function BatchPage() {
  const { batchId } = useParams<{ batchId: string }>();
  const { data: batch, isLoading, isError } = useBatch(batchId);
  const [dialog, setDialog] = useState<Dialog>(null);
  // "all", or one class's id. Printing follows it.
  const [filter, setFilter] = useState<string>("all");
  const groups = useMemo(() => (batch ? groupsOf(batch) : []), [batch]);
  const shown = filter === "all" ? groups : groups.filter((g) => g.classId === filter);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  // The IDs just added, marked New until the page reloads, and printable on
  // their own so slips already cut aren't printed again.
  const [added, setAdded] = useState<string[]>([]);
  const [printingNew, setPrintingNew] = useState(false);
  const printed = printingNew
    ? groups
        .map((g) => ({ ...g, participants: g.participants.filter((p) => added.includes(p.code)) }))
        .filter((g) => g.participants.length > 0)
    : shown;
  useEffect(() => {
    if (!printingNew) return;
    const done = () => setPrintingNew(false);
    window.addEventListener("afterprint", done);
    window.print();
    return () => window.removeEventListener("afterprint", done);
  }, [printingNew]);

  async function settle(updated: Batch) {
    queryClient.setQueryData(["batch", batchId], updated);
    await queryClient.invalidateQueries({ queryKey: ["batches"] });
    setDialog(null);
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex min-h-0 flex-1 flex-col print:hidden">
        <AppTopBar />
        <main className="min-h-0 flex-1 overflow-y-auto">
          <div className="mx-auto max-w-[1100px] px-4 py-5 sm:px-6 sm:py-6">
            <button
              onClick={() => navigate("/participants")}
              className="mb-4 flex items-center gap-1.5 text-[13px] text-muted-foreground hover:text-foreground"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
              Participants
            </button>

            {isLoading && <Notice>Loading batch…</Notice>}
            {isError && <Notice>This batch doesn&rsquo;t exist.</Notice>}

            {batch && (
              <>
                <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex min-w-0 flex-wrap items-baseline gap-x-3 gap-y-1">
                    <h1 className="text-[24px] font-semibold tracking-[-0.02em]">{batch.name}</h1>
                    <span className="text-[14px] text-muted-foreground">
                      {summary(batch)}
                      {batch.closed_at && " · Closed"}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    {filter !== "all" && shown[0] && (
                      <span className="mr-1 text-[13px] text-muted-foreground">
                        Prints {shown[0].name} only
                      </span>
                    )}
                    {!batch.closed_at && (
                      <Button variant="secondary" size="sm" onClick={() => setDialog({ kind: "add" })}>
                        <Plus className="h-4 w-4" />
                        Add IDs
                      </Button>
                    )}
                    {/* A plain link, like Download data: the browser saves the zip. */}
                    <Tooltip text="Download this batch's data" align="right">
                      <a
                        href={batchExportUrl(batch.id)}
                        download
                        aria-label="Download this batch's data"
                        className="inline-flex h-9 w-9 items-center justify-center rounded-md border bg-background transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      >
                        <Download className="h-4 w-4" />
                      </a>
                    </Tooltip>
                    <Tooltip text="Print slips" align={batch.closed_at ? "left" : "right"}>
                      <Button
                        variant="secondary"
                        size="icon"
                        aria-label="Print slips"
                        onClick={() => window.print()}
                      >
                        <Printer className="h-4 w-4" />
                      </Button>
                    </Tooltip>
                    {batch.closed_at && (
                      <Tooltip text="Delete batch" align="left">
                        <Button
                          variant="danger"
                          size="icon"
                          aria-label="Delete batch"
                          onClick={() => setDialog({ kind: "delete" })}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </Tooltip>
                    )}
                    {!batch.closed_at && (
                      <Tooltip text="Close batch" align="left">
                        <Button
                          variant="danger"
                          size="icon"
                          aria-label="Close batch"
                          onClick={() => setDialog({ kind: "close" })}
                        >
                          <Lock className="h-4 w-4" />
                        </Button>
                      </Tooltip>
                    )}
                  </div>
                </div>

                <div className="mb-3.5 flex flex-wrap gap-2" role="group" aria-label="Show">
                  <Chip
                    on={filter === "all"}
                    onClick={() => setFilter("all")}
                    label="All"
                    count={batch.participants.length}
                  />
                  {groups.map((g) => (
                    <Chip
                      key={g.classId}
                      on={filter === g.classId}
                      onClick={() => setFilter(g.classId)}
                      label={g.name}
                      count={g.participants.length}
                    />
                  ))}
                </div>

                {added.length > 0 && (
                  <div
                    role="status"
                    className="mb-3.5 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-accent-soft-border bg-accent-soft px-3.5 py-2.5 text-[13px] text-accent-soft-foreground"
                  >
                    <span>
                      {added.length === 1
                        ? "1 ID added. It\u2019s marked New below."
                        : `${added.length} IDs added. They\u2019re marked New below.`}
                    </span>
                    <Button size="sm" onClick={() => setPrintingNew(true)}>
                      Print the new IDs
                    </Button>
                  </div>
                )}

                <div className="overflow-hidden rounded-lg border">
                  <div className="hidden h-10 grid-cols-[200px_1fr_140px_28px] items-center gap-4 border-b px-4 text-[12px] font-medium text-muted-foreground sm:grid">
                    <span>ID</span>
                    <span>Class</span>
                    <span>Status</span>
                    <span />
                  </div>
                  {shown.map((g) => (
                    <section key={g.classId} aria-label={g.name}>
                      <div className="flex h-9 items-center gap-2 border-b bg-muted/40 px-4 text-[13px] font-semibold">
                        {g.name}
                        <span className="font-normal text-muted-foreground">
                          · {g.classLabel} · {g.participants.length}
                        </span>
                      </div>
                      {g.participants.map((p) => (
                        <Row
                          key={p.id}
                          participant={p}
                          isNew={added.includes(p.code)}
                          canVoid={!batch.closed_at}
                          onVoid={() => setDialog({ kind: "void", participant: p })}
                        />
                      ))}
                    </section>
                  ))}
                </div>
              </>
            )}
          </div>
        </main>
      </div>

      {batch && <Slips groups={printed} />}
      {batch && dialog?.kind === "add" && (
        <AddIdsDialog
          batch={batch}
          onCancel={() => setDialog(null)}
          onSubmit={async (classes) => {
            const updated = await addBatchIds(batch.id, classes);
            setAdded(updated.added ?? []);
            await settle(updated);
          }}
        />
      )}

      {batch && dialog?.kind === "close" && (
        <ConfirmDialog
          title={`Close ${batch.name}?`}
          confirmLabel="Close"
          cancelLabel="Cancel"
          tone="danger"
          onConfirm={async () => settle(await closeBatch(batch.id))}
          onCancel={() => setDialog(null)}
        >
          Its IDs will stop working.
        </ConfirmDialog>
      )}
      {batch && dialog?.kind === "delete" && (
        <ConfirmDialog
          title={`Delete ${batch.name}?`}
          confirmLabel="Delete"
          cancelLabel="Cancel"
          tone="danger"
          onConfirm={async () => {
            await deleteBatch(batch.id);
            await queryClient.invalidateQueries({ queryKey: ["batches"] });
            navigate("/participants", { replace: true });
          }}
          onCancel={() => setDialog(null)}
        >
          Every ID in this batch and everything recorded for them will be deleted, and this
          can&rsquo;t be undone.
        </ConfirmDialog>
      )}
      {batch && dialog?.kind === "void" && (
        <ConfirmDialog
          title={`Void ${dialog.participant.code}?`}
          confirmLabel="Void"
          cancelLabel="Cancel"
          tone="danger"
          onConfirm={async () => settle(await voidParticipant(batch.id, dialog.participant.id))}
          onCancel={() => setDialog(null)}
        >
          This ID will stop working.
        </ConfirmDialog>
      )}
    </div>
  );
}

function Row({
  participant: p,
  isNew = false,
  canVoid,
  onVoid,
}: {
  participant: BatchParticipant;
  isNew?: boolean;
  canVoid: boolean;
  onVoid: () => void;
}) {
  const status = STATUS[p.status];
  const voidable = canVoid && p.status !== "voided" && p.status !== "finished";
  return (
    <div className="grid grid-cols-[1fr_28px] items-center gap-4 border-b px-4 py-2.5 last:border-b-0 sm:grid-cols-[200px_1fr_140px_28px]">
      <span className="min-w-0">
        <span className="flex items-center gap-1.5">
          <Link
            to={`/grading?id=${encodeURIComponent(p.code)}`}
            className={`block font-mono text-[13px] tracking-wider hover:underline ${
              p.status === "voided" ? "text-muted-foreground/70 line-through" : ""
            }`}
          >
            {p.code}
          </Link>
          {/* A voided ID no longer works, so there is nothing to copy. */}
          {p.status !== "voided" && <CopyButton code={p.code} />}
          {isNew && (
            <span className="rounded-full border border-accent-soft-border bg-accent-soft px-1.5 text-[11px] font-semibold text-accent-soft-foreground">
              New
            </span>
          )}
        </span>
        {/* On narrow screens the columns collapse into this line. */}
        <span className="mt-0.5 block text-[12px] text-muted-foreground sm:hidden">
          {p.class_label} · {MODE_LABEL[p.mode]} · {status.label}
        </span>
      </span>
      <span className="hidden text-[13px] text-[#3f3f46] sm:block">
        {p.class_label} <span className="text-muted-foreground">· {MODE_LABEL[p.mode]}</span>
      </span>
      <span className={`hidden text-[13px] sm:block ${status.tone}`}>{status.label}</span>
      {voidable ? (
        <Tooltip text={`Void ${p.code}`} align="left">
          <button
            aria-label={`Void ${p.code}`}
            onClick={onVoid}
            className="flex h-7 w-7 items-center justify-center rounded-md text-fail-foreground hover:bg-fail focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40"
          >
            <Ban className="h-3.5 w-3.5" />
          </button>
        </Tooltip>
      ) : (
        <span />
      )}
    </div>
  );
}

function Chip({
  on,
  onClick,
  label,
  count,
}: {
  on: boolean;
  onClick: () => void;
  label: string;
  count: number;
}) {
  return (
    <button
      onClick={onClick}
      aria-pressed={on}
      className={cn(
        "inline-flex h-8 items-center gap-1.5 rounded-full border px-3 text-[13px] font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        on
          ? "border-accent-soft-border bg-accent-soft text-accent-soft-foreground"
          : "bg-background text-[#3f3f46] hover:bg-muted",
      )}
    >
      {label}
      <span className={on ? "font-normal text-primary" : "font-normal text-muted-foreground/70"}>
        {count}
      </span>
    </button>
  );
}

/** Copies the ID, then shows a tick and "Copied" for two seconds. */
function CopyButton({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    if (!copied) return;
    const t = setTimeout(() => setCopied(false), 2000);
    return () => clearTimeout(t);
  }, [copied]);
  return (
    <>
      <button
        aria-label={`Copy ${code}`}
        onClick={async () => {
          try {
            await navigator.clipboard.writeText(code);
            setCopied(true);
          } catch {
            // No clipboard (an insecure page, or permission refused): nothing to show.
          }
        }}
        className={cn(
          "flex h-[26px] w-[26px] items-center justify-center rounded-md transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40",
          copied ? "text-accent-soft-foreground" : "text-muted-foreground/70",
        )}
      >
        {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
      </button>
      {copied && <span className="text-[12px] text-accent-soft-foreground">Copied</span>}
    </>
  );
}

/** "15 IDs, 5 per class", or just the total when the classes got different counts. */
function summary(batch: Batch): string {
  const perClass = new Map<string, number>();
  for (const p of batch.participants) perClass.set(p.class_id, (perClass.get(p.class_id) ?? 0) + 1);
  const counts = new Set(perClass.values());
  const total = `${batch.participants.length} IDs`;
  return counts.size === 1 && perClass.size > 1 ? `${total}, ${[...counts][0]} per class` : total;
}

/** The printed sheet: each class's slips under a line naming it, three slips a
 *  row, cut along the dashes. The line is cut off before the slips go into the
 *  bowl, and the slips never name the class. Voided IDs are left out, since they
 *  would not work. Only the printer sees this. */
function Slips({ groups }: { groups: Group[] }) {
  const host = window.location.host;
  return (
    <div className="hidden grid-cols-3 print:grid">
      {groups.flatMap((g, i) => {
        const live = g.participants.filter((p) => p.status !== "voided");
        return [
          <div
            key={`h-${g.classId}`}
            className={cn(
              "col-span-3 mb-2 flex justify-between border-b border-black pb-1 text-[11px]",
              i > 0 && "mt-6",
            )}
          >
            <span className="font-semibold uppercase tracking-[0.04em]">
              {g.name} · {g.classLabel} · {live.length} {live.length === 1 ? "slip" : "slips"}
            </span>
            <span className="text-muted-foreground">
              Cut this line off before the slips go in the bowl.
            </span>
          </div>,
          ...live.map((p) => (
          <div
            key={p.id}
            className="flex break-inside-avoid flex-col gap-1.5 border border-dashed border-[#a1a1aa] px-4 py-4"
          >
            <span className="text-[10px] tracking-[0.06em] text-muted-foreground">
              PARTICIPANT ID
            </span>
            <span className="font-mono text-[17px] font-medium tracking-wider">{p.code}</span>
            <span className="text-[10px] leading-snug text-muted-foreground">
              Go to {host} and enter this ID.
            </span>
          </div>
          )),
        ];
      })}
    </div>
  );
}

function Notice({ children }: { children: React.ReactNode }) {
  return <p className="py-10 text-center text-[14px] text-muted-foreground">{children}</p>;
}
