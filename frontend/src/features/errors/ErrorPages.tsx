/** What shows instead of a page: an address the app does not know, or a page
 *  that crashed while rendering.
 *
 * Without these, React Router shows its own developer screen for both. "Back
 * to classes" goes home, `/`, which is the classes page for a student and an
 * instructor alike (and a participant's own screen in the trial).
 *
 * The crash screen has the wordmark alone, not the full top bar: the top bar
 * reads the account, and whatever just failed may be what it would need. */

import { isRouteErrorResponse, useNavigate, useRouteError } from "react-router-dom";

import { AppTopBar } from "../../components/AppTopBar";
import { Button } from "../../components/ui/button";

/** The catch-all route: an address that matches no page. */
export function NotFoundPage() {
  return (
    <div className="flex h-full flex-col">
      <AppTopBar />
      <Message
        title="Page not found"
        body="This page doesn't exist. Check the link, or go back to your classes."
      />
    </div>
  );
}

/** Every route's error element: a crash, or a 404 thrown along the way. */
export function RouteErrorPage() {
  const error = useRouteError();
  const missing = isRouteErrorResponse(error) && error.status === 404;
  return (
    <div className="flex h-full flex-col">
      <header className="flex h-14 shrink-0 items-center border-b px-4 sm:px-6">
        <span className="text-[15px] font-semibold tracking-[-0.01em]">
          SEN<span className="text-primary">SEE-I</span>
        </span>
      </header>
      {missing ? (
        <Message
          title="Page not found"
          body="This page doesn't exist. Check the link, or go back to your classes."
        />
      ) : (
        <Message
          title="Something went wrong"
          body="This page ran into a problem. Reload it, or go back to your classes."
          reload
        />
      )}
    </div>
  );
}

function Message({ title, body, reload = false }: { title: string; body: string; reload?: boolean }) {
  const navigate = useNavigate();
  return (
    <main className="flex flex-1 items-center justify-center p-6">
      <div className="flex w-full max-w-[420px] flex-col items-center text-center">
        <h1 className="text-[20px] font-semibold tracking-[-0.02em]">{title}</h1>
        <p className="mt-2 text-[14px] leading-[1.6] text-muted-foreground">{body}</p>
        <div className="mt-5 flex w-full flex-col-reverse gap-2 sm:w-auto sm:flex-row">
          {reload && (
            <Button
              variant="secondary"
              className="h-10 w-full sm:h-9 sm:w-auto"
              onClick={() => window.location.reload()}
            >
              Reload page
            </Button>
          )}
          {/* A full load rather than a client navigation after a crash, so
              whatever state broke the page does not come along. */}
          <Button
            className="h-10 w-full sm:h-9 sm:w-auto"
            onClick={() => (reload ? window.location.assign("/") : navigate("/"))}
          >
            Back to classes
          </Button>
        </div>
      </div>
    </main>
  );
}
