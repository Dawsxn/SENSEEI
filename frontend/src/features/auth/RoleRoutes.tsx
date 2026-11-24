/** Routing that depends on who is signed in.
 *
 * `/` is a different place for each role: students land on their classes,
 * instructors on theirs, and trial participants on their group's screen. Instructor pages send a student home rather than
 * rendering a page whose every request would be refused.
 */

import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { StudentClassesPage } from "../readings/StudentClassesPage";
import { TrialHome } from "../trial/TrialHome";
import { useIsParticipant } from "../trial/useTrial";
import { useMe } from "./useAuth";

export function HomeRoute() {
  const { data: user } = useMe();
  const participant = useIsParticipant();
  if (user?.role === "instructor") return <Navigate to="/classes" replace />;
  if (user?.role === "grader") return <Navigate to="/grading" replace />;
  if (participant) return <TrialHome />;
  return <StudentClassesPage />;
}

/** A page that is one address for both roles: a class, or a reading in one.
 *  An instructor gets their view of it and a student theirs. A grader or a
 *  trial participant has no business there and goes home. */
export function ByRole({ instructor, student }: { instructor: ReactNode; student: ReactNode }) {
  const { data: user } = useMe();
  const participant = useIsParticipant();
  if (!user) return null;
  if (user.role === "instructor") return <>{instructor}</>;
  if (user.role === "student" && !participant) return <>{student}</>;
  return <Navigate to="/" replace />;
}

/** The grading page: the grader, and the research team. */
export function RequireGrader({ children }: { children: ReactNode }) {
  const { data: user } = useMe();
  if (user && user.role !== "grader" && user.role !== "instructor") {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}

export function RequireInstructor({ children }: { children: ReactNode }) {
  const { data: user } = useMe();
  if (user && user.role !== "instructor") return <Navigate to="/" replace />;
  return <>{children}</>;
}
