import { useState, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, ShieldCheck, AlertTriangle, RefreshCw, Trash2, Edit, Eye, Upload, History, Power, Share2 } from "lucide-react";

import { apiClient } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import type { Watchlist, WatchlistCreate, WatchlistListResponse, WatchlistAsset, AssetCheckHistoryListResponse } from "@/features/watchlist/types";

const WatchlistPage = () => {
  const { user } = useAuth();
  const canManageWatchlists = user?.role === "admin" || user?.role === "analyst";
  const [selectedWatchlist, setSelectedWatchlist] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState<string | null>(null);
  const [showShareModal, setShowShareModal] = useState<string | null>(null);

  const queryClient = useQueryClient();

  const { data: watchlists, isLoading } = useQuery<WatchlistListResponse>({
    queryKey: ["watchlists", user?.id, user?.role],
    queryFn: async () => {
      const response = await apiClient.get<WatchlistListResponse>("/watchlists/");
      return response.data;
    },
    enabled: !!user, // Only fetch when user is available
  });

  const selectedWatchlistData = watchlists?.watchlists.find((w) => w.id === selectedWatchlist);

  const checkMutation = useMutation({
    mutationFn: async (watchlistId: string) => {
      const response = await apiClient.post(`/watchlists/${watchlistId}/check`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["watchlists"] });
    }
  });

  const deleteMutation = useMutation({
    mutationFn: async (watchlistId: string) => {
      await apiClient.delete(`/watchlists/${watchlistId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["watchlists"] });
      if (selectedWatchlist) {
        setSelectedWatchlist(null);
      }
    }
  });

  const handleCheck = (watchlistId: string) => {
    checkMutation.mutate(watchlistId);
  };

  const handleDelete = (watchlistId: string) => {
    if (confirm("Are you sure you want to delete this watchlist?")) {
      deleteMutation.mutate(watchlistId);
    }
  };

  const toggleActiveMutation = useMutation({
    mutationFn: async ({ watchlistId, isActive }: { watchlistId: string; isActive: boolean }) => {
      const watchlist = watchlists?.watchlists.find(w => w.id === watchlistId);
      if (!watchlist) return;
      
      // Get current form data and update is_active
      const formData = new FormData();
      formData.append("name", watchlist.name);
      formData.append("description", watchlist.description || "");
      formData.append("check_interval", watchlist.check_interval.toString());
      formData.append("notification_enabled", watchlist.notification_enabled.toString());
      formData.append("is_active", isActive.toString());
      
      // Include existing assets as JSON
      if (watchlist.assets && watchlist.assets.length > 0) {
        formData.append("assets_json", JSON.stringify(watchlist.assets));
      }
      
      const response = await apiClient.put(`/watchlists/${watchlistId}`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["watchlists"] });
    },
  });

  const handleToggleActive = (watchlistId: string, newActiveStatus: boolean) => {
    toggleActiveMutation.mutate({ watchlistId, isActive: newActiveStatus });
  };

  if (isLoading) {
    return <p className="text-slate-400 dark:text-slate-400 light:text-slate-600">Loading watchlists...</p>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
        <h2 className="text-2xl font-semibold text-white dark:text-white light:text-slate-900">Asset Watchlist</h2>
          <p className="text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">
            {canManageWatchlists 
              ? "Monitor high-value assets and trigger alerts when risk exceeds thresholds"
              : "View asset watchlists (read-only)"}
          </p>
        </div>
        {canManageWatchlists && (
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 rounded-lg bg-brand-600 dark:bg-brand-600 light:bg-brand-500 px-4 py-2 font-medium text-white dark:text-white light:text-slate-900 transition hover:bg-brand-700 dark:hover:bg-brand-700 light:hover:bg-brand-600"
          >
            <Plus className="h-4 w-4" />
            New Watchlist
          </button>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Watchlist List */}
        <div className="lg:col-span-1">
          <div className="rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/40 dark:bg-slate-900/40 light:bg-white p-4">
            <h3 className="mb-4 text-lg font-semibold text-white dark:text-white light:text-slate-900">Watchlists</h3>
            <div className="space-y-2">
              {watchlists?.watchlists.map((watchlist) => (
                <div
                  key={watchlist.id}
                  onClick={() => setSelectedWatchlist(watchlist.id)}
                  className={`cursor-pointer rounded-lg border p-3 transition ${
                    selectedWatchlist === watchlist.id
                      ? "border-brand-500 dark:border-brand-500 light:border-brand-600 bg-brand-500/20 dark:bg-brand-500/20 light:bg-brand-100"
                      : "border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-950/60 dark:bg-slate-950/60 light:bg-slate-50 hover:bg-slate-900 dark:hover:bg-slate-900 light:hover:bg-slate-100"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <p className="font-medium text-white dark:text-white light:text-slate-900">{watchlist.name}</p>
                        {!watchlist.is_active && (
                          <span className="rounded-full bg-slate-700 dark:bg-slate-700 light:bg-slate-300 px-2 py-0.5 text-xs text-slate-400 dark:text-slate-400 light:text-slate-600">
                            Inactive
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-400 dark:text-slate-400 light:text-slate-600">
                        {watchlist.assets.length} asset(s) | Check: {watchlist.check_interval}m
                      </p>
                    </div>
                    {canManageWatchlists ? (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleToggleActive(watchlist.id, !watchlist.is_active);
                        }}
                        className={`rounded-lg p-1.5 transition ${
                          watchlist.is_active
                            ? "bg-green-500/20 dark:bg-green-500/20 light:bg-green-100 text-green-400 dark:text-green-400 light:text-green-700 hover:bg-green-500/30 dark:hover:bg-green-500/30 light:hover:bg-green-200"
                            : "bg-slate-700 dark:bg-slate-700 light:bg-slate-300 text-slate-400 dark:text-slate-400 light:text-slate-600 hover:bg-slate-600 dark:hover:bg-slate-600 light:hover:bg-slate-400"
                        }`}
                        title={watchlist.is_active ? "Deactivate watchlist" : "Activate watchlist"}
                      >
                        <Power className={`h-3 w-3 ${watchlist.is_active ? "" : "opacity-50"}`} />
                      </button>
                    ) : (
                      watchlist.is_active ? (
                        <div className="h-2 w-2 rounded-full bg-green-400 dark:bg-green-400 light:bg-green-600" />
                      ) : (
                        <div className="h-2 w-2 rounded-full bg-slate-600 dark:bg-slate-600 light:bg-slate-400" />
                      )
                    )}
                  </div>
                </div>
              ))}
              {(!watchlists || watchlists.watchlists.length === 0) && (
                <p className="py-8 text-center text-sm text-slate-500 dark:text-slate-500 light:text-slate-500">No watchlists yet</p>
              )}
            </div>
          </div>
        </div>

        {/* Watchlist Detail */}
        <div className="lg:col-span-2">
          {selectedWatchlistData ? (
            <WatchlistDetail
              watchlist={selectedWatchlistData}
              onCheck={() => handleCheck(selectedWatchlistData.id)}
              onDelete={() => handleDelete(selectedWatchlistData.id)}
              onEdit={() => setShowEditModal(selectedWatchlistData.id)}
              onShare={() => setShowShareModal(selectedWatchlistData.id)}
              onToggleActive={(isActive: boolean) => handleToggleActive(selectedWatchlistData.id, isActive)}
              isChecking={checkMutation.isPending}
              canManage={canManageWatchlists}
              userRole={user?.role}
            />
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900/30 dark:bg-slate-900/30 light:bg-slate-50 p-12 text-center">
              <ShieldCheck className="mx-auto mb-4 h-12 w-12 text-slate-600 dark:text-slate-600 light:text-slate-400" />
              <p className="text-slate-400 dark:text-slate-400 light:text-slate-600">Select a watchlist to view details</p>
            </div>
          )}
        </div>
      </div>

      {showCreateModal && (
        <CreateWatchlistModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false);
            queryClient.invalidateQueries({ queryKey: ["watchlists"] });
          }}
        />
      )}

      {showEditModal && (
        <EditWatchlistModal
          watchlistId={showEditModal}
          onClose={() => setShowEditModal(null)}
          onSuccess={() => {
            setShowEditModal(null);
            queryClient.invalidateQueries({ queryKey: ["watchlists"] });
          }}
        />
      )}

      {showShareModal && (
        <ShareWatchlistModal
          watchlistId={showShareModal}
          onClose={() => setShowShareModal(null)}
          onSuccess={() => {
            setShowShareModal(null);
            queryClient.invalidateQueries({ queryKey: ["watchlists"] });
          }}
        />
      )}
    </div>
  );
};

