import { useQuery } from "@tanstack/react-query";

import { getTranscript } from "../../lib/api";

/** One session's read-only transcript (summary + timeline). */
export function useTranscript(sessionId: string | undefined) {
  return useQuery({
    queryKey: ["transcript", sessionId],
    queryFn: () => getTranscript(sessionId!),
    enabled: !!sessionId,
  });
}
