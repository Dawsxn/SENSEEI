/** One of the student's classes: its readings, filtered by whether they are
 *  done. A reading counts as finished once a session on it has ended, passed
 *  or failed, the same rule as the progress on the class card, which is where
 *  the progress lives; here the filter's counts say it. */

import { ChevronRight } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { AppTopBar } from "../../components/AppTopBar";
import { cn } from "../../lib/utils";
import { Breadcrumb, Notice, ReadingStatusChip } from "./parts";
import type { ReadingListItem } from "./types";
import { ClassSkeleton } from "./skeletons";
import { useMyClass } from "./useReadings";

type Filter = "all" | "todo" | "finished";

const FILTERS: { key: Filter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "todo", label: "To do" },
  { key: "finished", label: "Finished" },
];

const EMPTY: Record<Filter, string> = {
  all: "No readings available",
  todo: "Nothing left to do here.",
  finished: "No finished readings yet.",
};

const finished = (r: ReadingListItem) => r.status !== "not_started";

export function StudentClassPage() {
  const { classId } = useParams();
  const { data, isLoading, isError } = useMyClass(classId);
  const [filter, setFilter] = useState<Filter>("all");

  const readings = data?.readings ?? [];
  const done = readings.filter(finished).length;
  const counts: Record<Filter, number> = {
    all: readings.length,
    todo: readings.length - done,
    finished: done,
  };
  const shown = readings.filter((r) =>
    filter === "all"
      ? true
      : filter === "finished"
        ? finished(r)
        : !finished(r),
  );

  return (
    <div className="flex h-full flex-col">
      <AppTopBar />
      <main className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex max-w-[1148px] flex-col gap-4 px-4 py-4 sm:gap-5 sm:px-8 sm:py-6 lg:px-6">
          {isLoading && <ClassSkeleton />}
          {isError && (
            <Notice>Couldn't load this class. It may have been removed.</Notice>
          )}

          {data && (
            <>
              <div className="flex flex-col gap-2.5">
                <Breadcrumb
                  trail={[{ label: "Classes", to: "/" }]}
                  current={data.label}
                />
                <div className="min-w-0">
                  <h1 className="truncate text-[22px] font-semibold tracking-[-0.02em] sm:text-[24px]">
                    {data.name}
                  </h1>
                  {data.section && (
                    <div className="mt-0.5 truncate text-[14px] font-medium text-foreground/70">
                      {data.section}
                    </div>
                  )}
                </div>
              </div>

              {readings.length > 0 && (
                <div className="flex gap-0.5 self-stretch rounded-lg bg-muted p-[3px] sm:self-start">
                  {FILTERS.map((f) => (
                    <button
                      key={f.key}
                      type="button"
                      aria-pressed={filter === f.key}
                      onClick={() => setFilter(f.key)}
                      className={cn(
                        "flex-1 rounded-md py-[5px] text-[13px] font-medium sm:w-[104px] sm:flex-none",
                        filter === f.key
                          ? "bg-background text-foreground shadow-raised"
                          : "text-muted-foreground hover:text-foreground",
                      )}
                    >
                      {f.label}
                      <span className="ml-1 text-muted-foreground/70">
                        {counts[f.key]}
                      </span>
                    </button>
                  ))}
                </div>
              )}

              {shown.length === 0 ? (
                <Notice>{EMPTY[filter]}</Notice>
              ) : (
                <div className="overflow-hidden rounded-lg border">
                  {shown.map((r, i) => (
                    <Link
                      key={r.id}
                      to={`/classes/${data.id}/readings/${r.id}`}
                      className={cn(
                        "flex items-center gap-3 py-3.5 pl-4 pr-3 hover:bg-muted/50 focus-visible:bg-muted/50 focus-visible:outline-none sm:gap-5 sm:pl-5 sm:pr-4",
                        i > 0 && "border-t",
                      )}
                    >
                      <div className="min-w-0 flex-1">
                        <div className="text-[14px] font-medium">{r.title}</div>
                        {r.description && (
                          <div className="mt-0.5 text-[13px] text-muted-foreground">
                            {r.description}
                          </div>
                        )}
                      </div>
                      <ReadingStatusChip status={r.status} />
                      <ChevronRight className="h-[18px] w-[18px] shrink-0 text-muted-foreground/70" />
                    </Link>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
}
