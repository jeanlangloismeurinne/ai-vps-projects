import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  base: "./",
  plugins: [react()],
  // Three.js (~590 kB minified) and KaTeX (~270 kB) make up the main chunk.
  build: {
    chunkSizeWarningLimit: 950,
    // Phase 0 prototype (index.html) and the V2 app (v2.html, roadmap/v2.md) side by side.
    rollupOptions: { input: { main: "index.html", v2: "v2.html" } },
  },
  test: {
    include: ["tests/**/*.test.ts"],
  },
});
