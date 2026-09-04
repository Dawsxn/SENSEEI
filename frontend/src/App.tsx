import { TutoringScreen } from "./features/tutoring/TutoringScreen";

// The tutoring screen is the whole app for now; it carries its own top bar. A
// router and the other screens (reading list, sign in) arrive in later branches.
export default function App() {
  return <TutoringScreen />;
}
