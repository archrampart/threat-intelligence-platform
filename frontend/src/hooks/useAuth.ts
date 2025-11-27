import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { setAuthToken } from "@/lib/api";
import type { UserResponse } from "@/features/auth/types";

export const useAuth = () => {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    const userStr = localStorage.getItem("user");

    if (token && userStr) {
      setAuthToken(token);
      try {
        setUser(JSON.parse(userStr));
      } catch (e) {
        console.error("Failed to parse user data:", e);
        localStorage.removeItem("user");
        localStorage.removeItem("access_token");
      }
    }
    setIsLoading(false);
  }, []);

  const login = (token: string, userData: UserResponse) => {
    localStorage.setItem("access_token", token);
    localStorage.setItem("user", JSON.stringify(userData));
    setAuthToken(token);
    setUser(userData);
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
    setAuthToken(undefined);
    setUser(null);
    navigate("/login");
  };

  const isAuthenticated = !!user && !!localStorage.getItem("access_token");

  return {
    user,
    isLoading,
    isAuthenticated,
    login,
    logout
  };
};

