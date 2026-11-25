import type { ReactNode } from "react";
import { RouterProvider, createBrowserRouter } from "react-router-dom";

import { RequireAuth } from "./features/auth/RequireAuth";
import { ByRole, HomeRoute, RequireGrader, RequireInstructor } from "./features/auth/RoleRoutes";
import { ClassDetailPage } from "./features/classes/ClassDetailPage";
import { ClassReadingPage } from "./features/classes/ClassReadingPage";
import { ClassListPage } from "./features/classes/ClassListPage";
import { SignInScreen } from "./features/auth/SignInScreen";
import { HowItWorks } from "./features/intro/HowItWorks";
import { LibraryListPage } from "./features/library/LibraryListPage";
import { LibraryReadingPage } from "./features/library/LibraryReadingPage";
import { StudentClassPage } from "./features/readings/StudentClassPage";
import { StudentReadingPage } from "./features/readings/StudentReadingPage";
import { UploadReadingPage } from "./features/library/UploadReadingPage";
import { OldReviewLink, SessionReviewPage } from "./features/review/SessionReviewPage";
import { ReadingStepScreen } from "./features/tutoring/ReadingStepScreen";
import { TutoringScreen } from "./features/tutoring/TutoringScreen";
import { BatchPage } from "./features/trial/BatchPage";
import { ChatbotScreen, ReadingOnlyScreen } from "./features/trial/ControlGroupScreens";
import { GradingPage } from "./features/trial/GradingPage";
import { ParticipantsPage } from "./features/trial/ParticipantsPage";
import { PostTestScreen, PreTestScreen, TestDoneScreen } from "./features/trial/TestScreens";

const signedIn = (page: ReactNode) => <RequireAuth>{page}</RequireAuth>;
const instructor = (page: ReactNode) => signedIn(<RequireInstructor>{page}</RequireInstructor>);
const grader = (page: ReactNode) => signedIn(<RequireGrader>{page}</RequireGrader>);

// A data router rather than <BrowserRouter>, because only a data router can hold
// a navigation back: the upload page asks before discarding unsaved work.
//
// The instructor's reading pages live at /library, not /readings, which is the
// students' API. Pages and API share one origin, so a page path that is also an
// API path answers a refresh with JSON (docs/context/tech-stack.md).
const router = createBrowserRouter([
  // The sign-in screen is open; every other route requires a session.
  { path: "/login", element: <SignInScreen /> },
  { path: "/", element: signedIn(<HomeRoute />) },
  // The SEE-I walkthrough: before a student's first session, and from the help icon.
  { path: "/how-it-works", element: signedIn(<HowItWorks />) },
  // The reading step comes before the session and creates nothing; the session
  // row is written when /tutor is reached.
  { path: "/read/:readingId", element: signedIn(<ReadingStepScreen />) },
  { path: "/tutor/:readingId", element: signedIn(<TutoringScreen />) },
  // Sessions moved under their reading; an old link finds its new address.
  { path: "/review/:sessionId", element: signedIn(<OldReviewLink />) },
  { path: "/classes", element: instructor(<ClassListPage />) },
  // A class and a reading in it share one address across roles; a student's
  // list of classes is their home, `/`.
  {
    path: "/classes/:classId",
    element: signedIn(<ByRole instructor={<ClassDetailPage />} student={<StudentClassPage />} />),
  },
  {
    path: "/classes/:classId/readings/:readingId",
    element: signedIn(
      <ByRole instructor={<ClassReadingPage />} student={<StudentReadingPage />} />,
    ),
  },
  {
    path: "/classes/:classId/readings/:readingId/sessions/:sessionId",
    element: signedIn(
      <ByRole instructor={<SessionReviewPage />} student={<SessionReviewPage />} />,
    ),
  },
  { path: "/library", element: instructor(<LibraryListPage />) },
  { path: "/library/new", element: instructor(<UploadReadingPage />) },
  { path: "/library/:readingId", element: instructor(<LibraryReadingPage />) },
  // Trial mode only; the API under them answers 404 anywhere else.
  { path: "/participants", element: instructor(<ParticipantsPage />) },
  { path: "/participants/:batchId", element: instructor(<BatchPage />) },
  // The trial's control groups. A participant lands on theirs from `/`.
  { path: "/chat/:readingId", element: signedIn(<ChatbotScreen />) },
  { path: "/reading/:readingId", element: signedIn(<ReadingOnlyScreen />) },
  // The pre-test and post-test, for a class that has them, and the screen after.
  { path: "/pretest", element: signedIn(<PreTestScreen />) },
  { path: "/posttest", element: signedIn(<PostTestScreen />) },
  { path: "/finished", element: signedIn(<TestDoneScreen />) },
  // Grading the tests: the research team and the grader. `?id=` opens one ID.
  { path: "/grading", element: grader(<GradingPage />) },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
