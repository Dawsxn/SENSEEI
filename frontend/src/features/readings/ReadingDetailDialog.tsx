import { ChevronRight, X } from "lucide-react";
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "../../components/ui/button";
import { SessionStatusBadge } from "../../components/SessionStatusBadge";
import { formatDate } from "../../lib/format";
import { useReading, useReadingSessions } from "./useReadings";

/** The reading detail, from the mockup: core components, past sessions, and a
 *  new attempt. A plain modal — overlay click and Escape close it. */
export function ReadingDetailDialog({
  readingId,
  onClose,
}: {
  readingId: string;
  onClose: () => void;
}) {
  const navigate = useNavigate();
  const { data: reading } = useReading(readingId);
  const { data: sessions } = useReadingSessions(readingId);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  const completed = (sessions ?? []).filter((s) => s.status === "complete").length;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/30 p-0 sm:items-center sm:p-4"
      onClick={onClose}
    >
      <div
        className="flex max-h-[90vh] w-full max-w-[560px] flex-col overflow-hidden rounded-t-lg bg-background shadow-lg sm:rounded-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between px-6 pt-5">
          <div className="min-w-0">
            {reading && (
              <div className="text-[12px] font-medium uppercase tracking-wide text-muted-foreground">
                {reading.class_name}
              </div>
            )}
            <h2 className="text-[18px] font-semibold">{reading?.title ?? "…"}</h2>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="rounded-md p-1 text-muted-foreground hover:bg-muted"
          >
            <X className="h-[18px] w-[18px]" />
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-6 py-4">
          {reading && reading.core_components.length > 0 && (
            <section className="mb-5">
              <h3 className="mb-2 text-[12px] font-medium uppercase tracking-wide text-muted-foreground">
                Core {reading.core_components.length === 1 ? "component" : "components"}
              </h3>
              <ul className="space-y-1.5">
                {reading.core_components.map((c, i) => (
                  <li key={i} className="flex gap-2 text-[14px] text-[#3f3f46]">
                    <span className="text-muted-foreground">•</span>
                    <span>{c}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {sessions && sessions.length > 0 && (
            <section>
              <div className="mb-2 flex items-center justify-between">
                <h3 className="text-[12px] font-medium uppercase tracking-wide text-muted-foreground">
                  Past sessions
                </h3>
                <span className="text-[12px] text-muted-foreground">
                  {completed} of {sessions.length} completed
                </span>
              </div>
              <div className="overflow-hidden rounded-md border">
                {sessions.map((s, i) => (
                  <button
                    key={s.id}
                    onClick={() => navigate(`/review/${s.id}`)}
                    className={`flex w-full items-center gap-3 px-3 py-2.5 text-left hover:bg-muted ${
                      i > 0 ? "border-t" : ""
                    }`}
                  >
                    <span className="text-[14px] font-medium">Attempt {s.index}</span>
                    <SessionStatusBadge status={s.status} />
                    <span className="ml-auto text-[13px] text-muted-foreground">
                      {formatDate(s.started_at)}
                    </span>
                    <ChevronRight className="h-4 w-4 text-[#a1a1aa]" />
                  </button>
                ))}
              </div>
            </section>
          )}
        </div>

        <div className="flex items-center justify-between gap-3 border-t px-6 py-4">
          <span className="text-[13px] text-muted-foreground">
            Four steps, three attempts each.
          </span>
          <Button onClick={() => navigate(`/tutor/${readingId}`)}>
            Start a new attempt
          </Button>
        </div>
      </div>
    </div>
  );
}
