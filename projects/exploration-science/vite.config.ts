import { defineConfig } from "vitest/config";

export default defineConfig({
  base: "./",
  // Three.js (~590 kB minified) and KaTeX (~270 kB) make up the main chunk.
  build: { chunkSizeWarningLimit: 950 },
  test: {
    include: ["tests/**/*.test.ts"],
  },
});
