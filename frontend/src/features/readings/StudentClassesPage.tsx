/** A student's home: the classes they are in, as cards.
 *
 * Each card shows how many readings the class has, and opens it; how far the
 * student is through them is on the class page, in its To do and Finished
 * counts. Join a class sits beside the heading, in the same place however many
 * classes there are.
 */

import { useState } from "react";

import { AppTopBar } from "../../components/AppTopBar";
import { Button } from "../../components/ui/button";
import { ClassCard } from "./ClassCard";
import { JoinClassDialog } from "./JoinClassDialog";
import { Notice } from "./parts";
import { ClassesSkeleton } from "./skeletons";
import { useMyClasses } from "./useReadings";

export function StudentClassesPage() {
  const { data, isLoading, isError } = useMyClasses();
  const [joining, setJoining] = useState(false);

  return (
    <div className="flex h-full flex-col">
      <AppTopBar />
      <main className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex max-w-[1148px] flex-col gap-5 px-4 py-5 sm:gap-6 sm:px-8 sm:py-7 lg:px-6 lg:py-8">
          <div className="flex items-center justify-between gap-4">
            <h1 className="text-[22px] font-semibold tracking-[-0.02em] sm:text-[24px]">
              Classes
            </h1>
            <Button variant="secondary" size="sm" onClick={() => setJoining(true)}>
              + Join a class
            </Button>
          </div>

          {isLoading && <ClassesSkeleton />}
          {isError && <Notice>Couldn't load your classes. Try again.</Notice>}
          {data && data.length === 0 && (
            <Notice>No classes available</Notice>
          )}

          {data && data.length > 0 && (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 lg:grid-cols-4 lg:gap-5">
              {data.map((c, i) => (
                <ClassCard
                  key={c.id}
                  klass={c}
                  index={i}
                  meta={`${c.reading_count} ${c.reading_count === 1 ? "reading" : "readings"}`}
                />
              ))}
            </div>
          )}
        </div>
      </main>
      {joining && <JoinClassDialog onClose={() => setJoining(false)} />}
    </div>
  );
}
