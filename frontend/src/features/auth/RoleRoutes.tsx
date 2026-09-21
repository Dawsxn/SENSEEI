/** Routing that depends on who is signed in.
 *
 * `/` is a different place for each role: students land on their readings,
 * instructors on their classes. Instructor pages send a student home rather than
 * rendering a page whose every request would be refused.
 */

import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { ReadingListPage } from "../readings/ReadingListPage";
import { useMe } from "./useAuth";

export function HomeRoute() {
  const { data: user } = useMe();
  if (user?.role === "instructor") return <Navigate to="/classes" replace />;
  return <ReadingListPage />;
}

export function RequireInstructor({ children }: { children: ReactNode }) {
  const { data: user } = useMe();
  if (user && user.role !== "instructor") return <Navigate to="/" replace />;
  return <>{children}</>;
}
