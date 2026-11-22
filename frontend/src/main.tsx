import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import App from "./App.tsx";
import "./index.css";

// A page left open across a release still runs the old build, whose lazily
// loaded files (the PDF viewer, for one) no longer exist on the server. Vite
// reports that here; reloading picks up the new build. Once per minute at most,
// so a file that is really missing cannot loop the page.
window.addEventListener("vite:preloadError", (event) => {
  const key = "senseei-reloaded-for-release";
  try {
    const last = Number(sessionStorage.getItem(key) || 0);
    if (Date.now() - last < 60_000) return;
    sessionStorage.setItem(key, String(Date.now()));
  } catch {
    return; // no storage, no guard: let the error show instead of risking a loop
  }
  event.preventDefault();
  window.location.reload();
});

const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchOnWindowFocus: false, retry: 1 } },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
);
