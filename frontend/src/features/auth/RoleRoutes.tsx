/** Routing that depends on who is signed in.
 *
 * `/` is a different place for each role: students land on their readings,
 * instructors on their classes, and trial participants on their group's screen. Instructor pages send a student home rather than
 * rendering a page whose every request would be refused.
 */

import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { ReadingListPage } from "../readings/ReadingListPage";
import { TrialHome } from "../trial/TrialHome";
import { useIsParticipant } from "../trial/useTrial";
import { useMe } from "./useAuth";

export function HomeRoute() {
  const { data: user } = useMe();
  const participant = useIsParticipant();
  if (user?.role === "instructor") return <Navigate to="/classes" replace />;
  if (participant) return <TrialHome />;
  return <ReadingListPage />;
}

export function RequireInstructor({ children }: { children: ReactNode }) {
  const { data: user } = useMe();
  if (user && user.role !== "instructor") return <Navigate to="/" replace />;
  return <>{children}</>;
}
