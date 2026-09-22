/** An instructor's readings, and the way to upload a new one.
 *
 * As on the classes page, with nothing yet the upload button lives in the empty
 * state. A reading assigned to no class is shown greyed as Not assigned, since
 * that is a reading no student can see.
 */

import { ChevronRight } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { AppTopBar } from "../../components/AppTopBar";
import { Button } from "../../components/ui/button";
import { formatShortDate } from "../../lib/format";
import { useLibrary } from "./useLibrary";

export function LibraryListPage() {
  const { data, isLoading, isError } = useLibrary();
  const navigate = useNavigate();
  const readings = data ?? [];
  const upload = () => navigate("/library/new");

  return (
    <div className="flex h-full flex-col">
      <AppTopBar />
      <main className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[1100px] px-4 py-6 sm:px-6 sm:py-8">
          <div className="mb-5 flex items-center justify-between gap-3">
            <h1 className="text-[24px] font-semibold tracking-[-0.02em]">Readings</h1>
            {readings.length > 0 && <Button onClick={upload}>Upload a reading</Button>}
          </div>

          {isLoading && <Notice>Loading readings…</Notice>}
          {isError && <Notice>Couldn&rsquo;t load your readings.</Notice>}

          {data && readings.length === 0 && (
            <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed px-6 py-16 text-center">
              <span className="text-[15px] font-semibold">No readings yet</span>
              <Button className="mt-3" onClick={upload}>
                Upload a reading
              </Button>
            </div>
          )}

          {readings.length > 0 && (
            <div className="overflow-hidden rounded-lg border">
              <div className="hidden h-10 grid-cols-[1fr_200px_100px_100px_24px] items-center gap-4 border-b px-4 text-[12px] font-medium text-muted-foreground sm:grid">
                <span>Title</span>
                <span>Classes</span>
                <span>Sessions</span>
                <span>Added</span>
                <span />
              </div>
              {readings.map((r) => {
                const classes = r.classes.length ? r.classes.join(", ") : "Not assigned";
                const tone = r.classes.length ? "text-[#3f3f46]" : "text-muted-foreground/70";
                return (
                  <button
                    key={r.id}
                    onClick={() => navigate(`/library/${r.id}`)}
                    className="grid w-full grid-cols-[1fr_24px] items-center gap-4 border-b px-4 py-3.5 text-left last:border-b-0 hover:bg-muted/40 sm:grid-cols-[1fr_200px_100px_100px_24px]"
                  >
                    <span className="min-w-0">
                      <span className="block text-[14px] font-medium">{r.title}</span>
                      {r.description && (
                        <span className="mt-0.5 hidden truncate text-[12px] text-muted-foreground sm:block">
                          {r.description}
                        </span>
                      )}
                      {/* On narrow screens the columns collapse into this line. */}
                      <span className="mt-0.5 block text-[12px] text-muted-foreground sm:hidden">
                        <span className={r.classes.length ? "" : "text-muted-foreground/70"}>
                          {classes}
                        </span>{" "}
                        · {r.session_count} sessions · {formatShortDate(r.created_at)}
                      </span>
                    </span>
                    <span className={`hidden text-[13px] sm:block ${tone}`}>{classes}</span>
                    <span className="hidden text-[13px] text-muted-foreground sm:block">
                      {r.session_count}
                    </span>
                    <span className="hidden whitespace-nowrap text-[13px] text-muted-foreground sm:block">
                      {formatShortDate(r.created_at)}
                    </span>
                    <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/70" />
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

function Notice({ children }: { children: React.ReactNode }) {
  return <p className="py-10 text-center text-[14px] text-muted-foreground">{children}</p>;
}
