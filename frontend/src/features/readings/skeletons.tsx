/** Loading placeholders for the student's pages, each in the shape of the page
 *  it stands in for, so nothing jumps when the real content arrives. */

import { Loading, Skeleton } from "../../components/ui/Skeleton";

export function ClassesSkeleton() {
  return (
    <Loading
      label="Loading your classes"
      className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 lg:grid-cols-4 lg:gap-5"
    >
      {[0, 1].map((i) => (
        <div key={i} className="rounded-lg border">
          <Skeleton className="mx-2 mt-2 h-16 sm:h-24" />
          <div className="flex flex-col gap-2.5 px-4 pb-[18px] pt-3.5">
            <Skeleton className="h-4 w-28" />
            <Skeleton className="h-3.5 w-16" />
            <Skeleton className="h-3.5 w-20" />
          </div>
        </div>
      ))}
    </Loading>
  );
}

export function ClassSkeleton() {
  return (
    <Loading label="Loading the class" className="flex flex-col gap-4 sm:gap-5">
      <div className="flex flex-col gap-3">
        <Skeleton className="h-3.5 w-32" />
        <div className="flex flex-col gap-2">
          <Skeleton className="h-7 w-40" />
          <Skeleton className="h-3.5 w-12" />
        </div>
      </div>
      <Skeleton className="h-[34px] w-full rounded-lg sm:w-[318px]" />
      <div className="overflow-hidden rounded-lg border">
        {[0, 1, 2].map((i) => (
          <div key={i} className={`flex items-center gap-3 py-4 pl-4 pr-3 sm:gap-5 sm:pl-5 ${i ? "border-t" : ""}`}>
            <div className="flex min-w-0 flex-1 flex-col gap-2">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-3.5 w-56 max-w-full" />
            </div>
            <Skeleton className="h-[22px] w-24 rounded-full" />
          </div>
        ))}
      </div>
    </Loading>
  );
}

export function ReadingSkeleton() {
  return (
    <Loading label="Loading the reading" className="flex flex-col gap-6 sm:gap-7">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex flex-col gap-3">
          <Skeleton className="h-3.5 w-52" />
          <Skeleton className="h-7 w-48" />
          <Skeleton className="h-4 w-64 max-w-full" />
        </div>
        <Skeleton className="h-10 w-full sm:h-9 sm:w-[72px]" />
      </div>
      <div className="grid items-start gap-7 lg:grid-cols-[1fr_420px] lg:gap-8">
        <div className="flex flex-col gap-2.5">
          <Skeleton className="h-3 w-32" />
          <div className="flex flex-col gap-4 rounded-lg border px-4 py-4 sm:px-5">
            {["w-full", "w-11/12", "w-4/5"].map((w) => (
              <div key={w} className="flex gap-3">
                <Skeleton className="h-4 w-4 shrink-0" />
                <Skeleton className={`h-4 ${w}`} />
              </div>
            ))}
          </div>
        </div>
        <div className="flex flex-col gap-2.5">
          <Skeleton className="h-3 w-24" />
          <SessionRowsSkeleton />
        </div>
      </div>
    </Loading>
  );
}

/** Rows in the past sessions box, while the sessions load. */
export function SessionRowsSkeleton({ rows = 2 }: { rows?: number }) {
  return (
    <div className="overflow-hidden rounded-lg border">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className={`flex items-center gap-3 px-4 py-3 ${i ? "border-t" : ""}`}>
          <Skeleton className="h-4 w-[76px]" />
          <Skeleton className="h-[22px] w-24 rounded-full" />
          <Skeleton className="ml-auto h-3.5 w-20" />
        </div>
      ))}
    </div>
  );
}
