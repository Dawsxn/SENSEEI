/** Small display helpers for dates and durations. */

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/** "Sep 21" for a date this year, "Sep 21, 2025" otherwise. For narrow columns,
 *  where the year is noise until it stops being obvious. */
export function formatShortDate(iso: string): string {
  const date = new Date(iso);
  const thisYear = date.getFullYear() === new Date().getFullYear();
  return date.toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    ...(thisYear ? {} : { year: "numeric" }),
  });
}

/** "21 minutes" between two instants, or null if not both present. */
export function formatDuration(start: string, end: string | null): string | null {
  if (!end) return null;
  const minutes = Math.max(1, Math.round((+new Date(end) - +new Date(start)) / 60000));
  return `${minutes} minute${minutes === 1 ? "" : "s"}`;
}
