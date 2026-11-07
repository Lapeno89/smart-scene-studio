import { resolve } from "node:path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  build: {
    target: "es2022",
    cssCodeSplit: false,
    emptyOutDir: true,
    lib: {
      entry: resolve(import.meta.dirname, "src/panel.ts"),
      formats: ["es"],
      fileName: () => "smart-scene-studio.js",
    },
    outDir: resolve(
      import.meta.dirname,
      "../custom_components/smart_scene_studio/frontend/dist",
    ),
    rollupOptions: {
      output: { inlineDynamicImports: true },
    },
  },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.ts"],
    clearMocks: true,
    restoreMocks: true,
  },
});
