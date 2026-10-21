/** The research team's participant IDs, one batch per sitting.
 *
 * Laid out like the Classes page: a heading with a green add button, and a
 * table, or an empty state holding the button when there is nothing yet.
 *
 * Also where the trial's data leaves the app (Download data) and where a
 * participant who withdraws is deleted. */

import { useState } from "react";
import { ChevronRight, Download, Plus } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { AppTopBar } from "../../components/AppTopBar";
import { Tooltip } from "../../components/ui/Tooltip";
import { Button } from "../../components/ui/button";
import { TRIAL_EXPORT_URL, createBatch } from "../../lib/api";
import { formatShortDate } from "../../lib/format";
import { NewBatchDialog } from "./NewBatchDialog";
import { WithdrawCard } from "./WithdrawCard";
import type { NewBatch } from "./types";
import { useBatches } from "./useTrial";

export function ParticipantsPage() {
  const { data, isLoading, isError } = useBatches();
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const batches = data ?? [];

  async function create(batch: NewBatch) {
    const made = await createBatch(batch);
    await queryClient.invalidateQueries({ queryKey: ["batches"] });
    navigate(`/participants/${made.id}`);
  }

  return (
    <div className="flex h-full flex-col">
      <AppTopBar />
      <main className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[1100px] px-4 py-6 sm:px-6 sm:py-8">
          <div className="mb-5 flex h-9 items-center justify-between">
            <h1 className="text-[24px] font-semibold tracking-[-0.02em]">Participants</h1>
            {batches.length > 0 && (
              <div className="flex gap-2">
                {/* A plain link: the browser downloads the zip itself. */}
                <Tooltip text="Download data" align="left">
                  <a
                    href={TRIAL_EXPORT_URL}
                    download
                    aria-label="Download data"
                    className="inline-flex h-9 w-9 items-center justify-center rounded-md border bg-background transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <Download className="h-4 w-4" />
                  </a>
                </Tooltip>
                <Tooltip text="New batch" align="left">
                  <Button variant="accent" size="icon" aria-label="New batch" onClick={() => setCreating(true)}>
                    <Plus className="h-4 w-4" />
                  </Button>
                </Tooltip>
              </div>
            )}
          </div>

          {isLoading && <Notice>Loading batches…</Notice>}
          {isError && <Notice>Couldn&rsquo;t load the batches.</Notice>}

          {data && batches.length === 0 && (
            <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed px-6 py-16 text-center">
              <span className="text-[15px] font-semibold">No batches yet</span>
              <span className="text-[14px] text-muted-foreground">
                Make a batch of IDs for each sitting.
              </span>
              <Button className="mt-3" onClick={() => setCreating(true)}>
                <Plus className="h-4 w-4" />
                New batch
              </Button>
            </div>
          )}

          {batches.length > 0 && (
            <div className="overflow-hidden rounded-lg border">
              <div className="hidden h-10 grid-cols-[1fr_160px_100px_100px_100px_24px] items-center gap-4 border-b px-4 text-[12px] font-medium text-muted-foreground sm:grid">
                <span>Batch</span>
                <span>Created</span>
                <span>IDs</span>
                <span>Used</span>
                <span>Status</span>
                <span />
              </div>
              {batches.map((b) => (
                <button
                  key={b.id}
                  onClick={() => navigate(`/participants/${b.id}`)}
                  className="grid w-full grid-cols-[1fr_24px] items-center gap-4 border-b px-4 py-4 text-left last:border-b-0 hover:bg-muted/40 sm:grid-cols-[1fr_160px_100px_100px_100px_24px]"
                >
                  <span className="min-w-0">
                    <span className="block text-[14px] font-medium">{b.name}</span>
                    <span className="mt-0.5 block text-[13px] text-muted-foreground sm:hidden">
                      {b.used_count} of {b.id_count} used · {b.closed_at ? "Closed" : "Open"}
                    </span>
                  </span>
                  <span className="hidden text-[13px] text-muted-foreground sm:block">
                    {formatShortDate(b.created_at)}
                  </span>
                  <span className="hidden text-[13px] text-muted-foreground sm:block">{b.id_count}</span>
                  <span className="hidden text-[13px] text-muted-foreground sm:block">{b.used_count}</span>
                  <span
                    className={`hidden text-[13px] sm:block ${
                      b.closed_at ? "text-muted-foreground" : "text-accent-soft-foreground"
                    }`}
                  >
                    {b.closed_at ? "Closed" : "Open"}
                  </span>
                  <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/70" />
                </button>
              ))}
            </div>
          )}

          {batches.length > 0 && <WithdrawCard />}
        </div>
      </main>

      {creating && (
        <NewBatchDialog
          defaultName={`Sitting ${batches.length + 1}`}
          onSubmit={create}
          onCancel={() => setCreating(false)}
        />
      )}
    </div>
  );
}

function Notice({ children }: { children: React.ReactNode }) {
  return <p className="py-10 text-center text-[14px] text-muted-foreground">{children}</p>;
}
