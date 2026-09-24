/** One of the instructor's readings: the reading itself, its classes, and its
 *  core components.
 *
 * The reading shows both of its faces, the PDF students read and the text the
 * tutor grades against, so the instructor can check one against the other.
 * The text and the core components are shown read-only and marked Locked:
 * changing either would change what earlier sessions were graded against.
 *
 * No statistics here. Those belong to a reading within a class, on the class's
 * pages.
 */

import { Suspense, lazy, useState } from "react";
import { ChevronLeft, Lock } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";

import { AppTopBar } from "../../components/AppTopBar";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { Button } from "../../components/ui/button";
import {
  deleteLibraryReading,
  libraryFileUrl,
  setReadingClasses,
  updateLibraryReading,
} from "../../lib/api";
import { ReadingPanel } from "../tutoring/ReadingPanel";
import { EditReadingDialog, ReadingClassesDialog } from "./ReadingDialogs";
import { useLibraryReading } from "./useLibrary";

const PdfPanel = lazy(() =>
  import("../tutoring/PdfPanel").then((m) => ({ default: m.PdfPanel })),
);

type Dialog = "edit" | "classes" | "delete" | null;

export function LibraryReadingPage() {
  const { readingId } = useParams<{ readingId: string }>();
  const { data: reading, isLoading, isError } = useLibraryReading(readingId);
  const [dialog, setDialog] = useState<Dialog>(null);
  const [face, setFace] = useState<"pdf" | "text">("pdf");
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

  return (
    <div className="flex h-full flex-col">
      <AppTopBar />
      <main className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[1360px] px-4 py-5 sm:px-6 sm:py-6">
          <button
            onClick={() => navigate("/library")}
            className="mb-4 flex items-center gap-1.5 text-[13px] text-muted-foreground hover:text-foreground"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
            Readings
          </button>

          {isLoading && <p className="py-10 text-center text-[14px] text-muted-foreground">Loading reading…</p>}
          {isError && (
            <p className="py-10 text-center text-[14px] text-muted-foreground">
              This reading doesn&rsquo;t exist, or isn&rsquo;t yours.
            </p>
          )}

          {reading && (
            <>
              <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
                <div className="flex min-w-0 flex-col gap-1">
                  <h1 className="text-[22px] font-semibold tracking-[-0.02em] sm:text-[24px]">
                    {reading.title}
                  </h1>
                  {reading.description && (
                    <p className="text-[14px] text-muted-foreground">{reading.description}</p>
                  )}
                </div>
                <div className="flex gap-2">
                  <Button variant="secondary" size="sm" onClick={() => setDialog("edit")}>
                    Edit
                  </Button>
                  <Button variant="danger" size="sm" onClick={() => setDialog("delete")}>
                    Delete reading
                  </Button>
                </div>
              </div>

              <div className="grid items-start gap-5 lg:grid-cols-[1fr_380px]">
                {/* On narrow screens the short cards come first, above the long reading. */}
                <section className="order-2 flex h-[calc(100vh-230px)] min-h-[480px] flex-col overflow-hidden rounded-lg border lg:order-1">
                  <div className="shrink-0 border-b px-3 py-2">
                    <div className="inline-flex gap-0.5 rounded-md bg-muted p-[3px]">
                      {(["pdf", "text"] as const).map((f) => (
                        <button
                          key={f}
                          onClick={() => setFace(f)}
                          disabled={f === "pdf" && !reading.has_file}
                          className={`h-7 rounded px-3 text-[13px] font-medium disabled:opacity-50 ${
                            (f === "pdf" ? showPdf : !showPdf)
                              ? "bg-background text-foreground shadow-sm"
                              : "text-muted-foreground"
                          }`}
                        >
                          {f === "pdf" ? "PDF" : "Text"}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="min-h-0 flex-1">
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
                  </div>
                </section>

                <div className="order-1 flex flex-col gap-5 lg:order-2">
                  <section className="overflow-hidden rounded-lg border">
                    <div className="flex items-center justify-between border-b px-4 py-3">
                      <span className="text-[14px] font-semibold">Classes</span>
                      <Button variant="secondary" size="sm" onClick={() => setDialog("classes")}>
                        Change
                      </Button>
                    </div>
                    <p
                      className={`px-4 py-3.5 text-[14px] ${
                        reading.classes.length ? "" : "text-muted-foreground"
                      }`}
                    >
                      {reading.classes.length
                        ? reading.classes.map((c) => c.label).join(", ")
                        : "Not assigned"}
                    </p>
                  </section>

                  <section className="overflow-hidden rounded-lg border">
                    <div className="flex items-center justify-between border-b px-4 py-3.5">
                      <span className="text-[14px] font-semibold">Core components</span>
                      <span className="flex items-center gap-1.5 text-[13px] text-muted-foreground">
                        <Lock className="h-3.5 w-3.5" />
                        Locked
                      </span>
                    </div>
                    <ol>
                      {reading.core_components.map((c, i) => (
                        <li key={i} className="flex gap-2.5 border-b px-4 py-3 last:border-b-0">
                          <span className="w-3 shrink-0 text-[13px] leading-[21px] text-muted-foreground">
                            {i + 1}
                          </span>
                          <span className="text-[14px] leading-[1.5]">{c}</span>
                        </li>
                      ))}
                    </ol>
                  </section>
                </div>
              </div>
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
          confirmLabel="Delete"
          cancelLabel="Cancel"
          tone="danger"
          onConfirm={destroy}
          onCancel={close}
        >
          Students will lose access to it and their sessions on it.
        </ConfirmDialog>
      )}
    </div>
  );
}
