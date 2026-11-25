/** One of the instructor's readings, in three tabs: the reading itself, its
 *  core components, and the classes it is in.
 *
 * The reading shows both of its faces, the PDF students read and the text the
 * tutor grades against, so the instructor can check one against the other.
 * The text and the core components can't be changed, and each says why:
 * changing either would change what earlier sessions were graded against.
 *
 * No statistics here. Those belong to a reading within a class, which each
 * row on the Classes tab opens.
 */

import { Suspense, lazy, useState } from "react";
import { ChevronRight, Lock, MoreHorizontal } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";

import { AppTopBar } from "../../components/AppTopBar";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { Menu } from "../../components/ui/Menu";
import { Button } from "../../components/ui/button";
import {
  deleteLibraryReading,
  libraryFileUrl,
  setReadingClasses,
  updateLibraryReading,
} from "../../lib/api";
import { cn } from "../../lib/utils";
import { Breadcrumb, Notice } from "../readings/parts";
import { ReadingSkeleton } from "../readings/skeletons";
import { ReadingPanel } from "../tutoring/ReadingPanel";
import { EditReadingDialog, ReadingClassesDialog } from "./ReadingDialogs";
import { useLibraryReading } from "./useLibrary";

const PdfPanel = lazy(() =>
  import("../tutoring/PdfPanel").then((m) => ({ default: m.PdfPanel })),
);

type Dialog = "edit" | "classes" | "delete" | null;
type Tab = "reading" | "components" | "classes";

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

