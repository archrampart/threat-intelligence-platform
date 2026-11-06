import { Navigate } from "react-router-dom";
import type { PropsWithChildren } from "react";

import { useAuth } from "@/hooks/useAuth";

const ProtectedRoute = ({ children }: PropsWithChildren) => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 dark:bg-slate-950 light:bg-white">
        <div className="text-center">
          <p className="text-slate-400 dark:text-slate-400 light:text-slate-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;

