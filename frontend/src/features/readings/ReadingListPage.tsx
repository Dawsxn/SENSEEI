import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { AppTopBar } from "../../components/AppTopBar";
import { Button } from "../../components/ui/button";
import { cn } from "../../lib/utils";
import type { ReadingListItem, ReadingStatus } from "./types";
import { useReadings } from "./useReadings";

const ALL = "All classes";

export function ReadingListPage() {
  const { data, isLoading, isError } = useReadings();
  const [classFilter, setClassFilter] = useState<string>(ALL);

  const classes = useMemo(
    () => Array.from(new Set((data ?? []).map((r) => r.class_name))).sort(),
    [data],
  );
  const rows = (data ?? []).filter(
    (r) => classFilter === ALL || r.class_name === classFilter,
  );

  return (
    <div className="flex h-full flex-col">
      <AppTopBar />
      <main className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[1100px] px-4 py-6 sm:px-6 sm:py-8">
          <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <h1 className="text-[24px] font-semibold tracking-[-0.02em]">Readings</h1>
            {classes.length > 1 && (
              <select
                value={classFilter}
                onChange={(e) => setClassFilter(e.target.value)}
                className="h-9 rounded-md border bg-background px-3 text-[14px] outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <option>{ALL}</option>
                {classes.map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            )}
          </div>

          {isLoading && <Notice>Loading readings…</Notice>}
          {isError && <Notice>Couldn't load your readings. Try again.</Notice>}
          {data && rows.length === 0 && (
            <Notice>No readings assigned to your classes yet.</Notice>
          )}

          {rows.length > 0 && (
            <div className="overflow-hidden rounded-lg border">
              <div className="hidden items-center gap-4 border-b px-4 py-2.5 text-[12px] font-medium uppercase tracking-wide text-muted-foreground sm:flex">
                <span className="flex-1">Reading</span>
                <span className="w-40">Class</span>
                <span className="w-28">Status</span>
                <span className="w-24" />
              </div>
              {rows.map((r, i) => (
                <ReadingRow key={r.id} reading={r} first={i === 0} />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

function ReadingRow({ reading, first }: { reading: ReadingListItem; first: boolean }) {
  const navigate = useNavigate();
  const started = reading.status !== "not_started";

  return (
    <div
      className={cn(
        "flex flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:gap-4",
        !first && "border-t",
      )}
    >
      <div className="min-w-0 flex-1">
        <div className="text-[14px] font-medium">{reading.title}</div>
        {reading.description && (
          <div className="text-[13px] text-muted-foreground">{reading.description}</div>
        )}
      </div>

      <div className="flex items-center justify-between gap-4 sm:justify-start">
        <span className="text-[13px] text-muted-foreground sm:w-40">
          {reading.class_name}
        </span>
        <div className="sm:w-28">
          <StatusBadge status={reading.status} />
        </div>
        <div className="sm:w-24 sm:text-right">
          {started ? (
            <Button variant="secondary" size="sm" disabled title="Review coming soon">
              Review
            </Button>
          ) : (
            <Button size="sm" onClick={() => navigate(`/tutor/${reading.id}`)}>
              Start
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: ReadingStatus }) {
  const styles: Record<ReadingStatus, string> = {
    not_started: "border-border text-muted-foreground",
    complete: "border-[#bbf7d0] bg-[#f0fdf4] text-[#15803d]",
    failed: "border-fail-border bg-fail text-fail-foreground",
  };
  const label = { not_started: "Not started", complete: "Complete", failed: "Failed" };
  return (
    <span
      className={cn(
        "inline-flex rounded-full border px-2.5 py-0.5 text-[12px] font-medium",
        styles[status],
      )}
    >
      {label[status]}
    </span>
  );
}

function Notice({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed px-4 py-10 text-center text-[14px] text-muted-foreground">
      {children}
    </div>
  );
}
