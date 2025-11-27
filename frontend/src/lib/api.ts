import axios from "axios";

import { appConfig } from "@/config/env";

// Determine base URL: 
// - In Docker: VITE_API_BASE_URL=/api/v1 (already includes /api/v1)
// - In local dev: VITE_API_BASE_URL=http://127.0.0.1:8000 (needs /api/v1 added)
const getBaseURL = () => {
  const baseUrl = appConfig.apiBaseUrl;
  // If it's a full URL (starts with http), add /api/v1
  if (baseUrl.startsWith("http")) {
    return baseUrl + "/api/v1";
  }
  // Otherwise assume it's already the full path (like /api/v1 in Docker)
  return baseUrl;
};

export const apiClient = axios.create({
  baseURL: getBaseURL(),
  headers: {
    "Content-Type": "application/json"
  },
  timeout: 30000 // 30 seconds timeout
});

// Add request interceptor to log requests and ensure auth token is set
apiClient.interceptors.request.use(
  (config) => {
    // Ensure auth token is set from localStorage
    const token = localStorage.getItem("access_token");
    if (token && !config.headers.Authorization) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // Don't override Content-Type if it's already set explicitly (e.g., for form data)
    // Only set default JSON Content-Type if not already set
    if (!config.headers["Content-Type"] && !config.headers["content-type"]) {
      config.headers["Content-Type"] = "application/json";
    }
    
    // Log request for debugging (only in development)
    if (import.meta.env.DEV) {
      console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`, {
        contentType: config.headers["Content-Type"] || config.headers["content-type"],
      });
    }
    
    return config;
  },
  (error) => {
    console.error("[API Request Error]", error);
    return Promise.reject(error);
  }
);

// Add response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
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

    if (error.response?.status === 401) {
      // Unauthorized - clear auth and redirect to login
      // But don't redirect if we're already on login page
      const currentPath = window.location.pathname;
      if (currentPath !== "/login") {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("user");
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export const setAuthToken = (token?: string) => {
  if (token) {
    apiClient.defaults.headers.common.Authorization = `Bearer ${token}`;
  } else {
    delete apiClient.defaults.headers.common.Authorization;
  }
};
