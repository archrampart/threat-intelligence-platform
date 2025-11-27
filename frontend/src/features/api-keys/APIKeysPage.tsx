import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Key, CheckCircle, XCircle, Clock, RefreshCw, Trash2, Eye, EyeOff, TestTube } from "lucide-react";

import { apiClient } from "@/lib/api";
import type { APIKeyResponse, APIKeyCreate, APIKeyUpdate, APIKeyTestRequest } from "@/features/api-keys/types";
import type { APISourceResponse } from "@/features/api-sources/types";

const APIKeysPage = () => {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  const queryClient = useQueryClient();

  const { data: apiKeys, isLoading } = useQuery<APIKeyResponse[]>({
    queryKey: ["api-keys"],
    queryFn: async () => {
      const response = await apiClient.get<APIKeyResponse[]>("/api-keys/");
      return response.data;
    }
  });

  const { data: apiSources, isLoading: isLoadingSources } = useQuery<APISourceResponse[]>({
    queryKey: ["api-sources"],
    queryFn: async () => {
      try {
        const response = await apiClient.get<APISourceResponse[]>("/api-sources");
        return response.data;
      } catch (error) {
        console.error("Error fetching API sources:", error);
        throw error;
      }
    },
    retry: 1
  });

  const deleteMutation = useMutation({
    mutationFn: async (keyId: string) => {
      await apiClient.delete(`/api-keys/${keyId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["api-keys"] });
    }
  });

  const updateModeMutation = useMutation({
    mutationFn: async ({ keyId, updateMode }: { keyId: string; updateMode: "manual" | "auto" }) => {
      await apiClient.put<APIKeyResponse>(`/api-keys/${keyId}`, { update_mode: updateMode });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["api-keys"] });
    }
  });

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case "valid":
        return <CheckCircle className="h-4 w-4 text-green-400" />;
      case "invalid":
        return <XCircle className="h-4 w-4 text-red-400" />;
      default:
        return <Clock className="h-4 w-4 text-yellow-400" />;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-white dark:text-white light:text-slate-900">API Keys</h2>
          <p className="text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">Manage your threat intelligence API keys and credentials</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 rounded-lg bg-brand-600 dark:bg-brand-600 light:bg-brand-500 px-4 py-2 font-medium text-white transition hover:bg-brand-700 dark:hover:bg-brand-700 light:hover:bg-brand-600"
        >
          <Plus className="h-4 w-4" />
          Add API Key
        </button>
      </div>

      {isLoading ? (
        <p className="text-slate-400 dark:text-slate-400 light:text-slate-600">Loading API keys...</p>
      ) : apiKeys && apiKeys.length > 0 ? (
        <div className="space-y-3">
          {apiKeys.map((key) => (
            <APIKeyCard
              key={key.id}
              apiKey={key}
              onDelete={() => deleteMutation.mutate(key.id)}
              onUpdateMode={(mode) => updateModeMutation.mutate({ keyId: key.id, updateMode: mode })}
              isSelected={selectedKey === key.id}
              onSelect={() => setSelectedKey(selectedKey === key.id ? null : key.id)}
            />
          ))}
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900/30 dark:bg-slate-900/30 light:bg-slate-50 p-12 text-center">
          <Key className="mx-auto mb-4 h-12 w-12 text-slate-600 dark:text-slate-600 light:text-slate-400" />
          <p className="text-slate-400 dark:text-slate-400 light:text-slate-600">No API keys configured</p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="mt-4 rounded-lg bg-brand-600 dark:bg-brand-600 light:bg-brand-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700 dark:hover:bg-brand-700 light:hover:bg-brand-600"
          >
            Add Your First API Key
          </button>
        </div>
      )}

      {showCreateModal && (
        <CreateAPIKeyModal
          apiSources={apiSources || []}
          isLoadingSources={isLoadingSources}
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false);
            queryClient.invalidateQueries({ queryKey: ["api-keys"] });
          }}
        />
      )}
    </div>
  );
};

const APIKeyCard = ({
  apiKey,
  onDelete,
  onUpdateMode,
  isSelected,
  onSelect
}: {
  apiKey: APIKeyResponse;
  onDelete: () => void;
  onUpdateMode: (mode: "manual" | "auto") => void;
  isSelected: boolean;
  onSelect: () => void;
}) => {
  const [showKey, setShowKey] = useState(false);
  const [showTestModal, setShowTestModal] = useState(false);

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case "valid":
        return <CheckCircle className="h-4 w-4 text-green-400 dark:text-green-400 light:text-green-600" />;
      case "invalid":
        return <XCircle className="h-4 w-4 text-red-400 dark:text-red-400 light:text-red-600" />;
      default:
        return <Clock className="h-4 w-4 text-yellow-400 dark:text-yellow-400 light:text-yellow-600" />;
    }
  };

  return (
    <>
      <div
        className={`rounded-lg border p-4 transition ${
          isSelected 
            ? "border-brand-500 dark:border-brand-500 light:border-brand-600 bg-brand-500/10 dark:bg-brand-500/10 light:bg-brand-100" 
            : "border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/40 dark:bg-slate-900/40 light:bg-white hover:bg-slate-900/60 dark:hover:bg-slate-900/60 light:hover:bg-slate-50"
        }`}
      >
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="mb-2 flex items-center gap-3">
              <h3 className="text-lg font-semibold text-white dark:text-white light:text-slate-900">{apiKey.api_source_name || "Unknown Source"}</h3>
              {getStatusIcon(apiKey.test_status)}
              <span className="text-xs capitalize text-slate-400 dark:text-slate-400 light:text-slate-600">{apiKey.test_status}</span>
              {apiKey.is_active ? (
                <span className="rounded-full bg-green-950/30 dark:bg-green-950/30 light:bg-green-100 px-2 py-0.5 text-xs text-green-400 dark:text-green-400 light:text-green-700">Active</span>
              ) : (
                <span className="rounded-full bg-slate-800 dark:bg-slate-800 light:bg-slate-200 px-2 py-0.5 text-xs text-slate-500 dark:text-slate-500 light:text-slate-500">Inactive</span>
              )}
            </div>
            <div className="mb-2 flex items-center gap-2 text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">
              <span>Auto Update:</span>
              <div className="flex gap-2 items-center">
                <button
                  onClick={() => onUpdateMode("manual")}
                  className={`rounded px-2 py-0.5 text-xs transition ${
                    apiKey.update_mode === "manual"
                      ? "bg-slate-700 dark:bg-slate-700 light:bg-slate-200 text-slate-300 dark:text-slate-300 light:text-slate-700"
                      : "bg-slate-800 dark:bg-slate-800 light:bg-slate-100 text-slate-500 dark:text-slate-500 light:text-slate-600 hover:bg-slate-700 dark:hover:bg-slate-700 light:hover:bg-slate-200"
                  }`}
                  title="Manual: Only update when manually checked"
                >
                  OFF
                </button>
                <button
                  onClick={() => onUpdateMode("auto")}
                  className={`rounded px-2 py-0.5 text-xs transition ${
                    apiKey.update_mode === "auto"
                      ? "bg-brand-500/20 dark:bg-brand-500/20 light:bg-brand-100 text-brand-400 dark:text-brand-400 light:text-brand-700 border border-brand-500/50 dark:border-brand-500/50 light:border-brand-600"
                      : "bg-slate-800 dark:bg-slate-800 light:bg-slate-100 text-slate-500 dark:text-slate-500 light:text-slate-600 hover:bg-slate-700 dark:hover:bg-slate-700 light:hover:bg-slate-200"
                  }`}
                  title="Auto: Enable automatic updates (uses API quota)"
                >
                  ON
                </button>
                <span className="text-xs text-slate-500 dark:text-slate-500 light:text-slate-400 ml-1">
                  ({apiKey.update_mode === "auto" ? "Auto updates enabled" : "Manual only"})
                </span>
              </div>
            </div>
            {apiKey.username && <p className="text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">Username: {apiKey.username}</p>}
            {apiKey.last_used && (
              <p className="text-xs text-slate-500 dark:text-slate-500 light:text-slate-500">Last used: {new Date(apiKey.last_used).toLocaleString()}</p>
            )}
          </div>
          <div className="ml-4 flex gap-2">
            <button
              onClick={() => setShowTestModal(true)}
              className="rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white p-2 text-slate-400 dark:text-slate-400 light:text-slate-600 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100 hover:text-white dark:hover:text-white light:hover:text-slate-900"
              title="Test API Key"
            >
              <TestTube className="h-4 w-4" />
            </button>
            <button
              onClick={onDelete}
              className="rounded-lg border border-red-800 dark:border-red-800 light:border-red-300 bg-red-950/20 dark:bg-red-950/20 light:bg-red-50 p-2 text-red-400 dark:text-red-400 light:text-red-700 transition hover:bg-red-950/40 dark:hover:bg-red-950/40 light:hover:bg-red-100"
              title="Delete"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {showTestModal && (
        <TestAPIKeyModal
          apiKeyId={apiKey.id}
          apiSourceName={apiKey.api_source_name || ""}
          onClose={() => setShowTestModal(false)}
        />
      )}
    </>
  );
};

const CreateAPIKeyModal = ({
  apiSources,
  isLoadingSources,
  onClose,
  onSuccess
}: {
  apiSources: APISourceResponse[];
  isLoadingSources: boolean;
  onClose: () => void;
  onSuccess: () => void;
}) => {
  const [formData, setFormData] = useState<APIKeyCreate>({
    api_source_id: "",
    api_key: "",
    username: "",
    password: "",
    api_url: "",
    update_mode: "manual",
    is_active: true
  });
  const [showPassword, setShowPassword] = useState(false);

  // Get selected API source to check authentication type
  const selectedSource = apiSources.find(source => source.id === formData.api_source_id);
  const requiresApiKey = selectedSource?.authentication_type?.toLowerCase() !== "none";

  const createMutation = useMutation({
    mutationFn: async (data: APIKeyCreate) => {
      const response = await apiClient.post<APIKeyResponse>("/api-keys/", data);
      return response.data;
    },
    onSuccess: () => {
      onSuccess();
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate(formData);
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
        className="relative w-full max-w-2xl rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900 dark:bg-slate-900 light:bg-white p-6 max-h-[90vh] overflow-y-auto shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-6 flex items-center justify-between">
          <h3 className="text-xl font-semibold text-white dark:text-white light:text-slate-900">Add API Key</h3>
          <button 
            onClick={onClose} 
            className="text-slate-400 dark:text-slate-400 light:text-slate-600 hover:text-white dark:hover:text-white light:hover:text-slate-900 text-2xl leading-none w-8 h-8 flex items-center justify-center rounded hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100 transition"
            type="button"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">API Source *</label>
            {isLoadingSources ? (
              <div className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-slate-400 dark:text-slate-400 light:text-slate-600">
                Loading API sources...
              </div>
            ) : (
              <select
                value={formData.api_source_id}
                onChange={(e) => setFormData({ ...formData, api_source_id: e.target.value })}
                className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
                required
              >
                <option value="">Select API Source</option>
                {apiSources && apiSources.length > 0 ? (
                  apiSources.map((source) => (
                    <option key={source.id} value={source.id}>
                      {source.display_name}
                    </option>
                  ))
                ) : (
                  <option value="" disabled>No API sources available</option>
                )}
              </select>
            )}
            {!isLoadingSources && (!apiSources || apiSources.length === 0) && (
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-500 light:text-slate-500">No API sources found. Please contact an administrator.</p>
            )}
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">
              API Key {requiresApiKey ? "*" : "(Optional - Not required for this API)"}
            </label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                value={formData.api_key}
                onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 pr-10 text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
                required={requiresApiKey}
                placeholder={requiresApiKey ? "Enter API key" : "No API key required (optional)"}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-2 top-2 text-slate-400 dark:text-slate-400 light:text-slate-600 hover:text-white dark:hover:text-white light:hover:text-slate-900"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {!requiresApiKey && (
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-500 light:text-slate-500">
                This API source does not require an API key. You can leave this field empty.
              </p>
            )}
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">Username (Optional)</label>
              <input
                type="text"
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">Password (Optional)</label>
              <input
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
              />
            </div>
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">API URL Override (Optional)</label>
            <input
              type="url"
              value={formData.api_url}
              onChange={(e) => setFormData({ ...formData, api_url: e.target.value })}
              placeholder="https://custom-api.example.com"
              className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 placeholder:text-slate-500 dark:placeholder:text-slate-500 light:placeholder:text-slate-400 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
            />
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">Auto Update</label>
              <select
                value={formData.update_mode}
                onChange={(e) => setFormData({ ...formData, update_mode: e.target.value as "manual" | "auto" })}
                className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
              >
                <option value="manual">OFF - Manual only (Recommended to save API quota)</option>
                <option value="auto">ON - Enable automatic updates</option>
              </select>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-500 light:text-slate-400">
                <strong>Manual (OFF):</strong> Only queries when you manually check watchlists (recommended to save API quota).<br/>
                <strong>Auto (ON):</strong> Allows automatic updates if scheduler is enabled (uses API quota automatically).
              </p>
            </div>
            <div className="flex items-center gap-2 pt-8">
              <input
                type="checkbox"
                id="is_active"
                checked={formData.is_active}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                className="rounded border-slate-600 dark:border-slate-600 light:border-slate-400 text-brand-500 dark:text-brand-500 light:text-brand-600 focus:ring-brand-500 dark:focus:ring-brand-500 light:focus:ring-brand-600"
              />
              <label htmlFor="is_active" className="text-sm text-slate-300 dark:text-slate-300 light:text-slate-700">
                Active
              </label>
            </div>
          </div>

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
              disabled={createMutation.isPending || !formData.api_source_id || (requiresApiKey && !formData.api_key.trim())}
              className="rounded-lg bg-brand-600 dark:bg-brand-600 light:bg-brand-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700 dark:hover:bg-brand-700 light:hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {createMutation.isPending ? "Adding..." : "Add API Key"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const TestAPIKeyModal = ({
  apiKeyId,
  apiSourceName,
  onClose
}: {
  apiKeyId: string;
  apiSourceName: string;
  onClose: () => void;
}) => {
  const [testData, setTestData] = useState<APIKeyTestRequest>({
    test_ioc_type: "ip",
    test_ioc_value: "8.8.8.8"
  });

  const testMutation = useMutation({
    mutationFn: async (data: APIKeyTestRequest) => {
      const response = await apiClient.post(`/api-keys/${apiKeyId}/test`, data);
      return response.data;
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    testMutation.mutate(testData);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/50 light:bg-black/30 p-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900 dark:bg-slate-900 light:bg-white p-6">
        <div className="mb-6 flex items-center justify-between">
          <h3 className="text-xl font-semibold text-white dark:text-white light:text-slate-900">Test API Key</h3>
          <button onClick={onClose} className="text-slate-400 dark:text-slate-400 light:text-slate-600 hover:text-white dark:hover:text-white light:hover:text-slate-900">
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">IOC Type</label>
            <select
              value={testData.test_ioc_type}
              onChange={(e) => setTestData({ ...testData, test_ioc_type: e.target.value })}
              className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
            >
              <option value="ip">IP Address</option>
              <option value="domain">Domain</option>
              <option value="url">URL</option>
              <option value="hash">Hash</option>
            </select>
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">IOC Value</label>
            <input
              type="text"
              value={testData.test_ioc_value}
              onChange={(e) => setTestData({ ...testData, test_ioc_value: e.target.value })}
              className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 placeholder:text-slate-500 dark:placeholder:text-slate-500 light:placeholder:text-slate-400 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
              required
            />
          </div>

          {testMutation.data && (
            <div
              className={`rounded-lg border p-3 ${
                testMutation.data.success
                  ? "border-green-800 dark:border-green-800 light:border-green-300 bg-green-950/20 dark:bg-green-950/20 light:bg-green-50 text-green-400 dark:text-green-400 light:text-green-700"
                  : "border-red-800 dark:border-red-800 light:border-red-300 bg-red-950/20 dark:bg-red-950/20 light:bg-red-50 text-red-400 dark:text-red-400 light:text-red-700"
              }`}
            >
              <p className="text-sm">{testMutation.data.message}</p>
            </div>
          )}

          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white px-4 py-2 text-sm font-medium text-white dark:text-white light:text-slate-900 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100"
            >
              Close
            </button>
            <button
              type="submit"
              disabled={testMutation.isPending}
              className="rounded-lg bg-brand-600 dark:bg-brand-600 light:bg-brand-500 px-4 py-2 text-sm font-medium text-white dark:text-white light:text-slate-900 transition hover:bg-brand-700 dark:hover:bg-brand-700 light:hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {testMutation.isPending ? "Testing..." : "Test"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default APIKeysPage;

