import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { apiClient, clearLocalSession } from "@/lib/api";
import type { UserResponse } from "@/features/auth/types";

/**
 * Session state for the UI. Credentials live in httpOnly cookies; only the
 * (non-secret) user profile is cached in localStorage to render the shell quickly.
 * Any 401 from the API triggers a refresh or a redirect to /login (see lib/api.ts).
 */
export const useAuth = () => {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    // Remove tokens stored by older versions of the app
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    const userStr = localStorage.getItem("user");
    if (userStr) {
      try {
        setUser(JSON.parse(userStr));
      } catch {
        localStorage.removeItem("user");
      }
    }
    setIsLoading(false);
  }, []);

  const login = (userData: UserResponse) => {
    localStorage.setItem("user", JSON.stringify(userData));
    setUser(userData);
  };

  const logout = async () => {
    try {
      await apiClient.post("/auth/logout");
    } catch {
      // ignore: cookies are cleared server side when possible
    }
    clearLocalSession();
    setUser(null);
    navigate("/login");
  };

  return {
    user,
    isLoading,
    isAuthenticated: !!user,
    login,
    logout
  };
};
