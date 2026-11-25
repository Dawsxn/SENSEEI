import { useQuery } from "@tanstack/react-query";

import { ApiError, getMyClass, getMyClasses, getReading, getReadingSessions } from "../../lib/api";

/** The classes this student is in, with their progress. */
export function useMyClasses() {
  return useQuery({ queryKey: ["my-classes"], queryFn: getMyClasses });
}

/** One of the student's classes and its readings. */
export function useMyClass(classId: string | undefined) {
  return useQuery({
    queryKey: ["my-classes", classId],
    queryFn: () => getMyClass(classId!),
    enabled: !!classId,
  });
}

/** One reading's detail — its text, class and core components. */
export function useReading(readingId: string | undefined) {
  return useQuery({
    queryKey: ["reading", readingId],
    queryFn: () => getReading(readingId!),
    enabled: !!readingId,
    // A reading that does not exist will not start to on a second ask.
    retry: (count, error) => !(error instanceof ApiError && error.status === 404) && count < 2,
  });
}

/** The student's past sessions on a reading. */
export function useReadingSessions(readingId: string | undefined) {
  return useQuery({
    queryKey: ["reading-sessions", readingId],
    queryFn: () => getReadingSessions(readingId!),
    enabled: !!readingId,
  });
}
