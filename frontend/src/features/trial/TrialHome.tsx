/** Where a participant lands after signing in: straight into their group's
 * screen, or with tests into whichever stage the server says they are in. There
 * is no reading list; a participant has one reading.
 *
 * A reload lands here too, so it sends them back where they were: the session
 * if they started one, the reading if not. The control groups each have a
 * single screen, which a reload simply reopens. */

import { Navigate } from "react-router-dom";

import { useTrialStatus } from "./useTrial";

export function TrialHome() {
  const { data, isLoading, isError } = useTrialStatus();

  if (isLoading) return <Notice>Loading&hellip;</Notice>;
  if (isError || !data) return <Notice>Something went wrong. Please ask for help.</Notice>;

  if (!data.reading_id) {
    return <Notice>No reading yet. Please wait for the next instructions.</Notice>;
  }
  // With tests, the pre-test comes before the reading and the post-test after it.
  if (data.test_stage === "pretest") return <Navigate to="/pretest" replace />;
  if (data.test_stage === "posttest_ready" || data.test_stage === "posttest") {
    return <Navigate to="/posttest" replace />;
  }
  if (data.test_stage === "done") return <Navigate to="/finished" replace />;
  // The control groups have one screen each, which shows its own ending.
  if (data.mode === "chatbot") return <Navigate to={`/chat/${data.reading_id}`} replace />;
  if (data.mode === "reading_only") {
    return <Navigate to={`/reading/${data.reading_id}`} replace />;
  }
  if (data.session) return <Navigate to={`/tutor/${data.reading_id}`} replace />;
  if (data.time_up) return <Notice>Time&rsquo;s up. Please wait for the next instructions.</Notice>;
  return <Navigate to={`/read/${data.reading_id}`} replace />;
}

function Notice({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-full items-center justify-center px-6 text-center text-[14px] text-muted-foreground">
      {children}
    </div>
  );
}
