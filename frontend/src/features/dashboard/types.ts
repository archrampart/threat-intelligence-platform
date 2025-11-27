export interface DashboardStats {
  total_queries: number;
  queries_today: number;
  active_apis: number;
  total_apis: number;
  watchlist_assets: number;
  watchlist_alerts: number;
  critical_cves: number;
  total_reports: number;
}

export interface RiskDistribution {
  low: number;
  medium: number;
  high: number;
  critical: number;
  unknown: number;
}

export interface APIDistribution {
  source: string;
  count: number;
  percentage: number;
}

export interface IOCTypeDistribution {
  ioc_type: string;
  count: number;
  percentage: number;
}

export interface QueryTrend {
  date: string;
  count: number;
}

export interface RecentActivity {
  type: string;
  title: string;
  description?: string;
  timestamp: string;
}

export interface WatchlistSummary {
  active_watchlists: number;
  total_assets: number;
  alerts: number;
  last_check?: string;
}

export interface APIStatus {
  source: string;
  is_active: boolean;
  usage_today?: number;
  limit?: number;
  status: string;
  last_used?: string;
}

export interface CVESummary {
  published_last_24h: number;
  critical_count: number;
  high_count: number;
  last_updated?: string;
  recent_cves: string[];
}

export interface CVETrend {
  date: string;
  count: number;
}

export interface CVSSDistribution {
  score_range: string;
  count: number;
}

export interface DashboardResponse {
  stats: DashboardStats;
  risk_distribution: RiskDistribution;
  api_distribution: APIDistribution[];
  ioc_type_distribution: IOCTypeDistribution[];
  query_trend: QueryTrend[];
  recent_activities: RecentActivity[];
  watchlist_summary: WatchlistSummary;
  api_status: APIStatus[];
  cve_summary?: CVESummary;
  cve_trend?: CVETrend[];
  cvss_distribution?: CVSSDistribution[];
  generated_at: string;
}
