import { useQuery } from "@tanstack/react-query";

import { getClass, getClassReading, getClassStatistics, getClasses } from "../../lib/api";

/** The signed-in instructor's classes. */
export function useClasses() {
  return useQuery({ queryKey: ["classes"], queryFn: getClasses });
}

/** One class with its roster and readings. */
export function useClass(classId: string | undefined) {
  return useQuery({
    queryKey: ["class", classId],
    queryFn: () => getClass(classId!),
    enabled: !!classId,
  });
}

/** A class's statistics, and its readings with a session count each. */
export function useClassStatistics(classId: string | undefined) {
  return useQuery({
    queryKey: ["class-statistics", classId],
    queryFn: () => getClassStatistics(classId!),
    enabled: !!classId,
  });
}

/** One reading inside one class: its statistics and how far each student got. */
export function useClassReading(classId: string | undefined, readingId: string | undefined) {
  return useQuery({
    queryKey: ["class-reading", classId, readingId],
    queryFn: () => getClassReading(classId!, readingId!),
    enabled: !!classId && !!readingId,
  });
}
