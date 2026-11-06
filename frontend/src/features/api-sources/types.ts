export type SourceAccess = "none" | "free_key" | "freemium" | "on_request" | "paid" | "unknown";

export interface APISourceResponse {
  id: string;
  access?: SourceAccess;
  key_signup_url?: string | null;
  name: string;
  display_name: string;
  description?: string;
  api_type: string;
  base_url: string;
  documentation_url?: string;
  supported_ioc_types?: string[];
  authentication_type: string;
  request_config?: Record<string, unknown>;
  response_config?: Record<string, unknown>;
  rate_limit_config?: Record<string, unknown>;
  is_active: boolean;
  created_by?: string;
  created_at: string;
  updated_at: string;
}











