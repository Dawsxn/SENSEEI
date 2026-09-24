import { useQuery } from "@tanstack/react-query";

import { getLibrary, getLibraryReading } from "../../lib/api";

/** The signed-in instructor's readings. */
export function useLibrary() {
  return useQuery({ queryKey: ["library"], queryFn: getLibrary });
}

/** One of the instructor's readings, with its text, components and classes. */
export function useLibraryReading(readingId: string | undefined) {
  return useQuery({
    queryKey: ["library", readingId],
    queryFn: () => getLibraryReading(readingId!),
    enabled: !!readingId,
  });
}
