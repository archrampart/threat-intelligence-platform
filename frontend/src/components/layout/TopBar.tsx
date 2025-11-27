import { useMemo, useState, useEffect, useRef } from "react";
import { Menu, Bell, Sun, Moon, LogOut, User, Settings, Key, ChevronDown, X } from "lucide-react";
import { useMutation, useQueryClient, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { useAuth } from "@/hooks/useAuth";
import { apiClient } from "@/lib/api";
import type { UserResponse } from "@/features/auth/types";

const TopBar = () => {
  const { user, logout, login } = useAuth();
  const queryClient = useQueryClient();
  const formattedDate = useMemo(() => new Date().toLocaleString(), []);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [showEditProfile, setShowEditProfile] = useState(false);
  const [showChangePassword, setShowChangePassword] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  // Fetch alert stats for badge
  const { data: alertStats } = useQuery({
    queryKey: ["alerts", "stats"],
    queryFn: async () => {
      const response = await apiClient.get("/alerts/stats");
      return response.data;
    },
    refetchInterval: 30000, // Refetch every 30 seconds
    enabled: !!user, // Only fetch if user is logged in
  });
  
  // Theme state - default to dark mode
  const [isDark, setIsDark] = useState(() => {
    const saved = localStorage.getItem("theme");
    if (saved) {
      return saved === "dark";
    }
    // Default to dark mode
    return true;
  });

  useEffect(() => {
    // Apply theme to document on mount and when theme changes
    if (isDark) {
      document.documentElement.classList.add("dark");
      document.documentElement.classList.remove("light");
      document.body.classList.add("dark");
      document.body.classList.remove("light");
    } else {
      document.documentElement.classList.add("light");
      document.documentElement.classList.remove("dark");
      document.body.classList.add("light");
      document.body.classList.remove("dark");
    }
    localStorage.setItem("theme", isDark ? "dark" : "light");
  }, [isDark]);

  // Set initial theme on mount
  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add("dark");
      document.body.classList.add("dark");
    } else {
      document.documentElement.classList.add("light");
      document.body.classList.add("light");
    }
  }, []);

  const toggleTheme = () => {
    setIsDark(!isDark);
  };

  // Close user menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setIsUserMenuOpen(false);
      }
    };

    if (isUserMenuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isUserMenuOpen]);

  return (
    <header className="flex items-center justify-between border-b border-slate-800 px-6 py-4 dark:border-slate-800 light:border-slate-200">
      <div>
        <p className="text-xs uppercase tracking-widest text-slate-500 dark:text-slate-500 light:text-slate-600">Threat Intelligence</p>
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-semibold text-white dark:text-white light:text-slate-900">Operations Console</h1>
        </div>
      </div>
      <div className="flex items-center gap-4 text-slate-400 dark:text-slate-400 light:text-slate-600">
        <span className="hidden text-sm md:inline-flex">{formattedDate}</span>
        <button 
          onClick={toggleTheme}
          className="rounded-full border border-slate-700 dark:border-slate-700 light:border-slate-300 p-2 hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100 transition"
          title={isDark ? "Switch to light mode" : "Switch to dark mode"}
        >
          {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </button>
        <Link
          to="/alerts"
          className="relative rounded-full border border-slate-700 dark:border-slate-700 light:border-slate-300 p-2 hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100 transition"
        >
          <Bell className="h-4 w-4" />
          {alertStats && alertStats.unread > 0 && (
            <span className="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 dark:bg-red-500 light:bg-red-600 text-xs font-bold text-white">
              {alertStats.unread > 99 ? "99+" : alertStats.unread}
            </span>
          )}
        </Link>
        
        {user && (
          <div className="relative" ref={userMenuRef}>
            <button
              onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
              className="flex items-center gap-2 rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white px-3 py-2 hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100 transition"
            >
              <User className="h-4 w-4 text-slate-300 dark:text-slate-300 light:text-slate-700" />
              <span className="hidden text-sm text-slate-300 dark:text-slate-300 light:text-slate-700 md:inline-flex">{user.username}</span>
              <ChevronDown className={`h-4 w-4 text-slate-400 dark:text-slate-400 light:text-slate-600 transition-transform ${isUserMenuOpen ? "rotate-180" : ""}`} />
            </button>

            {isUserMenuOpen && (
              <div className="absolute right-0 mt-2 w-64 rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900 dark:bg-slate-900 light:bg-white shadow-xl z-50">
                <div className="p-4 border-b border-slate-800 dark:border-slate-800 light:border-slate-200">
                  <div className="flex items-center gap-3">
                    <div className="rounded-full bg-brand-500/20 dark:bg-brand-500/20 light:bg-brand-100 p-2">
                      <User className="h-5 w-5 text-brand-400 dark:text-brand-400 light:text-brand-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-white dark:text-white light:text-slate-900 truncate">
                        {user.full_name || user.username}
                      </p>
                      <p className="text-xs text-slate-400 dark:text-slate-400 light:text-slate-600 truncate">
                        {user.email}
                      </p>
                      <p className="text-xs uppercase text-slate-500 dark:text-slate-500 light:text-slate-500 mt-1">
                        {user.role}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="p-2">
                  <button
                    onClick={() => {
                      setIsUserMenuOpen(false);
                      setShowEditProfile(true);
                    }}
                    className="w-full flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-300 dark:text-slate-300 light:text-slate-700 hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100 transition"
                  >
                    <Settings className="h-4 w-4" />
                    <span>Edit Profile</span>
                  </button>
                  <button
                    onClick={() => {
                      setIsUserMenuOpen(false);
                      setShowChangePassword(true);
                    }}
                    className="w-full flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-300 dark:text-slate-300 light:text-slate-700 hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100 transition"
                  >
                    <Key className="h-4 w-4" />
                    <span>Change Password</span>
                  </button>
                </div>

                <div className="p-2 border-t border-slate-800 dark:border-slate-800 light:border-slate-200">
                  <button
                    onClick={() => {
                      setIsUserMenuOpen(false);
                      logout();
                    }}
                    className="w-full flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-red-400 dark:text-red-400 light:text-red-600 hover:bg-red-950/20 dark:hover:bg-red-950/20 light:hover:bg-red-50 transition"
                  >
                    <LogOut className="h-4 w-4" />
                    <span>Logout</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        <button className="rounded-full border border-slate-700 dark:border-slate-700 light:border-slate-300 p-2 hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100 transition md:hidden">
          <Menu className="h-4 w-4" />
        </button>
      </div>

      {showEditProfile && user && (
        <EditProfileModal
          user={user}
          onClose={() => setShowEditProfile(false)}
          onSuccess={async (updatedUser) => {
            setShowEditProfile(false);
            setIsUserMenuOpen(false); // Close dropdown menu
            // Fetch fresh user data from backend to ensure consistency
            try {
              const response = await apiClient.get<UserResponse>("/auth/me");
              const freshUser = response.data;
              const token = localStorage.getItem("access_token");
              if (token) {
                login(token, freshUser);
              }
            } catch (error) {
              console.error("Failed to refresh user data:", error);
              // Fallback to updatedUser from mutation
              const token = localStorage.getItem("access_token");
              if (token) {
                login(token, updatedUser);
              }
            }
          }}
        />
      )}

      {showChangePassword && (
        <ChangePasswordModal
          onClose={() => setShowChangePassword(false)}
        />
      )}
    </header>
  );
};

const EditProfileModal = ({
  user,
  onClose,
  onSuccess
}: {
  user: UserResponse;
  onClose: () => void;
  onSuccess: (updatedUser: UserResponse) => void;
}) => {
  const [formData, setFormData] = useState({
    full_name: user.full_name || "",
    email: user.email || ""
  });

  const updateMutation = useMutation({
    mutationFn: async (data: { full_name?: string; email?: string }) => {
      // Send full_name even if empty string to allow clearing it
      const payload: { full_name?: string; email?: string } = {};
      if (data.email !== undefined) {
        payload.email = data.email;
      }
      if (data.full_name !== undefined) {
        payload.full_name = data.full_name;
      }
      const response = await apiClient.put<UserResponse>("/auth/profile", payload);
      return response.data;
    },
    onSuccess: (updatedUser) => {
      console.log("Profile updated:", updatedUser);
      onSuccess(updatedUser);
    },
    onError: (error) => {
      console.error("Profile update error:", error);
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log("Submitting form data:", formData);
    updateMutation.mutate(formData);
  };

  return (
    <div 
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 dark:bg-black/70 light:bg-black/30 p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
    >
      <div 
        className="relative w-full max-w-md rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900 dark:bg-slate-900 light:bg-white p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-6 flex items-center justify-between">
          <h3 className="text-xl font-semibold text-white dark:text-white light:text-slate-900">Edit Profile</h3>
          <button 
            onClick={onClose} 
            className="text-slate-400 dark:text-slate-400 light:text-slate-600 hover:text-white dark:hover:text-white light:hover:text-slate-900 text-2xl leading-none w-8 h-8 flex items-center justify-center rounded hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100 transition"
            type="button"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">Full Name</label>
            <input
              type="text"
              value={formData.full_name}
              onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
              className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 placeholder:text-slate-500 dark:placeholder:text-slate-500 light:placeholder:text-slate-400 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
              placeholder="Your full name"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">Email</label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 placeholder:text-slate-500 dark:placeholder:text-slate-500 light:placeholder:text-slate-400 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
              placeholder="your.email@example.com"
              required
            />
          </div>

          <div className="rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-950/60 dark:bg-slate-950/60 light:bg-slate-50 p-3">
            <p className="text-xs text-slate-400 dark:text-slate-400 light:text-slate-600">
              <span className="font-medium">Username:</span> {user.username}
            </p>
            <p className="text-xs text-slate-400 dark:text-slate-400 light:text-slate-600 mt-1">
              <span className="font-medium">Role:</span> {user.role}
            </p>
          </div>

          {updateMutation.isError && (
            <div className="rounded-lg border border-red-800 dark:border-red-800 light:border-red-300 bg-red-950/20 dark:bg-red-950/20 light:bg-red-50 p-3 text-sm text-red-400 dark:text-red-400 light:text-red-700">
              {updateMutation.error instanceof Error ? updateMutation.error.message : "Failed to update profile"}
            </div>
          )}

          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white px-4 py-2 text-sm font-medium text-white dark:text-white light:text-slate-900 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={updateMutation.isPending}
              className="rounded-lg bg-brand-600 dark:bg-brand-600 light:bg-brand-500 px-4 py-2 text-sm font-medium text-white dark:text-white light:text-slate-900 transition hover:bg-brand-700 dark:hover:bg-brand-700 light:hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {updateMutation.isPending ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const ChangePasswordModal = ({
  onClose
}: {
  onClose: () => void;
}) => {
  const [formData, setFormData] = useState({
    current_password: "",
    new_password: "",
    confirm_password: ""
  });

  const changePasswordMutation = useMutation({
    mutationFn: async (data: { current_password: string; new_password: string }) => {
      const response = await apiClient.put("/auth/change-password", data);
      return response.data;
    },
    onSuccess: () => {
      alert("Password changed successfully");
      onClose();
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (formData.new_password !== formData.confirm_password) {
      alert("New passwords do not match");
      return;
    }

    if (formData.new_password.length < 6) {
      alert("Password must be at least 6 characters");
      return;
    }

    changePasswordMutation.mutate({
      current_password: formData.current_password,
      new_password: formData.new_password
    });
  };

  return (
    <div 
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 dark:bg-black/70 light:bg-black/30 p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
    >
      <div 
        className="relative w-full max-w-md rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900 dark:bg-slate-900 light:bg-white p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-6 flex items-center justify-between">
          <h3 className="text-xl font-semibold text-white dark:text-white light:text-slate-900">Change Password</h3>
          <button 
            onClick={onClose} 
            className="text-slate-400 dark:text-slate-400 light:text-slate-600 hover:text-white dark:hover:text-white light:hover:text-slate-900 text-2xl leading-none w-8 h-8 flex items-center justify-center rounded hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100 transition"
            type="button"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">Current Password</label>
            <input
              type="password"
              value={formData.current_password}
              onChange={(e) => setFormData({ ...formData, current_password: e.target.value })}
              className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 placeholder:text-slate-500 dark:placeholder:text-slate-500 light:placeholder:text-slate-400 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
              placeholder="Enter current password"
              required
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">New Password</label>
            <input
              type="password"
              value={formData.new_password}
              onChange={(e) => setFormData({ ...formData, new_password: e.target.value })}
              className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 placeholder:text-slate-500 dark:placeholder:text-slate-500 light:placeholder:text-slate-400 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
              placeholder="Enter new password"
              required
              minLength={6}
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">Confirm New Password</label>
            <input
              type="password"
              value={formData.confirm_password}
              onChange={(e) => setFormData({ ...formData, confirm_password: e.target.value })}
              className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 placeholder:text-slate-500 dark:placeholder:text-slate-500 light:placeholder:text-slate-400 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
              placeholder="Confirm new password"
              required
              minLength={6}
            />
          </div>

          {changePasswordMutation.isError && (
            <div className="rounded-lg border border-red-800 dark:border-red-800 light:border-red-300 bg-red-950/20 dark:bg-red-950/20 light:bg-red-50 p-3 text-sm text-red-400 dark:text-red-400 light:text-red-700">
              {changePasswordMutation.error instanceof Error ? changePasswordMutation.error.message : "Failed to change password"}
            </div>
          )}

          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white px-4 py-2 text-sm font-medium text-white dark:text-white light:text-slate-900 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={changePasswordMutation.isPending}
              className="rounded-lg bg-brand-600 dark:bg-brand-600 light:bg-brand-500 px-4 py-2 text-sm font-medium text-white dark:text-white light:text-slate-900 transition hover:bg-brand-700 dark:hover:bg-brand-700 light:hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {changePasswordMutation.isPending ? "Changing..." : "Change Password"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default TopBar;
