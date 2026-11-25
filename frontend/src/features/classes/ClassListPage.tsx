/** An instructor's home: their classes, as cards, and the way to make a new one.
 *
 * The same cards as a student's home, with how many students and readings each
 * class has. The join code is on the class's own page, where it is shared from.
 */

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { AppTopBar } from "../../components/AppTopBar";
import { Button } from "../../components/ui/button";
import { createClass } from "../../lib/api";
import { useTrialMode } from "../auth/useAuth";
import { ClassCard } from "../readings/ClassCard";
import { Notice } from "../readings/parts";
import { ClassesSkeleton } from "../readings/skeletons";
import { ClassFormDialog } from "./ClassFormDialog";
import { MODE_LABEL, type ClassFields, type ClassListItem } from "./types";
import { useClasses } from "./useClasses";

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

export function ClassListPage() {
  const { data, isLoading, isError } = useClasses();
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  // On the trial instance a class is a group: its mode matters, and its people
  // are participants.
  const trial = useTrialMode();

  async function create(fields: ClassFields) {
    const created = await createClass(fields);
    await queryClient.invalidateQueries({ queryKey: ["classes"] });
    // Straight to the new class, where its join code is.
    navigate(`/classes/${created.id}`);
  }

  const meta = (c: ClassListItem) =>
    trial
      ? `${MODE_LABEL[c.mode]} · ${plural(c.student_count, "participant", "participants")}`
      : `${plural(c.student_count, "student", "students")} · ${plural(c.reading_count, "reading", "readings")}`;

  return (
    <div className="flex h-full flex-col">
      <AppTopBar />
      <main className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex max-w-[1148px] flex-col gap-5 px-4 py-5 sm:gap-6 sm:px-8 sm:py-7 lg:px-6 lg:py-8">
          <div className="flex items-center justify-between gap-4">
            <h1 className="text-[22px] font-semibold tracking-[-0.02em] sm:text-[24px]">
              Classes
            </h1>
            <Button variant="secondary" size="sm" onClick={() => setCreating(true)}>
              + New class
            </Button>
          </div>

          {isLoading && <ClassesSkeleton />}
          {isError && <Notice>Couldn't load your classes. Try again.</Notice>}
          {data && data.length === 0 && <Notice>No classes available</Notice>}

          {data && data.length > 0 && (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 lg:grid-cols-4 lg:gap-5">
              {data.map((c, i) => (
                <ClassCard key={c.id} klass={c} index={i} meta={meta(c)} />
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
