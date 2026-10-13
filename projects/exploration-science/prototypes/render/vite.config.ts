// Build of the render prototypes alone, every asset inlined, for a one-page preview.
import { resolve } from "node:path";
import { defineConfig } from "vite";

export default defineConfig({
  root: import.meta.dirname,
  base: "./",
  build: {
    outDir: resolve(import.meta.dirname, "../../dist-prototypes"),
    emptyOutDir: true,
    assetsInlineLimit: () => true,
    chunkSizeWarningLimit: 20000,
    rollupOptions: { output: { inlineDynamicImports: true } },
  },
  assetsInclude: ["**/*.hdr", "**/*.glb"],
});
