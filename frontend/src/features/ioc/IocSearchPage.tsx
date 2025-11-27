import { useState, useEffect } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { Search, AlertCircle, CheckCircle, XCircle, Clock, Shield, Filter, X } from "lucide-react";

import { apiClient } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import type { IOCQueryRequest, IOCQueryResponse, IOCQueryHistoryListResponse } from "@/features/ioc/types";

const IocSearchPage = () => {
  const { user } = useAuth();
  const canViewHistory = true; // Allow all authenticated users (admin, analyst, viewer) to view history
  const [searchParams, setSearchParams] = useSearchParams();
  const [iocType, setIocType] = useState<"ip" | "domain" | "url" | "hash">("ip");
  const [iocValue, setIocValue] = useState("");
  const [riskFilter, setRiskFilter] = useState<string | null>(null);
  const [historyIocTypeFilter, setHistoryIocTypeFilter] = useState<string>("");
  const [historyIocValueFilter, setHistoryIocValueFilter] = useState<string>("");
  const [historySourceFilter, setHistorySourceFilter] = useState<string>("");
  const [historyWatchlistFilter, setHistoryWatchlistFilter] = useState<string>("");
  const [startDateFilter, setStartDateFilter] = useState<string>("");
  const [endDateFilter, setEndDateFilter] = useState<string>("");
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const queryMutation = useMutation({
    mutationFn: async (payload: IOCQueryRequest) => {
      const response = await apiClient.post<IOCQueryResponse>("/ioc/query", payload);
      return response.data;
    },
    onSuccess: () => {
      // Refetch history after successful query
      historyQuery.refetch();
    }
  });

  // Read risk filter from URL params
  useEffect(() => {
    const riskParam = searchParams.get("risk");
    if (riskParam) {
      setRiskFilter(riskParam);
      setPage(1);
    } else {
      // Clear filter if risk param is removed from URL
      setRiskFilter(null);
    }
  }, [searchParams]);

  // Fetch API sources for filter dropdown
  const apiSourcesQuery = useQuery({
    queryKey: ["api-sources"],
    queryFn: async () => {
      const response = await apiClient.get("/api-sources");
      return response.data;
    },
    enabled: canViewHistory,
  });

  // Fetch watchlists for filter dropdown
  const watchlistsQuery = useQuery({
    queryKey: ["watchlists"],
    queryFn: async () => {
      const response = await apiClient.get("/watchlists/");
      return response.data;
    },
    enabled: canViewHistory,
  });

  const historyQuery = useQuery<IOCQueryHistoryListResponse>({
    queryKey: ["ioc-history", riskFilter, historyIocTypeFilter, historyIocValueFilter, historySourceFilter, historyWatchlistFilter, startDateFilter, endDateFilter, page],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("page_size", String(pageSize));
      if (riskFilter) {
        params.set("risk_level", riskFilter);
      }
      if (historyIocTypeFilter) {
        params.set("ioc_type", historyIocTypeFilter);
      }
      if (historyIocValueFilter) {
        params.set("ioc_value", historyIocValueFilter);
      }
      if (historySourceFilter) {
        params.set("source", historySourceFilter);
      }
      if (historyWatchlistFilter) {
        params.set("watchlist_id", historyWatchlistFilter);
      }
      if (startDateFilter) {
        params.set("start_date", new Date(startDateFilter).toISOString());
      }
      if (endDateFilter) {
        params.set("end_date", new Date(endDateFilter).toISOString());
      }
      const response = await apiClient.get<IOCQueryHistoryListResponse>(`/ioc/history?${params.toString()}`);
      return response.data;
    },
    enabled: canViewHistory, // Only enabled for admin and analyst
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!iocValue.trim()) return;

    queryMutation.mutate({
      ioc_type: iocType,
      ioc_value: iocValue.trim(),
      // sources parameter omitted - will use all active sources
    });
  };

  const getRiskColor = (risk?: string) => {
    switch (risk?.toLowerCase()) {
      case "high":
      case "critical":
        return "text-red-400 dark:text-red-400 light:text-red-600";
      case "medium":
        return "text-yellow-400 dark:text-yellow-400 light:text-yellow-600";
      case "low":
        return "text-green-400 dark:text-green-400 light:text-green-600";
      default:
        return "text-slate-400 dark:text-slate-400 light:text-slate-600";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case "success":
        return <CheckCircle className="h-4 w-4 text-green-400 dark:text-green-400 light:text-green-600" />;
      case "error":
        return <XCircle className="h-4 w-4 text-red-400 dark:text-red-400 light:text-red-600" />;
      case "pending":
        return <Clock className="h-4 w-4 text-yellow-400 dark:text-yellow-400 light:text-yellow-600" />;
      default:
        return <AlertCircle className="h-4 w-4 text-slate-400 dark:text-slate-400 light:text-slate-600" />;
    }
  };

  const handleClearRiskFilter = () => {
    setRiskFilter(null);
    setPage(1);
    searchParams.delete("risk");
    setSearchParams(searchParams);
  };

  return (
    <div className="space-y-6">
      <header>
        <div>
          <h2 className="text-2xl font-semibold text-white dark:text-white light:text-slate-900">IOC Search</h2>
          <p className="text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">Query IPs, domains, URLs, and hashes across all configured threat intelligence sources.</p>
        </div>
      </header>

      {/* Search Form */}
      <form onSubmit={handleSubmit} className="rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/40 dark:bg-slate-900/40 light:bg-white p-6">
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">IOC Type</label>
            <select
              value={iocType}
              onChange={(e) => setIocType(e.target.value as typeof iocType)}
              className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
            >
              <option value="ip">IP Address</option>
              <option value="domain">Domain</option>
              <option value="url">URL</option>
              <option value="hash">Hash (MD5/SHA1/SHA256)</option>
            </select>
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">IOC Value</label>
            <input
              type="text"
              value={iocValue}
              onChange={(e) => setIocValue(e.target.value)}
              placeholder="e.g., 8.8.8.8 or example.com"
              className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 placeholder:text-slate-500 dark:placeholder:text-slate-500 light:placeholder:text-slate-400 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
              required
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={queryMutation.isPending || !iocValue.trim()}
          className="mt-6 w-full rounded-lg bg-brand-600 dark:bg-brand-600 light:bg-brand-500 px-4 py-2 font-medium text-white transition hover:bg-brand-700 dark:hover:bg-brand-700 light:hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {queryMutation.isPending ? "Querying..." : "Query IOC"}
        </button>
      </form>

      {/* Query Results */}
      {queryMutation.data && (
        <div className="rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/40 dark:bg-slate-900/40 light:bg-white p-6">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-white dark:text-white light:text-slate-900">Query Results</h3>
              <p className="text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">
                {queryMutation.data.ioc_type.toUpperCase()}: {queryMutation.data.ioc_value}
              </p>
            </div>
            {queryMutation.data.overall_risk && (
              <div className="flex items-center gap-2">
                <Shield className="h-5 w-5 text-brand-400 dark:text-brand-400 light:text-brand-600" />
                <span className={`text-lg font-semibold ${getRiskColor(queryMutation.data.overall_risk)}`}>
                  {queryMutation.data.overall_risk.toUpperCase()}
                </span>
              </div>
            )}
          </div>

          {/* Group sources by risk level */}
          {(() => {
            const getRiskLevel = (riskScore: number | null | undefined): string => {
              if (riskScore === null || riskScore === undefined) return "unknown";
              if (riskScore >= 0.8) return "high";
              if (riskScore >= 0.5) return "medium";
              if (riskScore >= 0.2) return "low";
              return "clean";
            };

            const groupedSources = queryMutation.data.queried_sources.reduce((acc, source) => {
              const riskLevel = getRiskLevel(source.risk_score);
              if (!acc[riskLevel]) {
                acc[riskLevel] = [];
              }
              acc[riskLevel].push(source);
              return acc;
            }, {} as Record<string, typeof queryMutation.data.queried_sources>);

            const riskOrder = ["high", "medium", "low", "clean", "unknown", "error", "skipped"];

            return (
              <div className="space-y-4">
                {riskOrder.map((riskLevel) => {
                  const sources = groupedSources[riskLevel] || [];
                  if (sources.length === 0) return null;

                  return (
                    <div key={riskLevel} className="rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-950/60 dark:bg-slate-950/60 light:bg-slate-50 p-4">
                      <div className="mb-3 flex items-center gap-2">
                        <span className={`text-sm font-semibold uppercase ${getRiskColor(riskLevel)}`}>
                          {riskLevel === "high" ? "High Risk" : riskLevel === "medium" ? "Medium Risk" : riskLevel === "low" ? "Low Risk" : riskLevel === "clean" ? "Clean" : riskLevel === "unknown" ? "Unknown" : riskLevel === "error" ? "Error" : "Skipped"}
                        </span>
                        <span className="text-xs text-slate-500 dark:text-slate-500 light:text-slate-500">
                          ({sources.length} {sources.length === 1 ? "source" : "sources"})
                        </span>
                      </div>
                      <div className="space-y-2">
                        {sources.map((source, idx) => (
                          <div key={idx} className="flex items-center justify-between rounded-lg bg-slate-900/40 dark:bg-slate-900/40 light:bg-slate-100 px-3 py-2">
                            <div className="flex items-center gap-3">
                              {getStatusIcon(source.status)}
                              <span className="font-medium text-white dark:text-white light:text-slate-900 capitalize">{source.source}</span>
                            </div>
                            <div className="flex items-center gap-3">
                              {source.risk_score !== null && source.risk_score !== undefined && (
                                <span className={`text-sm font-semibold ${getRiskColor(getRiskLevel(source.risk_score))}`}>
                                  {(source.risk_score * 100).toFixed(0)}%
                                </span>
                              )}
                              {source.description && (
                                <span className="text-xs text-slate-400 dark:text-slate-400 light:text-slate-600 max-w-md truncate" title={source.description}>
                                  {source.description}
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            );
          })()}
        </div>
      )}

      {/* History Filters - Only for Admin and Analyst */}
      {canViewHistory && (
        <div className="rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/40 dark:bg-slate-900/40 light:bg-white p-6">
          <div className="mb-4 flex items-center gap-2">
            <Filter className="h-4 w-4 text-brand-400 dark:text-brand-400 light:text-brand-600" />
            <h3 className="text-lg font-semibold text-white dark:text-white light:text-slate-900">History Filters</h3>
          </div>
          <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 xl:grid-cols-4">
            {/* Risk Filter */}
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">Risk Level</label>
              <select
                value={riskFilter || ""}
                onChange={(e) => {
                  const newRisk = e.target.value || null;
                  setRiskFilter(newRisk);
                  setPage(1);
                  if (newRisk) {
                    searchParams.set("risk", newRisk);
                  } else {
                    searchParams.delete("risk");
                  }
                  setSearchParams(searchParams);
                }}
                className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-3 py-2 text-sm text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
              >
                <option value="">All Risks</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
                <option value="unknown">Unknown</option>
              </select>
            </div>

            {/* IOC Type Filter */}
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">IOC Type</label>
              <select
                value={historyIocTypeFilter}
                onChange={(e) => {
                  setHistoryIocTypeFilter(e.target.value);
                  setPage(1);
                }}
                className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-3 py-2 text-sm text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
              >
                <option value="">All Types</option>
                <option value="ip">IP Address</option>
                <option value="domain">Domain</option>
                <option value="url">URL</option>
                <option value="hash">Hash</option>
              </select>
            </div>

            {/* IOC Value Filter */}
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">IOC Value</label>
              <input
                type="text"
                value={historyIocValueFilter}
                onChange={(e) => {
                  setHistoryIocValueFilter(e.target.value);
                  setPage(1);
                }}
                placeholder="Search IOC value..."
                className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-3 py-2 text-sm text-white dark:text-white light:text-slate-900 placeholder:text-slate-500 dark:placeholder:text-slate-500 light:placeholder:text-slate-400 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
              />
            </div>

            {/* API Source Filter */}
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">API Source</label>
              <select
                value={historySourceFilter}
                onChange={(e) => {
                  setHistorySourceFilter(e.target.value);
                  setPage(1);
                }}
                className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-3 py-2 text-sm text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
              >
                <option value="">All Sources</option>
                {apiSourcesQuery.data?.map((source: any) => (
                  <option key={source.id} value={source.name}>
                    {source.display_name || source.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Watchlist Filter */}
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">Watchlist</label>
              <select
                value={historyWatchlistFilter}
                onChange={(e) => {
                  setHistoryWatchlistFilter(e.target.value);
                  setPage(1);
                }}
                className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-3 py-2 text-sm text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
              >
                <option value="">All Watchlists</option>
                {watchlistsQuery.data?.watchlists?.map((watchlist: any) => (
                  <option key={watchlist.id} value={watchlist.id}>
                    {watchlist.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Start Date Filter */}
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">Start Date</label>
              <input
                type="date"
                value={startDateFilter}
                onChange={(e) => {
                  setStartDateFilter(e.target.value);
                  setPage(1);
                }}
                className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-3 py-2 text-sm text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
              />
            </div>

            {/* End Date Filter */}
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">End Date</label>
              <input
                type="date"
                value={endDateFilter}
                onChange={(e) => {
                  setEndDateFilter(e.target.value);
                  setPage(1);
                }}
                className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-3 py-2 text-sm text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
              />
            </div>

            {/* Clear Filters Button */}
            <div className="flex items-end">
              <button
                onClick={() => {
                  setRiskFilter(null);
                  setHistoryIocTypeFilter("");
                  setHistoryIocValueFilter("");
                  setHistorySourceFilter("");
                  setHistoryWatchlistFilter("");
                  setStartDateFilter("");
                  setEndDateFilter("");
                  setPage(1);
                  searchParams.delete("risk");
                  setSearchParams(searchParams);
                }}
                className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white px-4 py-2 text-sm font-medium text-slate-400 dark:text-slate-400 light:text-slate-600 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100 hover:text-white dark:hover:text-white light:hover:text-slate-900"
              >
                Clear All Filters
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Query History - Only for Admin and Analyst */}
      {canViewHistory && (
      <div className="rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/40 dark:bg-slate-900/40 light:bg-white p-6">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white dark:text-white light:text-slate-900">
            {riskFilter ? `Queries with ${riskFilter.toUpperCase()} Risk` : "Recent Queries"}
          </h3>
          <div className="flex items-center gap-3">
            {historyQuery.data && historyQuery.data.total > 0 && (
              <span className="text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">
                {historyQuery.data.total} total | Page {page} of {historyQuery.data.total_pages || 1}
              </span>
            )}
            {historyQuery.data && historyQuery.data.total > 0 && (
              <div className="flex gap-2">
                <button
                  onClick={async () => {
                    try {
                      const params = new URLSearchParams();
                      if (riskFilter) params.set('risk_level', riskFilter);
                      if (historyIocTypeFilter) params.set('ioc_type', historyIocTypeFilter);
                      if (historyIocValueFilter) params.set('ioc_value', historyIocValueFilter);
                      if (historySourceFilter) params.set('source', historySourceFilter);
                      if (historyWatchlistFilter) params.set('watchlist_id', historyWatchlistFilter);
                      if (startDateFilter) params.set('start_date', new Date(startDateFilter).toISOString());
                      if (endDateFilter) params.set('end_date', new Date(endDateFilter).toISOString());
                      params.set('format', 'json');
                      
                      const response = await apiClient.get(`/ioc/history/export?${params.toString()}`, {
                        responseType: 'blob'
                      });
                      
                      const blob = new Blob([response.data], { type: 'application/json' });
                      const downloadUrl = window.URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = downloadUrl;
                      a.download = `ioc_query_history_${new Date().toISOString().split('T')[0]}.json`;
                      document.body.appendChild(a);
                      a.click();
                      window.URL.revokeObjectURL(downloadUrl);
                      document.body.removeChild(a);
                    } catch (error: any) {
                      console.error('Export error:', error);
                      alert(`Failed to export JSON: ${error?.response?.data?.detail || error?.message || 'Unknown error'}`);
                    }
                  }}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-700 hover:bg-slate-600 text-white dark:text-white light:text-white transition"
                >
                  Export JSON
                </button>
              </div>
            )}
          </div>
        </div>
        
        {historyQuery.isLoading ? (
          <div className="py-8 text-center text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">
            Loading query history...
          </div>
        ) : historyQuery.data && historyQuery.data.items.length > 0 ? (
            <>
              <div className="space-y-2">
                {historyQuery.data.items.map((item) => (
                  <div key={item.id} className="rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-950/60 dark:bg-slate-950/60 light:bg-slate-50 p-4 hover:bg-slate-900 dark:hover:bg-slate-900 light:hover:bg-slate-100 transition">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-3">
                        <span className="text-xs font-medium uppercase text-slate-500 dark:text-slate-500 light:text-slate-600">{item.ioc_type}</span>
                        <span className="font-mono text-sm text-white dark:text-white light:text-slate-900">{item.ioc_value}</span>
                        {item.status && (
                          <span className={`text-xs font-medium px-2 py-0.5 rounded ${getRiskColor(item.status)}`}>
                            {item.status.toUpperCase()}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-3">
                        {item.risk_score !== null && item.risk_score !== undefined && (
                          <span className={`text-sm font-semibold ${getRiskColor(item.status || "")}`}>
                            {(item.risk_score * 100).toFixed(0)}%
                          </span>
                        )}
                        <span className="text-xs text-slate-500 dark:text-slate-500 light:text-slate-500">{new Date(item.query_date).toLocaleString()}</span>
                      </div>
                    </div>
                    {item.queried_sources && item.queried_sources.length > 0 && (
                      <div className="mt-2 flex flex-wrap items-center gap-2">
                        <span className="text-xs font-medium text-slate-400 dark:text-slate-400 light:text-slate-600">Sources:</span>
                        {item.queried_sources.map((source, idx) => {
                          const sourceRiskLevel = source.risk_score !== null && source.risk_score !== undefined
                            ? (source.risk_score >= 0.8 ? "high" : source.risk_score >= 0.5 ? "medium" : source.risk_score >= 0.2 ? "low" : "clean")
                            : "unknown";
                          return (
                            <span
                              key={idx}
                              className={`rounded px-2 py-0.5 text-xs font-medium ${
                                sourceRiskLevel === "high"
                                  ? "bg-red-950/30 dark:bg-red-950/30 light:bg-red-50 text-red-400 dark:text-red-400 light:text-red-600"
                                  : sourceRiskLevel === "medium"
                                  ? "bg-yellow-950/30 dark:bg-yellow-950/30 light:bg-yellow-50 text-yellow-400 dark:text-yellow-400 light:text-yellow-600"
                                  : sourceRiskLevel === "low"
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
                          );
                        })}
                      </div>
                    )}
                  </div>
                ))}
              </div>
              
              {/* Pagination */}
              {(historyQuery.data.total_pages || 0) > 1 && (
                <div className="mt-4 flex items-center justify-between">
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white px-4 py-2 text-sm text-white dark:text-white light:text-slate-900 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setPage(p => p + 1)}
                    disabled={page >= (historyQuery.data.total_pages || 1)}
                    className="rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white px-4 py-2 text-sm text-white dark:text-white light:text-slate-900 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              )}
            </>
          ) : (
            <div className="py-8 text-center text-sm text-slate-500 dark:text-slate-500 light:text-slate-500">
              {riskFilter ? `No queries found with ${riskFilter.toUpperCase()} risk level` : "No query history yet"}
            </div>
          )}
      </div>
      )}

      {queryMutation.isError && (
        <div className="rounded-lg border border-red-800 dark:border-red-800 light:border-red-300 bg-red-950/20 dark:bg-red-950/20 light:bg-red-50 p-4 text-red-400 dark:text-red-400 light:text-red-700">
          Error: {queryMutation.error instanceof Error ? queryMutation.error.message : "Failed to query IOC"}
        </div>
      )}
    </div>
  );
};

export default IocSearchPage;
