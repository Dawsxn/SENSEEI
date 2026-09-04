import { useQuery } from "@tanstack/react-query";

import { getReading, getReadings } from "../../lib/api";

/** The readings this student can see. A plain request-response read. */
export function useReadings() {
  return useQuery({ queryKey: ["readings"], queryFn: getReadings });
}

/** One reading's detail — its text, class and core components. */
export function useReading(readingId: string | undefined) {
  return useQuery({
    queryKey: ["reading", readingId],
    queryFn: () => getReading(readingId!),
    enabled: !!readingId,
  });
}
