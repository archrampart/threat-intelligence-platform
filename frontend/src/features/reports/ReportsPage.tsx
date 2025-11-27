import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, FileText, Download, Trash2, Eye, Calendar } from "lucide-react";

import { apiClient } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import type { ReportResponse, ReportListResponse, ReportCreate } from "@/features/reports/types";

const ReportsPage = () => {
  const { user } = useAuth();
  const canCreateOrDelete = user?.role === "admin" || user?.role === "analyst";
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const pageSize = 20;

  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery<ReportListResponse>({
    queryKey: ["reports", page, search],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString()
      });
      if (search) {
        params.append("search", search);
      }
      const response = await apiClient.get<ReportListResponse>(`/reports/?${params}`);
      return response.data;
    }
  });

  const deleteMutation = useMutation({
    mutationFn: async (reportId: string) => {
      await apiClient.delete(`/reports/${reportId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reports"] });
    }
  });

  const exportMutation = useMutation({
    mutationFn: async ({ reportId, format }: { reportId: string; format: string }) => {
      const response = await apiClient.post(
        `/reports/${reportId}/export`,
        { format, include_raw_data: false },
        { responseType: "blob" }
      );
      
      // Get filename from Content-Disposition header if available
      const contentDisposition = response.headers['content-disposition'];
      let filename = `report_${reportId}.${format.toLowerCase()}`;
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="(.+)"/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }
      
      return { blob: response.data, filename };
    },
    onSuccess: ({ blob, filename }) => {
      // Check if blob is valid
      if (!blob || blob.size === 0) {
        console.error("Empty blob received");
        alert("Failed to download report: Empty file received");
        return;
      }
      
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    },
    onError: (error: any) => {
      console.error("Export error:", error);
      alert(`Failed to export report: ${error?.message || "Unknown error"}`);
    }
  });

  const handleDelete = (reportId: string) => {
    if (confirm("Are you sure you want to delete this report?")) {
      deleteMutation.mutate(reportId);
    }
  };

  const handleExport = (reportId: string, format: string) => {
    exportMutation.mutate({ reportId, format });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-white dark:text-white light:text-slate-900">Reports</h2>
          <p className="text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">
            {canCreateOrDelete 
              ? "Generate and download IOC analysis reports" 
              : "View and download IOC analysis reports (read-only)"}
          </p>
        </div>
        {canCreateOrDelete && (
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 rounded-lg bg-brand-600 dark:bg-brand-600 light:bg-brand-500 px-4 py-2 font-medium text-white transition hover:bg-brand-700 dark:hover:bg-brand-700 light:hover:bg-brand-600"
          >
            <Plus className="h-4 w-4" />
            New Report
          </button>
        )}
      </div>

      {/* Search */}
      <div className="rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/40 dark:bg-slate-900/40 light:bg-white p-4">
        <input
          type="text"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          placeholder="Search reports by title or description..."
          className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 placeholder:text-slate-500 dark:placeholder:text-slate-500 light:placeholder:text-slate-400 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
        />
      </div>

      {/* Reports List */}
      {isLoading ? (
        <p className="text-slate-400 dark:text-slate-400 light:text-slate-600">Loading reports...</p>
      ) : data && data.items.length > 0 ? (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">
            <span>
              Showing {data.items.length} of {data.total} reports
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white px-3 py-1 text-sm text-white dark:text-white light:text-slate-900 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Previous
              </button>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={page >= data.total_pages}
                className="rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white px-3 py-1 text-sm text-white dark:text-white light:text-slate-900 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>

          <div className="space-y-3">
            {data.items.map((report) => (
              <ReportCard
                key={report.id}
                report={report}
                onDelete={() => handleDelete(report.id)}
                onExport={handleExport}
                isExporting={exportMutation.isPending}
                canDelete={canCreateOrDelete}
              />
            ))}
          </div>
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900/30 dark:bg-slate-900/30 light:bg-slate-50 p-12 text-center">
          <FileText className="mx-auto mb-4 h-12 w-12 text-slate-600 dark:text-slate-600 light:text-slate-400" />
          <p className="text-slate-400 dark:text-slate-400 light:text-slate-600">No reports found</p>
        </div>
      )}

      {showCreateModal && (
        <CreateReportModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false);
            queryClient.invalidateQueries({ queryKey: ["reports"] });
          }}
        />
      )}
    </div>
  );
};

const ReportCard = ({
  report,
  onDelete,
  onExport,
  isExporting,
  canDelete
}: {
  report: ReportResponse;
  onDelete: () => void;
  onExport: (reportId: string, format: string) => void;
  isExporting: boolean;
  canDelete: boolean;
}) => {
  const getFormatColor = (format: string) => {
    switch (format.toUpperCase()) {
      case "PDF":
        return "text-red-400 dark:text-red-400 light:text-red-600 bg-red-950/30 dark:bg-red-950/30 light:bg-red-50 border-red-800 dark:border-red-800 light:border-red-300";
      case "HTML":
        return "text-blue-400 dark:text-blue-400 light:text-blue-600 bg-blue-950/30 dark:bg-blue-950/30 light:bg-blue-50 border-blue-800 dark:border-blue-800 light:border-blue-300";
      case "JSON":
        return "text-green-400 dark:text-green-400 light:text-green-600 bg-green-950/30 dark:bg-green-950/30 light:bg-green-50 border-green-800 dark:border-green-800 light:border-green-300";
      default:
        return "text-slate-400 dark:text-slate-400 light:text-slate-600 bg-slate-900/30 dark:bg-slate-900/30 light:bg-slate-50 border-slate-800 dark:border-slate-800 light:border-slate-200";
    }
  };

  return (
    <div className="rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/40 dark:bg-slate-900/40 light:bg-white p-4 transition hover:bg-slate-900/60 dark:hover:bg-slate-900/60 light:hover:bg-slate-50">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="mb-2 flex items-center gap-3">
            <h3 className="text-lg font-semibold text-white dark:text-white light:text-slate-900">{report.title}</h3>
            <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${getFormatColor(report.format)}`}>
              {report.format}
            </span>
          </div>
          {report.description && <p className="mb-2 text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">{report.description}</p>}
          <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 dark:text-slate-500 light:text-slate-500">
            <div className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              <span>Created: {new Date(report.created_at).toLocaleDateString()}</span>
            </div>
            {report.ioc_query_ids && report.ioc_query_ids.length > 0 && (
              <span>{report.ioc_query_ids.length} IOC query(ies)</span>
            )}
          </div>
        </div>
        <div className="ml-4 flex gap-2">
          <button
            onClick={() => onExport(report.id, report.format)}
            disabled={isExporting}
            className="rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white p-2 text-slate-400 dark:text-slate-400 light:text-slate-600 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100 hover:text-white dark:hover:text-white light:hover:text-slate-900 disabled:opacity-50"
            title={`Export as ${report.format}`}
          >
            <Download className="h-4 w-4" />
          </button>
          {canDelete && (
            <button
              onClick={onDelete}
              className="rounded-lg border border-red-800 dark:border-red-800 light:border-red-300 bg-red-950/20 dark:bg-red-950/20 light:bg-red-50 p-2 text-red-400 dark:text-red-400 light:text-red-700 transition hover:bg-red-950/40 dark:hover:bg-red-950/40 light:hover:bg-red-100"
              title="Delete report"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

const CreateReportModal = ({
  onClose,
  onSuccess
}: {
  onClose: () => void;
  onSuccess: () => void;
}) => {
  const [formData, setFormData] = useState<ReportCreate>({
    title: "",
    description: undefined,
    format: "PDF",
    ioc_query_ids: [],
    watchlist_id: undefined,
    ioc_type: undefined,
    risk_level: undefined,
    start_date: undefined,
    end_date: undefined,
    source: undefined,
  });
  
  const [useFilters, setUseFilters] = useState(false);

  // Fetch watchlists
  const { data: watchlistsData } = useQuery({
    queryKey: ["watchlists"],
    queryFn: async () => {
      try {
        const response = await apiClient.get("/watchlists/");
        return response.data;
      } catch (error: any) {
        return { watchlists: [] };
      }
    },
    retry: false,
    refetchOnWindowFocus: false,
    throwOnError: false,
  });

  // Build query params for IOC history
  const buildIocHistoryParams = () => {
    const params = new URLSearchParams({
      page: "1",
      page_size: "100"
    });
    
    if (useFilters) {
      if (formData.watchlist_id) params.append("watchlist_id", formData.watchlist_id);
      if (formData.ioc_type) params.append("ioc_type", formData.ioc_type);
      if (formData.risk_level) params.append("risk_level", formData.risk_level);
      if (formData.start_date) params.append("start_date", formData.start_date);
      if (formData.end_date) params.append("end_date", formData.end_date);
      if (formData.source) params.append("source", formData.source);
    }
    
    return params.toString();
  };

  const { data: iocHistory, isLoading: isLoadingHistory } = useQuery({
    queryKey: ["ioc-history", useFilters, formData.watchlist_id, formData.ioc_type, formData.risk_level, formData.start_date, formData.end_date, formData.source],
    queryFn: async () => {
      try {
        const params = buildIocHistoryParams();
        const response = await apiClient.get(`/ioc/history?${params}`);
        return response.data;
      } catch (error: any) {
        // Silently handle ALL errors - don't show error to user
        // Just return empty data so report creation can proceed
        // Always return empty data - never throw
        // This prevents React Query from setting error state
        return { items: [], total: 0, page: 1, page_size: 100, total_pages: 0 };
      }
    },
    retry: false,
    refetchOnWindowFocus: false,
    throwOnError: false,
    retryOnMount: false
  });

  const createMutation = useMutation({
    mutationFn: async (data: ReportCreate) => {
      // Clean up data - remove empty description and ensure format is uppercase
      const payload: any = {
        title: data.title.trim(),
        format: data.format.toUpperCase(),
      };
      
      // If using filters, send filter parameters instead of specific query IDs
      if (useFilters && (data.watchlist_id || data.ioc_type || data.risk_level || data.start_date || data.end_date || data.source)) {
        if (data.watchlist_id) payload.watchlist_id = data.watchlist_id;
        if (data.ioc_type) payload.ioc_type = data.ioc_type;
        if (data.risk_level) payload.risk_level = data.risk_level;
        // Convert date strings to ISO format with time
        if (data.start_date) {
          // Add time to start_date (beginning of day)
          payload.start_date = `${data.start_date}T00:00:00Z`;
        }
        if (data.end_date) {
          // Add time to end_date (end of day)
          payload.end_date = `${data.end_date}T23:59:59Z`;
        }
        if (data.source) payload.source = data.source;
      } else {
        // Use specific query IDs if provided
        payload.ioc_query_ids = data.ioc_query_ids || [];
      }
      
      if (data.description && data.description.trim()) {
        payload.description = data.description.trim();
      }
      
      console.log("Creating report with payload:", payload);
      console.log("API Base URL:", import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000");
      
      // Check if user is authenticated
      const token = localStorage.getItem("access_token");
      if (!token) {
        const authError: any = new Error("You are not logged in. Please log in and try again.");
        authError.isAuthError = true;
        throw authError;
      }
      console.log("Auth token present:", token ? "Yes (length: " + token.length + ")" : "No");
      
      try {
        const response = await apiClient.post<ReportResponse>("/reports/", payload);
        console.log("Report created successfully:", response.data);
        return response.data;
      } catch (error: any) {
        console.error("Full error object:", error);
        console.error("Error response:", error?.response);
        console.error("Error message:", error?.message);
        console.error("Error code:", error?.code);
        
        // Check if it's a network error
        const errorMessage = error?.message || "";
        const isNetworkError = 
          error?.isNetworkError ||
          error?.isSilent ||
          errorMessage.includes("Backend server is not reachable") ||
          error?.code === "ECONNREFUSED" ||
          errorMessage.includes("Network Error") ||
          errorMessage.includes("timeout") ||
          errorMessage.includes("ERR_NETWORK") ||
          !error?.response; // No response usually means network error
        
        if (isNetworkError) {
          // Create a more user-friendly error for network issues
          const networkError: any = new Error("Cannot connect to backend server. Please make sure the backend is running and try again.");
          networkError.isNetworkError = true;
          networkError.originalError = error;
          throw networkError;
        }
        
        // Check for authentication errors
        if (error?.response?.status === 401) {
          const authError: any = new Error("Authentication failed. Please log in again.");
          authError.isAuthError = true;
          throw authError;
        }
        
        // Check for validation errors
        if (error?.response?.status === 422 || error?.response?.status === 400) {
          const validationError: any = new Error(
            error?.response?.data?.detail || "Invalid data. Please check your input."
          );
          validationError.isValidationError = true;
          throw validationError;
        }
        
        // Re-throw other errors with original message
        throw error;
      }
    },
    onSuccess: () => {
      onSuccess();
    },
    onError: (error: any) => {
      console.error("Error creating report:", error);
      // Error will be shown in the UI
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate(formData);
  };

  const toggleIocQuery = (queryId: string) => {
    const current = formData.ioc_query_ids || [];
    if (current.includes(queryId)) {
      setFormData({ ...formData, ioc_query_ids: current.filter((id) => id !== queryId) });
    } else {
      setFormData({ ...formData, ioc_query_ids: [...current, queryId] });
    }
  };

  const handleSelectAll = () => {
    if (!iocHistory?.items) return;
    const allIds = iocHistory.items.map((query: any) => query.id);
    const current = formData.ioc_query_ids || [];
    
    // If all are selected, deselect all; otherwise select all
    if (allIds.length > 0 && current.length === allIds.length && 
        allIds.every((id: string) => current.includes(id))) {
      setFormData({ ...formData, ioc_query_ids: [] });
    } else {
      setFormData({ ...formData, ioc_query_ids: allIds });
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/50 light:bg-black/30 p-4">
      <div className="w-full max-w-2xl rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900 dark:bg-slate-900 light:bg-white p-6">
        <div className="mb-6 flex items-center justify-between">
          <h3 className="text-xl font-semibold text-white dark:text-white light:text-slate-900">Create Report</h3>
          <button onClick={onClose} className="text-slate-400 dark:text-slate-400 light:text-slate-600 hover:text-white dark:hover:text-white light:hover:text-slate-900">
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">Title *</label>
            <input
              type="text"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
              required
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">Description (Optional)</label>
            <textarea
              value={formData.description || ""}
              onChange={(e) => setFormData({ ...formData, description: e.target.value || undefined })}
              className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
              rows={3}
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">Format</label>
            <select
              value={formData.format}
              onChange={(e) => setFormData({ ...formData, format: e.target.value })}
              className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
            >
              <option value="PDF">PDF</option>
              <option value="HTML">HTML</option>
              <option value="JSON">JSON</option>
            </select>
          </div>

          {/* Filter Options */}
          <div className="rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-950/60 dark:bg-slate-950/60 light:bg-slate-50 p-4">
            <div className="mb-3 flex items-center justify-between">
              <label className="block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">Filter Options</label>
              <label className="flex cursor-pointer items-center gap-2">
                <input
                  type="checkbox"
                  checked={useFilters}
                  onChange={(e) => {
                    setUseFilters(e.target.checked);
                    if (!e.target.checked) {
                      // Clear filters when unchecked
                      setFormData({
                        ...formData,
                        watchlist_id: undefined,
                        ioc_type: undefined,
                        risk_level: undefined,
                        start_date: undefined,
                        end_date: undefined,
                        source: undefined,
                        ioc_query_ids: []
                      });
                    }
                  }}
                  className="rounded border-slate-600 dark:border-slate-600 light:border-slate-400 text-brand-500 dark:text-brand-500 light:text-brand-600 focus:ring-brand-500 dark:focus:ring-brand-500 light:focus:ring-brand-600"
                />
                <span className="text-sm text-slate-300 dark:text-slate-300 light:text-slate-700">Use Filters</span>
              </label>
            </div>

            {useFilters && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Watchlist Filter */}
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-400 dark:text-slate-400 light:text-slate-600">Watchlist</label>
                  <select
                    value={formData.watchlist_id || ""}
                    onChange={(e) => setFormData({ ...formData, watchlist_id: e.target.value || undefined, ioc_query_ids: [] })}
                    className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-3 py-2 text-sm text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
                  >
                    <option value="">All Watchlists</option>
                    {watchlistsData?.watchlists?.map((watchlist: any) => (
                      <option key={watchlist.id} value={watchlist.id}>
                        {watchlist.name}
                      </option>
                    ))}
                  </select>
                </div>

                {/* IOC Type Filter */}
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-400 dark:text-slate-400 light:text-slate-600">IOC Type</label>
                  <select
                    value={formData.ioc_type || ""}
                    onChange={(e) => setFormData({ ...formData, ioc_type: e.target.value || undefined, ioc_query_ids: [] })}
                    className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-3 py-2 text-sm text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
                  >
                    <option value="">All Types</option>
                    <option value="ip">IP</option>
                    <option value="domain">Domain</option>
                    <option value="url">URL</option>
                    <option value="hash">Hash</option>
                    <option value="cve">CVE</option>
                  </select>
                </div>

                {/* Risk Level Filter */}
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-400 dark:text-slate-400 light:text-slate-600">Risk Level</label>
                  <select
                    value={formData.risk_level || ""}
                    onChange={(e) => setFormData({ ...formData, risk_level: e.target.value || undefined, ioc_query_ids: [] })}
                    className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-3 py-2 text-sm text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
                  >
                    <option value="">All Risk Levels</option>
                    <option value="critical">Critical</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                    <option value="unknown">Unknown</option>
                  </select>
                </div>

                {/* API Source Filter */}
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-400 dark:text-slate-400 light:text-slate-600">API Source</label>
                  <input
                    type="text"
                    value={formData.source || ""}
                    onChange={(e) => setFormData({ ...formData, source: e.target.value || undefined, ioc_query_ids: [] })}
                    placeholder="Filter by API source..."
                    className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-3 py-2 text-sm text-white dark:text-white light:text-slate-900 placeholder:text-slate-500 dark:placeholder:text-slate-500 light:placeholder:text-slate-400 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
                  />
                </div>

                {/* Start Date Filter */}
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-400 dark:text-slate-400 light:text-slate-600">Start Date</label>
                  <input
                    type="date"
                    value={formData.start_date || ""}
                    onChange={(e) => setFormData({ ...formData, start_date: e.target.value || undefined, ioc_query_ids: [] })}
                    className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-3 py-2 text-sm text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
                  />
                </div>

                {/* End Date Filter */}
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-400 dark:text-slate-400 light:text-slate-600">End Date</label>
                  <input
                    type="date"
                    value={formData.end_date || ""}
                    onChange={(e) => setFormData({ ...formData, end_date: e.target.value || undefined, ioc_query_ids: [] })}
                    className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-3 py-2 text-sm text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
                  />
                </div>
              </div>
            )}
          </div>

          {/* IOC Queries Selection (only shown when not using filters) */}
          {!useFilters && (
            <div>
              <div className="mb-2 flex items-center justify-between">
                <label className="block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">Select IOC Queries (Optional)</label>
                {iocHistory?.items && iocHistory.items.length > 0 && (
                  <button
                    type="button"
                    onClick={handleSelectAll}
                    className="text-xs text-brand-400 dark:text-brand-400 light:text-brand-600 hover:text-brand-300 dark:hover:text-brand-300 light:hover:text-brand-500 transition"
                  >
                    {formData.ioc_query_ids && formData.ioc_query_ids.length === iocHistory.items.length
                      ? "Deselect All"
                      : "Select All"}
                  </button>
                )}
              </div>
            
            {isLoadingHistory ? (
              <div className="rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-950/60 dark:bg-slate-950/60 light:bg-slate-50 p-4 text-center text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">
                Loading IOC queries...
              </div>
            ) : (!iocHistory || !iocHistory.items || iocHistory.items.length === 0) ? (
              <div className="rounded-lg border border-yellow-800 dark:border-yellow-800 light:border-yellow-300 bg-yellow-950/20 dark:bg-yellow-950/20 light:bg-yellow-50 p-4 text-center text-sm text-yellow-400 dark:text-yellow-400 light:text-yellow-700">
                No IOC queries available. You can still create a report without selecting queries.
              </div>
            ) : (
              <div className="max-h-60 space-y-2 overflow-y-auto rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-950/60 dark:bg-slate-950/60 light:bg-slate-50 p-3">
                {iocHistory?.items && iocHistory.items.length > 0 ? (
                  iocHistory.items.map((query: any) => (
                    <label
                      key={query.id}
                      className="flex cursor-pointer items-center gap-2 rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/60 dark:bg-slate-900/60 light:bg-white p-2 hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100"
                    >
                      <input
                        type="checkbox"
                        checked={formData.ioc_query_ids?.includes(query.id) || false}
                        onChange={() => toggleIocQuery(query.id)}
                        className="rounded border-slate-600 dark:border-slate-600 light:border-slate-400 text-brand-500 dark:text-brand-500 light:text-brand-600 focus:ring-brand-500 dark:focus:ring-brand-500 light:focus:ring-brand-600"
                      />
                      <div className="flex-1">
                        <span className="text-xs uppercase text-slate-500 dark:text-slate-500 light:text-slate-500">{query.ioc_type}</span>
                        <span className="ml-2 font-mono text-sm text-white dark:text-white light:text-slate-900">{query.ioc_value}</span>
                        {query.risk_score && (
                          <span className="ml-2 text-xs text-slate-400 dark:text-slate-400 light:text-slate-600">Risk: {(query.risk_score * 100).toFixed(0)}%</span>
                        )}
                      </div>
                    </label>
                  ))
                ) : (
                  <p className="py-4 text-center text-sm text-slate-500 dark:text-slate-500 light:text-slate-500">No IOC queries found</p>
                )}
              </div>
            )}
            
            {formData.ioc_query_ids && formData.ioc_query_ids.length > 0 && (
              <p className="mt-2 text-xs text-slate-400 dark:text-slate-400 light:text-slate-600">
                {formData.ioc_query_ids.length} query(ies) selected
              </p>
            )}
          </div>
          )}

          {/* Show filtered results count when using filters */}
          {useFilters && iocHistory && (
            <div className="rounded-lg border border-blue-800 dark:border-blue-800 light:border-blue-300 bg-blue-950/20 dark:bg-blue-950/20 light:bg-blue-50 p-3">
              <p className="text-sm text-blue-400 dark:text-blue-400 light:text-blue-700">
                {iocHistory.total > 0 
                  ? `Found ${iocHistory.total} IOC query(ies) matching the filters. These will be included in the report.`
                  : "No IOC queries found matching the filters. Report will be created with no queries."}
              </p>
            </div>
          )}

          {createMutation.isError && (
            <div className="rounded-lg border border-red-800 dark:border-red-800 light:border-red-300 bg-red-950/20 dark:bg-red-950/20 light:bg-red-50 p-3 text-sm text-red-400 dark:text-red-400 light:text-red-700">
              <div className="font-semibold mb-1">Error creating report:</div>
              <div className="mb-2">
                {createMutation.error instanceof Error 
                  ? createMutation.error.message 
                  : (createMutation.error as any)?.response?.data?.detail || "Failed to create report"}
              </div>
              
              {(createMutation.error as any)?.isNetworkError && (
                <div className="mt-2 space-y-1 text-xs text-yellow-300 dark:text-yellow-300 light:text-yellow-700">
                  <div>💡 Troubleshooting steps:</div>
                  <ol className="list-decimal list-inside ml-2 space-y-1">
                    <li>Check if backend is running: <code className="bg-slate-900 dark:bg-slate-900 light:bg-slate-200 px-1 rounded">curl {import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"}/api/v1/health</code></li>
                    <li>Restart backend: <code className="bg-slate-900 dark:bg-slate-900 light:bg-slate-200 px-1 rounded">./start.sh</code></li>
                    <li>Check backend URL: <code className="bg-slate-900 dark:bg-slate-900 light:bg-slate-200 px-1 rounded">{import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"}</code></li>
                    <li>Check browser console for detailed error logs</li>
                  </ol>
                </div>
              )}
              
              {(createMutation.error as any)?.isAuthError && (
                <div className="mt-2 text-xs text-yellow-300 dark:text-yellow-300 light:text-yellow-700">
                  Please log out and log in again to refresh your authentication token.
                </div>
              )}
              
              {(createMutation.error as any)?.isValidationError && (
                <div className="mt-2 text-xs text-yellow-300 dark:text-yellow-300 light:text-yellow-700">
                  Please check your input and try again.
                </div>
              )}
            </div>
          )}

          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white px-4 py-2 text-sm font-medium text-white dark:text-white light:text-slate-900 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending || !formData.title.trim()}
              className="rounded-lg bg-brand-600 dark:bg-brand-600 light:bg-brand-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700 dark:hover:bg-brand-700 light:hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {createMutation.isPending ? "Creating..." : "Create Report"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ReportsPage;
