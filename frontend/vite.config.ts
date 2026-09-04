import path from "node:path";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Production is one service, one origin, no CORS (see docs/context/tech-stack.md).
// In development the frontend runs on Vite's own port, so it proxies API calls to
// the backend instead, which keeps the same-origin assumption true here too: the
// browser only ever talks to localhost:5173.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: {
    port: 5173,
    proxy: {
      "/sessions": { target: "http://localhost:8000", changeOrigin: true },
      "/health": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
  },
});
