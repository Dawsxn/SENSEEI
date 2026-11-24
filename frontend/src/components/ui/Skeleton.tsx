import { useEffect, useState, type ReactNode } from "react";

import { cn } from "../../lib/utils";

/** A grey block that pulses in place of something still loading. */
export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={cn("animate-pulse rounded-md bg-border/70", className)} />;
}

/** Placeholders for a page or panel that is loading.
 *
 * Held back for a moment, so a load that finishes quickly shows nothing rather
 * than a flash of grey. Screen readers hear `label` once, not every block. */
export function Loading({
  label,
  delay = 200,
  className,
  children,
}: {
  label: string;
  delay?: number;
  className?: string;
  children: ReactNode;
}) {
  const [shown, setShown] = useState(delay === 0);
  useEffect(() => {
    if (delay === 0) return;
    const timer = setTimeout(() => setShown(true), delay);
    return () => clearTimeout(timer);
  }, [delay]);
  return (
    <div role="status" aria-label={label} aria-busy="true" className={className}>
      {shown && children}
    </div>
  );
}
