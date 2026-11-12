/** One batch: its IDs, what each has done, and the slips to print.
 *
 * Printing uses the browser's own print, with the page swapped for a sheet of
 * slips: the ID and where to enter it, nothing else. The slips come in the
 * batch's shuffled order and never show the class, so handing them out from the
 * top of the stack assigns the groups at random.
 *
 * Closing the batch ends the sitting; voiding one ID handles a spoiled slip or
 * someone who left. Both ask first, because neither can be undone. */

import { useState } from "react";
import { Ban, ChevronLeft, Lock, Printer } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";

import { AppTopBar } from "../../components/AppTopBar";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { Tooltip } from "../../components/ui/Tooltip";
import { Button } from "../../components/ui/button";
import { closeBatch, voidParticipant } from "../../lib/api";
import { MODE_LABEL } from "../classes/types";
import type { Batch, BatchParticipant, ParticipantStatus } from "./types";
import { useBatch } from "./useTrial";

const STATUS: Record<ParticipantStatus, { label: string; tone: string }> = {
  not_used: { label: "Not used", tone: "text-muted-foreground/70" },
  signed_in: { label: "Signed in", tone: "" },
  finished: { label: "Finished", tone: "" },
  voided: { label: "Voided", tone: "text-fail-foreground" },
};

type Dialog = { kind: "close" } | { kind: "void"; participant: BatchParticipant } | null;

export function BatchPage() {
  const { batchId } = useParams<{ batchId: string }>();
  const { data: batch, isLoading, isError } = useBatch(batchId);
  const [dialog, setDialog] = useState<Dialog>(null);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

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
                  <div className="flex gap-2">
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

                <div className="rounded-lg border">
                  <div className="hidden h-10 grid-cols-[200px_1fr_140px_28px] items-center gap-4 border-b px-4 text-[12px] font-medium text-muted-foreground sm:grid">
                    <span>ID</span>
                    <span>Class</span>
                    <span>Status</span>
                    <span />
                  </div>
                  {batch.participants.map((p) => (
                    <Row
                      key={p.id}
                      participant={p}
                      canVoid={!batch.closed_at}
                      onVoid={() => setDialog({ kind: "void", participant: p })}
                    />
                  ))}
                </div>
              </>
            )}
          </div>
        </main>
      </div>

      {batch && <Slips batch={batch} />}

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
  canVoid,
  onVoid,
}: {
  participant: BatchParticipant;
  canVoid: boolean;
  onVoid: () => void;
}) {
  const status = STATUS[p.status];
  const voidable = canVoid && p.status !== "voided" && p.status !== "finished";
  return (
    <div className="grid grid-cols-[1fr_28px] items-center gap-4 border-b px-4 py-2.5 last:border-b-0 sm:grid-cols-[200px_1fr_140px_28px]">
      <span className="min-w-0">
        <span
          className={`block font-mono text-[13px] tracking-wider ${
            p.status === "voided" ? "text-muted-foreground/70 line-through" : ""
          }`}
        >
          {p.code}
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

/** "15 IDs, 5 per class", or just the total when the classes got different counts. */
function summary(batch: Batch): string {
  const perClass = new Map<string, number>();
  for (const p of batch.participants) perClass.set(p.class_id, (perClass.get(p.class_id) ?? 0) + 1);
  const counts = new Set(perClass.values());
  const total = `${batch.participants.length} IDs`;
  return counts.size === 1 && perClass.size > 1 ? `${total}, ${[...counts][0]} per class` : total;
}

/** The printed sheet: three slips a row, cut along the dashes. Voided IDs are
 *  left out, since they would not work. Only the printer sees this. */
function Slips({ batch }: { batch: Batch }) {
  const host = window.location.host;
  return (
    <div className="hidden grid-cols-3 print:grid">
      {batch.participants
        .filter((p) => p.status !== "voided")
        .map((p) => (
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
        ))}
    </div>
  );
}

function Notice({ children }: { children: React.ReactNode }) {
  return <p className="py-10 text-center text-[14px] text-muted-foreground">{children}</p>;
}
