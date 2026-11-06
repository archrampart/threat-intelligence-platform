import { Navigate, Route, Routes } from "react-router-dom";

import AppLayout from "@/components/layout/AppLayout";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import DashboardPage from "@/features/dashboard/DashboardPage";
import IocSearchPage from "@/features/ioc/IocSearchPage";
import DarkWebPage from "@/features/darkweb/DarkWebPage";
import CvePage from "@/features/cve/CvePage";
import WatchlistPage from "@/features/watchlist/WatchlistPage";
import ReportsPage from "@/features/reports/ReportsPage";
import APIKeysPage from "@/features/api-keys/APIKeysPage";
import UsersPage from "@/features/users/UsersPage";
import AlertsPage from "@/features/alerts/AlertsPage";
import LoginPage from "@/features/auth/LoginPage";

const App = () => {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <AppLayout>
              <Routes>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/ioc" element={<IocSearchPage />} />
                <Route path="/darkweb" element={<DarkWebPage />} />
                <Route path="/cves" element={<CvePage />} />
                <Route path="/watchlist" element={<WatchlistPage />} />
                <Route path="/reports" element={<ReportsPage />} />
                <Route path="/api-keys" element={<APIKeysPage />} />
                <Route path="/users" element={<UsersPage />} />
                <Route path="/alerts" element={<AlertsPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </AppLayout>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
};

export default App;
