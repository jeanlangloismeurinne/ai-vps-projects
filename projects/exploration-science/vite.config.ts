import { defineConfig } from "vitest/config";

export default defineConfig({
  base: "./",
  // Three.js alone weighs ~590 kB minified; split it out when the bundle grows.
  build: { chunkSizeWarningLimit: 700 },
  test: {
    include: ["tests/**/*.test.ts"],
  },
});
