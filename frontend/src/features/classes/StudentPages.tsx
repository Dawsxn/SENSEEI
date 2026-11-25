/** The instructor's two views of one student.
 *
 * In a class (`/classes/:class/students/:student`): where they are on each of
 * the class's readings, flagged or not. On a reading
 * (`/classes/:class/readings/:reading/students/:student`): every session they
 * finished on it, newest first, each opening its review. The two meet: a reading
 * on the first opens the second, and so does a student on a reading's page.
 *
 * A session that ran out of tries stays Flagged in the second list after a
 * later one passes; only the flag on the reading, which follows the latest
 * session, clears.
 */

import { useState } from "react";
import { ChevronRight, MoreHorizontal } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";

import { AppTopBar } from "../../components/AppTopBar";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { Menu } from "../../components/ui/Menu";
import { Loading, Skeleton } from "../../components/ui/Skeleton";
import { formatDate, formatShortDate } from "../../lib/format";
import { cn } from "../../lib/utils";
import { removeStudent } from "../../lib/api";
import { Breadcrumb, Notice, SessionStatusChip } from "../readings/parts";
import { ProgressChip, StepBar } from "./parts";
import { useClassStudent, useStudentSessions } from "./useClasses";

function Page({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-full flex-col">
      <AppTopBar />
      <main className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex max-w-[1148px] flex-col gap-4 px-4 py-4 sm:gap-5 sm:px-8 sm:py-6 lg:px-6">
          {children}
        </div>
      </main>
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[12px] font-medium uppercase tracking-[0.06em] text-muted-foreground">{children}</div>
  );
}

function ListSkeleton({ label }: { label: string }) {
  return (
    <Loading label={label} className="flex flex-col gap-4 sm:gap-5">
      <Skeleton className="h-3.5 w-52" />
      <div className="flex flex-col gap-1.5">
        <Skeleton className="h-6 w-40" />
        <Skeleton className="h-4 w-56 max-w-full" />
      </div>
      <div className="overflow-hidden rounded-lg border bg-card">
        {[0, 1, 2].map((i) => (
          <div key={i} className={cn("px-5 py-4", i > 0 && "border-t")}>
            <Skeleton className="h-4 w-44" />
          </div>
        ))}
      </div>
    </Loading>
  );
}

