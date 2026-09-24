import type { ReactNode } from "react";
import { RouterProvider, createBrowserRouter } from "react-router-dom";

import { RequireAuth } from "./features/auth/RequireAuth";
import { HomeRoute, RequireInstructor } from "./features/auth/RoleRoutes";
import { ClassDetailPage } from "./features/classes/ClassDetailPage";
import { ClassReadingPage } from "./features/classes/ClassReadingPage";
import { ClassListPage } from "./features/classes/ClassListPage";
import { SignInScreen } from "./features/auth/SignInScreen";
import { LibraryListPage } from "./features/library/LibraryListPage";
import { LibraryReadingPage } from "./features/library/LibraryReadingPage";
import { UploadReadingPage } from "./features/library/UploadReadingPage";
import { SessionReviewPage } from "./features/review/SessionReviewPage";
import { ReadingStepScreen } from "./features/tutoring/ReadingStepScreen";
import { TutoringScreen } from "./features/tutoring/TutoringScreen";

const signedIn = (page: ReactNode) => <RequireAuth>{page}</RequireAuth>;
const instructor = (page: ReactNode) => signedIn(<RequireInstructor>{page}</RequireInstructor>);

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
  // The reading step comes before the session and creates nothing; the session
  // row is written when /tutor is reached.
  { path: "/read/:readingId", element: signedIn(<ReadingStepScreen />) },
  { path: "/tutor/:readingId", element: signedIn(<TutoringScreen />) },
  { path: "/review/:sessionId", element: signedIn(<SessionReviewPage />) },
  { path: "/classes", element: instructor(<ClassListPage />) },
  { path: "/classes/:classId", element: instructor(<ClassDetailPage />) },
  {
    path: "/classes/:classId/readings/:readingId",
    element: instructor(<ClassReadingPage />),
  },
  { path: "/library", element: instructor(<LibraryListPage />) },
  { path: "/library/new", element: instructor(<UploadReadingPage />) },
  { path: "/library/:readingId", element: instructor(<LibraryReadingPage />) },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
