import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Bell, BellOff, CheckCircle2, Filter, Trash2, X, Circle } from "lucide-react";
import { apiClient } from "@/lib/api";
import type { Alert, AlertListResponse, AlertStatsResponse } from "./types";
import { AlertSeverity, AlertType } from "./types";

const AlertsPage = () => {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [isReadFilter, setIsReadFilter] = useState<boolean | null>(null);
  const [severityFilter, setSeverityFilter] = useState<AlertSeverity | "">("");
  const [typeFilter, setTypeFilter] = useState<AlertType | "">("");
  const pageSize = 20;

  const { data: stats, error: statsError } = useQuery<AlertStatsResponse>({
    queryKey: ["alerts", "stats"],
    queryFn: async () => {
      try {
        const response = await apiClient.get("/alerts/stats");
        return response.data;
      } catch (error: any) {
        console.error("Error fetching alert stats:", error);
        throw error;
      }
    },
    retry: 1,
  });

  const { data, isLoading, error: alertsError } = useQuery<AlertListResponse>({
    queryKey: ["alerts", page, isReadFilter, severityFilter, typeFilter],
    queryFn: async () => {
      try {
        const params = new URLSearchParams();
        if (isReadFilter !== null) params.set("is_read", String(isReadFilter));
        if (severityFilter) params.set("severity", severityFilter);
        if (typeFilter) params.set("alert_type", typeFilter);
        params.set("page", String(page));
        params.set("page_size", String(pageSize));
        
        const response = await apiClient.get(`/alerts/?${params.toString()}`);
        return response.data;
      } catch (error: any) {
        console.error("Error fetching alerts:", error);
        throw error;
      }
    },
    retry: 1,
  });

  const markAsReadMutation = useMutation({
    mutationFn: async (alertId: string) => {
      await apiClient.put(`/alerts/${alertId}/read`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
    },
  });

  const markAsUnreadMutation = useMutation({
    mutationFn: async (alertId: string) => {
      await apiClient.put(`/alerts/${alertId}/unread`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
    },
  });

  const markAllAsReadMutation = useMutation({
    mutationFn: async () => {
      try {
        const response = await apiClient.post("/alerts/read-all");
        return response.data;
      } catch (error: any) {
        console.error("API Error:", error);
        throw error;
      }
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      // Show success message if data contains count
      if (data && typeof data === 'object' && 'count' in data) {
        const count = data.count || 0;
        console.log(`Successfully marked ${count} alerts as read`);
      }
    },
    onError: (error: any) => {
      console.error("Error marking all alerts as read:", error);
      let errorMessage = "Failed to mark all alerts as read. Please try again.";
      
      if (error?.response?.data) {
        if (typeof error.response.data === 'string') {
          errorMessage = error.response.data;
        } else if (error.response.data.detail) {
          errorMessage = typeof error.response.data.detail === 'string' 
            ? error.response.data.detail 
            : JSON.stringify(error.response.data.detail);
        } else if (error.response.data.message) {
          errorMessage = typeof error.response.data.message === 'string'
            ? error.response.data.message
            : JSON.stringify(error.response.data.message);
        }
      } else if (error?.message) {
        errorMessage = typeof error.message === 'string' ? error.message : JSON.stringify(error.message);
      }
      
      alert(errorMessage);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (alertId: string) => {
      await apiClient.delete(`/alerts/${alertId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
    },
  });

  const getSeverityColor = (severity: AlertSeverity) => {
    switch (severity) {
      case AlertSeverity.CRITICAL:
        return "text-red-400 dark:text-red-400 light:text-red-600 bg-red-950/30 dark:bg-red-950/30 light:bg-red-50 border-red-800 dark:border-red-800 light:border-red-300";
      case AlertSeverity.HIGH:
        return "text-orange-400 dark:text-orange-400 light:text-orange-600 bg-orange-950/30 dark:bg-orange-950/30 light:bg-orange-50 border-orange-800 dark:border-orange-800 light:border-orange-300";
      case AlertSeverity.MEDIUM:
        return "text-yellow-400 dark:text-yellow-400 light:text-yellow-600 bg-yellow-950/30 dark:bg-yellow-950/30 light:bg-yellow-50 border-yellow-800 dark:border-yellow-800 light:border-yellow-300";
      case AlertSeverity.LOW:
        return "text-green-400 dark:text-green-400 light:text-green-600 bg-green-950/30 dark:bg-green-950/30 light:bg-green-50 border-green-800 dark:border-green-800 light:border-green-300";
      default:
        return "text-slate-400 dark:text-slate-400 light:text-slate-600 bg-slate-900/30 dark:bg-slate-900/30 light:bg-slate-50 border-slate-800 dark:border-slate-800 light:border-slate-200";
    }
  };

  const getTypeLabel = (type: AlertType) => {
    switch (type) {
      case AlertType.WATCHLIST:
        return "Watchlist";
      case AlertType.IOC_QUERY:
        return "IOC Query";
      case AlertType.CVE:
        return "CVE";
      case AlertType.SYSTEM:
        return "System";
      default:
        return type;
    }
  };

  // Show error message if there's an error
  if (alertsError || statsError) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white dark:text-white light:text-slate-900">Alerts</h1>
          <p className="mt-1 text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">
            Security alerts and notifications
          </p>
        </div>
        <div className="rounded-lg border border-red-800 dark:border-red-800 light:border-red-300 bg-red-950/20 dark:bg-red-950/20 light:bg-red-50 p-4">
          <p className="text-red-400 dark:text-red-400 light:text-red-600">
            {alertsError?.message || statsError?.message || "Error loading alerts. Please try again."}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white dark:text-white light:text-slate-900">Alerts</h1>
          <p className="mt-1 text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">
            Security alerts and notifications
          </p>
        </div>
        {stats && stats.unread > 0 && (
          <button
            onClick={() => markAllAsReadMutation.mutate()}
            disabled={markAllAsReadMutation.isPending}
            className="flex items-center gap-2 rounded-lg bg-brand-600 hover:bg-brand-700 text-white dark:text-white light:text-white px-4 py-2 text-sm font-medium transition disabled:opacity-50"
          >
            <CheckCircle2 className="h-4 w-4" />
            Mark All Read
          </button>
        )}
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid gap-4 md:grid-cols-4">
          <div className="rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-950/60 dark:bg-slate-950/60 light:bg-slate-50 p-4">
            <p className="text-xs text-slate-500 dark:text-slate-500 light:text-slate-500">Total Alerts</p>
            <p className="text-2xl font-bold text-white dark:text-white light:text-slate-900">{stats.total}</p>
          </div>
          <div className="rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-950/60 dark:bg-slate-950/60 light:bg-slate-50 p-4">
            <p className="text-xs text-slate-500 dark:text-slate-500 light:text-slate-500">Unread</p>
            <p className="text-2xl font-bold text-red-400 dark:text-red-400 light:text-red-600">{stats.unread}</p>
          </div>
          <div className="rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-950/60 dark:bg-slate-950/60 light:bg-slate-50 p-4">
            <p className="text-xs text-slate-500 dark:text-slate-500 light:text-slate-500">High/Critical</p>
            <p className="text-2xl font-bold text-orange-400 dark:text-orange-400 light:text-orange-600">
              {(stats.by_severity?.high || 0) + (stats.by_severity?.critical || 0)}
            </p>
          </div>
          <div className="rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-950/60 dark:bg-slate-950/60 light:bg-slate-50 p-4">
            <p className="text-xs text-slate-500 dark:text-slate-500 light:text-slate-500">Watchlist</p>
            <p className="text-2xl font-bold text-white dark:text-white light:text-slate-900">
              {stats.by_type?.watchlist || 0}
            </p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/40 dark:bg-slate-900/40 light:bg-white p-4">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-slate-400 dark:text-slate-400 light:text-slate-600" />
            <span className="text-sm font-medium text-white dark:text-white light:text-slate-900">Filters:</span>
          </div>
          
          <select
            value={isReadFilter === null ? "" : String(isReadFilter)}
            onChange={(e) => setIsReadFilter(e.target.value === "" ? null : e.target.value === "true")}
            className="rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-3 py-1.5 text-sm text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
          >
            <option value="">All</option>
            <option value="false">Unread</option>
            <option value="true">Read</option>
          </select>

          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value as AlertSeverity | "")}
            className="rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-3 py-1.5 text-sm text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
          >
            <option value="">All Severities</option>
            <option value={AlertSeverity.CRITICAL}>Critical</option>
            <option value={AlertSeverity.HIGH}>High</option>
            <option value={AlertSeverity.MEDIUM}>Medium</option>
            <option value={AlertSeverity.LOW}>Low</option>
          </select>

          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value as AlertType | "")}
            className="rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-3 py-1.5 text-sm text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
          >
            <option value="">All Types</option>
            <option value={AlertType.WATCHLIST}>Watchlist</option>
            <option value={AlertType.IOC_QUERY}>IOC Query</option>
            <option value={AlertType.CVE}>CVE</option>
            <option value={AlertType.SYSTEM}>System</option>
          </select>

          {(isReadFilter !== null || severityFilter || typeFilter) && (
            <button
              onClick={() => {
                setIsReadFilter(null);
                setSeverityFilter("");
                setTypeFilter("");
              }}
              className="flex items-center gap-1 rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white px-2 py-1 text-xs text-slate-400 dark:text-slate-400 light:text-slate-600 hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100"
            >
              <X className="h-3 w-3" />
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Alerts List */}
      {isLoading ? (
        <div className="py-12 text-center text-slate-400 dark:text-slate-400 light:text-slate-600">
          Loading alerts...
        </div>
      ) : data && data.items.length > 0 ? (
        <div className="space-y-3">
          {data.items.map((alert) => (
            <div
              key={alert.id}
              className={`rounded-lg border ${
                alert.is_read
                  ? "border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/40 dark:bg-slate-900/40 light:bg-slate-50"
                  : "border-brand-600 dark:border-brand-600 light:border-brand-500 bg-brand-950/20 dark:bg-brand-950/20 light:bg-brand-50"
              } p-4`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="mb-2 flex items-center gap-2">
                    {!alert.is_read && (
                      <span className="h-2 w-2 rounded-full bg-brand-400 dark:bg-brand-400 light:bg-brand-600" />
                    )}
                    <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${getSeverityColor(alert.severity)}`}>
                      {alert.severity.toUpperCase()}
                    </span>
                    <span className="rounded bg-slate-800 dark:bg-slate-800 light:bg-slate-200 px-2 py-0.5 text-xs text-slate-400 dark:text-slate-400 light:text-slate-600">
                      {getTypeLabel(alert.alert_type)}
                    </span>
                    <span className="text-xs text-slate-500 dark:text-slate-500 light:text-slate-500">
                      {new Date(alert.created_at).toLocaleString()}
                    </span>
                  </div>
                  <h3 className={`mb-1 text-lg font-semibold ${alert.is_read ? "text-slate-400 dark:text-slate-400 light:text-slate-600" : "text-white dark:text-white light:text-slate-900"}`}>
                    {alert.title}
                  </h3>
                  {alert.message && (
                    <p className="text-sm text-slate-300 dark:text-slate-300 light:text-slate-700">{alert.message}</p>
                  )}
                  {alert.metadata && (
                    <div className="mt-2 space-y-1">
                      {alert.metadata.ioc_value && (
                        <div className="text-xs text-slate-500 dark:text-slate-500 light:text-slate-500">
                          <span className="font-mono">{alert.metadata.ioc_type?.toUpperCase()}: {alert.metadata.ioc_value}</span>
                        </div>
                      )}
                      {alert.metadata.queried_sources && Array.isArray(alert.metadata.queried_sources) && alert.metadata.queried_sources.length > 0 && (
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-xs font-medium text-slate-400 dark:text-slate-400 light:text-slate-600">Sources:</span>
                          {alert.metadata.queried_sources.map((source: any, idx: number) => (
                            <span
                              key={idx}
                              className={`rounded px-2 py-0.5 text-xs font-medium ${
                                source.risk_score >= 0.8
                                  ? "bg-red-950/30 dark:bg-red-950/30 light:bg-red-50 text-red-400 dark:text-red-400 light:text-red-600"
                                  : source.risk_score >= 0.5
                                  ? "bg-yellow-950/30 dark:bg-yellow-950/30 light:bg-yellow-50 text-yellow-400 dark:text-yellow-400 light:text-yellow-600"
                                  : source.risk_score >= 0.2
                                  ? "bg-green-950/30 dark:bg-green-950/30 light:bg-green-50 text-green-400 dark:text-green-400 light:text-green-600"
                                  : "bg-slate-800 dark:bg-slate-800 light:bg-slate-200 text-slate-400 dark:text-slate-400 light:text-slate-600"
                              }`}
                              title={source.description || source.source}
                            >
                              {source.source}
                              {source.risk_score !== null && source.risk_score !== undefined && (
                                <span className="ml-1">({(source.risk_score * 100).toFixed(0)}%)</span>
                              )}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
                <div className="ml-4 flex gap-2">
                  {!alert.is_read ? (
                    <button
                      onClick={() => markAsReadMutation.mutate(alert.id)}
                      disabled={markAsReadMutation.isPending}
                      className="rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white p-2 text-slate-400 dark:text-slate-400 light:text-slate-600 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100 hover:text-white dark:hover:text-white light:hover:text-slate-900 disabled:opacity-50"
                      title="Mark as read"
                    >
                      <CheckCircle2 className="h-4 w-4" />
                    </button>
                  ) : (
                    <button
                      onClick={() => markAsUnreadMutation.mutate(alert.id)}
                      disabled={markAsUnreadMutation.isPending}
                      className="rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white p-2 text-slate-400 dark:text-slate-400 light:text-slate-600 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100 hover:text-white dark:hover:text-white light:hover:text-slate-900 disabled:opacity-50"
                      title="Mark as unread"
                    >
                      <Circle className="h-4 w-4" />
                    </button>
                  )}
                  <button
                    onClick={() => deleteMutation.mutate(alert.id)}
                    disabled={deleteMutation.isPending}
                    className="rounded-lg border border-red-800 dark:border-red-800 light:border-red-300 bg-red-950/20 dark:bg-red-950/20 light:bg-red-50 p-2 text-red-400 dark:text-red-400 light:text-red-600 transition hover:bg-red-950/40 dark:hover:bg-red-950/40 light:hover:bg-red-100 disabled:opacity-50"
                    title="Delete"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900/30 dark:bg-slate-900/30 light:bg-slate-50 p-12 text-center">
          <BellOff className="mx-auto mb-4 h-12 w-12 text-slate-600 dark:text-slate-600 light:text-slate-400" />
          <p className="text-slate-400 dark:text-slate-400 light:text-slate-600">No alerts found</p>
        </div>
      )}

      {/* Pagination */}
      {data && data.total_pages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">
            Page {page} of {data.total_pages} | Total: {data.total}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white px-4 py-2 text-sm text-white dark:text-white light:text-slate-900 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={page >= data.total_pages}
              className="rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white px-4 py-2 text-sm text-white dark:text-white light:text-slate-900 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default AlertsPage;

