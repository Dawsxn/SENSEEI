/** One reading in one of the student's classes: what it covers, the student's
 *  past sessions on it, and Start.
 *
 * Start always reads the same: the past sessions beside it already show
 * whether this is a first attempt. A student who has never been through the
 * SEE-I walkthrough goes through it first, on the way to the reading. Opening a session goes to its review, whose
 * breadcrumb leads back here.
 */

import { ChevronRight } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { AppTopBar } from "../../components/AppTopBar";
import { useMe } from "../auth/useAuth";
import { Button } from "../../components/ui/button";
import { formatDate } from "../../lib/format";
import { cn } from "../../lib/utils";
import { Breadcrumb, Notice, SessionStatusChip } from "./parts";
import { ReadingSkeleton, SessionRowsSkeleton } from "./skeletons";
import { useMyClass, useReading, useReadingSessions } from "./useReadings";

export function StudentReadingPage() {
  const { classId, readingId } = useParams();
  const navigate = useNavigate();
  const klass = useMyClass(classId);
  const reading = useReading(readingId);
  const { data: sessions } = useReadingSessions(readingId);
  const { data: me } = useMe();

  // The reading must belong to this class, or the breadcrumb would lie.
  const notInClass = klass.data && !klass.data.readings.some((r) => r.id === readingId);
  const failed = klass.isError || reading.isError;
  const r = reading.data;

  return (
    <div className="flex h-full flex-col">
      <AppTopBar />
      <main className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex max-w-[1148px] flex-col gap-6 px-4 pb-8 pt-4 sm:gap-7 sm:px-8 sm:pb-12 sm:pt-6 lg:px-6">
          {failed && <Notice>Couldn't load this reading. Try again.</Notice>}
          {!failed && notInClass && <Notice>This reading isn't in this class.</Notice>}
          {!failed && !notInClass && (!klass.data || !r) && <ReadingSkeleton />}

          {!failed && !notInClass && klass.data && r && (
            <>
              <div className="flex flex-col gap-2.5">
                <Breadcrumb
                  trail={[
                    { label: "Classes", to: "/" },
                    { label: klass.data.label, to: `/classes/${klass.data.id}` },
                  ]}
                  current={r.title}
                />
                <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between sm:gap-6">
                  <div className="min-w-0">
                    <h1 className="text-[22px] font-semibold tracking-[-0.02em] sm:text-[24px]">
                      {r.title}
                    </h1>
                    {r.description && (
                      <p className="mt-1 text-[14px] text-muted-foreground">{r.description}</p>
                    )}
                  </div>
                  <Button
                    className="h-10 w-full px-5 sm:h-9 sm:w-auto"
                    onClick={() =>
                      navigate(
                        me && !me.seen_intro
                          ? `/how-it-works?next=${encodeURIComponent(`/read/${r.id}`)}`
                          : `/read/${r.id}`,
                      )
                    }
                  >
                    Start
                  </Button>
                </div>
              </div>

              <div className="grid items-start gap-7 lg:grid-cols-[1fr_420px] lg:gap-8">
                {r.core_components.length > 0 && (
                  <section className="flex flex-col gap-2.5">
                    <SectionLabel>
                      Core {r.core_components.length === 1 ? "component" : "components"}
                    </SectionLabel>
                    <ol className="rounded-lg border bg-card px-4 py-0.5 sm:px-5 sm:py-1">
                      {r.core_components.map((c, i) => (
                        <li
                          key={i}
                          className={cn(
                            "flex gap-2.5 py-3 text-[14px] leading-[1.5] text-foreground/80 sm:gap-3",
                            i > 0 && "border-t border-muted",
                          )}
                        >
                          <span className="w-5 shrink-0 font-medium text-muted-foreground/70">
                            {i + 1}
                          </span>
                          <span>{c}</span>
                        </li>
                      ))}
                    </ol>
                  </section>
                )}

                <section className="flex flex-col gap-2.5">
                  <SectionLabel>Past sessions</SectionLabel>
                  {!sessions && <SessionRowsSkeleton />}
                  <div className={cn("overflow-hidden rounded-lg border bg-card", !sessions && "hidden")}>
                    {sessions && sessions.length === 0 && (
                      <div className="px-4 py-7 text-center text-[14px] text-muted-foreground">
                        No attempts yet
                      </div>
                    )}
                    {sessions?.map((s, i) => (
                      <Link
                        key={s.id}
                        to={`/classes/${klass.data.id}/readings/${r.id}/sessions/${s.id}`}
                        className={cn(
                          "flex items-center gap-2.5 px-3.5 py-3 hover:bg-muted/50 focus-visible:bg-muted/50 focus-visible:outline-none sm:gap-3 sm:px-4",
                          i > 0 && "border-t",
                        )}
                      >
                        <span className="shrink-0 text-[14px] font-medium sm:w-[76px]">
                          Attempt {s.index}
                        </span>
                        <SessionStatusChip status={s.status} />
                        <span className="ml-auto whitespace-nowrap text-[13px] text-muted-foreground">
                          {formatDate(s.started_at)}
                        </span>
                        <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground/70" />
                      </Link>
                    ))}
                  </div>
                </section>
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-[12px] font-medium uppercase tracking-[0.04em] text-muted-foreground">
      {children}
    </h2>
  );
}
