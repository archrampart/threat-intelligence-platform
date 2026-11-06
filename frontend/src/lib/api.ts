import axios from "axios";

import { appConfig } from "@/config/env";

export const apiClient = axios.create({
  baseURL: appConfig.apiBaseUrl,
  // Session lives in httpOnly cookies (never readable by scripts)
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
    // CSRF guard: required by the backend for cookie-authenticated state changes
    "X-Requested-With": "XMLHttpRequest"
  },
  timeout: 30000
});

// One shared refresh at a time; concurrent 401s wait for it.
let refreshing: Promise<boolean> | null = null;

const refreshSession = (): Promise<boolean> => {
  if (!refreshing) {
    refreshing = apiClient
      .post("/auth/refresh", undefined, { _skipAuthRetry: true } as any)
      .then(() => true)
      .catch(() => false)
      .finally(() => {
        refreshing = null;
      });
  }
  return refreshing;
};

export const clearLocalSession = () => {
  localStorage.removeItem("user");
  // Tokens from older versions of the app
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
};

// Add response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    // Network error handling
    if (!error.response) {
      console.error("Network Error:", error.message);
      // Check if backend is reachable
      const isNetworkError = 
        error.code === "ECONNREFUSED" || 
        error.message?.includes("Network Error") ||
        error.message?.includes("timeout") ||
        error.code === "ERR_NETWORK";
      
      if (isNetworkError) {
        // Create a custom error that can be caught and handled gracefully
        const networkError: any = new Error("Backend server is not reachable. Please check if the backend is running.");
        networkError.isNetworkError = true;
        networkError.isSilent = true; // Flag for silent handling
        return Promise.reject(networkError);
      }
      return Promise.reject(error);
    }

    const original = error.config as any;
    const url: string = original?.url ?? "";
    if (error.response?.status === 401 && original && !original._skipAuthRetry && !url.includes("/auth/login")) {
      // Access cookie expired: rotate the session once and replay the request
      if (!original._retried && (await refreshSession())) {
        original._retried = true;
        return apiClient(original);
      }
      clearLocalSession();
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);
