import path from "node:path";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  // The browser always talks to the dev server (same origin, so session cookies work);
  // VITE_API_BASE_URL only says where the dev server forwards /api/ requests.
  const apiTarget = (env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/api\/v1\/?$/, "");

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        "@": path.resolve(import.meta.dirname, "./src")
      }
    },
    server: {
      port: 5173,
      // Vite serves index.html for client-side routes by default (SPA fallback)
      proxy: {
        // Trailing slash matters: "/api" would also capture SPA routes such as /api-keys
        "/api/": {
          target: apiTarget.startsWith("http") ? apiTarget : "http://127.0.0.1:8000",
          changeOrigin: true
        }
      }
    },
    build: {
      sourcemap: false,
      chunkSizeWarningLimit: 900,
      rollupOptions: {
        output: {
          manualChunks(id: string) {
            if (!id.includes("node_modules")) return undefined;
            if (id.includes("recharts") || id.includes("d3-")) return "charts";
            if (id.includes("leaflet")) return "map";
            if (id.includes("react")) return "react";
            return "vendor";
          }
        }
      }
    }
  };
});
