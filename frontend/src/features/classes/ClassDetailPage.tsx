/** One class: who is in it, the code that lets people in, and what it reads.
 *
 * The roster takes the main column because it is what changes. The join code is
 * large and monospaced because it is read aloud in a room and copied off a
 * projector. The readings are read-only here; which classes a reading goes to is
 * changed on the reading's own page.
 *
 * Removing a student and deleting the class both take access away rather than
 * data: the sessions stay in the database for the study, but neither the student
 * nor this page can reach them afterwards, and the dialogs say only what the
 * person clicking will notice.
 */

import { useState } from "react";
import { ChevronLeft, ChevronRight, Copy, Pencil, Trash2, Upload } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";

import { AppTopBar } from "../../components/AppTopBar";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { InfoTip, Tooltip } from "../../components/ui/Tooltip";
import { Button } from "../../components/ui/button";
import { formatShortDate } from "../../lib/format";
import { deleteClass, removeStudent, replaceJoinCode, updateClass } from "../../lib/api";
import { ClassFormDialog } from "./ClassFormDialog";
import { StatisticsSection } from "./StatisticsSection";
import type { ClassFields, ClassStudent } from "./types";
import { useClass, useClassStatistics } from "./useClasses";

type Dialog =
  | { kind: "edit" }
  | { kind: "code" }
  | { kind: "delete" }
  | { kind: "remove"; student: ClassStudent }
  | null;

