import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BellRing, Loader2, Send, X } from "lucide-react";

import { apiClient } from "@/lib/api";

interface NotificationSettings {
  enabled: boolean;
  format: "slack" | "teams" | "generic";
  min_severity: "info" | "low" | "medium" | "high" | "critical";
  webhook_configured: boolean;
  webhook_url_masked: string;
}

const inputClass =
  "w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-2 text-white focus:border-brand-500 focus:outline-hidden light:border-slate-300 light:bg-white light:text-slate-900";

const NotificationSettingsModal = ({ onClose }: { onClose: () => void }) => {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery<NotificationSettings>({
    queryKey: ["notification-settings"],
    queryFn: async () => (await apiClient.get<NotificationSettings>("/auth/notifications")).data
  });

  const [enabled, setEnabled] = useState(false);
  const [format, setFormat] = useState<NotificationSettings["format"]>("slack");
  const [minSeverity, setMinSeverity] = useState<NotificationSettings["min_severity"]>("high");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => {
    if (data) {
      setEnabled(data.enabled);
      setFormat(data.format);
      setMinSeverity(data.min_severity);
    }
  }, [data]);

  const save = useMutation({
    mutationFn: async (removeUrl: boolean = false) =>
      (
        await apiClient.put<NotificationSettings>("/auth/notifications", {
          enabled,
          format,
          min_severity: minSeverity,
          // empty string removes the stored URL, omitted keeps it
          webhook_url: removeUrl ? "" : webhookUrl.trim() || undefined
        })
      ).data,
    onSuccess: (saved) => {
      queryClient.setQueryData(["notification-settings"], saved);
      setWebhookUrl("");
      setMessage({ ok: true, text: "Settings saved" });
    },
    onError: (e: any) => setMessage({ ok: false, text: e?.response?.data?.detail || "Could not save settings" })
  });

  const test = useMutation({
    mutationFn: async () => (await apiClient.post<{ success: boolean; detail: string }>("/auth/notifications/test")).data,
    onSuccess: (r) => setMessage({ ok: r.success, text: r.success ? `Test sent (${r.detail})` : `Delivery failed: ${r.detail}` }),
    onError: (e: any) => setMessage({ ok: false, text: e?.response?.data?.detail || "Test failed" })
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" role="dialog" aria-modal="true" aria-labelledby="notif-title">
      <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-xl light:border-slate-200 light:bg-white">
        <div className="mb-4 flex items-center justify-between">
          <h3 id="notif-title" className="flex items-center gap-2 text-xl font-semibold text-white light:text-slate-900">
            <BellRing className="h-5 w-5 text-brand-400" /> Alert notifications
          </h3>
          <button type="button" aria-label="Close" onClick={onClose} className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 light:hover:bg-slate-100">
            <X className="h-4 w-4" />
          </button>
        </div>

        {isLoading ? (
          <p className="text-sm text-slate-400">Loading...</p>
        ) : (
          <form
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              setMessage(null);
              save.mutate(false);
            }}
          >
            <p className="text-sm text-slate-400">
              Watchlist alerts at or above the selected severity are posted to your own webhook. The URL is stored encrypted
              and never shown again.
            </p>

            <label className="flex items-center gap-2 text-sm text-slate-300 light:text-slate-700">
              <input type="checkbox" className="h-4 w-4 accent-brand-500" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
              Send alerts to my webhook
            </label>

            <div>
              <label htmlFor="notif-url" className="mb-1 block text-sm font-medium text-slate-300 light:text-slate-700">
                Webhook URL (https)
              </label>
              <input
                id="notif-url"
                type="url"
                inputMode="url"
                autoComplete="off"
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                placeholder={data?.webhook_configured ? `Configured: ${data.webhook_url_masked} (leave empty to keep)` : "https://hooks.slack.com/services/..."}
                className={inputClass}
              />
              {data?.webhook_configured && (
                <button
                  type="button"
                  onClick={() => save.mutate(true)}
                  className="mt-1 text-xs text-red-400 hover:underline"
                >
                  Remove stored URL
                </button>
              )}
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="notif-format" className="mb-1 block text-sm font-medium text-slate-300 light:text-slate-700">
                  Format
                </label>
                <select id="notif-format" value={format} onChange={(e) => setFormat(e.target.value as typeof format)} className={inputClass}>
                  <option value="slack">Slack</option>
                  <option value="teams">Microsoft Teams (Workflows)</option>
                  <option value="generic">Generic JSON</option>
                </select>
              </div>
              <div>
                <label htmlFor="notif-sev" className="mb-1 block text-sm font-medium text-slate-300 light:text-slate-700">
                  Minimum severity
                </label>
                <select id="notif-sev" value={minSeverity} onChange={(e) => setMinSeverity(e.target.value as typeof minSeverity)} className={inputClass}>
                  <option value="low">Low and above</option>
                  <option value="medium">Medium and above</option>
                  <option value="high">High and above</option>
                  <option value="critical">Critical only</option>
                </select>
              </div>
            </div>

            {message && (
              <p className={`rounded-lg p-2 text-sm ${message.ok ? "bg-emerald-950/40 text-emerald-300" : "bg-red-950/40 text-red-300"}`}>{message.text}</p>
            )}

            <div className="flex flex-wrap justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => {
                  setMessage(null);
                  test.mutate();
                }}
                disabled={!data?.webhook_configured || test.isPending}
                className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800 disabled:opacity-50 light:border-slate-300 light:text-slate-700"
              >
                {test.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />} Send test
              </button>
              <button
                type="submit"
                disabled={save.isPending}
                className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
              >
                {save.isPending ? "Saving..." : "Save"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

export default NotificationSettingsModal;
