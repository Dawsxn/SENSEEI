/** An instructor's home: their classes, and the way to make a new one.
 *
 * With no classes yet, the New class button lives in the empty state rather than
 * above an empty table, so the first thing an instructor sees is what to do.
 */

import { useState } from "react";
import { ChevronRight, Plus } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { AppTopBar } from "../../components/AppTopBar";
import { Tooltip } from "../../components/ui/Tooltip";
import { Button } from "../../components/ui/button";
import { createClass } from "../../lib/api";
import { ClassFormDialog } from "./ClassFormDialog";
import type { ClassFields } from "./types";
import { useClasses } from "./useClasses";

export function ClassListPage() {
  const { data, isLoading, isError } = useClasses();
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  async function create(fields: ClassFields) {
    const created = await createClass(fields);
    await queryClient.invalidateQueries({ queryKey: ["classes"] });
    // Straight to the new class, where its join code is.
    navigate(`/classes/${created.id}`);
  }

  const classes = data ?? [];

  return (
    <div className="flex h-full flex-col">
      <AppTopBar />
      <main className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[1100px] px-4 py-6 sm:px-6 sm:py-8">
          <div className="mb-5 flex items-center justify-between">
            <h1 className="text-[24px] font-semibold tracking-[-0.02em]">Classes</h1>
            {/* An icon alone: the heading beside it already says what is being
                made, and the tooltip names it for anyone unsure. */}
            {classes.length > 0 && (
              <Tooltip text="New class" align="left">
                <Button variant="accent" size="icon" aria-label="New class" onClick={() => setCreating(true)}>
                  <Plus className="h-4 w-4" />
                </Button>
              </Tooltip>
            )}
          </div>

          {isLoading && <Notice>Loading classes…</Notice>}
          {isError && <Notice>Couldn&rsquo;t load your classes.</Notice>}

          {data && classes.length === 0 && (
            <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed px-6 py-16 text-center">
              <span className="text-[15px] font-semibold">No classes yet</span>
              <span className="text-[14px] text-muted-foreground">
                Create a class to get a join code for your students.
              </span>
              <Button className="mt-3" onClick={() => setCreating(true)}>
                <Plus className="h-4 w-4" />
                New class
              </Button>
            </div>
          )}

          {classes.length > 0 && (
            <div className="overflow-hidden rounded-lg border">
              {/* Column headings only where there is room for the columns. */}
              <div className="hidden h-10 grid-cols-[1fr_120px_160px_100px_100px_24px] items-center gap-4 border-b px-4 text-[12px] font-medium text-muted-foreground sm:grid">
                <span>Class</span>
                <span>Section</span>
                <span>Join code</span>
                <span>Students</span>
                <span>Readings</span>
                <span />
              </div>
              {classes.map((c) => (
                <button
                  key={c.id}
                  onClick={() => navigate(`/classes/${c.id}`)}
                  className="grid w-full grid-cols-[1fr_24px] items-center gap-4 border-b px-4 py-4 text-left last:border-b-0 hover:bg-muted/40 sm:grid-cols-[1fr_120px_160px_100px_100px_24px]"
                >
                  <span className="min-w-0">
                    <span className="block text-[14px] font-medium">{c.name}</span>
                    {/* On narrow screens the columns collapse into this line. */}
                    <span className="mt-0.5 block text-[13px] text-muted-foreground sm:hidden">
                      {c.section} · {c.student_count} students · {c.join_code}
                    </span>
                  </span>
                  <span className="hidden text-[13px] text-[#3f3f46] sm:block">{c.section}</span>
                  <span className="hidden font-mono text-[13px] tracking-wider text-[#3f3f46] sm:block">
                    {c.join_code}
                  </span>
                  <span className="hidden text-[13px] text-muted-foreground sm:block">
                    {c.student_count}
                  </span>
                  <span className="hidden text-[13px] text-muted-foreground sm:block">
                    {c.reading_count}
                  </span>
                  <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/70" />
                </button>
              ))}
            </div>
          )}
        </div>
      </main>

      {creating && (
        <ClassFormDialog mode="new" onSubmit={create} onCancel={() => setCreating(false)} />
      )}
    </div>
  );
}

function Notice({ children }: { children: React.ReactNode }) {
  return <p className="py-10 text-center text-[14px] text-muted-foreground">{children}</p>;
}