/** One student in one class. */
export function ClassStudentPage() {
  const { classId, studentId } = useParams<{ classId: string; studentId: string }>();
  const { data, isLoading, isError } = useClassStudent(classId, studentId);
  const [removing, setRemoving] = useState(false);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  async function remove() {
    await removeStudent(classId!, studentId!);
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["class", classId] }),
      queryClient.invalidateQueries({ queryKey: ["classes"] }),
    ]);
    navigate(`/classes/${classId}`);
  }

  return (
    <Page>
      {isLoading && <ListSkeleton label="Loading the student" />}
      {isError && <Notice>This student isn't in this class.</Notice>}
      {data && (
        <>
          <div className="flex flex-col gap-2.5">
            <Breadcrumb
              trail={[
                { label: "Classes", to: "/classes" },
                { label: data.class_label, to: `/classes/${classId}` },
              ]}
              current={data.name}
            />
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <h1 className="truncate text-[22px] font-semibold tracking-[-0.02em] sm:text-[24px]">{data.name}</h1>
                <p className="mt-1 text-[14px] text-muted-foreground">
                  {data.email} · Joined {formatShortDate(data.enrolled_at)}
                </p>
              </div>
              <Menu
                label={`Options for ${data.name}`}
                trigger={<MoreHorizontal className="h-4 w-4" />}
                className="flex h-9 w-9 items-center justify-center rounded-md border bg-background text-foreground/80 hover:bg-muted"
                items={[{ label: "Remove from class", danger: true, onSelect: () => setRemoving(true) }]}
              />
            </div>
          </div>

          <SectionLabel>Readings</SectionLabel>
          {data.readings.length === 0 ? (
            <Notice>No readings available</Notice>
          ) : (
            <div className="overflow-hidden rounded-lg border bg-card">
              {data.readings.map((r, i) => {
                const stopped = r.status === "stopped_early" || r.status === "timed_out";
                const to = r.session_id ? `/classes/${classId}/readings/${r.id}/students/${studentId}` : null;
                const body = (
                  <>
                    <span className="min-w-0 flex-1">
                      <span className="block text-[14px] font-medium">{r.title}</span>
                      {r.description && (
                        <span className="mt-0.5 block text-[13px] text-muted-foreground">{r.description}</span>
                      )}
                    </span>
                    <StepBar
                      passed={r.steps_passed}
                      stopped={stopped}
                      className="order-last w-full basis-full sm:order-none sm:w-[132px] sm:basis-auto"
                    />
                    <ProgressChip status={r.status} />
                    <span className="hidden w-[52px] whitespace-nowrap text-right text-[13px] text-muted-foreground sm:block">
                      {r.last_session_at ? formatShortDate(r.last_session_at) : ""}
                    </span>
                    <ChevronRight className={cn("h-[18px] w-[18px] shrink-0 text-muted-foreground/70", !to && "invisible")} />
                  </>
                );
                const cls = cn(
                  "flex flex-wrap items-center gap-x-3 gap-y-2.5 py-3.5 pl-4 pr-3 sm:flex-nowrap sm:gap-4 sm:pl-5 sm:pr-4",
                  i > 0 && "border-t",
                );
                return to ? (
                  <Link key={r.id} to={to} className={cn(cls, "hover:bg-muted/50 focus-visible:bg-muted/50 focus-visible:outline-none")}>
                    {body}
                  </Link>
                ) : (
                  <div key={r.id} className={cls}>
                    {body}
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}

      {data && removing && (
        <ConfirmDialog
          title={`Remove ${data.name}?`}
          confirmLabel="Remove"
          cancelLabel="Cancel"
          tone="danger"
          onConfirm={remove}
          onCancel={() => setRemoving(false)}
        >
          They will no longer see this class&rsquo;s readings or their sessions in it.
        </ConfirmDialog>
      )}
    </Page>
  );
}

/** One student's sessions on one reading. */
export function StudentSessionsPage() {
  const { classId, readingId, studentId } = useParams<{
    classId: string;
    readingId: string;
    studentId: string;
  }>();
  const { data, isLoading, isError } = useStudentSessions(classId, readingId, studentId);

  return (
    <Page>
      {isLoading && <ListSkeleton label="Loading the sessions" />}
      {isError && <Notice>Couldn't load this student's sessions.</Notice>}
      {data && (
        <>
          <div className="flex flex-col gap-2.5">
            <Breadcrumb
              trail={[
                { label: "Classes", to: "/classes" },
                { label: data.class_label, to: `/classes/${classId}` },
                { label: data.reading_title, to: `/classes/${classId}/readings/${readingId}` },
              ]}
              current={data.name}
            />
            <div className="min-w-0">
              <h1 className="truncate text-[22px] font-semibold tracking-[-0.02em] sm:text-[24px]">{data.name}</h1>
              <p className="mt-1 text-[14px] text-muted-foreground">{data.email}</p>
            </div>
          </div>

          <SectionLabel>Sessions</SectionLabel>
          {data.sessions.length === 0 ? (
            <Notice>No sessions available</Notice>
          ) : (
            <div className="overflow-hidden rounded-lg border bg-card">
              {data.sessions.map((s, i) => (
                <Link
                  key={s.id}
                  to={`/classes/${classId}/readings/${readingId}/sessions/${s.id}`}
                  className={cn(
                    "flex items-center gap-3 py-3.5 pl-4 pr-3 hover:bg-muted/50 focus-visible:bg-muted/50 focus-visible:outline-none sm:gap-4 sm:pl-5 sm:pr-4",
                    i > 0 && "border-t",
                  )}
                >
                  <span className="w-[84px] shrink-0 text-[14px] font-medium">Attempt {s.index}</span>
                  <SessionStatusChip status={s.status} instructor />
                  <span className="flex-1" />
                  <span className="hidden whitespace-nowrap text-[13px] text-muted-foreground sm:block">
                    {formatDate(s.started_at)}
                  </span>
                  <ChevronRight className="h-[18px] w-[18px] shrink-0 text-muted-foreground/70" />
                </Link>
              ))}
            </div>
          )}
        </>
      )}
    </Page>
  );
}
