import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { Shield, LogIn } from "lucide-react";

import { apiClient, setAuthToken } from "@/lib/api";
import { appConfig } from "@/config/env";
import { useAuth } from "@/hooks/useAuth";
import type { LoginRequest, TokenResponse, UserResponse } from "@/features/auth/types";

const LoginPage = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const loginMutation = useMutation({
    mutationFn: async (payload: LoginRequest) => {
      // OAuth2PasswordRequestForm expects application/x-www-form-urlencoded
      // Use fetch API directly to avoid axios Content-Type issues
      const formData = new URLSearchParams();
      formData.append("username", payload.username);
      formData.append("password", payload.password);

      // Handle both full URLs (local dev) and paths (Docker)
      let baseURL = appConfig.apiBaseUrl;
      if (baseURL.startsWith("http")) {
        baseURL = baseURL + "/api/v1";
      }
      const response = await fetch(`${baseURL}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: formData.toString(),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Login failed" }));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const data: TokenResponse = await response.json();
      return data;
    },
    onSuccess: async (data) => {
      // Store tokens
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
      setAuthToken(data.access_token);

      // Get user info
      try {
        const userResponse = await apiClient.get<UserResponse>("/auth/me");
        login(data.access_token, userResponse.data);
        navigate("/");
      } catch (err) {
        console.error("Failed to get user info:", err);
        setError("Failed to get user information");
      }
    },
    onError: (err: unknown) => {
      setError(err instanceof Error ? err.message : "Login failed");
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    loginMutation.mutate({ username, password });
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 dark:bg-slate-950 light:bg-slate-50 px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mb-4 flex justify-center">
            <div className="rounded-2xl bg-brand-500/20 dark:bg-brand-500/20 light:bg-brand-100 p-4">
              <Shield className="h-8 w-8 text-brand-400 dark:text-brand-400 light:text-brand-600" />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-white dark:text-white light:text-slate-900">ARCHRAMPART</h1>
          <p className="mt-2 text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">Threat Intelligence Hub</p>
        </div>

        <form onSubmit={handleSubmit} className="rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/40 dark:bg-slate-900/40 light:bg-white p-8">
          <h2 className="mb-6 text-xl font-semibold text-white dark:text-white light:text-slate-900">Sign In</h2>

          {error && (
            <div className="mb-4 rounded-lg border border-red-800 dark:border-red-800 light:border-red-300 bg-red-950/20 dark:bg-red-950/20 light:bg-red-50 p-3 text-sm text-red-400 dark:text-red-400 light:text-red-700">
              {error}
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 placeholder:text-slate-500 dark:placeholder:text-slate-500 light:placeholder:text-slate-400 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
                placeholder="Enter your username"
                required
                autoFocus
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 placeholder:text-slate-500 dark:placeholder:text-slate-500 light:placeholder:text-slate-400 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
                placeholder="Enter your password"
                required
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loginMutation.isPending}
            className="mt-6 flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 dark:bg-brand-600 light:bg-brand-500 px-4 py-2 font-medium text-white transition hover:bg-brand-700 dark:hover:bg-brand-700 light:hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <LogIn className="h-4 w-4" />
            {loginMutation.isPending ? "Signing in..." : "Sign In"}
          </button>

        </form>
      </div>
    </div>
  );
};

export default LoginPage;

