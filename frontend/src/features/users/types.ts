export interface UserResponse {
  id: string;
  username: string;
  email: string;
  full_name?: string;
  role: "admin" | "analyst" | "viewer";
  is_active: boolean;
  language_preference: string;
}

export interface UserCreate {
  username: string;
  email: string;
  password: string;
  role: "admin" | "analyst" | "viewer";
  is_active?: boolean;
  full_name?: string;
  language_preference?: string;
}

export interface UserUpdate {
  username?: string;
  email?: string;
  role?: "admin" | "analyst" | "viewer";
  is_active?: boolean;
  full_name?: string;
  language_preference?: string;
}

export interface UserListResponse {
  items: UserResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ChangeRoleRequest {
  role: "admin" | "analyst" | "viewer";
}





