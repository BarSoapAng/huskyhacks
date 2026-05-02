import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

function normalizeBackendUrl(value: string | undefined) {
  return (value || "http://127.0.0.1:8000").replace(/\/+$/, "");
}

export default defineConfig(({ mode }) => {
  const rootEnv = loadEnv(mode, "..", "");
  const webEnv = loadEnv(mode, ".", "");
  const backendUrl = normalizeBackendUrl(
    webEnv.VITE_BACKEND_URL ||
      rootEnv.VITE_BACKEND_URL ||
      rootEnv.EXTENSION_PORT
  );

  return {
    plugins: [react()],
    define: {
      __BACKEND_URL__: JSON.stringify(backendUrl)
    },
    server: {
      port: 5173
    }
  };
});
