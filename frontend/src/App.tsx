import { BrowserRouter, Route, Routes } from "react-router-dom";

import { RequireAuth } from "./features/auth/RequireAuth";
import { HomeRoute, RequireInstructor } from "./features/auth/RoleRoutes";
import { ClassDetailPage } from "./features/classes/ClassDetailPage";
import { ClassListPage } from "./features/classes/ClassListPage";
import { SignInScreen } from "./features/auth/SignInScreen";
import { SessionReviewPage } from "./features/review/SessionReviewPage";
import { ReadingStepScreen } from "./features/tutoring/ReadingStepScreen";
import { TutoringScreen } from "./features/tutoring/TutoringScreen";

// The sign-in screen is open; every other route requires a session.
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<SignInScreen />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <HomeRoute />
            </RequireAuth>
          }
        />
        {/* The reading step comes before the session and creates nothing; the
            session row is written when /tutor is reached. */}
        <Route
          path="/read/:readingId"
          element={
            <RequireAuth>
              <ReadingStepScreen />
            </RequireAuth>
          }
        />
        <Route
          path="/tutor/:readingId"
          element={
            <RequireAuth>
              <TutoringScreen />
            </RequireAuth>
          }
        />
        <Route
          path="/classes"
          element={
            <RequireAuth>
              <RequireInstructor>
                <ClassListPage />
              </RequireInstructor>
            </RequireAuth>
          }
        />
        <Route
          path="/classes/:classId"
          element={
            <RequireAuth>
              <RequireInstructor>
                <ClassDetailPage />
              </RequireInstructor>
            </RequireAuth>
          }
        />
        <Route
          path="/review/:sessionId"
          element={
            <RequireAuth>
              <SessionReviewPage />
            </RequireAuth>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
