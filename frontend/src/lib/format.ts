/** Small display helpers for dates and durations. */

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/** "21 minutes" between two instants, or null if not both present. */
export function formatDuration(start: string, end: string | null): string | null {
  if (!end) return null;
  const minutes = Math.max(1, Math.round((+new Date(end) - +new Date(start)) / 60000));
  return `${minutes} minute${minutes === 1 ? "" : "s"}`;
}
