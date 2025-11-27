import path from "path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const resolvePath = (str: string) => path.resolve(__dirname, str);

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    // Custom plugin to handle React Router history mode
    {
      name: "history-api-fallback",
      configureServer(server) {
        // This middleware runs early in the chain
        // It intercepts non-API routes and serves index.html
        server.middlewares.use((req, res, next) => {
          const url = req.url || "";
          
          // CRITICAL: Only proxy actual API routes (/api/v1/*)
          // All other routes should serve index.html for React Router
          if (url.startsWith("/api/v1/")) {
            // This is an API request - let proxy handle it
            return next();
          }
          
          // Also allow /docs and /openapi.json (FastAPI docs)
          if (url.startsWith("/docs") || url.startsWith("/openapi.json")) {
            return next();
          }
          
          // If request is for a static file (has extension), let it through
          if (/\.\w+$/.test(url) && !url.endsWith(".html")) {
            return next();
          }
          
          // If request is for Vite HMR or other Vite internal routes, let it through
          if (url.startsWith("/@") || url.startsWith("/node_modules") || url.startsWith("/src") || url.startsWith("/vite") || url.startsWith("/assets")) {
            return next();
          }
          
          // For all other routes (including /api-keys, /dashboard, etc.), serve index.html
          // React Router will handle the routing on the client side
          req.url = "/index.html";
          next();
        });
      }
    }
  ],
  resolve: {
    alias: {
      "@": resolvePath("./src")
    }
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        // Only proxy requests that actually start with /api/
        configure: (proxy, _options) => {
          proxy.on("error", (err, _req, res) => {
            console.log("proxy error", err);
          });
        }
      }
    }
  }
});
