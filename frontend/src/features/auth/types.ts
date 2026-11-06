export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token?: string | null;
  refresh_token?: string | null;
}

export interface UserResponse {
  id: string;
  username: string;
  email: string;
  full_name?: string;
  role: "admin" | "analyst" | "viewer";
  is_active: boolean;
  language_preference: string;
  created_at?: string;
}

