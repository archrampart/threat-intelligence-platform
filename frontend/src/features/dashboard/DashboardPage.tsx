import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Activity, Database, Shield, ShieldAlert, ShieldCheck, FileText, TrendingUp, PieChart as PieChartIcon, BarChart3, CheckCircle2, XCircle, AlertCircle, AlertTriangle, Settings, RefreshCw, AlertOctagon, AlertCircle as AlertCircleIcon } from "lucide-react";

import { apiClient } from "@/lib/api";
import StatCard from "@/components/widgets/StatCard";
import QueryTrendChart from "@/components/charts/QueryTrendChart";
import RiskDistributionChart from "@/components/charts/RiskDistributionChart";
import IOCTypeDistributionChart from "@/components/charts/IOCTypeDistributionChart";
import CVETrendChart from "@/components/charts/CVETrendChart";
import CVSSDistributionChart from "@/components/charts/CVSSDistributionChart";
import APIDistributionChart from "@/components/charts/APIDistributionChart";
import CVEDetailModal from "@/features/cve/CVEDetailModal";
import DashboardEditModal from "./DashboardEditModal";
import { getWidgetVisibility, isWidgetVisible } from "./widgetConfig";
import type { DashboardResponse } from "@/features/dashboard/types";

const DashboardPage = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [selectedCveId, setSelectedCveId] = useState<string | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [widgetVisibility, setWidgetVisibility] = useState<Record<string, boolean>>(() => getWidgetVisibility());

  // Reload widget visibility when modal closes (after save)
  useEffect(() => {
    if (!isEditModalOpen) {
      setWidgetVisibility(getWidgetVisibility());
    }
  }, [isEditModalOpen]);

  // Check all watchlists mutation
  const checkAllWatchlistsMutation = useMutation({
    mutationFn: async () => {
      const response = await apiClient.post("/watchlists/check-all");
      return response.data;
    },
    onSuccess: (data) => {
      // Refresh dashboard data
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["watchlists"] });
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      
      // Show success message
      alert(`Successfully checked ${data.total_watchlists} watchlist(s). Total ${data.total_checked_items} item(s) checked.`);
    },
    onError: (error: any) => {
      console.error("Error checking watchlists:", error);
      alert(error?.response?.data?.detail || "Failed to check watchlists. Please try again.");
    },
  });
  
  const { data, isLoading, error } = useQuery<DashboardResponse>({
    queryKey: ["dashboard"],
    queryFn: async () => {
      try {
        const response = await apiClient.get<DashboardResponse>("/dashboard/");
        return response.data;
      } catch (err: any) {
        console.error("Dashboard error:", err);
        throw err;
      }
    },
    retry: 1,
    refetchOnWindowFocus: false
  });

  if (isLoading) {
    return <p className="text-slate-400 dark:text-slate-400 light:text-slate-600">Loading dashboard...</p>;
  }

  if (error) {
    const errorMessage = error instanceof Error 
      ? error.message 
      : (error as any)?.message || "Unknown error";
    
    return (
      <div className="rounded-2xl border border-red-800 dark:border-red-800 light:border-red-300 bg-red-950/20 dark:bg-red-950/20 light:bg-red-50 p-6">
        <p className="text-red-400 dark:text-red-400 light:text-red-700 font-semibold mb-2">Error loading dashboard</p>
        <p className="text-red-300 dark:text-red-300 light:text-red-600 text-sm">{errorMessage}</p>
        <p className="text-slate-400 dark:text-slate-400 light:text-slate-600 text-xs mt-2">
          Make sure the backend is running at {import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"}
        </p>
      </div>
    );
  }

  if (!data) {
    return <p className="text-slate-400 dark:text-slate-400 light:text-slate-600">No data available</p>;
  }

  const { stats } = data;

  const handleSaveWidgets = (visibility: Record<string, boolean>) => {
    setWidgetVisibility(visibility);
  };

  return (
    <div className="space-y-6">
      {/* Header with Customize Button */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white dark:text-white light:text-slate-900">Dashboard</h1>
          <p className="text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">Overview of your threat intelligence platform</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => checkAllWatchlistsMutation.mutate()}
            disabled={checkAllWatchlistsMutation.isPending}
            className="flex items-center gap-2 rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white px-4 py-2 text-sm font-medium text-white dark:text-white light:text-slate-900 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
            title="Check all watchlists manually"
          >
            <RefreshCw className={`h-4 w-4 ${checkAllWatchlistsMutation.isPending ? 'animate-spin' : ''}`} />
            Check All Watchlists
          </button>
          <button
            onClick={() => setIsEditModalOpen(true)}
            className="flex items-center gap-2 rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white px-4 py-2 text-sm font-medium text-white dark:text-white light:text-slate-900 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100"
          >
            <Settings className="h-4 w-4" />
            Customize
          </button>
        </div>
      </div>

      {/* Stat Cards Section */}
      {(() => {
        const visibleStatCards = [];
        if (isWidgetVisible('stat_total_queries', widgetVisibility)) {
          visibleStatCards.push(<StatCard key="stat_total_queries" title="Total Queries" value={stats.total_queries} subtitle={`+${stats.queries_today} today`} icon={Activity} />);
        }
        if (isWidgetVisible('stat_active_apis', widgetVisibility)) {
          visibleStatCards.push(<StatCard key="stat_active_apis" title="Active APIs" value={`${stats.active_apis}/${stats.total_apis}`} subtitle="Connected sources" icon={Database} />);
        }
        if (isWidgetVisible('stat_watchlist_assets', widgetVisibility)) {
          visibleStatCards.push(<StatCard key="stat_watchlist_assets" title="Watchlist Assets" value={stats.watchlist_assets} subtitle={`${stats.watchlist_alerts} alerts`} icon={ShieldCheck} />);
        }
        if (isWidgetVisible('stat_reports', widgetVisibility)) {
          visibleStatCards.push(<StatCard key="stat_reports" title="Reports" value={stats.total_reports} subtitle="Generated" icon={FileText} />);
        }
        return visibleStatCards.length > 0 ? (
          <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            {visibleStatCards.map((card, index) => (
              <div key={`stat-card-${index}`}>
                {card}
              </div>
            ))}
          </section>
        ) : null;
      })()}

      {/* Risk Level Stat Cards */}
      {(() => {
        const visibleRiskCards = [];
        if (isWidgetVisible('stat_risk_critical', widgetVisibility)) {
          visibleRiskCards.push(
            <button
              key="stat_risk_critical"
              onClick={() => navigate('/ioc?risk=critical')}
              className="rounded-2xl border border-red-800 dark:border-red-800 light:border-red-300 bg-red-950/20 dark:bg-red-950/20 light:bg-red-50 p-4 shadow-lg shadow-red-900/20 dark:shadow-red-900/20 light:shadow-red-200/20 transition hover:bg-red-950/30 dark:hover:bg-red-950/30 light:hover:bg-red-100 hover:border-red-700 dark:hover:border-red-700 light:hover:border-red-400 cursor-pointer text-left w-full"
            >
              <div className="flex items-center justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <p className="text-xs uppercase tracking-wider text-red-400 dark:text-red-400 light:text-red-600 mb-1">Critical Risks</p>
                  <p className="text-2xl font-bold text-red-400 dark:text-red-400 light:text-red-600 mb-1">{data.risk_distribution.critical || 0}</p>
                  <p className="text-sm text-red-300 dark:text-red-300 light:text-red-500">High priority threats</p>
                </div>
                <div className="flex-shrink-0 rounded-xl bg-red-500/10 dark:bg-red-500/10 light:bg-red-100 p-3 text-red-400 dark:text-red-400 light:text-red-600">
                  <AlertOctagon className="h-5 w-5" />
                </div>
              </div>
            </button>
          );
        }
        if (isWidgetVisible('stat_risk_high', widgetVisibility)) {
          visibleRiskCards.push(
            <button
              key="stat_risk_high"
              onClick={() => navigate('/ioc?risk=high')}
              className="rounded-2xl border border-orange-800 dark:border-orange-800 light:border-orange-300 bg-orange-950/20 dark:bg-orange-950/20 light:bg-orange-50 p-4 shadow-lg shadow-orange-900/20 dark:shadow-orange-900/20 light:shadow-orange-200/20 transition hover:bg-orange-950/30 dark:hover:bg-orange-950/30 light:hover:bg-orange-100 hover:border-orange-700 dark:hover:border-orange-700 light:hover:border-orange-400 cursor-pointer text-left w-full"
            >
              <div className="flex items-center justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <p className="text-xs uppercase tracking-wider text-orange-400 dark:text-orange-400 light:text-orange-600 mb-1">High Risks</p>
                  <p className="text-2xl font-bold text-orange-400 dark:text-orange-400 light:text-orange-600 mb-1">{data.risk_distribution.high || 0}</p>
                  <p className="text-sm text-orange-300 dark:text-orange-300 light:text-orange-500">Requires attention</p>
                </div>
                <div className="flex-shrink-0 rounded-xl bg-orange-500/10 dark:bg-orange-500/10 light:bg-orange-100 p-3 text-orange-400 dark:text-orange-400 light:text-orange-600">
                  <AlertTriangle className="h-5 w-5" />
                </div>
              </div>
            </button>
          );
        }
        if (isWidgetVisible('stat_risk_medium', widgetVisibility)) {
          visibleRiskCards.push(
            <button
              key="stat_risk_medium"
              onClick={() => navigate('/ioc?risk=medium')}
              className="rounded-2xl border border-yellow-800 dark:border-yellow-800 light:border-yellow-300 bg-yellow-950/20 dark:bg-yellow-950/20 light:bg-yellow-50 p-4 shadow-lg shadow-yellow-900/20 dark:shadow-yellow-900/20 light:shadow-yellow-200/20 transition hover:bg-yellow-950/30 dark:hover:bg-yellow-950/30 light:hover:bg-yellow-100 hover:border-yellow-700 dark:hover:border-yellow-700 light:hover:border-yellow-400 cursor-pointer text-left w-full"
            >
              <div className="flex items-center justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <p className="text-xs uppercase tracking-wider text-yellow-400 dark:text-yellow-400 light:text-yellow-600 mb-1">Medium Risks</p>
                  <p className="text-2xl font-bold text-yellow-400 dark:text-yellow-400 light:text-yellow-600 mb-1">{data.risk_distribution.medium || 0}</p>
                  <p className="text-sm text-yellow-300 dark:text-yellow-300 light:text-yellow-500">Monitor closely</p>
                </div>
                <div className="flex-shrink-0 rounded-xl bg-yellow-500/10 dark:bg-yellow-500/10 light:bg-yellow-100 p-3 text-yellow-400 dark:text-yellow-400 light:text-yellow-600">
                  <AlertCircleIcon className="h-5 w-5" />
                </div>
              </div>
            </button>
          );
        }
        if (isWidgetVisible('stat_risk_low', widgetVisibility)) {
          visibleRiskCards.push(
            <button
              key="stat_risk_low"
              onClick={() => navigate('/ioc?risk=low')}
              className="rounded-2xl border border-green-800 dark:border-green-800 light:border-green-300 bg-green-950/20 dark:bg-green-950/20 light:bg-green-50 p-4 shadow-lg shadow-green-900/20 dark:shadow-green-900/20 light:shadow-green-200/20 transition hover:bg-green-950/30 dark:hover:bg-green-950/30 light:hover:bg-green-100 hover:border-green-700 dark:hover:border-green-700 light:hover:border-green-400 cursor-pointer text-left w-full"
            >
              <div className="flex items-center justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <p className="text-xs uppercase tracking-wider text-green-400 dark:text-green-400 light:text-green-600 mb-1">Low Risks</p>
                  <p className="text-2xl font-bold text-green-400 dark:text-green-400 light:text-green-600 mb-1">{data.risk_distribution.low || 0}</p>
                  <p className="text-sm text-green-300 dark:text-green-300 light:text-green-500">Minimal threat</p>
                </div>
                <div className="flex-shrink-0 rounded-xl bg-green-500/10 dark:bg-green-500/10 light:bg-green-100 p-3 text-green-400 dark:text-green-400 light:text-green-600">
                  <ShieldCheck className="h-5 w-5" />
                </div>
              </div>
            </button>
          );
        }
        return visibleRiskCards.length > 0 ? (
          <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            {visibleRiskCards.map((card, index) => (
              <div key={`risk-card-${index}`}>
                {card}
              </div>
            ))}
          </section>
        ) : null;
      })()}

      {/* Top Row: Query Trend, Risk Distribution, IOC Type Distribution, CVE Summary */}
      {(() => {
        const topRowWidgets = [];
        if (isWidgetVisible('chart_query_trend', widgetVisibility)) {
          topRowWidgets.push(
            <div key="chart_query_trend" className="rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/30 dark:bg-slate-900/30 light:bg-white p-6 overflow-hidden">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-white dark:text-white light:text-slate-900 truncate pr-2">Query Trend (7 Days)</h2>
                <TrendingUp className="h-4 w-4 text-brand-400 dark:text-brand-400 light:text-brand-600 flex-shrink-0" />
              </div>
              {data.query_trend && data.query_trend.length > 0 ? (
                <QueryTrendChart data={data.query_trend} />
              ) : (
                <div className="flex h-[300px] items-center justify-center text-slate-400 dark:text-slate-400 light:text-slate-600">
                  No query data available
                </div>
              )}
            </div>
          );
        }
        if (isWidgetVisible('chart_risk_distribution', widgetVisibility)) {
          topRowWidgets.push(
            <div key="chart_risk_distribution" className="rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/30 dark:bg-slate-900/30 light:bg-white p-6 overflow-hidden">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-white dark:text-white light:text-slate-900 truncate pr-2">Risk Distribution</h2>
                <ShieldAlert className="h-4 w-4 text-brand-400 dark:text-brand-400 light:text-brand-600 flex-shrink-0" />
              </div>
              <RiskDistributionChart 
                data={data.risk_distribution} 
                onSegmentClick={(risk) => navigate(`/ioc?risk=${risk}`)}
              />
            </div>
          );
        }
        if (isWidgetVisible('chart_ioc_type_distribution', widgetVisibility)) {
          topRowWidgets.push(
            <div key="chart_ioc_type_distribution" className="rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/30 dark:bg-slate-900/30 light:bg-white p-6 overflow-hidden">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-white dark:text-white light:text-slate-900 truncate pr-2">IOC Type Distribution</h2>
                <BarChart3 className="h-4 w-4 text-brand-400 dark:text-brand-400 light:text-brand-600 flex-shrink-0" />
              </div>
              <IOCTypeDistributionChart data={data.ioc_type_distribution || []} />
            </div>
          );
        }
        if (data.cve_summary && isWidgetVisible('widget_cve_summary', widgetVisibility)) {
          topRowWidgets.push(
            <div key="widget_cve_summary" className="rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/30 dark:bg-slate-900/30 light:bg-white p-6 overflow-hidden">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-white dark:text-white light:text-slate-900 truncate pr-2">CVE Summary</h2>
                <AlertTriangle className="h-4 w-4 text-brand-400 dark:text-brand-400 light:text-brand-600 flex-shrink-0" />
              </div>
              <div className="mt-4 grid gap-3">
                <div className="flex items-center justify-between rounded-lg bg-slate-900/60 dark:bg-slate-900/60 light:bg-slate-50 px-4 py-3">
                  <span className="text-slate-400 dark:text-slate-400 light:text-slate-600">Published (24h)</span>
                  <span className="text-lg font-semibold text-white dark:text-white light:text-slate-900">{data.cve_summary.published_last_24h}</span>
                </div>
                <div className="flex items-center justify-between rounded-lg bg-red-950/30 dark:bg-red-950/30 light:bg-red-50 px-4 py-3 border border-red-800 dark:border-red-800 light:border-red-300">
                  <span className="text-slate-400 dark:text-slate-400 light:text-slate-600">Critical (7d)</span>
                  <span className="text-lg font-semibold text-red-400 dark:text-red-400 light:text-red-600">{data.cve_summary.critical_count}</span>
                </div>
                <div className="flex items-center justify-between rounded-lg bg-orange-950/30 dark:bg-orange-950/30 light:bg-orange-50 px-4 py-3 border border-orange-800 dark:border-orange-800 light:border-orange-300">
                  <span className="text-slate-400 dark:text-slate-400 light:text-slate-600">High (7d)</span>
                  <span className="text-lg font-semibold text-orange-400 dark:text-orange-400 light:text-orange-600">{data.cve_summary.high_count}</span>
                </div>
                {data.cve_summary.last_updated && (
                  <div className="flex items-center justify-between rounded-lg bg-slate-900/60 dark:bg-slate-900/60 light:bg-slate-50 px-4 py-3">
                    <span className="text-slate-400 dark:text-slate-400 light:text-slate-600">Last Updated</span>
                    <span className="text-sm text-slate-500 dark:text-slate-500 light:text-slate-500">
                      {new Date(data.cve_summary.last_updated).toLocaleString()}
                    </span>
                  </div>
                )}
                {data.cve_summary.recent_cves && data.cve_summary.recent_cves.length > 0 && (
                  <div className="mt-2 rounded-lg bg-slate-900/60 dark:bg-slate-900/60 light:bg-slate-50 px-4 py-3 overflow-hidden">
                    <p className="mb-2 text-xs font-medium text-slate-400 dark:text-slate-400 light:text-slate-600">Recent CVEs:</p>
                    <div className="flex flex-wrap gap-1 overflow-hidden">
                      {data.cve_summary.recent_cves.map((cveId, idx) => (
                        <button
                          key={idx}
                          onClick={() => setSelectedCveId(cveId)}
                          className="rounded bg-slate-800 dark:bg-slate-800 light:bg-slate-200 px-2 py-0.5 text-xs font-mono text-brand-400 dark:text-brand-400 light:text-brand-600 hover:bg-slate-700 dark:hover:bg-slate-700 light:hover:bg-slate-300 transition cursor-pointer break-words max-w-full truncate"
                          title={cveId}
                        >
                          {cveId}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        }
        return topRowWidgets.length > 0 ? (
          <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 mb-6">
            {topRowWidgets.map((widget) => widget)}
          </section>
        ) : null;
      })()}

      {/* Bottom Row: API Usage Distribution, API Status, Recent Activity, Watchlist Summary */}
      {(() => {
        const bottomRowWidgets = [];
        if (isWidgetVisible('chart_api_distribution', widgetVisibility)) {
          bottomRowWidgets.push(
            <div key="chart_api_distribution" className="rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/30 dark:bg-slate-900/30 light:bg-white p-6 overflow-hidden">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-white dark:text-white light:text-slate-900 truncate pr-2">API Usage Distribution</h2>
                <PieChartIcon className="h-4 w-4 text-brand-400 dark:text-brand-400 light:text-brand-600 flex-shrink-0" />
              </div>
              {data.api_distribution && data.api_distribution.length > 0 ? (
                <APIDistributionChart data={data.api_distribution} />
              ) : (
                <div className="flex h-[300px] items-center justify-center text-slate-400 dark:text-slate-400 light:text-slate-600">
                  No API usage data available
                </div>
              )}
            </div>
          );
        }
        if (isWidgetVisible('widget_api_status', widgetVisibility)) {
          bottomRowWidgets.push(
            <div key="widget_api_status" className="rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/30 dark:bg-slate-900/30 light:bg-white p-6 overflow-hidden">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-white dark:text-white light:text-slate-900 truncate pr-2">API Status</h2>
                <Database className="h-4 w-4 text-brand-400 dark:text-brand-400 light:text-brand-600 flex-shrink-0" />
              </div>
              <div className="mt-4 space-y-2">
                {data.api_status && data.api_status.length > 0 ? (
                  data.api_status.map((api, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between rounded-lg bg-slate-900/60 dark:bg-slate-900/60 light:bg-slate-50 px-4 py-3 overflow-hidden"
                    >
                      <div className="flex items-center gap-3 min-w-0 flex-1">
                        {api.status === "active" ? (
                          <CheckCircle2 className="h-4 w-4 text-green-400 dark:text-green-400 light:text-green-600 flex-shrink-0" />
                        ) : api.status === "error" ? (
                          <XCircle className="h-4 w-4 text-red-400 dark:text-red-400 light:text-red-600 flex-shrink-0" />
                        ) : (
                          <AlertCircle className="h-4 w-4 text-yellow-400 dark:text-yellow-400 light:text-yellow-600 flex-shrink-0" />
                        )}
                        <div className="min-w-0 flex-1">
                          <span className="text-sm font-medium text-white dark:text-white light:text-slate-900 break-words overflow-hidden block truncate">{api.source}</span>
                          {api.usage_today !== undefined && (
                            <span className="text-xs text-slate-500 dark:text-slate-500 light:text-slate-500">
                              ({api.usage_today} today)
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0 ml-2">
                        <span
                          className={`rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap ${
                            api.status === "active"
                              ? "bg-green-950/30 dark:bg-green-950/30 light:bg-green-50 text-green-400 dark:text-green-400 light:text-green-600"
                              : api.status === "error"
                              ? "bg-red-950/30 dark:bg-red-950/30 light:bg-red-50 text-red-400 dark:text-red-400 light:text-red-600"
                              : "bg-yellow-950/30 dark:bg-yellow-950/30 light:bg-yellow-50 text-yellow-400 dark:text-yellow-400 light:text-yellow-600"
                          }`}
                        >
                          {api.status}
                        </span>
                        {api.last_used && (
                          <span className="text-xs text-slate-500 dark:text-slate-500 light:text-slate-500 whitespace-nowrap">
                            {new Date(api.last_used).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="rounded-lg bg-slate-900/60 dark:bg-slate-900/60 light:bg-slate-50 px-4 py-3 text-center text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">
                    No API sources configured
                  </div>
                )}
              </div>
            </div>
          );
        }
        if (isWidgetVisible('widget_recent_activity', widgetVisibility)) {
          bottomRowWidgets.push(
            <div key="widget_recent_activity" className="rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/30 dark:bg-slate-900/30 light:bg-white p-6 overflow-hidden">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-white dark:text-white light:text-slate-900 truncate pr-2">Recent Activity</h2>
                <Shield className="h-4 w-4 text-brand-400 dark:text-brand-400 light:text-brand-600 flex-shrink-0" />
              </div>
              <div className="mt-4 space-y-3">
                {data.recent_activities.slice(0, 5).map((activity) => (
                  <div key={`${activity.type}-${activity.timestamp}`} className="rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-950/60 dark:bg-slate-950/60 light:bg-slate-50 p-3 overflow-hidden">
                    <p className="text-sm font-medium text-white dark:text-white light:text-slate-900 break-words overflow-hidden">{activity.title}</p>
                    {activity.description ? (
                      <p className="text-xs text-slate-400 dark:text-slate-400 light:text-slate-600 break-words overflow-hidden mt-1">{activity.description}</p>
                    ) : null}
                    <p className="text-xs text-slate-500 dark:text-slate-500 light:text-slate-500 mt-1">{new Date(activity.timestamp).toLocaleString()}</p>
                  </div>
                ))}
              </div>
            </div>
          );
        }
        if (isWidgetVisible('widget_watchlist_summary', widgetVisibility)) {
          bottomRowWidgets.push(
            <div key="widget_watchlist_summary" className="rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/30 dark:bg-slate-900/30 light:bg-white p-6 overflow-hidden">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-white dark:text-white light:text-slate-900 truncate pr-2">Watchlist Summary</h2>
                <ShieldCheck className="h-4 w-4 text-brand-400 dark:text-brand-400 light:text-brand-600 flex-shrink-0" />
              </div>
              <div className="mt-4 grid gap-3">
                <div className="flex items-center justify-between rounded-lg bg-slate-900/60 dark:bg-slate-900/60 light:bg-slate-50 px-4 py-3">
                  <span className="text-slate-400 dark:text-slate-400 light:text-slate-600">Active Watchlists</span>
                  <span className="text-lg font-semibold text-white dark:text-white light:text-slate-900">{data.watchlist_summary.active_watchlists}</span>
                </div>
                <div className="flex items-center justify-between rounded-lg bg-slate-900/60 dark:bg-slate-900/60 light:bg-slate-50 px-4 py-3">
                  <span className="text-slate-400 dark:text-slate-400 light:text-slate-600">Total Assets</span>
                  <span className="text-lg font-semibold text-white dark:text-white light:text-slate-900">{data.watchlist_summary.total_assets}</span>
                </div>
                <div className="flex items-center justify-between rounded-lg bg-slate-900/60 dark:bg-slate-900/60 light:bg-slate-50 px-4 py-3">
                  <span className="text-slate-400 dark:text-slate-400 light:text-slate-600">Alerts</span>
                  <span className="text-lg font-semibold text-red-400 dark:text-red-400 light:text-red-600">{data.watchlist_summary.alerts}</span>
                </div>
                {data.watchlist_summary.last_check && (
                  <div className="flex items-center justify-between rounded-lg bg-slate-900/60 dark:bg-slate-900/60 light:bg-slate-50 px-4 py-3">
                    <span className="text-slate-400 dark:text-slate-400 light:text-slate-600">Last Check</span>
                    <span className="text-sm text-slate-500 dark:text-slate-500 light:text-slate-500">
                      {new Date(data.watchlist_summary.last_check).toLocaleString()}
                    </span>
                  </div>
                )}
              </div>
            </div>
          );
        }
        return bottomRowWidgets.length > 0 ? (
          <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
            {bottomRowWidgets.map((widget) => widget)}
          </section>
        ) : null;
      })()}

      {/* CVE Charts Section */}
      {(() => {
        const visibleCveCharts = [];
        if (isWidgetVisible('cve_chart_trend', widgetVisibility)) {
          visibleCveCharts.push(
            <div key="cve_chart_trend" className="rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/30 dark:bg-slate-900/30 light:bg-white p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-white dark:text-white light:text-slate-900">CVE Publication Trend (7 Days)</h2>
                <TrendingUp className="h-4 w-4 text-brand-400 dark:text-brand-400 light:text-brand-600" />
              </div>
              {data.cve_trend && data.cve_trend.length > 0 ? (
                <CVETrendChart data={data.cve_trend} />
              ) : (
                <div className="flex h-[300px] items-center justify-center text-slate-400 dark:text-slate-400 light:text-slate-600">
                  No CVE trend data available
                </div>
              )}
            </div>
          );
        }
        if (isWidgetVisible('cve_chart_cvss_distribution', widgetVisibility)) {
          visibleCveCharts.push(
            <div key="cve_chart_cvss_distribution" className="rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/30 dark:bg-slate-900/30 light:bg-white p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-white dark:text-white light:text-slate-900">CVSS Score Distribution</h2>
                <BarChart3 className="h-4 w-4 text-brand-400 dark:text-brand-400 light:text-brand-600" />
              </div>
              {data.cvss_distribution && data.cvss_distribution.length > 0 ? (
                <CVSSDistributionChart data={data.cvss_distribution} />
              ) : (
                <div className="flex h-[300px] items-center justify-center text-slate-400 dark:text-slate-400 light:text-slate-600">
                  No CVSS distribution data available
                </div>
              )}
            </div>
          );
        }
        return visibleCveCharts.length > 0 ? (
          <section className="flex flex-wrap gap-6">
            {visibleCveCharts.map((chart, index) => (
              <div key={`cve-chart-${index}`} className="flex-1 min-w-[300px] max-w-full lg:max-w-[calc(50%-0.75rem)]">
                {chart}
              </div>
            ))}
          </section>
        ) : null;
      })()}

      {/* CVE Detail Modal */}
      {selectedCveId && (
        <CVEDetailModal
          cveId={selectedCveId}
          onClose={() => setSelectedCveId(null)}
        />
      )}

      {/* Dashboard Edit Modal */}
      <DashboardEditModal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        onSave={handleSaveWidgets}
      />
    </div>
  );
};

export default DashboardPage;
