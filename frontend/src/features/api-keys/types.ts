export interface APIKeyCreate {
  api_source_id: string;
  api_key: string;
  username?: string;
  password?: string;
  api_url?: string;
  update_mode: "manual" | "auto";
  is_active: boolean;
}

export interface APIKeyUpdate {
  api_key?: string;
  username?: string;
  password?: string;
  api_url?: string;
  update_mode?: "manual" | "auto";
  is_active?: boolean;
}

export interface APIKeyResponse {
  id: string;
  user_id: string;
  api_source_id: string;
  api_source_name?: string;
  username?: string;
  api_url?: string;
  update_mode: string;
  is_active: boolean;
  test_status: string;
  last_test_date?: string;
  last_used?: string;
  rate_limit?: string;
  created_at: string;
  updated_at: string;
}

export interface APIKeyListResponse {
  items: APIKeyResponse[];
  total: number;
}

export interface APIKeyTestRequest {
  test_ioc_type: string;
  test_ioc_value: string;
  api_key?: string;
  username?: string;
  password?: string;
  api_url?: string;
}

export interface APIKeyTestResponse {
  success: boolean;
  message: string;
  test_status: string;
  error?: string;
  response_data?: Record<string, unknown>;
}











