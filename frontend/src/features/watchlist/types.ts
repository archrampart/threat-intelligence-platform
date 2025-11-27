export interface WatchlistAsset {
  id: string;
  ioc_type: string;
  ioc_value: string;
  description?: string;
  risk_threshold?: string;
  is_active: boolean;
  created_at?: string;
}

export interface WatchlistBase {
  name: string;
  description?: string;
  check_interval: number;
  notification_enabled: boolean;
}

export interface WatchlistCreate extends WatchlistBase {
  assets: WatchlistAsset[];
}

export interface Watchlist extends WatchlistBase {
  id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  assets: WatchlistAsset[];
  shared_with_user_ids?: string[]; // User IDs of viewers who can access this watchlist
}

export interface WatchlistListResponse {
  watchlists: Watchlist[];
}

export interface AssetCheckHistory {
  id: string;
  check_date: string;
  risk_score?: string;
  status?: string;
  threat_intelligence_data?: Record<string, any>;
  sources_checked?: string[];
  alert_triggered: boolean;
}

export interface AssetCheckHistoryListResponse {
  items: AssetCheckHistory[];
  total: number;
}

