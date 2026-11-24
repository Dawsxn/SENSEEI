import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { Loading } from "../../components/ui/Skeleton";
import { DevSignOut } from "../trial/DevSignOut";
import { useMe } from "./useAuth";

/** Gate a route on being signed in; if the check fails (401), send the visitor
 *  to the sign-in screen.
 *
 * While the check is in flight the page is blank, since which page and whose
 * it is are not known yet, so there is no shape to stand in for. It usually
 * takes a moment; only a slow one, on a bad connection, earns a word. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { data, isLoading, isError } = useMe();

  if (isLoading) {
    return (
      <Loading
        label="Loading"
        delay={500}
        className="flex h-full items-center justify-center text-[13px] text-muted-foreground"
      >
        Loading…
      </Loading>
    );
  }
  if (isError || !data) return <Navigate to="/login" replace />;
  return (
    <>
      {children}
      {/* Local testing only: a trial participant has no way out otherwise. */}
      <DevSignOut />
    </>
  );
}
