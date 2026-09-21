import { useQuery } from "@tanstack/react-query";

import { getClass, getClasses } from "../../lib/api";

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
