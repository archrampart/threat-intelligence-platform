const fallbackApiUrl = "http://127.0.0.1:8000";

export const appConfig = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || fallbackApiUrl,
  env: import.meta.env.MODE || "development"
};
