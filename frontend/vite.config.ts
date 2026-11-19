/// <reference types="vitest" />
import react from "@vitejs/plugin-react";
import path from "node:path";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  // API_CIBLE permet de viser un autre port quand 8000 est déjà pris par un autre projet.
  server: { proxy: { "/api": process.env.API_CIBLE ?? "http://127.0.0.1:8000" } },
  build: { chunkSizeWarningLimit: 900 },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
