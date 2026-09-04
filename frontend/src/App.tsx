import { BrowserRouter, Route, Routes } from "react-router-dom";

import { ReadingListPage } from "./features/readings/ReadingListPage";
import { TutoringScreen } from "./features/tutoring/TutoringScreen";

// Two routes: the reading list (the app's home) and the tutoring screen, keyed
// by the reading the session is on. A router and the other screens (sign in,
// session review) arrive in later branches.
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ReadingListPage />} />
        <Route path="/tutor/:readingId" element={<TutoringScreen />} />
      </Routes>
    </BrowserRouter>
  );
}
