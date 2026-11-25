/** An instructor's readings, and the way to upload a new one.
 *
 * Rows as on a class page. Each shows the classes it is in as chips, two at
 * most with a "+N" for the rest, so a row keeps one height; the reading's own
 * page lists them all. A reading in no class says so, since no student sees it.
 */

import { ChevronRight } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import { AppTopBar } from "../../components/AppTopBar";
import { Skeleton } from "../../components/ui/Skeleton";
import { Button } from "../../components/ui/button";
import { cn } from "../../lib/utils";
import { Notice } from "../readings/parts";
import { useLibrary } from "./useLibrary";

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;
const SHOWN = 2;

export function LibraryListPage() {
  const { data, isLoading, isError } = useLibrary();
  const navigate = useNavigate();

  return (
    <div className="flex h-full flex-col">
      <AppTopBar />
      <main className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex max-w-[1148px] flex-col gap-5 px-4 py-5 sm:gap-6 sm:px-8 sm:py-7 lg:px-6 lg:py-8">
          <div className="flex items-center justify-between gap-4">
            <h1 className="text-[22px] font-semibold tracking-[-0.02em] sm:text-[24px]">Readings</h1>
            <Button variant="secondary" size="sm" onClick={() => navigate("/library/new")}>
              + Upload reading
            </Button>
          </div>

          {isLoading && <RowsSkeleton />}
          {isError && <Notice>Couldn't load your readings. Try again.</Notice>}
          {data && data.length === 0 && <Notice>No readings available</Notice>}

          {data && data.length > 0 && (
            <div className="overflow-hidden rounded-lg border">
              {data.map((r, i) => (
                <Link
                  key={r.id}
                  to={`/library/${r.id}`}
                  className={cn(
                    "flex flex-wrap items-center gap-x-3 gap-y-2 py-3.5 pl-4 pr-3 hover:bg-muted/50 focus-visible:bg-muted/50 focus-visible:outline-none sm:flex-nowrap sm:gap-5 sm:pl-5 sm:pr-4",
                    i > 0 && "border-t",
                  )}
                >
                  <div className="min-w-0 flex-1 basis-[calc(100%-30px)] sm:basis-auto">
                    <div className="text-[14px] font-medium">{r.title}</div>
                    {r.description && (
                      <div className="mt-0.5 text-[13px] text-muted-foreground">{r.description}</div>
                    )}
                  </div>
                  <ChevronRight className="order-1 h-[18px] w-[18px] shrink-0 text-muted-foreground/70 sm:order-none sm:hidden" />
                  <div className="order-2 flex min-w-0 flex-1 gap-1.5 sm:order-none sm:w-[260px] sm:flex-none">
                    {r.classes.length === 0 ? (
                      <span className="text-[12px] text-muted-foreground/70">Not in a class</span>
                    ) : (
                      <>
                        {r.classes.slice(0, SHOWN).map((label) => (
                          <span
                            key={label}
                            className="inline-flex h-[22px] shrink-0 items-center rounded-full bg-muted px-2 text-[12px] font-medium text-foreground/80"
                          >
                            {label}
                          </span>
                        ))}
                        {r.classes.length > SHOWN && (
                          <span
                            title={r.classes.slice(SHOWN).join(", ")}
                            className="inline-flex h-[22px] shrink-0 items-center rounded-full border px-2 text-[12px] font-medium text-muted-foreground"
                          >
                            +{r.classes.length - SHOWN}
                          </span>
                        )}
                      </>
                    )}
                  </div>
                  <span className="order-3 shrink-0 whitespace-nowrap text-[13px] text-muted-foreground sm:order-none sm:w-[84px] sm:text-right">
                    {plural(r.session_count, "session", "sessions")}
                  </span>
                  <ChevronRight className="hidden h-[18px] w-[18px] shrink-0 text-muted-foreground/70 sm:block" />
                </Link>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

function RowsSkeleton() {
  return (
    <div className="overflow-hidden rounded-lg border" aria-hidden>
      {["w-[180px]", "w-[140px]"].map((w, i) => (
        <div key={i} className={cn("flex items-center gap-5 py-4 pl-5 pr-4", i > 0 && "border-t")}>
          <div className="flex-1">
            <Skeleton className={cn("h-3.5", w)} />
            <Skeleton className="mt-2 h-3 w-[240px] max-w-full" />
          </div>
          <Skeleton className="h-[22px] w-[84px] rounded-full" />
        </div>
      ))}
    </div>
  );
}
