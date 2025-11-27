export interface ReportCreate {
  title: string;
  description?: string;
  ioc_query_ids?: string[];
  format: string;
  // Filter options for IOC queries
  watchlist_id?: string;
  ioc_type?: string;
  risk_level?: string;
  start_date?: string;
  end_date?: string;
  source?: string;
}

export interface ReportUpdate {
  title?: string;
  description?: string;
  format?: string;
}

export interface ReportResponse {
  id: string;
  user_id: string;
  title: string;
  description?: string;
  content?: string;
  format: string;
  shared_link?: string;
  ioc_query_ids?: string[];
  created_at: string;
  updated_at: string;
}

export interface ReportListResponse {
  items: ReportResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ReportExportRequest {
  format: string;
  include_raw_data: boolean;
}