const WatchlistDetail = ({
  watchlist,
  onCheck,
  onDelete,
  onEdit,
  onShare,
  onToggleActive,
  isChecking,
  canManage,
  userRole
}: {
  watchlist: Watchlist;
  onCheck: () => void;
  onDelete: () => void;
  onEdit: () => void;
  onShare: () => void;
  onToggleActive: (isActive: boolean) => void;
  isChecking: boolean;
  canManage: boolean;
  userRole?: string; // Add user role to determine if user can check items
}) => {
  const [showHistoryModal, setShowHistoryModal] = useState<string | null>(null);
  const [checkingItem, setCheckingItem] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const checkItemMutation = useMutation({
    mutationFn: async (itemId: string) => {
      const response = await apiClient.post(`/watchlists/items/${itemId}/check`);
      return response.data;
    },
    onSuccess: () => {
      setCheckingItem(null);
      queryClient.invalidateQueries({ queryKey: ["watchlists"] });
      queryClient.invalidateQueries({ queryKey: ["asset-check-history", showHistoryModal] });
    }
  });

  const handleCheckItem = (itemId: string) => {
    setCheckingItem(itemId);
    checkItemMutation.mutate(itemId);
  };

  const getRiskColor = (risk?: string) => {
    switch (risk?.toLowerCase()) {
      case "high":
      case "critical":
        return "text-red-400 dark:text-red-400 light:text-red-600";
      case "medium":
        return "text-yellow-400 dark:text-yellow-400 light:text-yellow-600";
      case "low":
        return "text-green-400 dark:text-green-400 light:text-green-600";
      default:
        return "text-slate-400 dark:text-slate-400 light:text-slate-600";
    }
  };

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/40 dark:bg-slate-900/40 light:bg-white p-6">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xl font-semibold text-white dark:text-white light:text-slate-900">{watchlist.name}</h3>
              {!watchlist.is_active && (
                <span className="rounded-full bg-slate-700 dark:bg-slate-700 light:bg-slate-300 px-2 py-1 text-xs text-slate-400 dark:text-slate-400 light:text-slate-600">
                  Inactive
                </span>
              )}
            </div>
            {watchlist.description && <p className="text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">{watchlist.description}</p>}
          </div>
          <div className="flex gap-2">
            {canManage && (
              <button
                onClick={() => onToggleActive(!watchlist.is_active)}
                className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-sm transition ${
                  watchlist.is_active
                    ? "border-green-700 dark:border-green-700 light:border-green-300 bg-green-500/20 dark:bg-green-500/20 light:bg-green-100 text-green-400 dark:text-green-400 light:text-green-700 hover:bg-green-500/30 dark:hover:bg-green-500/30 light:hover:bg-green-200"
                    : "border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-700 dark:bg-slate-700 light:bg-slate-300 text-slate-400 dark:text-slate-400 light:text-slate-600 hover:bg-slate-600 dark:hover:bg-slate-600 light:hover:bg-slate-400"
                }`}
                title={watchlist.is_active ? "Deactivate watchlist" : "Activate watchlist"}
              >
                <Power className={`h-4 w-4 ${watchlist.is_active ? "" : "opacity-50"}`} />
                {watchlist.is_active ? "Active" : "Inactive"}
              </button>
            )}
            <div className="flex items-center gap-2">
              {canManage && (
                <>
                  <button
                    onClick={onShare}
                    className="flex items-center gap-2 rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-3 py-2 text-sm text-white dark:text-white light:text-slate-900 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100"
                    title="Share with viewers"
                  >
                    <Share2 className="h-4 w-4" />
                    Share
                  </button>
                  <button
                    onClick={onEdit}
                    className="flex items-center gap-2 rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-3 py-2 text-sm text-white dark:text-white light:text-slate-900 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100"
                  >
                    <Edit className="h-4 w-4" />
                    Edit
                  </button>
                  <button
                    onClick={onCheck}
                    disabled={isChecking}
                    className="flex items-center gap-2 rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-3 py-2 text-sm text-white dark:text-white light:text-slate-900 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100 disabled:opacity-50"
                  >
                    <RefreshCw className={`h-4 w-4 ${isChecking ? "animate-spin" : ""}`} />
                    Check All
                  </button>
                  <button
                    onClick={onDelete}
                    className="flex items-center gap-2 rounded-lg border border-red-800 dark:border-red-800 light:border-red-300 bg-red-950/20 dark:bg-red-950/20 light:bg-red-50 px-3 py-2 text-sm text-red-400 dark:text-red-400 light:text-red-700 transition hover:bg-red-950/40 dark:hover:bg-red-950/40 light:hover:bg-red-100"
                  >
                    <Trash2 className="h-4 w-4" />
                    Delete
                  </button>
                </>
              )}
              {/* Show "Check All" button for viewer users (can check shared watchlists) */}
              {!canManage && userRole === "viewer" && watchlist.assets.length > 0 && (
                <button
                  onClick={onCheck}
                  disabled={isChecking}
                  className="flex items-center gap-2 rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-3 py-2 text-sm text-white dark:text-white light:text-slate-900 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100 disabled:opacity-50"
                >
                  <RefreshCw className={`h-4 w-4 ${isChecking ? "animate-spin" : ""}`} />
                  Check All
                </button>
              )}
            </div>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-950/60 dark:bg-slate-950/60 light:bg-slate-50 p-3">
            <p className="text-xs text-slate-500 dark:text-slate-500 light:text-slate-500">Status</p>
            <p className={`text-sm font-semibold ${watchlist.is_active ? "text-green-400 dark:text-green-400 light:text-green-600" : "text-slate-500 dark:text-slate-500 light:text-slate-500"}`}>
              {watchlist.is_active ? "Active" : "Inactive"}
            </p>
          </div>
          <div className="rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-950/60 dark:bg-slate-950/60 light:bg-slate-50 p-3">
            <p className="text-xs text-slate-500 dark:text-slate-500 light:text-slate-500">Check Interval</p>
            <p className="text-sm font-semibold text-white dark:text-white light:text-slate-900">{watchlist.check_interval} minutes</p>
          </div>
          <div className="rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-950/60 dark:bg-slate-950/60 light:bg-slate-50 p-3">
            <p className="text-xs text-slate-500 dark:text-slate-500 light:text-slate-500">Assets</p>
            <p className="text-sm font-semibold text-white dark:text-white light:text-slate-900">{watchlist.assets.length}</p>
          </div>
        </div>
      </div>

      {/* Assets List */}
      <div className="rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/40 dark:bg-slate-900/40 light:bg-white p-6">
        <h4 className="mb-4 text-lg font-semibold text-white dark:text-white light:text-slate-900">Assets</h4>
        <div className="space-y-2">
          {watchlist.assets.map((asset) => (
            <div key={asset.id} className="flex items-center justify-between rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-950/60 dark:bg-slate-950/60 light:bg-slate-50 p-3">
              <div className="flex-1">
                <div className="flex items-center gap-3">
                  <span className="rounded bg-slate-800 dark:bg-slate-800 light:bg-slate-200 px-2 py-0.5 text-xs font-medium uppercase text-slate-400 dark:text-slate-400 light:text-slate-600">
                    {asset.ioc_type}
                  </span>
                  <span className="font-mono text-sm text-white dark:text-white light:text-slate-900">{asset.ioc_value}</span>
                  {asset.risk_threshold && (
                    <span className={`text-xs font-medium ${getRiskColor(asset.risk_threshold)}`}>
                      Threshold: {asset.risk_threshold}
                    </span>
                  )}
                </div>
                {asset.description && <p className="mt-1 text-xs text-slate-400 dark:text-slate-400 light:text-slate-600">{asset.description}</p>}
              </div>
              <div className="ml-4 flex gap-2">
                <button
                  onClick={() => setShowHistoryModal(asset.id)}
                  className="rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white px-3 py-1.5 text-xs text-white dark:text-white light:text-slate-900 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100"
                  title="View check history"
                >
                  <History className="h-3 w-3" />
                </button>
                {/* Show Check button for admin/analyst (can manage) OR viewer (can check shared watchlists) */}
                {(canManage || userRole === "viewer") && (
                  <button
                    onClick={() => handleCheckItem(asset.id)}
                    disabled={checkingItem === asset.id}
                    className="rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white px-3 py-1.5 text-xs text-white dark:text-white light:text-slate-900 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100 disabled:opacity-50"
                  >
                    {checkingItem === asset.id ? "Checking..." : "Check"}
                  </button>
                )}
              </div>
            </div>
          ))}
          {showHistoryModal && (
            <AssetCheckHistoryModal
              assetId={showHistoryModal}
              assetValue={watchlist.assets.find(a => a.id === showHistoryModal)?.ioc_value || ""}
              onClose={() => setShowHistoryModal(null)}
            />
          )}
          {watchlist.assets.length === 0 && (
            <p className="py-8 text-center text-sm text-slate-500 dark:text-slate-500 light:text-slate-500">No assets in this watchlist</p>
          )}
        </div>
      </div>
    </div>
  );
};

const CreateWatchlistModal = ({
  onClose,
  onSuccess
}: {
  onClose: () => void;
  onSuccess: () => void;
}) => {
  const [formData, setFormData] = useState<WatchlistCreate>({
    name: "",
    description: "",
    check_interval: 60,
    notification_enabled: true,
    assets: []
  });
  const [newAsset, setNewAsset] = useState<Omit<WatchlistAsset, "id" | "created_at">>({
    ioc_type: "ip",
    ioc_value: "",
    description: "",
    risk_threshold: undefined,
    is_active: true
  });
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadResult, setUploadResult] = useState<{ added: number; skipped: number } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const createMutation = useMutation({
    mutationFn: async (data: { formData: WatchlistCreate; file: File | null }) => {
      const formDataToSend = new FormData();
      formDataToSend.append("name", data.formData.name);
      if (data.formData.description) {
        formDataToSend.append("description", data.formData.description);
      }
      formDataToSend.append("check_interval", data.formData.check_interval.toString());
      formDataToSend.append("notification_enabled", data.formData.notification_enabled.toString());
      
      if (data.file) {
        formDataToSend.append("file", data.file);
      }
      
      const response = await apiClient.post<Watchlist>("/watchlists/", formDataToSend, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });
      return response.data;
    },
    onSuccess: (data) => {
      // Count assets from response
      const added = data.assets.length;
      if (uploadFile && added > 0) {
        setUploadResult({ added, skipped: 0 });
      }
      onSuccess();
    }
  });

  const handleAddAsset = () => {
    if (!newAsset.ioc_value.trim()) return;
    setFormData({
      ...formData,
      assets: [
        ...formData.assets,
        {
          ...newAsset,
          id: crypto.randomUUID(),
          ioc_value: newAsset.ioc_value.trim()
        }
      ]
    });
    setNewAsset({
      ioc_type: "ip",
      ioc_value: "",
      description: "",
      risk_threshold: undefined,
      is_active: true
    });
  };

  const handleRemoveAsset = (index: number) => {
    setFormData({
      ...formData,
      assets: formData.assets.filter((_, i) => i !== index)
    });
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setUploadFile(file);
      setUploadResult(null);
    }
  };

  const handleRemoveFile = () => {
    setUploadFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate({ formData, file: uploadFile });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/50 light:bg-black/30 p-4">
      <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900 dark:bg-slate-900 light:bg-white p-6">
        <div className="mb-6 flex items-center justify-between">
          <h3 className="text-xl font-semibold text-white dark:text-white light:text-slate-900">Create Watchlist</h3>
          <button onClick={onClose} className="text-slate-400 dark:text-slate-400 light:text-slate-600 hover:text-white dark:hover:text-white dark:text-white light:text-slate-900 light:hover:text-slate-900">
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">Name *</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
              required
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">Description</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
              rows={2}
            />
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">Check Interval (minutes) *</label>
              <input
                type="number"
                min={5}
                value={formData.check_interval}
                onChange={(e) => setFormData({ ...formData, check_interval: parseInt(e.target.value) || 60 })}
                className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
                required
              />
            </div>
            <div className="flex items-center gap-2 pt-8">
              <input
                type="checkbox"
                id="notifications"
                checked={formData.notification_enabled}
                onChange={(e) => setFormData({ ...formData, notification_enabled: e.target.checked })}
                className="rounded border-slate-600 dark:border-slate-600 light:border-slate-400 text-brand-500 dark:text-brand-500 light:text-brand-600 focus:ring-brand-500 dark:focus:ring-brand-500 light:focus:ring-brand-600"
              />
              <label htmlFor="notifications" className="text-sm text-slate-300 dark:text-slate-300 light:text-slate-700">
                Enable notifications
              </label>
            </div>
          </div>

          {/* Upload from File */}
          <div className="rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-950/60 dark:bg-slate-950/60 light:bg-slate-50 p-4">
            <h4 className="mb-3 text-sm font-semibold text-white dark:text-white light:text-slate-900">Upload IOCs from TXT File</h4>
            <div className="mb-4">
              <input
                ref={fileInputRef}
                type="file"
                accept=".txt"
                onChange={handleFileSelect}
                className="hidden"
                id="watchlist-file-upload"
              />
              <label
                htmlFor="watchlist-file-upload"
                className="flex cursor-pointer items-center gap-2 rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white px-4 py-2 text-sm text-white dark:text-white light:text-slate-900 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100"
              >
                <Upload className="h-4 w-4" />
                {uploadFile ? uploadFile.name : "Select TXT File"}
              </label>
              {uploadFile && (
                <div className="mt-2 flex items-center gap-2">
                  <span className="text-xs text-slate-400 dark:text-slate-400 light:text-slate-600">{uploadFile.name}</span>
                  <button
                    type="button"
                    onClick={handleRemoveFile}
                    className="text-xs text-red-400 dark:text-red-400 light:text-red-600 hover:text-red-300 dark:hover:text-red-300 light:hover:text-red-700"
                  >
                    Remove
                  </button>
                </div>
              )}
              {uploadResult && (
                <p className="mt-2 text-xs text-green-400 dark:text-green-400 light:text-green-600">
                  Successfully imported {uploadResult.added} IOC(s) from file
                </p>
              )}
              <p className="mt-2 text-xs text-slate-500 dark:text-slate-500 light:text-slate-500">
                One IOC per line. Supported: IP, Domain, URL, Hash (MD5, SHA1, SHA256)
                <br />
                <span className="text-slate-400 dark:text-slate-400 light:text-slate-600">
                  Format: "IP    Domain" (e.g., "172.31.22.44    devops-runner01.company.local") will create both IP and Domain assets
                </span>
              </p>
            </div>
          </div>

          {/* Add Asset Manually */}
          <div className="rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-950/60 dark:bg-slate-950/60 light:bg-slate-50 p-4">
            <h4 className="mb-3 text-sm font-semibold text-white dark:text-white light:text-slate-900">Add Asset Manually (Optional)</h4>
            <div className="grid gap-3 md:grid-cols-5">
              <select
                value={newAsset.ioc_type}
                onChange={(e) => setNewAsset({ ...newAsset, ioc_type: e.target.value })}
                className="rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white px-3 py-2 text-sm text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
              >
                <option value="ip">IP</option>
                <option value="domain">Domain</option>
                <option value="url">URL</option>
                <option value="hash">Hash</option>
              </select>
              <input
                type="text"
                value={newAsset.ioc_value}
                onChange={(e) => setNewAsset({ ...newAsset, ioc_value: e.target.value })}
                placeholder="Value"
                className="col-span-2 rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white px-3 py-2 text-sm text-white dark:text-white light:text-slate-900 placeholder:text-slate-500 dark:placeholder:text-slate-500 light:placeholder:text-slate-400 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
              />
              <select
                value={newAsset.risk_threshold || ""}
                onChange={(e) => setNewAsset({ ...newAsset, risk_threshold: e.target.value || undefined })}
                className="rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white px-3 py-2 text-sm text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
              >
                <option value="">No threshold</option>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
              <button
                type="button"
                onClick={handleAddAsset}
                disabled={!newAsset.ioc_value.trim()}
                className="rounded-lg bg-brand-600 dark:bg-brand-600 light:bg-brand-500 px-3 py-2 text-sm font-medium text-white dark:text-white light:text-slate-900 transition hover:bg-brand-700 dark:hover:bg-brand-700 light:hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Add
              </button>
            </div>
            {newAsset.description && (
              <input
                type="text"
                value={newAsset.description}
                onChange={(e) => setNewAsset({ ...newAsset, description: e.target.value })}
                placeholder="Description (optional)"
                className="mt-2 w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white px-3 py-2 text-sm text-white dark:text-white light:text-slate-900 placeholder:text-slate-500 dark:placeholder:text-slate-500 light:placeholder:text-slate-400 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
              />
            )}
          </div>

          {/* Assets List */}
          {formData.assets.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-semibold text-white dark:text-white light:text-slate-900">Assets ({formData.assets.length})</h4>
              {formData.assets.map((asset, index) => (
                <div key={asset.id} className="flex items-center justify-between rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-950/60 dark:bg-slate-950/60 light:bg-slate-50 p-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs uppercase text-slate-500 dark:text-slate-500 light:text-slate-500">{asset.ioc_type}</span>
                    <span className="font-mono text-sm text-white dark:text-white light:text-slate-900">{asset.ioc_value}</span>
                    {asset.risk_threshold && (
                      <span className="text-xs text-slate-400 dark:text-slate-400 light:text-slate-600">({asset.risk_threshold})</span>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => handleRemoveAsset(index)}
                    className="text-red-400 dark:text-red-400 light:text-red-600 hover:text-red-300 dark:hover:text-red-300 light:hover:text-red-700"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
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
              disabled={createMutation.isPending || !formData.name.trim()}
              className="rounded-lg bg-brand-600 dark:bg-brand-600 light:bg-brand-500 px-4 py-2 text-sm font-medium text-white dark:text-white light:text-slate-900 transition hover:bg-brand-700 dark:hover:bg-brand-700 light:hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {createMutation.isPending ? "Creating..." : "Create Watchlist"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const EditWatchlistModal = ({
  watchlistId,
  onClose,
  onSuccess
}: {
  watchlistId: string;
  onClose: () => void;
  onSuccess: () => void;
}) => {
  const [formData, setFormData] = useState<WatchlistCreate | null>(null);
  const [newAsset, setNewAsset] = useState<Omit<WatchlistAsset, "id" | "created_at">>({
    ioc_type: "ip",
    ioc_value: "",
    description: "",
    risk_threshold: undefined,
    is_active: true
  });
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadResult, setUploadResult] = useState<{ added: number; skipped: number } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch watchlist data
  const { data: watchlist, isLoading } = useQuery<Watchlist>({
    queryKey: ["watchlist", watchlistId],
    queryFn: async () => {
      const response = await apiClient.get<Watchlist>(`/watchlists/${watchlistId}`);
      return response.data;
    },
    enabled: !!watchlistId,
  });

  // Initialize form data when watchlist is loaded
  useEffect(() => {
    if (watchlist) {
      setFormData({
        name: watchlist.name,
        description: watchlist.description || "",
        check_interval: watchlist.check_interval,
        notification_enabled: watchlist.notification_enabled,
        assets: watchlist.assets
      });
    }
  }, [watchlist]);

  const updateMutation = useMutation({
    mutationFn: async (data: { formData: WatchlistCreate; file: File | null }) => {
      const formDataToSend = new FormData();
      formDataToSend.append("name", data.formData.name);
      if (data.formData.description) {
        formDataToSend.append("description", data.formData.description);
      }
      formDataToSend.append("check_interval", data.formData.check_interval.toString());
      formDataToSend.append("notification_enabled", data.formData.notification_enabled.toString());
      
      // Add assets as JSON string
      if (data.formData.assets && data.formData.assets.length > 0) {
        formDataToSend.append("assets_json", JSON.stringify(data.formData.assets.map(asset => ({
          ioc_type: asset.ioc_type,
          ioc_value: asset.ioc_value,
          description: asset.description,
          risk_threshold: asset.risk_threshold,
          is_active: asset.is_active
        }))));
      }
      
      if (data.file) {
        formDataToSend.append("file", data.file);
      }
      
      const response = await apiClient.put<Watchlist>(`/watchlists/${watchlistId}`, formDataToSend, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });
      return response.data;
    },
    onSuccess: (data) => {
      const added = data.assets.length;
      if (uploadFile && added > 0) {
        setUploadResult({ added, skipped: 0 });
      }
      onSuccess();
    }
  });

  const handleAddAsset = () => {
    if (!newAsset.ioc_value.trim() || !formData) return;
    setFormData({
      ...formData,
      assets: [
        ...formData.assets,
        {
          ...newAsset,
          id: crypto.randomUUID(),
          ioc_value: newAsset.ioc_value.trim()
        }
      ]
    });
    setNewAsset({
      ioc_type: "ip",
      ioc_value: "",
      description: "",
      risk_threshold: undefined,
      is_active: true
    });
  };

  const handleRemoveAsset = (index: number) => {
    if (!formData) return;
    setFormData({
      ...formData,
      assets: formData.assets.filter((_, i) => i !== index)
    });
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setUploadFile(file);
      setUploadResult(null);
    }
  };

  const handleRemoveFile = () => {
    setUploadFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData) return;
    updateMutation.mutate({ formData, file: uploadFile });
  };

  if (isLoading || !formData) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
        <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <p className="text-slate-400">Loading watchlist...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/50 light:bg-black/30 p-4">
      <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900 dark:bg-slate-900 light:bg-white p-6">
        <div className="mb-6 flex items-center justify-between">
          <h3 className="text-xl font-semibold text-white dark:text-white light:text-slate-900">Edit Watchlist</h3>
          <button onClick={onClose} className="text-slate-400 dark:text-slate-400 light:text-slate-600 hover:text-white dark:hover:text-white light:hover:text-slate-900">
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">Name *</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
              required
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">Description</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
              rows={2}
            />
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">Check Interval (minutes) *</label>
              <input
                type="number"
                min={5}
                value={formData.check_interval}
                onChange={(e) => setFormData({ ...formData, check_interval: parseInt(e.target.value) || 60 })}
                className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
                required
              />
            </div>
            <div className="flex items-center gap-2 pt-8">
              <input
                type="checkbox"
                id="edit-notifications"
                checked={formData.notification_enabled}
                onChange={(e) => setFormData({ ...formData, notification_enabled: e.target.checked })}
                className="rounded border-slate-600 dark:border-slate-600 light:border-slate-400 text-brand-500 dark:text-brand-500 light:text-brand-600 focus:ring-brand-500 dark:focus:ring-brand-500 light:focus:ring-brand-600"
              />
              <label htmlFor="edit-notifications" className="text-sm text-slate-300 dark:text-slate-300 light:text-slate-700">
                Enable notifications
              </label>
            </div>
          </div>

          {/* Upload from File */}
          <div className="rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-950/60 dark:bg-slate-950/60 light:bg-slate-50 p-4">
            <h4 className="mb-3 text-sm font-semibold text-white dark:text-white light:text-slate-900">Upload Additional IOCs from TXT File</h4>
            <div className="mb-4">
              <input
                ref={fileInputRef}
                type="file"
                accept=".txt"
                onChange={handleFileSelect}
                className="hidden"
                id="edit-watchlist-file-upload"
              />
              <label
                htmlFor="edit-watchlist-file-upload"
                className="flex cursor-pointer items-center gap-2 rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white px-4 py-2 text-sm text-white dark:text-white light:text-slate-900 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100"
              >
                <Upload className="h-4 w-4" />
                {uploadFile ? uploadFile.name : "Select TXT File"}
              </label>
              {uploadFile && (
                <div className="mt-2 flex items-center gap-2">
                  <span className="text-xs text-slate-400 dark:text-slate-400 light:text-slate-600">{uploadFile.name}</span>
                  <button
                    type="button"
                    onClick={handleRemoveFile}
                    className="text-xs text-red-400 dark:text-red-400 light:text-red-600 hover:text-red-300 dark:hover:text-red-300 light:hover:text-red-700"
                  >
                    Remove
                  </button>
                </div>
              )}
              {uploadResult && (
                <p className="mt-2 text-xs text-green-400 dark:text-green-400 light:text-green-600">
                  Successfully imported {uploadResult.added} IOC(s) from file
                </p>
              )}
              <p className="mt-2 text-xs text-slate-500 dark:text-slate-500 light:text-slate-500">
                One IOC per line. Supported: IP, Domain, URL, Hash (MD5, SHA1, SHA256)
                <br />
                <span className="text-slate-400 dark:text-slate-400 light:text-slate-600">
                  Format: "IP    Domain" (e.g., "172.31.22.44    devops-runner01.company.local") will create both IP and Domain assets
                </span>
              </p>
            </div>
          </div>

          {/* Add Asset Manually */}
          <div className="rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-950/60 dark:bg-slate-950/60 light:bg-slate-50 p-4">
            <h4 className="mb-3 text-sm font-semibold text-white dark:text-white light:text-slate-900">Add Asset Manually (Optional)</h4>
            <div className="grid gap-3 md:grid-cols-5">
              <select
                value={newAsset.ioc_type}
                onChange={(e) => setNewAsset({ ...newAsset, ioc_type: e.target.value })}
                className="rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white px-3 py-2 text-sm text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
              >
                <option value="ip">IP</option>
                <option value="domain">Domain</option>
                <option value="url">URL</option>
                <option value="hash">Hash</option>
              </select>
              <input
                type="text"
                value={newAsset.ioc_value}
                onChange={(e) => setNewAsset({ ...newAsset, ioc_value: e.target.value })}
                placeholder="Value"
                className="col-span-2 rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white px-3 py-2 text-sm text-white dark:text-white light:text-slate-900 placeholder:text-slate-500 dark:placeholder:text-slate-500 light:placeholder:text-slate-400 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
              />
              <select
                value={newAsset.risk_threshold || ""}
                onChange={(e) => setNewAsset({ ...newAsset, risk_threshold: e.target.value || undefined })}
                className="rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white px-3 py-2 text-sm text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
              >
                <option value="">No threshold</option>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
              <button
                type="button"
                onClick={handleAddAsset}
                disabled={!newAsset.ioc_value.trim()}
                className="rounded-lg bg-brand-600 dark:bg-brand-600 light:bg-brand-500 px-3 py-2 text-sm font-medium text-white dark:text-white light:text-slate-900 transition hover:bg-brand-700 dark:hover:bg-brand-700 light:hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Add
              </button>
            </div>
            {newAsset.description && (
              <input
                type="text"
                value={newAsset.description}
                onChange={(e) => setNewAsset({ ...newAsset, description: e.target.value })}
                placeholder="Description (optional)"
                className="mt-2 w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white px-3 py-2 text-sm text-white dark:text-white light:text-slate-900 placeholder:text-slate-500 dark:placeholder:text-slate-500 light:placeholder:text-slate-400 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
              />
            )}
          </div>

          {/* Assets List */}
          {formData.assets.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-semibold text-white dark:text-white light:text-slate-900">Assets ({formData.assets.length})</h4>
              <p className="text-xs text-slate-400 dark:text-slate-400 light:text-slate-600 mb-2">
                You can update the risk threshold for each asset below
              </p>
              {formData.assets.map((asset, index) => (
                <div key={asset.id} className="flex items-center justify-between gap-3 rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-950/60 dark:bg-slate-950/60 light:bg-slate-50 p-3">
                  <div className="flex flex-1 items-center gap-2 min-w-0">
                    <span className="text-xs uppercase text-slate-500 dark:text-slate-500 light:text-slate-500 whitespace-nowrap">{asset.ioc_type}</span>
                    <span className="font-mono text-sm text-white dark:text-white light:text-slate-900 truncate">{asset.ioc_value}</span>
                  </div>
                  <select
                    value={asset.risk_threshold || ""}
                    onChange={(e) => {
                      if (!formData) return;
                      const updatedAssets = [...formData.assets];
                      updatedAssets[index] = {
                        ...updatedAssets[index],
                        risk_threshold: e.target.value || undefined
                      };
                      setFormData({ ...formData, assets: updatedAssets });
                    }}
                    className="rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white px-2 py-1.5 text-xs text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none whitespace-nowrap"
                    title="Risk threshold for alert triggering"
                  >
                    <option value="">No threshold</option>
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                  <button
                    type="button"
                    onClick={() => handleRemoveAsset(index)}
                    className="text-red-400 dark:text-red-400 light:text-red-600 hover:text-red-300 dark:hover:text-red-300 light:hover:text-red-700 flex-shrink-0"
                    title="Remove asset"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
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
              disabled={updateMutation.isPending || !formData.name.trim()}
              className="rounded-lg bg-brand-600 dark:bg-brand-600 light:bg-brand-500 px-4 py-2 text-sm font-medium text-white dark:text-white light:text-slate-900 transition hover:bg-brand-700 dark:hover:bg-brand-700 light:hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {updateMutation.isPending ? "Updating..." : "Update Watchlist"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const AssetCheckHistoryModal = ({
  assetId,
  assetValue,
  onClose
}: {
  assetId: string;
  assetValue: string;
  onClose: () => void;
}) => {
  const { data, isLoading } = useQuery<AssetCheckHistoryListResponse>({
    queryKey: ["asset-check-history", assetId],
    queryFn: async () => {
      const response = await apiClient.get(`/watchlists/items/${assetId}/history?limit=50`);
      return response.data;
    },
  });

  const getRiskColor = (risk?: string) => {
    if (!risk) return "text-slate-400 dark:text-slate-400 light:text-slate-600";
    switch (risk.toLowerCase()) {
      case "high":
      case "critical":
        return "text-red-400 dark:text-red-400 light:text-red-600";
      case "medium":
        return "text-yellow-400 dark:text-yellow-400 light:text-yellow-600";
      case "low":
        return "text-green-400 dark:text-green-400 light:text-green-600";
      default:
        return "text-slate-400 dark:text-slate-400 light:text-slate-600";
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/50 light:bg-black/30 p-4">
      <div className="w-full max-w-4xl max-h-[90vh] overflow-y-auto rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900 dark:bg-slate-900 light:bg-white">
        <div className="sticky top-0 border-b border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-950 dark:bg-slate-950 light:bg-slate-50 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xl font-semibold text-white dark:text-white light:text-slate-900">Check History</h3>
              <p className="mt-1 text-sm text-slate-400 dark:text-slate-400 light:text-slate-600 font-mono">{assetValue}</p>
            </div>
            <button
              onClick={onClose}
              className="rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white p-2 text-slate-400 dark:text-slate-400 light:text-slate-600 hover:text-white dark:hover:text-white light:hover:text-slate-900 transition"
            >
              ✕
            </button>
          </div>
        </div>

        <div className="p-6">
          {isLoading ? (
            <div className="py-12 text-center text-slate-400 dark:text-slate-400 light:text-slate-600">Loading history...</div>
          ) : data && data.items.length > 0 ? (
            <div className="space-y-3">
              {data.items.map((history) => (
                <div
                  key={history.id}
                  className={`rounded-lg border p-4 ${
                    history.alert_triggered
                      ? "border-red-800 dark:border-red-800 light:border-red-300 bg-red-950/20 dark:bg-red-950/20 light:bg-red-50"
                      : "border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-950/60 dark:bg-slate-950/60 light:bg-slate-50"
                  }`}
                >
                  <div className="mb-2 flex items-center justify-between">
                    <span className="text-xs text-slate-500 dark:text-slate-500 light:text-slate-500">
                      {new Date(history.check_date).toLocaleString()}
                    </span>
                    <div className="flex items-center gap-2">
                      {history.status && (
                        <span className={`text-xs font-medium ${getRiskColor(history.status)}`}>
                          {history.status.toUpperCase()}
                        </span>
                      )}
                      {history.risk_score && (
                        <span className={`text-sm font-semibold ${getRiskColor(history.risk_score)}`}>
                          {history.risk_score}
                        </span>
                      )}
                      {history.alert_triggered && (
                        <span className="rounded-full bg-red-500 dark:bg-red-500 light:bg-red-600 px-2 py-0.5 text-xs font-medium text-white">
                          Alert
                        </span>
                      )}
                    </div>
                  </div>
                  {history.sources_checked && history.sources_checked.length > 0 && (
                    <div className="mb-2">
                      <p className="text-xs text-slate-400 dark:text-slate-400 light:text-slate-600">Sources checked:</p>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {history.sources_checked.map((source, idx) => (
                          <span
                            key={idx}
                            className="rounded bg-slate-800 dark:bg-slate-800 light:bg-slate-200 px-2 py-0.5 text-xs text-slate-400 dark:text-slate-400 light:text-slate-600"
                          >
                            {source}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {history.threat_intelligence_data && (
                    <details className="mt-2">
                      <summary className="cursor-pointer text-xs text-slate-400 dark:text-slate-400 light:text-slate-600 hover:text-white dark:hover:text-white light:hover:text-slate-900">
                        View Details
                      </summary>
                      <pre className="mt-2 overflow-auto rounded bg-slate-900 dark:bg-slate-900 light:bg-slate-100 p-3 text-xs text-slate-300 dark:text-slate-300 light:text-slate-700">
                        {JSON.stringify(history.threat_intelligence_data, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="py-12 text-center text-slate-400 dark:text-slate-400 light:text-slate-600">
              No check history available
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const ShareWatchlistModal = ({
  watchlistId,
  onClose,
  onSuccess
}: {
  watchlistId: string;
  onClose: () => void;
  onSuccess: () => void;
}) => {
  const [selectedUserIds, setSelectedUserIds] = useState<string[]>([]);
  const queryClient = useQueryClient();

  // Fetch watchlist to get current shared users
  const { data: watchlist } = useQuery<Watchlist>({
    queryKey: ["watchlist", watchlistId],
    queryFn: async () => {
      const response = await apiClient.get<Watchlist>(`/watchlists/${watchlistId}`);
      return response.data;
    },
    enabled: !!watchlistId,
  });

  // Fetch all users (only viewers)
  const { data: usersData, isLoading: isLoadingUsers } = useQuery<import("@/features/users/types").UserListResponse>({
    queryKey: ["users", "viewers"],
    queryFn: async () => {
      const response = await apiClient.get<import("@/features/users/types").UserListResponse>("/users/?role=viewer&is_active=true&page_size=100");
      return response.data;
    },
  });

  // Initialize selected users from watchlist's shared_with_user_ids
  useEffect(() => {
    if (watchlist && watchlist.shared_with_user_ids) {
      setSelectedUserIds(watchlist.shared_with_user_ids || []);
    }
  }, [watchlist]);

  const shareMutation = useMutation({
    mutationFn: async (userIds: string[]) => {
      const response = await apiClient.put(`/watchlists/${watchlistId}/share`, {
        user_ids: userIds
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["watchlists"] });
      queryClient.invalidateQueries({ queryKey: ["watchlist", watchlistId] });
      onSuccess();
    },
    onError: (error: any) => {
      console.error("Failed to share watchlist:", error);
      alert(`Failed to share watchlist: ${error?.response?.data?.detail || error?.message || "Unknown error"}`);
    }
  });

  const handleToggleUser = (userId: string) => {
    setSelectedUserIds(prev => 
      prev.includes(userId)
        ? prev.filter(id => id !== userId)
        : [...prev, userId]
    );
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    shareMutation.mutate(selectedUserIds);
  };

  const viewerUsers = usersData?.items.filter(user => user.role === "viewer" && user.is_active) || [];

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/50 light:bg-black/30 p-4"
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
          <h3 className="text-xl font-semibold text-white dark:text-white light:text-slate-900">Share Watchlist</h3>
          <button 
            onClick={onClose} 
            className="text-slate-400 dark:text-slate-400 light:text-slate-600 hover:text-white dark:hover:text-white light:hover:text-slate-900"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <p className="mb-3 text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">
              Select viewer users who can view and monitor this watchlist:
            </p>
            
            {isLoadingUsers ? (
              <div className="py-8 text-center text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">
                Loading users...
              </div>
            ) : viewerUsers.length === 0 ? (
              <div className="py-8 text-center text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">
                No active viewer users found
              </div>
            ) : (
              <div className="max-h-64 space-y-2 overflow-y-auto rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-950/60 dark:bg-slate-950/60 light:bg-slate-50 p-3">
                {viewerUsers.map((user) => (
                  <label
                    key={user.id}
                    className="flex cursor-pointer items-center gap-3 rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/40 dark:bg-slate-900/40 light:bg-white p-3 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100"
                  >
                    <input
                      type="checkbox"
                      checked={selectedUserIds.includes(user.id)}
                      onChange={() => handleToggleUser(user.id)}
                      className="h-4 w-4 rounded border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white text-brand-500 focus:ring-brand-500"
                    />
                    <div className="flex-1">
                      <div className="font-medium text-white dark:text-white light:text-slate-900">
                        {user.full_name || user.username}
                      </div>
                      <div className="text-xs text-slate-400 dark:text-slate-400 light:text-slate-600">
                        {user.email}
                      </div>
                    </div>
                  </label>
                ))}
              </div>
            )}
          </div>

          {shareMutation.isError && (
            <div className="rounded-lg border border-red-800 dark:border-red-800 light:border-red-300 bg-red-950/20 dark:bg-red-950/20 light:bg-red-50 p-3 text-sm text-red-400 dark:text-red-400 light:text-red-700">
              {(shareMutation.error as any)?.response?.data?.detail || "Failed to share watchlist"}
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
              disabled={shareMutation.isPending}
              className="rounded-lg bg-brand-600 dark:bg-brand-600 light:bg-brand-500 px-4 py-2 text-sm font-medium text-white dark:text-white light:text-slate-900 transition hover:bg-brand-700 dark:hover:bg-brand-700 light:hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {shareMutation.isPending ? "Sharing..." : "Share Watchlist"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default WatchlistPage;
