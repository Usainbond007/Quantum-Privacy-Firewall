import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig(({ mode }) => {
  const apiTarget =
    loadEnv(mode, ".", "VITE_").VITE_API_PROXY_TARGET ||
    "http://127.0.0.1:8567";

  return {
    base: "./",
    plugins: [react(), tailwindcss()],
    server: {
      proxy: {
        "/api": apiTarget,
        "/docs": apiTarget,
        "/openapi.json": apiTarget,
      },
    },
  };
});
