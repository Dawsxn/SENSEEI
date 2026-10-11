/** One reading inside one class: how it went, and how far each student got.
 *
 * The pairing is the point. A reading's numbers only mean something for the
 * class that read it, and progress here is progress on this reading, not on the
 * course. That is also why this page lives under the class rather than under the
 * reading: the Readings tab shows a reading itself, with no statistics at all.
 *
 * A student who ran out of attempts carries a flag. `student-tutoring-loop.md`
 * calls that flag half the purpose of the fallback: ending the session without
 * telling the instructor does half the job.
 */

import { ChevronLeft, ChevronRight, Flag } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";

import { AppTopBar } from "../../components/AppTopBar";
import { formatShortDate } from "../../lib/format";
import { StatisticsSection } from "./StatisticsSection";
import type { ReadingProgress, RosterStudent } from "./types";
import { useClassReading } from "./useClasses";

const STATUS: Record<ReadingProgress, string> = {
  completed: "Completed",
  stopped_early: "Stopped early",
  not_started: "Not started",
};

export function ClassReadingPage() {
  const { classId, readingId } = useParams<{ classId: string; readingId: string }>();
  const { data, isLoading, isError } = useClassReading(classId, readingId);
  const navigate = useNavigate();

  return (
    <div className="flex h-full flex-col">
      <AppTopBar />
      <main className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[1100px] px-4 py-5 sm:px-6 sm:py-6">
          <button
            onClick={() => navigate(`/classes/${classId}`)}
            className="mb-4 flex items-center gap-1.5 text-[13px] text-muted-foreground hover:text-foreground"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
            {data?.class_label ?? "Class"}
          </button>

          {isLoading && <Notice>Loading reading…</Notice>}
          {isError && <Notice>This reading isn&rsquo;t in this class.</Notice>}

          {data && (
            <div className="flex flex-col gap-5">
              <div className="flex flex-col gap-1">
                <h1 className="text-[22px] font-semibold tracking-[-0.02em] sm:text-[24px]">
                  {data.title}
                </h1>
                {data.description && (
                  <p className="text-[14px] text-muted-foreground">{data.description}</p>
                )}
              </div>

              <StatisticsSection statistics={data.statistics} scope="For this reading only." />

              <section className="overflow-hidden rounded-lg border">
                <div className="hidden h-10 grid-cols-[1fr_160px_200px_120px_24px] items-center gap-4 border-b px-4 text-[12px] font-medium text-muted-foreground sm:grid">
                  <span>Student</span>
                  <span>Progress</span>
                  <span>Status</span>
                  <span>Last session</span>
                  <span />
                </div>

                {data.students.length === 0 ? (
                  <p className="px-6 py-12 text-center text-[14px] font-medium">
                    No students yet
                  </p>
                ) : (
                  data.students.map((s) => (
                    <StudentRow
                      key={s.id}
                      student={s}
                      onOpen={() => s.session_id && navigate(`/review/${s.session_id}`)}
                    />
                  ))
                )}
              </section>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

function StudentRow({ student, onOpen }: { student: RosterStudent; onOpen: () => void }) {
  const stopped = student.status === "stopped_early";
  const started = student.status !== "not_started";

  return (
    <button
      onClick={onOpen}
      disabled={!started}
      className="grid w-full grid-cols-[1fr_24px] items-center gap-4 border-b px-4 py-2.5 text-left last:border-b-0 enabled:hover:bg-muted/40 sm:grid-cols-[1fr_160px_200px_120px_24px]"
    >
      <span className="flex min-w-0 items-center gap-3">
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-muted text-[11px] font-medium text-muted-foreground">
          {initials(student.name)}
        </span>
        <span className="min-w-0">
          <span className="flex items-center gap-1.5 text-[14px] font-medium">
            <span className="truncate">{student.name}</span>
            {stopped && <Flag className="h-3 w-3 shrink-0 text-fail-foreground" />}
          </span>
          <span className="block truncate text-[12px] text-muted-foreground">
            {student.email}
          </span>
          {/* On narrow screens the columns collapse into this line. */}
          <span className="mt-1 flex items-center gap-2 sm:hidden">
            <Progress passed={student.steps_passed} stopped={stopped} />
            <span
              className={`text-[12px] ${stopped ? "text-fail-foreground" : "text-muted-foreground"}`}
            >
              {stopped && student.stopped_on
                ? `Stopped on ${student.stopped_on}`
                : STATUS[student.status]}
              {student.last_session_at && `, ${formatShortDate(student.last_session_at)}`}
            </span>
          </span>
        </span>
      </span>

      <span className="hidden sm:block">
        <Progress passed={student.steps_passed} stopped={stopped} />
      </span>
      <span className="hidden flex-col gap-0.5 sm:flex">
        <span
          className={`text-[13px] ${
            stopped ? "text-fail-foreground" : started ? "" : "text-muted-foreground/70"
          }`}
        >
          {STATUS[student.status]}
        </span>
        {stopped && student.stopped_on && (
          <span className="text-[12px] text-muted-foreground">
            Stopped on {student.stopped_on}
          </span>
        )}
      </span>
      <span className="hidden whitespace-nowrap text-[13px] text-muted-foreground sm:block">
        {student.last_session_at ? formatShortDate(student.last_session_at) : ""}
      </span>
      <ChevronRight
        className={`h-3.5 w-3.5 text-muted-foreground/70 ${started ? "" : "invisible"}`}
      />
    </button>
  );
}

/** One mark per SEE-I step, filled for each step passed. A stopped session's
 *  marks are pale red, so a row that needs attention reads as one at a glance. */
function Progress({ passed, stopped }: { passed: number; stopped: boolean }) {
  return (
    <span className="flex gap-[3px]">
      {[0, 1, 2, 3].map((i) => (
        <span
          key={i}
          className={`h-1 w-[22px] rounded-sm ${
            i < passed ? (stopped ? "bg-fail-border" : "bg-primary") : "bg-border"
          }`}
        />
      ))}
    </span>
  );
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]!.toUpperCase())
    .join("");
}

function Notice({ children }: { children: React.ReactNode }) {
  return <p className="py-10 text-center text-[14px] text-muted-foreground">{children}</p>;
}
