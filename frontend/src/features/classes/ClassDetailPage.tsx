/** One class: its readings, its students, and how it is doing, a tab each.
 *
 * Laid out like a student's class page: the breadcrumb, the name with the
 * section under it, and the same segmented control, here switching between
 * three things rather than filtering one. Readings come first, since a reading
 * is what an instructor opens most; the join code sits in the header, ready to
 * copy without scrolling, since it is what they share in front of a class.
 *
 * A flag shows where it needs attention: on a reading, how many of its
 * students are flagged; on a student, that they are flagged on some reading,
 * which their own page names.
 *
 * What changes the class itself (editing it, a new join code, deleting it) is
 * in the ⋯ menu, and removing a student is in that student's own ⋯, so nothing
 * that takes something away sits in plain view to be pressed by mistake.
 * Removing a student and deleting the class both take access away rather than
 * data: the sessions stay in the database for the study, but neither the student
 * nor this page can reach them afterwards, and the dialogs say only what the
 * person clicking will notice.
 *
 * On the trial instance a class is one of the study's groups. Its students are
 * participant IDs with no name or email, it has no join code worth showing, and
 * IDs are voided from their batch rather than removed here.
 */

import { useState } from "react";
import { ChevronRight, Copy, MoreHorizontal } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";

import { AppTopBar } from "../../components/AppTopBar";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { Menu } from "../../components/ui/Menu";
import { Loading, Skeleton } from "../../components/ui/Skeleton";
import { Button } from "../../components/ui/button";
import { formatShortDate } from "../../lib/format";
import { cn } from "../../lib/utils";
import { deleteClass, removeStudent, replaceJoinCode, updateClass } from "../../lib/api";
import { useTrialMode } from "../auth/useAuth";
import { Breadcrumb, Notice } from "../readings/parts";
import { ClassFormDialog } from "./ClassFormDialog";
import { FlagPill, Initials } from "./parts";
import { ReadingPicker } from "./ReadingPicker";
import { StatisticsSection } from "./StatisticsSection";
import { MODE_LABEL, type ClassFields, type ClassStudent } from "./types";
import { useClass, useClassStatistics } from "./useClasses";

type Tab = "readings" | "students" | "statistics";

type Dialog =
  | { kind: "edit" }
  | { kind: "code" }
  | { kind: "delete" }
  | { kind: "remove"; student: ClassStudent }
  | { kind: "pick" }
  | null;

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

