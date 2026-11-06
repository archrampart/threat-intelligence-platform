/**
 * API base URL used by the browser.
 *
 * Authentication uses httpOnly SameSite=Strict cookies, so the API must be same-origin:
 * - development: always "/api/v1", forwarded by the Vite dev server (VITE_API_BASE_URL is
 *   the proxy target, see vite.config.ts)
 * - production / Docker: "/api/v1" behind nginx (or a full URL on the same site)
 */
const configured = import.meta.env.VITE_API_BASE_URL as string | undefined;

const resolveApiBaseUrl = (): string => {
  if (import.meta.env.DEV || !configured) return "/api/v1";
  return configured.startsWith("http") ? `${configured.replace(/\/$/, "")}/api/v1` : configured;
};

export const appConfig = {
  apiBaseUrl: resolveApiBaseUrl(),
  env: import.meta.env.MODE || "development"
};