export function ClassDetailPage() {
  const { classId } = useParams<{ classId: string }>();
  const { data: klass, isLoading, isError } = useClass(classId);
  const { data: dashboard } = useClassStatistics(classId);
  const [dialog, setDialog] = useState<Dialog>(null);
  const [copied, setCopied] = useState(false);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const refresh = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ["class", classId] }),
      queryClient.invalidateQueries({ queryKey: ["classes"] }),
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

  return (
    <div className="flex h-full flex-col">
      <AppTopBar />
      <main className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[1100px] px-4 py-5 sm:px-6 sm:py-6">
          <button
            onClick={() => navigate("/classes")}
            className="mb-4 flex items-center gap-1.5 text-[13px] text-muted-foreground hover:text-foreground"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
            Classes
          </button>

          {isLoading && <p className="py-10 text-center text-[14px] text-muted-foreground">Loading class…</p>}
          {isError && (
            <p className="py-10 text-center text-[14px] text-muted-foreground">
              This class doesn&rsquo;t exist, or isn&rsquo;t yours.
            </p>
          )}

          {klass && (
            <>
              <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
                <h1 className="text-[24px] font-semibold tracking-[-0.02em]">{klass.label}</h1>
                {/* Icons only: a pencil and a bin need no caption, and the
                    class's own name is right beside them. */}
                <div className="flex gap-2">
                  <Tooltip text="Edit class">
                    <Button
                      variant="secondary"
                      size="icon"
                      aria-label="Edit class"
                      onClick={() => setDialog({ kind: "edit" })}
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                  </Tooltip>
                  <Tooltip text="Delete class" align="left">
                    <Button
                      variant="danger"
                      size="icon"
                      aria-label="Delete class"
                      onClick={() => setDialog({ kind: "delete" })}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </Tooltip>
                </div>
              </div>

              {dashboard && (
                <div className="mb-5">
                  <StatisticsSection
                    statistics={dashboard.statistics}
                    scope="Across all readings in this class."
                  />
                </div>
              )}

              <div className="grid items-start gap-5 lg:grid-cols-[1fr_380px]">
                {/* On narrow screens the join code comes first: it is what an
                    instructor opens this page for on a phone in front of a class. */}
                <section className="order-2 rounded-lg border lg:order-1">
                  <CardHead title="Students" count={klass.students.length} />
                  {klass.students.length === 0 ? (
                    <div className="flex flex-col gap-1.5 px-6 py-12 text-center">
                      <span className="text-[14px] font-medium">No students yet</span>
                      <span className="text-[13px] text-muted-foreground">
                        Share the join code. Students who use it appear here.
                      </span>
                    </div>
                  ) : (
                    klass.students.map((s) => (
                      <div
                        key={s.id}
                        className="grid grid-cols-[28px_1fr_auto] items-center gap-3 border-b px-4 py-2.5 last:border-b-0 sm:grid-cols-[28px_1fr_110px_auto]"
                      >
                        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-muted text-[11px] font-medium text-muted-foreground">
                          {initials(s.name)}
                        </span>
                        <span className="min-w-0">
                          <span className="block truncate text-[14px] font-medium">{s.name}</span>
                          <span className="block truncate text-[12px] text-muted-foreground">{s.email}</span>
                        </span>
                        <span className="hidden whitespace-nowrap text-[13px] text-muted-foreground sm:block">
                          Joined {formatShortDate(s.enrolled_at)}
                        </span>
                        {/* A bin, like the one on the class itself. The
                            student's name is beside it, so it needs no caption. */}
                        <Tooltip text={`Remove ${s.name}`} align="left">
                          <button
                            aria-label={`Remove ${s.name}`}
                            onClick={() => setDialog({ kind: "remove", student: s })}
                            className="flex h-7 w-7 items-center justify-center rounded-md text-fail-foreground hover:bg-fail focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </Tooltip>
                      </div>
                    ))
                  )}
                </section>

                <div className="order-1 flex flex-col gap-5 lg:order-2">
                  <section className="rounded-lg border">
                    <CardHead
                      title="Join code"
                      tip="The code students use to join this class."
                    />
                    <div className="flex flex-col gap-3.5 px-4 pb-4 pt-[18px]">
                      <span className="font-mono text-[28px] font-medium tracking-[0.06em]">
                        {klass.join_code}
                      </span>
                      <div className="flex gap-2">
                        <Button variant="secondary" size="sm" onClick={() => copy(klass.join_code)}>
                          <Copy className="h-3.5 w-3.5 text-muted-foreground" />
                          {copied ? "Copied" : "Copy"}
                        </Button>
                        <Button variant="secondary" size="sm" onClick={() => setDialog({ kind: "code" })}>
                          New code
                        </Button>
                      </div>
                    </div>
                  </section>

                  {/* Each reading leads to how that reading went in this class. */}
                  <section className="rounded-lg border">
                    <div className="flex items-center justify-between border-b px-4 py-2.5">
                      <span className="flex items-center gap-2 text-[14px] font-semibold">
                        Readings
                        <span className="text-[13px] font-normal text-muted-foreground">
                          {klass.readings.length}
                        </span>
                      </span>
                      {/* Uploading from here starts the usual flow with this
                          class already ticked. */}
                      <Tooltip text="Upload a reading" align="left">
                        <Button
                          variant="accent"
                          size="icon"
                          aria-label="Upload a reading"
                          className="h-8 w-8"
                          onClick={() => navigate(`/library/new?class=${classId}`)}
                        >
                          <Upload className="h-3.5 w-3.5" />
                        </Button>
                      </Tooltip>
                    </div>
                    {klass.readings.length === 0 ? (
                      <p className="px-4 py-5 text-[13px] text-muted-foreground">
                        No readings yet.
                      </p>
                    ) : (
                      klass.readings.map((r) => {
                        const sessions = dashboard?.readings.find((d) => d.id === r.id)
                          ?.session_count;
                        return (
                          <button
                            key={r.id}
                            onClick={() => navigate(`/classes/${classId}/readings/${r.id}`)}
                            className="grid w-full grid-cols-[1fr_24px] items-center gap-3 border-b px-4 py-3 text-left last:rounded-b-lg last:border-b-0 hover:bg-muted/40"
                          >
                            <span className="min-w-0">
                              <span className="block truncate text-[14px] font-medium">
                                {r.title}
                              </span>
                              <span className="block text-[12px] text-muted-foreground">
                                {sessions === undefined
                                  ? r.description
                                  : `${sessions} ${sessions === 1 ? "session" : "sessions"}`}
                              </span>
                            </span>
                            <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/70" />
                          </button>
                        );
                      })
                    )}
                  </section>
                </div>
              </div>
            </>
          )}
        </div>
      </main>

      {klass && dialog?.kind === "edit" && (
        <ClassFormDialog
          mode="edit"
          initial={{ name: klass.name, section: klass.section }}
          onSubmit={edit}
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

function CardHead({
  title,
  count,
  tip,
}: {
  title: string;
  count?: number;
  tip?: string;
}) {
  return (
    <div className="flex items-center justify-between border-b px-4 py-3.5">
      <span className="flex items-center gap-1.5 text-[14px] font-semibold">
        {title}
        {tip && <InfoTip text={tip} />}
      </span>
      {count !== undefined && <span className="text-[13px] text-muted-foreground">{count}</span>}
    </div>
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
