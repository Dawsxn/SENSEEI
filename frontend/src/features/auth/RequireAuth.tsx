import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { useMe } from "./useAuth";

/** Gate a route on being signed in. While the check is in flight, render
 *  nothing; if it fails (401), send the visitor to the sign-in screen. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { data, isLoading, isError } = useMe();

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center text-[13px] text-muted-foreground">
        Loading…
      </div>
    );
  }
  if (isError || !data) return <Navigate to="/login" replace />;
  return <>{children}</>;
}
