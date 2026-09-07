import { BrowserRouter, Route, Routes } from "react-router-dom";

import { ReadingListPage } from "./features/readings/ReadingListPage";
import { SessionReviewPage } from "./features/review/SessionReviewPage";
import { TutoringScreen } from "./features/tutoring/TutoringScreen";

// The reading list (home), the tutoring screen keyed by its reading, and the
// read-only review of a past session. Sign in arrives in a later branch.
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ReadingListPage />} />
        <Route path="/tutor/:readingId" element={<TutoringScreen />} />
        <Route path="/review/:sessionId" element={<SessionReviewPage />} />
      </Routes>
    </BrowserRouter>
  );
}