export function LibraryReadingPage() {
  const { readingId } = useParams<{ readingId: string }>();
  const { data: reading, isLoading, isError } = useLibraryReading(readingId);
  const [dialog, setDialog] = useState<Dialog>(null);
  const [face, setFace] = useState<"pdf" | "text">("pdf");
  const [tab, setTab] = useState<Tab>("reading");
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const close = () => setDialog(null);
  const refresh = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ["library"] }),
      queryClient.invalidateQueries({ queryKey: ["classes"] }),
    ]);

  async function edit(fields: { title: string; description: string | null }) {
    await updateLibraryReading(readingId!, fields);
    await refresh();
    close();
  }

  async function reassign(classIds: string[]) {
    await setReadingClasses(readingId!, classIds);
    await refresh();
    close();
  }

  async function destroy() {
    await deleteLibraryReading(readingId!);
    // Leave first, and drop this reading's cache rather than refetching it:
    // refetching a reading that was just deleted only earns a 404.
    navigate("/library");
    queryClient.removeQueries({ queryKey: ["library", readingId] });
    await queryClient.invalidateQueries({ queryKey: ["library"] });
    await queryClient.invalidateQueries({ queryKey: ["classes"] });
  }

  const showPdf = reading?.has_file && face === "pdf";
  const tabs: { key: Tab; label: string; count?: number }[] = reading
    ? [
        { key: "reading", label: "Reading" },
        { key: "components", label: "Core components", count: reading.core_components.length },
        { key: "classes", label: "Classes", count: reading.classes.length },
      ]
    : [];

  return (
    <div className="flex h-full flex-col">
      <AppTopBar />
      <main className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex max-w-[1148px] flex-col gap-4 px-4 py-4 sm:gap-5 sm:px-8 sm:py-6 lg:px-6">
          {isLoading && <ReadingSkeleton />}
          {isError && <Notice>This reading doesn't exist, or isn't yours.</Notice>}

          {reading && (
            <>
              <div className="flex flex-col gap-2.5">
                <Breadcrumb trail={[{ label: "Readings", to: "/library" }]} current={reading.title} />
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <h1 className="text-[22px] font-semibold tracking-[-0.02em] sm:text-[24px]">
                      {reading.title}
                    </h1>
                    {reading.description && (
                      <p className="mt-0.5 text-[14px] text-muted-foreground">{reading.description}</p>
                    )}
                  </div>
                  <Menu
                    label="Reading options"
                    trigger={<MoreHorizontal className="h-4 w-4" />}
                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border bg-background text-foreground/80 hover:bg-muted"
                    items={[
                      { label: "Edit reading", onSelect: () => setDialog("edit") },
                      { label: "Delete reading", danger: true, onSelect: () => setDialog("delete") },
                    ]}
                  />
                </div>
              </div>

              <div role="tablist" className="flex gap-6 overflow-x-auto border-b">
                {tabs.map((t) => (
                  <button
                    key={t.key}
                    type="button"
                    role="tab"
                    aria-selected={tab === t.key}
                    onClick={() => setTab(t.key)}
                    className={cn(
                      "-mb-px shrink-0 whitespace-nowrap border-b-2 pb-2.5 text-[14px] font-medium",
                      tab === t.key
                        ? "border-foreground text-foreground"
                        : "border-transparent text-muted-foreground hover:text-foreground",
                    )}
                  >
                    {t.label}
                    {t.count !== undefined && <span className="ml-1 text-muted-foreground/70">{t.count}</span>}
                  </button>
                ))}
              </div>

              {tab === "reading" && (
                <>
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <div className="inline-flex gap-0.5 self-start rounded-lg bg-muted p-[3px]">
                      {(["pdf", "text"] as const).map((f) => (
                        <button
                          key={f}
                          type="button"
                          onClick={() => setFace(f)}
                          disabled={f === "pdf" && !reading.has_file}
                          className={cn(
                            "w-[88px] rounded-md py-[5px] text-[13px] font-medium disabled:opacity-50",
                            (f === "pdf" ? showPdf : !showPdf)
                              ? "bg-background text-foreground shadow-raised"
                              : "text-muted-foreground hover:text-foreground",
                          )}
                        >
                          {f === "pdf" ? "PDF" : "Text"}
                        </button>
                      ))}
                    </div>
                    {!showPdf && (
                      <LockNote>The text can't be changed because students' answers are checked against it.</LockNote>
                    )}
                  </div>
                  <section className="h-[calc(100vh-300px)] min-h-[420px] overflow-hidden rounded-lg border">
                    {showPdf ? (
                      <Suspense fallback={<p className="p-6 text-[13px] text-muted-foreground">Loading the PDF…</p>}>
                        <PdfPanel
                          fileUrl={libraryFileUrl(reading.id)}
                          fallback={<ReadingPanel content={reading.content} />}
                        />
                      </Suspense>
                    ) : (
                      <ReadingPanel content={reading.content} />
                    )}
                  </section>
                </>
              )}

              {tab === "components" && (
                <>
                  <LockNote>
                    Core components can't be changed because students' answers are checked against them.
                  </LockNote>
                  <ol className="overflow-hidden rounded-lg border">
                    {reading.core_components.map((c, i) => (
                      <li key={i} className={cn("flex gap-3 px-4 py-3.5", i > 0 && "border-t")}>
                        <span className="w-4 shrink-0 text-[14px] font-medium leading-[1.5] text-muted-foreground/70">
                          {i + 1}
                        </span>
                        <span className="text-[14px] leading-[1.5]">{c}</span>
                      </li>
                    ))}
                  </ol>
                </>
              )}

              {tab === "classes" && (
                <>
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <p className="text-[13px] text-muted-foreground">
                      Students in these classes can open this reading.
                    </p>
                    <Button
                      variant="secondary"
                      size="sm"
                      className="w-full sm:w-auto"
                      onClick={() => setDialog("classes")}
                    >
                      Change classes
                    </Button>
                  </div>
                  {reading.classes.length === 0 ? (
                    <Notice>No classes available</Notice>
                  ) : (
                    <div className="overflow-hidden rounded-lg border">
                      {reading.classes.map((c, i) => (
                        <Link
                          key={c.id}
                          to={`/classes/${c.id}/readings/${reading.id}`}
                          className={cn(
                            "flex items-center gap-3 py-3.5 pl-4 pr-3 hover:bg-muted/50 focus-visible:bg-muted/50 focus-visible:outline-none sm:gap-5 sm:pl-5 sm:pr-4",
                            i > 0 && "border-t",
                          )}
                        >
                          <div className="min-w-0 flex-1">
                            <div className="text-[14px] font-medium">{c.label}</div>
                            <div className="mt-0.5 text-[13px] text-muted-foreground">
                              {plural(c.student_count, "student", "students")}
                            </div>
                          </div>
                          <span className="shrink-0 whitespace-nowrap text-[13px] text-muted-foreground">
                            {plural(c.session_count, "session", "sessions")}
                          </span>
                          <ChevronRight className="h-[18px] w-[18px] shrink-0 text-muted-foreground/70" />
                        </Link>
                      ))}
                    </div>
                  )}
                </>
              )}
            </>
          )}
        </div>
      </main>

      {reading && dialog === "edit" && (
        <EditReadingDialog
          initial={{ title: reading.title, description: reading.description }}
          onSubmit={edit}
          onCancel={close}
        />
      )}
      {reading && dialog === "classes" && (
        <ReadingClassesDialog
          initial={reading.classes.map((c) => c.id)}
          onSubmit={reassign}
          onCancel={close}
        />
      )}
      {reading && dialog === "delete" && (
        <ConfirmDialog
          title={`Delete ${reading.title}?`}
          confirmLabel="Delete reading"
          cancelLabel="Cancel"
          tone="danger"
          onConfirm={destroy}
          onCancel={close}
        >
          {deleteBody(reading.classes.length, reading.session_count)}
        </ConfirmDialog>
      )}
    </div>
  );
}

/** What deleting takes with it, in counts, so it reads the same for any number
 *  of classes. */
export function deleteBody(classes: number, sessions: number) {
  const from = classes ? `removes the reading from ${plural(classes, "class", "classes")}` : "";
  const gone = sessions ? `deletes its ${plural(sessions, "session", "sessions")}` : "";
  const what = [from, gone].filter(Boolean).join(" and ");
  return `${what ? `This ${what}. ` : ""}You can't undo this.`;
}

function LockNote({ children }: { children: React.ReactNode }) {
  return (
    <p className="flex items-start gap-2 text-[13px] text-muted-foreground">
      <Lock className="mt-[3px] h-3.5 w-3.5 shrink-0" />
      {children}
    </p>
  );
}
