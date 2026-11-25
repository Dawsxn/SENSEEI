/** One reading inside one class: who is flagged, how far each student got, and
 *  how the reading went, a tab each for the last two.
 *
 * The pairing is the point. A reading's numbers only mean something for the
 * class that read it, and progress here is progress on this reading. That is
 * also why this page lives under the class; View reading opens the reading
 * itself, under Readings.
 *
 * A student who ran out of tries is flagged, and the flagged ones are listed in
 * a red box above everything else. `student-tutoring-loop.md` calls that flag
 * half the purpose of the fallback: ending the session without telling the
 * instructor does half the job. A student's row opens all their sessions on the
 * reading, not just the latest, so an earlier flag is never out of reach.
 */

import { useState } from "react";
import { ChevronRight, Flag } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { AppTopBar } from "../../components/AppTopBar";
import { Loading, Skeleton } from "../../components/ui/Skeleton";
import { Button } from "../../components/ui/button";
import { formatShortDate } from "../../lib/format";
import { cn } from "../../lib/utils";
import { useTrialMode } from "../auth/useAuth";
import { Breadcrumb, Notice } from "../readings/parts";
import { Initials, ProgressChip, StepBar } from "./parts";
import { StatisticsSection } from "./StatisticsSection";
import type { RosterStudent } from "./types";
import { useClassReading } from "./useClasses";

type Tab = "students" | "statistics";