export function ClassDetailPage() {
  const { classId } = useParams<{ classId: string }>();
  const { data: klass, isLoading, isError } = useClass(classId);
  const { data: dashboard } = useClassStatistics(classId);
  const [tab, setTab] = useState<Tab>("readings");
  const [dialog, setDialog] = useState<Dialog>(null);
  const [copied, setCopied] = useState(false);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const trial = useTrialMode();

  const refresh = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ["class", classId] }),
      queryClient.invalidateQueries({ queryKey: ["class-statistics", classId] }),
      queryClient.invalidateQueries({ queryKey: ["classes"] }),
      queryClient.invalidateQueries({ queryKey: ["library"] }),
    ]);
  const close = () => setDialog(null);

  async function edit(fields: ClassFields) {
    await updateClass(classId!, fields);
    await refresh();
    close();
  }

  async function newCode() {
    await replaceJoinCode(classId!);
    await refresh();
    close();
  }

  async function remove(student: ClassStudent) {
    await removeStudent(classId!, student.id);
    await refresh();
    close();
  }

  async function destroy() {
    await deleteClass(classId!);
    await queryClient.invalidateQueries({ queryKey: ["classes"] });
    navigate("/classes");
  }

  async function copy(code: string) {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  const people = trial ? "Participants" : "Students";
  const tabs: { key: Tab; label: string; count?: number }[] = klass
    ? [
        { key: "readings", label: "Readings", count: klass.readings.length },
        { key: "students", label: people, count: klass.students.length },
        { key: "statistics", label: "Statistics" },
      ]
    : [];

  return (
    <div className="flex h-full flex-col">
      <AppTopBar />
      <main className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex max-w-[1148px] flex-col gap-4 px-4 py-4 sm:gap-5 sm:px-8 sm:py-6 lg:px-6">
          {isLoading && <ClassSkeleton />}
          {isError && <Notice>This class doesn't exist, or isn't yours.</Notice>}

          {klass && (
            <>
              <div className="flex flex-col gap-2.5">
                <Breadcrumb trail={[{ label: "Classes", to: "/classes" }]} current={klass.label} />
                <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-3">
                  <div className="min-w-0">
                    <h1 className="truncate text-[22px] font-semibold tracking-[-0.02em] sm:text-[24px]">
                      {klass.name}
                    </h1>
                    <div className="mt-0.5 truncate text-[14px] font-medium text-foreground/70">
                      {trial ? `${klass.section} · ${MODE_LABEL[klass.mode]}` : klass.section}
                    </div>
                  </div>
                  <div className="flex w-full items-center gap-2 sm:w-auto">
                    {!trial && (
                      <div className="flex h-9 flex-1 items-center gap-2.5 rounded-lg border bg-card pl-3 pr-1.5 sm:flex-none">
                        <span className="text-[12px] text-muted-foreground">Join code</span>
                        <span className="flex-1 font-mono text-[14px] font-medium tracking-[0.06em]">
                          {klass.join_code}
                        </span>
                        <Button
                          variant="secondary"
                          size="sm"
                          className="h-[26px] px-2 text-[12px]"
                          onClick={() => copy(klass.join_code)}
                        >
                          <Copy className="h-3 w-3 text-muted-foreground" />
                          {copied ? "Copied" : "Copy"}
                        </Button>
                      </div>
                    )}
                    <Menu
                      label="Class options"
                      trigger={<MoreHorizontal className="h-4 w-4" />}
                      className="flex h-9 w-9 items-center justify-center rounded-md border bg-background text-foreground/80 hover:bg-muted"
                      items={[
                        { label: "Edit class", onSelect: () => setDialog({ kind: "edit" }) },
                        ...(trial
                          ? []
                          : [{ label: "New join code", onSelect: () => setDialog({ kind: "code" as const }) }]),
                        { label: "Delete class", danger: true, onSelect: () => setDialog({ kind: "delete" }) },
                      ]}
                    />
                  </div>
                </div>
              </div>

              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div role="tablist" className="flex gap-0.5 rounded-lg bg-muted p-[3px] sm:self-start">
                  {tabs.map((t) => (
                    <button
                      key={t.key}
                      type="button"
                      role="tab"
                      aria-selected={tab === t.key}
                      onClick={() => setTab(t.key)}
                      className={cn(
                        "flex-1 rounded-md py-[5px] text-[13px] font-medium sm:w-[112px] sm:flex-none",
                        tab === t.key
                          ? "bg-card text-foreground shadow-raised"
                          : "text-muted-foreground hover:text-foreground",
                      )}
                    >
                      {t.label}
                      {t.count !== undefined && (
                        <span className="ml-1 text-muted-foreground/70">{t.count}</span>
                      )}
                    </button>
                  ))}
                </div>
                {tab === "readings" && (
                  <Menu
                    trigger="+ Add reading"
                    className="inline-flex h-9 w-full items-center justify-center rounded-md border bg-background px-3 text-[13px] font-medium hover:bg-muted sm:h-8 sm:w-auto"
                    items={[
                      {
                        label: "Upload a new reading",
                        onSelect: () => navigate(`/library/new?class=${classId}`),
                      },
                      { label: "Choose from your readings", onSelect: () => setDialog({ kind: "pick" }) },
                    ]}
                  />
                )}
              </div>

              {tab === "readings" &&
                (klass.readings.length === 0 ? (
                  <Notice>No readings available</Notice>
                ) : (
                  <div className="overflow-hidden rounded-lg border bg-card">
                    {klass.readings.map((r, i) => {
                      const counts = dashboard?.readings.find((d) => d.id === r.id);
                      const sessions = counts?.session_count;
                      return (
                        <Link
                          key={r.id}
                          to={`/classes/${classId}/readings/${r.id}`}
                          className={cn(
                            "flex items-center gap-3 py-3.5 pl-4 pr-3 hover:bg-muted/50 focus-visible:bg-muted/50 focus-visible:outline-none sm:gap-5 sm:pl-5 sm:pr-4",
                            i > 0 && "border-t",
                          )}
                        >
                          <div className="min-w-0 flex-1">
                            <div className="text-[14px] font-medium">{r.title}</div>
                            {r.description && (
                              <div className="mt-0.5 text-[13px] text-muted-foreground">{r.description}</div>
                            )}
                          </div>
                          {!!counts?.flagged_count && <FlagPill>{counts.flagged_count} flagged</FlagPill>}
                          {sessions !== undefined && (
                            <span className="shrink-0 whitespace-nowrap text-[13px] text-muted-foreground">
                              {plural(sessions, "session", "sessions")}
                            </span>
                          )}
                          <ChevronRight className="h-[18px] w-[18px] shrink-0 text-muted-foreground/70" />
                        </Link>
                      );
                    })}
                  </div>
                ))}

              {tab === "students" &&
                (klass.students.length === 0 ? (
                  <Notice>
                    {trial
                      ? "No participants yet. Participants appear here once you make a batch."
                      : "No students have joined this class yet."}
                  </Notice>
                ) : (
                  <div className="overflow-hidden rounded-lg border bg-card">
                    {klass.students.map((s, i) =>
                      trial ? (
                        <div
                          key={s.id}
                          className={cn("flex items-center gap-3 px-4 py-3 sm:px-5", i > 0 && "border-t")}
                        >
                          <span className="flex-1 truncate font-mono text-[13px] tracking-wider">
                            {s.participant_code ?? s.name}
                          </span>
                          <span className="whitespace-nowrap text-[13px] text-muted-foreground">
                            {s.signed_in_at ? `Signed in ${formatShortDate(s.signed_in_at)}` : "Not signed in"}
                          </span>
                        </div>
                      ) : (
                        <div
                          key={s.id}
                          className={cn("flex items-center gap-1 pr-2 hover:bg-muted/50 sm:pr-3", i > 0 && "border-t")}
                        >
                          {/* The row opens the student; the ⋯ beside it is apart from the link. */}
                          <Link
                            to={`/classes/${classId}/students/${s.id}`}
                            className="flex min-w-0 flex-1 items-center gap-3 py-3 pl-4 focus-visible:outline-none sm:gap-4 sm:pl-5"
                          >
                            <Initials name={s.name} />
                            <span className="min-w-0 flex-1">
                              <span className="block truncate text-[14px] font-medium">{s.name}</span>
                              <span className="block truncate text-[13px] text-muted-foreground">{s.email}</span>
                            </span>
                            {dashboard?.flagged_student_ids?.includes(s.id) && <FlagPill>Flagged</FlagPill>}
                            <span className="hidden whitespace-nowrap text-[13px] text-muted-foreground sm:block">
                              Joined {formatShortDate(s.enrolled_at)}
                            </span>
                          </Link>
                          <Menu
                            label={`Options for ${s.name}`}
                            trigger={<MoreHorizontal className="h-4 w-4" />}
                            className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
                            items={[
                              {
                                label: "Remove from class",
                                danger: true,
                                onSelect: () => setDialog({ kind: "remove", student: s }),
                              },
                            ]}
                          />
                          <Link
                            to={`/classes/${classId}/students/${s.id}`}
                            tabIndex={-1}
                            aria-hidden
                            className="flex h-8 items-center"
                          >
                            <ChevronRight className="h-[18px] w-[18px] shrink-0 text-muted-foreground/70" />
                          </Link>
                        </div>
                      ),
                    )}
                  </div>
                ))}

              {tab === "statistics" &&
                (dashboard ? (
                  <StatisticsSection statistics={dashboard.statistics} />
                ) : (
                  <Loading label="Loading the statistics">
                    <div className="grid gap-4 lg:grid-cols-3">
                      {[0, 1, 2].map((i) => (
                        <Skeleton key={i} className="h-[200px] rounded-lg" />
                      ))}
                    </div>
                  </Loading>
                ))}
            </>
          )}
        </div>
      </main>

      {klass && dialog?.kind === "edit" && (
        <ClassFormDialog
          mode="edit"
          initial={{
            name: klass.name,
            section: klass.section,
            mode: klass.mode,
            test_key: klass.test_key ?? null,
          }}
          modeLocked={klass.mode_locked}
          tests={klass.tests ?? []}
          onSubmit={edit}
          onCancel={close}
        />
      )}
      {klass && dialog?.kind === "pick" && (
        <ReadingPicker
          classId={klass.id}
          classLabel={klass.label}
          onDone={async () => {
            await refresh();
            close();
          }}
          onCancel={close}
        />
      )}
      {klass && dialog?.kind === "code" && (
        <ConfirmDialog
          title="Get a new join code?"
          confirmLabel="New code"
          cancelLabel="Cancel"
          onConfirm={newCode}
          onCancel={close}
        >
          The current code will stop working. Students already in the class stay in it.
        </ConfirmDialog>
      )}
      {klass && dialog?.kind === "remove" && (
        <ConfirmDialog
          title={`Remove ${dialog.student.name}?`}
          confirmLabel="Remove"
          cancelLabel="Cancel"
          tone="danger"
          onConfirm={() => remove(dialog.student)}
          onCancel={close}
        >
          They will no longer see this class&rsquo;s readings or their sessions in it.
        </ConfirmDialog>
      )}
      {klass && dialog?.kind === "delete" && (
        <ConfirmDialog
          title={`Delete ${klass.label}?`}
          confirmLabel="Delete"
          cancelLabel="Cancel"
          tone="danger"
          onConfirm={destroy}
          onCancel={close}
        >
          Students will lose access to its readings and their sessions in it.
        </ConfirmDialog>
      )}
    </div>
  );
}

function ClassSkeleton() {
  return (
    <Loading label="Loading the class" className="flex flex-col gap-4 sm:gap-5">
      <Skeleton className="h-3.5 w-40" />
      <div className="flex flex-col gap-1.5">
        <Skeleton className="h-6 w-36" />
        <Skeleton className="h-4 w-12" />
      </div>
      <Skeleton className="h-9 w-full rounded-lg sm:w-[344px]" />
      <div className="overflow-hidden rounded-lg border bg-card">
        {[0, 1, 2].map((i) => (
          <div key={i} className={cn("flex flex-col gap-1.5 px-5 py-4", i > 0 && "border-t")}>
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-3.5 w-64 max-w-full" />
          </div>
        ))}
      </div>
    </Loading>
  );
}
