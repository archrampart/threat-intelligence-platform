export enum AlertType {
  WATCHLIST = "watchlist",
  IOC_QUERY = "ioc_query",
  CVE = "cve",
  SYSTEM = "system",
}

export enum AlertSeverity {
  LOW = "low",
  MEDIUM = "medium",
  HIGH = "high",
  CRITICAL = "critical",
}

export interface Alert {
  id: string;
  user_id: string;
  watchlist_id?: string;
  asset_id?: string;
  alert_type: AlertType;
  severity: AlertSeverity;
  title: string;
  message?: string;
  metadata?: Record<string, any>;
  is_read: boolean;
  created_at: string;
}

export interface AlertListResponse {
  items: Alert[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AlertStatsResponse {
  total: number;
  unread: number;
  by_severity: Record<string, number>;
  by_type: Record<string, number>;
}