export function ClassReadingPage() {
  const { classId, readingId } = useParams<{ classId: string; readingId: string }>();
  const { data, isLoading, isError } = useClassReading(classId, readingId);
  const [tab, setTab] = useState<Tab>("students");
  const navigate = useNavigate();
  const trial = useTrialMode();
  const people = trial ? "Participants" : "Students";
  const flagged = data?.students.filter((s) => s.status === "stopped_early") ?? [];
  const sessionsOf = (s: RosterStudent) => `/classes/${classId}/readings/${readingId}/students/${s.id}`;

  return (
    <div className="flex h-full flex-col">
      <AppTopBar />
      <main className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex max-w-[1148px] flex-col gap-4 px-4 py-4 sm:gap-5 sm:px-8 sm:py-6 lg:px-6">
          {isLoading && <PageSkeleton />}
          {isError && <Notice>This reading isn't in this class.</Notice>}

          {data && (
            <>
              <div className="flex flex-col gap-2.5">
                <Breadcrumb
                  trail={[
                    { label: "Classes", to: "/classes" },
                    { label: data.class_label, to: `/classes/${classId}` },
                  ]}
                  current={data.title}
                />
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
                  <div className="min-w-0">
                    <h1 className="text-[22px] font-semibold tracking-[-0.02em] sm:text-[24px]">{data.title}</h1>
                    {data.description && (
                      <p className="mt-1 text-[14px] text-muted-foreground">{data.description}</p>
                    )}
                  </div>
                  <Button
                    variant="secondary"
                    size="sm"
                    className="h-10 w-full sm:h-8 sm:w-auto"
                    onClick={() => navigate(`/library/${readingId}`)}
                  >
                    View reading
                  </Button>
                </div>
              </div>

              {flagged.length > 0 && (
                <section aria-label="Flagged" className="overflow-hidden rounded-lg border border-fail-border bg-fail">
                  <div className="flex items-center gap-2 px-4 py-3 text-[14px] font-semibold text-fail-foreground">
                    <Flag className="h-3.5 w-3.5" aria-hidden />
                    Flagged
                    <span className="font-normal">{flagged.length}</span>
                  </div>
                  {flagged.map((s) => (
                    <Link
                      key={s.id}
                      to={sessionsOf(s)}
                      className="flex items-center gap-3 border-t border-fail-border bg-background px-4 py-3 hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      {!trial && <Initials name={s.name} />}
                      <span className={cn("min-w-0 flex-1 truncate", trial ? "font-mono text-[13px] tracking-wider" : "text-[14px] font-medium")}>
                        {s.name}
                      </span>
                      {s.last_session_at && (
                        <span className="whitespace-nowrap text-[13px] text-muted-foreground">
                          {formatShortDate(s.last_session_at)}
                        </span>
                      )}
                      <ChevronRight className="h-[18px] w-[18px] shrink-0 text-muted-foreground/70" />
                    </Link>
                  ))}
                </section>
              )}

              <div role="tablist" className="flex gap-0.5 self-stretch rounded-lg bg-muted p-[3px] sm:self-start">
                {(
                  [
                    { key: "students", label: people, count: data.students.length },
                    { key: "statistics", label: "Statistics" },
                  ] as { key: Tab; label: string; count?: number }[]
                ).map((t) => (
                  <button
                    key={t.key}
                    type="button"
                    role="tab"
                    aria-selected={tab === t.key}
                    onClick={() => setTab(t.key)}
                    className={cn(
                      "flex-1 rounded-md py-[5px] text-[13px] font-medium sm:w-[112px] sm:flex-none",
                      tab === t.key
                        ? "bg-background text-foreground shadow-raised"
                        : "text-muted-foreground hover:text-foreground",
                    )}
                  >
                    {t.label}
                    {t.count !== undefined && <span className="ml-1 text-muted-foreground/70">{t.count}</span>}
                  </button>
                ))}
              </div>

              {tab === "students" &&
                (data.students.length === 0 ? (
                  <Notice>
                    {trial ? "No participants yet." : "No students have joined this class yet."}
                  </Notice>
                ) : (
                  <div className="overflow-hidden rounded-lg border">
                    {data.students.map((s, i) => (
                      <StudentRow key={s.id} student={s} trial={trial} to={s.session_id ? sessionsOf(s) : null} first={i === 0} />
                    ))}
                  </div>
                ))}

              {tab === "statistics" && <StatisticsSection statistics={data.statistics} />}
            </>
          )}
        </div>
      </main>
    </div>
  );
}

/** A student and how far they got. Opens their sessions on the reading, once
 *  there is one to open. On a phone the progress takes a line of its own. */
function StudentRow({
  student,
  trial,
  to,
  first,
}: {
  student: RosterStudent;
  /** Trial mode: the student is a participant ID, with no name or email. */
  trial: boolean;
  to: string | null;
  first: boolean;
}) {
  const stopped = student.status === "stopped_early" || student.status === "timed_out";
  const body = (
    <>
      {!trial && <Initials name={student.name} />}
      <span className="min-w-0 flex-1">
        <span className={cn("block truncate", trial ? "font-mono text-[13px] tracking-wider" : "text-[14px] font-medium")}>
          {student.name}
        </span>
        {!trial && (
          <span className="hidden truncate text-[13px] text-muted-foreground sm:block">{student.email}</span>
        )}
      </span>
      <StepBar passed={student.steps_passed} stopped={stopped} className="order-last w-full basis-full pl-11 sm:order-none sm:w-[132px] sm:basis-auto sm:pl-0" />
      <ProgressChip status={student.status} />
      <span className="hidden w-[52px] whitespace-nowrap text-right text-[13px] text-muted-foreground sm:block">
        {student.last_session_at ? formatShortDate(student.last_session_at) : ""}
      </span>
      <ChevronRight className={cn("h-[18px] w-[18px] shrink-0 text-muted-foreground/70", !to && "invisible")} />
    </>
  );
  const cls = cn(
    "flex flex-wrap items-center gap-x-3 gap-y-2.5 py-3 pl-4 pr-3 sm:flex-nowrap sm:gap-4 sm:pl-5 sm:pr-4",
    !first && "border-t",
  );
  return to ? (
    <Link to={to} className={cn(cls, "hover:bg-muted/50 focus-visible:bg-muted/50 focus-visible:outline-none")}>
      {body}
    </Link>
  ) : (
    <div className={cls}>{body}</div>
  );
}

function PageSkeleton() {
  return (
    <Loading label="Loading the reading" className="flex flex-col gap-4 sm:gap-5">
      <Skeleton className="h-3.5 w-52" />
      <div className="flex flex-col gap-1.5">
        <Skeleton className="h-6 w-40" />
        <Skeleton className="h-4 w-64 max-w-full" />
      </div>
      <Skeleton className="h-9 w-full rounded-lg sm:w-[232px]" />
      <div className="overflow-hidden rounded-lg border">
        {[0, 1, 2].map((i) => (
          <div key={i} className={cn("flex items-center gap-3 px-5 py-4", i > 0 && "border-t")}>
            <Skeleton className="h-8 w-8 rounded-full" />
            <Skeleton className="h-4 w-40" />
          </div>
        ))}
      </div>
    </Loading>
  );
}
