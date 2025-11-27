export interface IOCQueryRequest {
  ioc_type: "ip" | "domain" | "url" | "hash";
  ioc_value: string;
  sources?: string[];
}

export interface IOCSourceResult {
  source: string;
  status: string;
  risk_score?: number;
  description?: string;
  raw?: Record<string, unknown>;
}

export interface IOCQueryResponse {
  ioc_type: string;
  ioc_value: string;
  overall_risk?: string;
  queried_sources: IOCSourceResult[];
  queried_at: string;
}

export interface IOCQueryHistoryItem {
  id: string;
  ioc_type: string;
  ioc_value: string;
  risk_score?: number;
  status?: string;
  query_date: string;
  created_at: string;
  queried_sources?: IOCSourceResult[];  // Sources that reported this risk
}

export interface IOCQueryHistoryListResponse {
  items: IOCQueryHistoryItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}



