import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, User, Mail, Shield, Trash2, Edit, Check, X, Search, Filter, AlertTriangle } from "lucide-react";

import { apiClient } from "@/lib/api";
import type { UserResponse, UserListResponse, UserCreate, UserUpdate, ChangeRoleRequest } from "@/features/users/types";

const UsersPage = () => {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<boolean | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingUser, setEditingUser] = useState<UserResponse | null>(null);
  const pageSize = 20;

  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery<UserListResponse>({
    queryKey: ["users", page, search, roleFilter, statusFilter],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString()
      });
      if (search) {
        params.append("search", search);
      }
      if (roleFilter) {
        params.append("role", roleFilter);
      }
      if (statusFilter !== null) {
        params.append("is_active", statusFilter.toString());
      }
      const response = await apiClient.get<UserListResponse>(`/users/?${params}`);
      return response.data;
    }
  });

  const deleteMutation = useMutation({
    mutationFn: async (userId: string) => {
      await apiClient.delete(`/users/${userId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
    }
  });

  const activateMutation = useMutation({
    mutationFn: async ({ userId, isActive }: { userId: string; isActive: boolean }) => {
      const response = await apiClient.put(`/users/${userId}/activate?is_active=${isActive}`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (error: any) => {
      console.error("Failed to update user status:", error);
      alert(`Failed to update user status: ${error?.response?.data?.detail || error?.message || "Unknown error"}`);
    }
  });

  const changeRoleMutation = useMutation({
    mutationFn: async ({ userId, role }: { userId: string; role: string }) => {
      const response = await apiClient.put(`/users/${userId}/role`, { role } as ChangeRoleRequest);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (error: any) => {
      console.error("Failed to change user role:", error);
      alert(`Failed to change user role: ${error?.response?.data?.detail || error?.message || "Unknown error"}`);
    }
  });

  const hardDeleteMutation = useMutation({
    mutationFn: async (userId: string) => {
      await apiClient.delete(`/users/${userId}/hard`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (error: any) => {
      console.error("Failed to delete user:", error);
      alert(`Failed to delete user: ${error?.response?.data?.detail || error?.message || "Unknown error"}`);
    }
  });

  const handleDelete = (userId: string, username: string) => {
    if (confirm(`Are you sure you want to deactivate user "${username}"?`)) {
      deleteMutation.mutate(userId);
    }
  };

  const handleHardDelete = (userId: string, username: string) => {
    if (confirm(`⚠️ WARNING: Are you sure you want to PERMANENTLY DELETE user "${username}"?\n\nThis action cannot be undone!`)) {
      hardDeleteMutation.mutate(userId);
    }
  };

  const handleActivate = (userId: string, currentStatus: boolean) => {
    try {
      activateMutation.mutate({ userId, isActive: !currentStatus });
    } catch (error) {
      console.error("Error activating user:", error);
    }
  };

  const handleChangeRole = (userId: string, newRole: string) => {
    try {
      changeRoleMutation.mutate({ userId, role: newRole });
    } catch (error) {
      console.error("Error changing role:", error);
    }
  };

  const getRoleColor = (role: string) => {
    switch (role.toLowerCase()) {
      case "admin":
        return "text-red-400 dark:text-red-400 light:text-red-600 bg-red-950/30 dark:bg-red-950/30 light:bg-red-50 border-red-800 dark:border-red-800 light:border-red-300";
      case "analyst":
        return "text-blue-400 dark:text-blue-400 light:text-blue-600 bg-blue-950/30 dark:bg-blue-950/30 light:bg-blue-50 border-blue-800 dark:border-blue-800 light:border-blue-300";
      case "viewer":
        return "text-green-400 dark:text-green-400 light:text-green-600 bg-green-950/30 dark:bg-green-950/30 light:bg-green-50 border-green-800 dark:border-green-800 light:border-green-300";
      default:
        return "text-slate-400 dark:text-slate-400 light:text-slate-600 bg-slate-900/30 dark:bg-slate-900/30 light:bg-slate-50 border-slate-800 dark:border-slate-800 light:border-slate-200";
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-white dark:text-white light:text-slate-900">User Management</h2>
          <p className="text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">Manage users, roles, and permissions</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 rounded-lg bg-brand-600 dark:bg-brand-600 light:bg-brand-500 px-4 py-2 font-medium text-white transition hover:bg-brand-700 dark:hover:bg-brand-700 light:hover:bg-brand-600"
        >
          <Plus className="h-4 w-4" />
          New User
        </button>
      </div>

      {/* Search and Filters */}
      <div className="rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/40 dark:bg-slate-900/40 light:bg-white p-6">
        <div className="grid gap-4 md:grid-cols-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400 dark:text-slate-400 light:text-slate-600" />
            <input
              type="text"
              placeholder="Search by username or email..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white pl-10 pr-4 py-2 text-sm text-white dark:text-white light:text-slate-900 placeholder-slate-500 dark:placeholder-slate-500 light:placeholder-slate-400 focus:border-brand-500 focus:outline-none"
            />
          </div>
          <div>
            <select
              value={roleFilter}
              onChange={(e) => {
                setRoleFilter(e.target.value);
                setPage(1);
              }}
              className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-sm text-white dark:text-white light:text-slate-900 focus:border-brand-500 focus:outline-none"
            >
              <option value="">All Roles</option>
              <option value="admin">Admin</option>
              <option value="analyst">Analyst</option>
              <option value="viewer">Viewer</option>
            </select>
          </div>
          <div>
            <select
              value={statusFilter === null ? "" : statusFilter.toString()}
              onChange={(e) => {
                const value = e.target.value;
                setStatusFilter(value === "" ? null : value === "true");
                setPage(1);
              }}
              className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-sm text-white dark:text-white light:text-slate-900 focus:border-brand-500 focus:outline-none"
            >
              <option value="">All Status</option>
              <option value="true">Active</option>
              <option value="false">Inactive</option>
            </select>
          </div>
        </div>
      </div>

      {/* Users List */}
      {isLoading ? (
        <div className="rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/40 dark:bg-slate-900/40 light:bg-white p-12 text-center">
          <p className="text-slate-400 dark:text-slate-400 light:text-slate-600">Loading users...</p>
        </div>
      ) : data && data.items.length > 0 ? (
        <div className="space-y-4">
          <div className="rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/40 dark:bg-slate-900/40 light:bg-white overflow-hidden">
            <table className="w-full">
              <thead className="bg-slate-950/60 dark:bg-slate-950/60 light:bg-slate-50 border-b border-slate-800 dark:border-slate-800 light:border-slate-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase text-slate-400 dark:text-slate-400 light:text-slate-600">User</th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase text-slate-400 dark:text-slate-400 light:text-slate-600">Role</th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase text-slate-400 dark:text-slate-400 light:text-slate-600">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase text-slate-400 dark:text-slate-400 light:text-slate-600">Language</th>
                  <th className="px-6 py-3 text-right text-xs font-medium uppercase text-slate-400 dark:text-slate-400 light:text-slate-600">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 dark:divide-slate-800 light:divide-slate-200">
                {data.items.map((user) => (
                  <tr key={user.id} className="hover:bg-slate-900/40 dark:hover:bg-slate-900/40 light:hover:bg-slate-50 transition">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-500/20 dark:bg-brand-500/20 light:bg-brand-100 text-brand-400 dark:text-brand-400 light:text-brand-600">
                          <User className="h-5 w-5" />
                        </div>
                        <div>
                          <div className="font-medium text-white dark:text-white light:text-slate-900">
                            {user.full_name || user.username}
                          </div>
                          <div className="flex items-center gap-2 text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">
                            <Mail className="h-3 w-3" />
                            {user.email}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <select
                        value={user.role}
                        onChange={(e) => handleChangeRole(user.id, e.target.value)}
                        disabled={changeRoleMutation.isPending}
                        className={`rounded-full border px-3 py-1 text-xs font-medium ${getRoleColor(user.role)} focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed`}
                      >
                        <option value="admin">Admin</option>
                        <option value="analyst">Analyst</option>
                        <option value="viewer">Viewer</option>
                      </select>
                    </td>
                    <td className="px-6 py-4">
                      <button
                        onClick={() => handleActivate(user.id, user.is_active)}
                        disabled={activateMutation.isPending}
                        className={`flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium transition disabled:opacity-50 disabled:cursor-not-allowed ${
                          user.is_active
                            ? "border-green-800 dark:border-green-800 light:border-green-300 bg-green-950/20 dark:bg-green-950/20 light:bg-green-50 text-green-400 dark:text-green-400 light:text-green-700"
                            : "border-red-800 dark:border-red-800 light:border-red-300 bg-red-950/20 dark:bg-red-950/20 light:bg-red-50 text-red-400 dark:text-red-400 light:text-red-700"
                        }`}
                      >
                        {activateMutation.isPending ? (
                          <>
                            <div className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
                            Updating...
                          </>
                        ) : user.is_active ? (
                          <>
                            <Check className="h-3 w-3" />
                            Active
                          </>
                        ) : (
                          <>
                            <X className="h-3 w-3" />
                            Inactive
                          </>
                        )}
                      </button>
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-400 dark:text-slate-400 light:text-slate-600 uppercase">
                      {user.language_preference}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => setEditingUser(user)}
                          className="rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white p-2 text-slate-400 dark:text-slate-400 light:text-slate-600 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100 hover:text-white dark:hover:text-white light:hover:text-slate-900"
                          title="Edit user"
                        >
                          <Edit className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(user.id, user.username)}
                          className="rounded-lg border border-orange-800 dark:border-orange-800 light:border-orange-300 bg-orange-950/20 dark:bg-orange-950/20 light:bg-orange-50 p-2 text-orange-400 dark:text-orange-400 light:text-orange-700 transition hover:bg-orange-950/40 dark:hover:bg-orange-950/40 light:hover:bg-orange-100"
                          title="Deactivate user (soft delete)"
                        >
                          <X className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => handleHardDelete(user.id, user.username)}
                          disabled={hardDeleteMutation.isPending}
                          className="rounded-lg border border-red-800 dark:border-red-800 light:border-red-300 bg-red-950/20 dark:bg-red-950/20 light:bg-red-50 p-2 text-red-400 dark:text-red-400 light:text-red-700 transition hover:bg-red-950/40 dark:hover:bg-red-950/40 light:hover:bg-red-100 disabled:opacity-50"
                          title="Permanently delete user"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {(data.total_pages || 0) > 1 && (
            <div className="flex items-center justify-between">
              <div className="text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">
                Showing {((page - 1) * pageSize) + 1} to {Math.min(page * pageSize, data.total)} of {data.total} users
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white px-4 py-2 text-sm text-white dark:text-white light:text-slate-900 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage(p => p + 1)}
                  disabled={page >= (data.total_pages || 1)}
                  className="rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white px-4 py-2 text-sm text-white dark:text-white light:text-slate-900 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900/30 dark:bg-slate-900/30 light:bg-slate-50 p-12 text-center">
          <User className="mx-auto mb-4 h-12 w-12 text-slate-600 dark:text-slate-600 light:text-slate-400" />
          <p className="text-slate-400 dark:text-slate-400 light:text-slate-600">No users found</p>
        </div>
      )}

      {/* Create User Modal */}
      {showCreateModal && (
        <CreateUserModal
          onClose={() => {
            console.log("Closing create modal");
            setShowCreateModal(false);
          }}
          onSuccess={() => {
            console.log("Create modal success callback");
            setShowCreateModal(false);
            queryClient.invalidateQueries({ queryKey: ["users"] });
          }}
        />
      )}

      {/* Edit User Modal */}
      {editingUser && editingUser.id && (
        <EditUserModal
          user={editingUser}
          onClose={() => setEditingUser(null)}
          onSuccess={() => {
            setEditingUser(null);
            queryClient.invalidateQueries({ queryKey: ["users"] });
          }}
        />
      )}
    </div>
  );
};

// Create User Modal Component
const CreateUserModal = ({
  onClose,
  onSuccess
}: {
  onClose: () => void;
  onSuccess: () => void;
}) => {
  const [formData, setFormData] = useState<UserCreate>({
    username: "",
    email: "",
    password: "",
    role: "viewer" as const,
    is_active: true,
    full_name: undefined,
    language_preference: "en",
  });

  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: async (data: UserCreate) => {
      try {
        // Validate required fields
        if (!data.username || !data.username.trim()) {
          throw new Error("Username is required");
        }
        if (!data.email || !data.email.trim()) {
          throw new Error("Email is required");
        }
        if (!data.password || data.password.length < 6) {
          throw new Error("Password must be at least 6 characters");
        }

        // Clean up the data - remove empty strings for optional fields
        const cleanedData: Record<string, any> = {
          username: data.username.trim(),
          email: data.email.trim().toLowerCase(),
          password: data.password,
          role: (data.role || "viewer").toLowerCase(),
          is_active: data.is_active !== undefined ? Boolean(data.is_active) : true,
          language_preference: data.language_preference || "en",
        };
        
        // Only include full_name if it's not empty - Pydantic will use default (None) if field is missing
        if (data.full_name && typeof data.full_name === "string" && data.full_name.trim()) {
          cleanedData.full_name = data.full_name.trim();
        }
        // Don't include full_name at all if it's empty - let Pydantic use default None
        
        console.log("Creating user with data:", { ...cleanedData, password: "***" });
        console.log("Data type check:", {
          role: typeof cleanedData.role,
          is_active: typeof cleanedData.is_active,
          full_name: typeof cleanedData.full_name,
        });
        
        const response = await apiClient.post<UserResponse>("/users/", cleanedData);
        console.log("User created successfully:", response.data);
        return response.data;
      } catch (error: any) {
        console.error("Error in createMutation:", error);
        throw error;
      }
    },
    onSuccess: (data) => {
      console.log("User creation successful, resetting form", data);
      // Use setTimeout to avoid state update issues
      setTimeout(() => {
        try {
          // Reset form
          setFormData({
            username: "",
            email: "",
            password: "",
            role: "viewer" as const,
            is_active: true,
            full_name: undefined,
            language_preference: "en",
          });
          queryClient.invalidateQueries({ queryKey: ["users"] });
          
          // Call onSuccess callback safely with a small delay
          setTimeout(() => {
            try {
              if (typeof onSuccess === "function") {
                onSuccess();
              }
            } catch (error) {
              console.error("Error calling onSuccess:", error);
            }
          }, 100);
        } catch (error) {
          console.error("Error in onSuccess callback:", error);
        }
      }, 0);
    },
    onError: (error: any) => {
      console.error("Failed to create user:", error);
      console.error("Error details:", {
        message: error?.message,
        response: error?.response?.data,
        status: error?.response?.status,
        statusText: error?.response?.statusText,
      });
      // Show user-friendly error message
      if (error?.response?.data?.detail) {
        const detail = error.response.data.detail;
        if (Array.isArray(detail)) {
          // Pydantic validation errors
          const errorMessages = detail.map((err: any) => {
            const field = err.loc ? err.loc.join('.') : 'unknown';
            return `${field}: ${err.msg}`;
          }).join('\n');
          alert(`Validation Error:\n${errorMessages}`);
        } else if (typeof detail === 'string') {
          alert(`Error: ${detail}`);
        } else {
          alert(`Error: ${JSON.stringify(detail)}`);
        }
      } else {
        alert(`Failed to create user: ${error?.message || 'Unknown error'}`);
      }
    }
  });

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    console.log("Form submitted with data:", { ...formData, password: "***" });
    try {
      createMutation.mutate(formData);
    } catch (error) {
      console.error("Error in handleSubmit:", error);
    }
  };

  const handleClose = () => {
    try {
      if (typeof onClose === "function") {
        onClose();
      }
    } catch (error) {
      console.error("Error closing modal:", error);
    }
  };

  return (
      <div 
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/50 light:bg-black/30"
        onClick={(e) => {
          if (e.target === e.currentTarget) {
            handleClose();
          }
        }}
      >
        <div 
          className="w-full max-w-md rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900 dark:bg-slate-900 light:bg-white p-6"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-xl font-semibold text-white dark:text-white light:text-slate-900">Create User</h3>
            <button onClick={handleClose} className="text-slate-400 dark:text-slate-400 light:text-slate-600 hover:text-white dark:hover:text-white light:hover:text-slate-900">
              ✕
            </button>
          </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-400 dark:text-slate-400 light:text-slate-600">Username</label>
            <input
              type="text"
              required
              value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 focus:border-brand-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-400 dark:text-slate-400 light:text-slate-600">Email</label>
            <input
              type="email"
              required
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 focus:border-brand-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-400 dark:text-slate-400 light:text-slate-600">Password</label>
            <input
              type="password"
              required
              minLength={6}
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 focus:border-brand-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-400 dark:text-slate-400 light:text-slate-600">Full Name (Optional)</label>
            <input
              type="text"
              value={formData.full_name ?? ""}
              onChange={(e) => {
                const value = e.target.value;
                setFormData({ 
                  ...formData, 
                  full_name: value === "" ? undefined : value 
                });
              }}
              className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 focus:border-brand-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-400 dark:text-slate-400 light:text-slate-600">Role</label>
            <select
              value={formData.role}
              onChange={(e) => setFormData({ ...formData, role: e.target.value as "admin" | "analyst" | "viewer" })}
              className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 focus:border-brand-500 focus:outline-none"
            >
              <option value="admin">Admin</option>
              <option value="analyst">Analyst</option>
              <option value="viewer">Viewer</option>
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-400 dark:text-slate-400 light:text-slate-600">Language</label>
            <select
              value={formData.language_preference}
              onChange={(e) => setFormData({ ...formData, language_preference: e.target.value })}
              className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 focus:border-brand-500 focus:outline-none"
            >
              <option value="en">English</option>
              <option value="tr">Turkish</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="is_active"
              checked={formData.is_active ?? true}
              onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
              className="h-4 w-4 rounded border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white text-brand-500 focus:ring-brand-500"
            />
            <label htmlFor="is_active" className="text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">Active</label>
          </div>

          {createMutation.isError && (
            <div className="rounded-lg border border-red-800 dark:border-red-800 light:border-red-300 bg-red-950/20 dark:bg-red-950/20 light:bg-red-50 p-3 text-sm text-red-400 dark:text-red-400 light:text-red-700">
              {(createMutation.error as any)?.response?.data?.detail || "Failed to create user"}
            </div>
          )}

          <div className="flex gap-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="flex-1 rounded-lg bg-brand-600 dark:bg-brand-600 light:bg-brand-500 px-4 py-2 font-medium text-white transition hover:bg-brand-700 dark:hover:bg-brand-700 light:hover:bg-brand-600 disabled:opacity-50"
            >
              {createMutation.isPending ? "Creating..." : "Create User"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// Edit User Modal Component
const EditUserModal = ({
  user,
  onClose,
  onSuccess
}: {
  user: UserResponse;
  onClose: () => void;
  onSuccess: () => void;
}) => {
  const [formData, setFormData] = useState<UserUpdate>({
    username: user?.username || "",
    email: user?.email || "",
    role: user?.role || "viewer",
    is_active: user?.is_active ?? true,
    full_name: user?.full_name || "",
    language_preference: user?.language_preference || "en",
  });

  const queryClient = useQueryClient();

  // Update formData when user changes
  useEffect(() => {
    if (user) {
      setFormData({
        username: user.username || "",
        email: user.email || "",
        role: user.role || "viewer",
        is_active: user.is_active ?? true,
        full_name: user.full_name || "",
        language_preference: user.language_preference || "en",
      });
    }
  }, [user]);

  const updateMutation = useMutation({
    mutationFn: async (data: UserUpdate) => {
      if (!user || !user.id) {
        throw new Error("User ID is required");
      }
      const response = await apiClient.put<UserResponse>(`/users/${user.id}`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      onSuccess();
    },
    onError: (error: any) => {
      console.error("Failed to update user:", error);
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!user || !user.id) {
      console.error("Cannot submit: user or user.id is missing");
      return;
    }
    updateMutation.mutate(formData);
  };

  if (!user || !user.id) {
    return null;
  }

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/50 light:bg-black/30"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
    >
      <div 
        className="w-full max-w-md rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900 dark:bg-slate-900 light:bg-white p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-xl font-semibold text-white dark:text-white light:text-slate-900">Edit User</h3>
          <button onClick={onClose} className="text-slate-400 dark:text-slate-400 light:text-slate-600 hover:text-white dark:hover:text-white light:hover:text-slate-900">
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-400 dark:text-slate-400 light:text-slate-600">Username</label>
            <input
              type="text"
              required
              value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 focus:border-brand-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-400 dark:text-slate-400 light:text-slate-600">Email</label>
            <input
              type="email"
              required
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 focus:border-brand-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-400 dark:text-slate-400 light:text-slate-600">Full Name (Optional)</label>
            <input
              type="text"
              value={formData.full_name || ""}
              onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
              className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 focus:border-brand-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-400 dark:text-slate-400 light:text-slate-600">Role</label>
            <select
              value={formData.role}
              onChange={(e) => setFormData({ ...formData, role: e.target.value as "admin" | "analyst" | "viewer" })}
              className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 focus:border-brand-500 focus:outline-none"
            >
              <option value="admin">Admin</option>
              <option value="analyst">Analyst</option>
              <option value="viewer">Viewer</option>
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-400 dark:text-slate-400 light:text-slate-600">Language</label>
            <select
              value={formData.language_preference}
              onChange={(e) => setFormData({ ...formData, language_preference: e.target.value })}
              className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 focus:border-brand-500 focus:outline-none"
            >
              <option value="en">English</option>
              <option value="tr">Turkish</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="edit_is_active"
              checked={formData.is_active ?? true}
              onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
              className="h-4 w-4 rounded border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white text-brand-500 focus:ring-brand-500"
            />
            <label htmlFor="edit_is_active" className="text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">Active</label>
          </div>

          {updateMutation.isError && (
            <div className="rounded-lg border border-red-800 dark:border-red-800 light:border-red-300 bg-red-950/20 dark:bg-red-950/20 light:bg-red-50 p-3 text-sm text-red-400 dark:text-red-400 light:text-red-700">
              {(updateMutation.error as any)?.response?.data?.detail || "Failed to update user"}
            </div>
          )}

          <div className="flex gap-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={updateMutation.isPending}
              className="flex-1 rounded-lg bg-brand-600 dark:bg-brand-600 light:bg-brand-500 px-4 py-2 font-medium text-white transition hover:bg-brand-700 dark:hover:bg-brand-700 light:hover:bg-brand-600 disabled:opacity-50"
            >
              {updateMutation.isPending ? "Updating..." : "Update User"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default UsersPage;

