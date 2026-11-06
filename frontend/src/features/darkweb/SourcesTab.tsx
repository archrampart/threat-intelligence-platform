import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CircleAlert, CircleCheck, CircleDashed, CirclePause, ExternalLink, Eye, Loader2, Plus, Rss, Trash2 } from "lucide-react";

import { apiClient } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import type { DarkWebSource, FeedConfig, FeedPreview } from "@/features/darkweb/types";

const errorText = (e: any) => e?.response?.data?.detail || e?.message || "Request failed";

const card = "rounded-2xl border border-slate-800 bg-slate-900/40 p-5 light:border-slate-200 light:bg-white";
const input =
  "w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-brand-500 focus:outline-hidden light:border-slate-300 light:bg-white light:text-slate-900";
const buttonPrimary =
  "inline-flex items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700 disabled:opacity-50";
const buttonGhost =
  "inline-flex items-center justify-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-300 transition hover:bg-slate-800 disabled:opacity-50 light:border-slate-300 light:text-slate-700 light:hover:bg-slate-100";

const CATEGORY_LABEL: Record<DarkWebSource["category"], string> = {
  ransomware: "Ransomware leaks",
  infostealer: "Infostealer logs",
  breach: "Breaches",
  telegram: "Telegram",
  forum: "Forums & markets",
  news: "Security news",
  feed: "Custom feed"
};

const STATUS_META = {
  ok: { label: "Healthy", icon: CircleCheck, className: "text-emerald-400 light:text-emerald-600" },
  error: { label: "Failing", icon: CircleAlert, className: "text-red-400 light:text-red-600" },
  never: { label: "Not fetched yet", icon: CircleDashed, className: "text-slate-400" },
  disabled: { label: "Disabled by admin", icon: CirclePause, className: "text-slate-500" }
} as const;

const Toggle = ({ checked, onChange, label, disabled }: { checked: boolean; onChange: (v: boolean) => void; label: string; disabled?: boolean }) => (
  <label className={`inline-flex items-center gap-2 text-xs text-slate-300 light:text-slate-700 ${disabled ? "opacity-50" : "cursor-pointer"}`}>
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative h-5 w-9 rounded-full transition ${checked ? "bg-brand-600" : "bg-slate-700 light:bg-slate-300"}`}
    >
      <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition ${checked ? "left-4" : "left-0.5"}`} />
    </button>
    {label}
  </label>
);

const when = (value?: string | null) => (value ? new Date(value).toLocaleString() : "-");

const EMPTY_FEED: FeedConfig = { url: "", format: "rss", severity: "high" };

const AddFeedForm = ({ onDone }: { onDone: () => void }) => {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [config, setConfig] = useState<FeedConfig>(EMPTY_FEED);
  const [preview, setPreview] = useState<FeedPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const set = (patch: Partial<FeedConfig>) => {
    setConfig((c) => ({ ...c, ...patch }));
    setPreview(null);
  };
  const clean = (): FeedConfig => {
    const out: FeedConfig = { url: config.url.trim(), format: config.format, severity: config.severity };
    if (config.format === "json") {
      for (const key of ["items_path", "title_path", "text_path", "url_path", "date_path"] as const) {
        const value = config[key]?.trim();
        if (value) out[key] = value;
      }
    }
    return out;
  };

  const test = useMutation({
    mutationFn: async () => (await apiClient.post<FeedPreview>("/darkweb/sources/preview", clean(), { timeout: 60000 })).data,
    onSuccess: (p) => { setPreview(p); setError(null); },
    onError: (e) => { setPreview(null); setError(errorText(e)); }
  });
  const save = useMutation({
    mutationFn: async () => apiClient.post("/darkweb/sources", { name, description: description || undefined, config: clean() }),
    onSuccess: () => { setName(""); setDescription(""); setConfig(EMPTY_FEED); setPreview(null); setError(null); onDone(); },
    onError: (e) => setError(errorText(e))
  });

  return (
    <form className={`${card} space-y-3`} onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
      <h3 className="flex items-center gap-2 font-semibold text-white light:text-slate-900">
        <Rss className="h-4 w-4 text-brand-400" /> Add a custom feed (admin)
      </h3>
      <p className="text-sm text-slate-400">
        Any RSS/Atom or JSON feed - e.g. a CTI provider, a leak tracker or your own collection. Every item is matched against all
        users' monitored assets. Test the mapping before saving.
      </p>
      <div className="grid gap-3 md:grid-cols-2">
        <input aria-label="Feed name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Name, e.g. CERT advisories" className={input} />
        <input aria-label="Description" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Description (optional)" className={input} />
        <input aria-label="Feed URL" value={config.url} onChange={(e) => set({ url: e.target.value })} placeholder="https://example.org/feed.xml" className={`${input} md:col-span-2`} inputMode="url" />
        <select aria-label="Format" value={config.format} onChange={(e) => set({ format: e.target.value as FeedConfig["format"] })} className={input}>
          <option value="rss">RSS / Atom</option>
          <option value="json">JSON</option>
        </select>
        <select aria-label="Severity of matches" value={config.severity} onChange={(e) => set({ severity: e.target.value as FeedConfig["severity"] })} className={input}>
          <option value="critical">Matches are critical</option>
          <option value="high">Matches are high</option>
          <option value="medium">Matches are medium</option>
          <option value="low">Matches are low</option>
        </select>
      </div>
      {config.format === "json" && (
        <div className="grid gap-3 md:grid-cols-3">
          {([
            ["items_path", "Items JSONPath", "$.data[*]"],
            ["title_path", "Title field *", "$.title"],
            ["text_path", "Text field", "$.description"],
            ["url_path", "Link field", "$.url"],
            ["date_path", "Date field", "$.published"]
          ] as const).map(([key, label, placeholder]) => (
            <div key={key}>
              <label className="mb-1 block text-xs text-slate-400" htmlFor={`feed-${key}`}>{label}</label>
              <input id={`feed-${key}`} value={config[key] ?? ""} onChange={(e) => set({ [key]: e.target.value })} placeholder={placeholder} className={`${input} font-mono`} />
            </div>
          ))}
        </div>
      )}
      {error && <p className="text-sm text-red-400">{error}</p>}
      {preview && (
        <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3 text-sm light:border-slate-200 light:bg-slate-50">
          <p className="mb-2 text-xs text-emerald-400">Parsed {preview.count} items. First {preview.items.length}:</p>
          <ul className="space-y-1">
            {preview.items.map((item, i) => (
              <li key={i} className="truncate text-slate-300 light:text-slate-700">
                <span className="font-medium">{item.title}</span>
                {item.text && <span className="text-slate-500"> - {item.text}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        <button type="button" className={buttonGhost} onClick={() => test.mutate()} disabled={!config.url.trim() || test.isPending}>
          {test.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Eye className="h-4 w-4" />} Test feed
        </button>
        <button type="submit" className={buttonPrimary} disabled={!name.trim() || !preview || save.isPending}>
          <Plus className="h-4 w-4" /> Save source
        </button>
        {!preview && <span className="self-center text-xs text-slate-500">Run a successful test before saving.</span>}
      </div>
    </form>
  );
};

const SourcesTab = () => {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const queryClient = useQueryClient();
  const { data: sources = [], isLoading } = useQuery<DarkWebSource[]>({
    queryKey: ["darkweb-sources"],
    queryFn: async () => (await apiClient.get<DarkWebSource[]>("/darkweb/sources")).data
  });
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["darkweb-sources"] });

  const preference = useMutation({
    mutationFn: async ({ key, enabled }: { key: string; enabled: boolean }) =>
      apiClient.put(`/darkweb/sources/${key}/preference`, { enabled }),
    onSuccess: refresh
  });
  const globalToggle = useMutation({
    mutationFn: async ({ key, enabled }: { key: string; enabled: boolean }) => apiClient.put(`/darkweb/sources/${key}`, { is_enabled: enabled }),
    onSuccess: refresh
  });
  const remove = useMutation({ mutationFn: async (key: string) => apiClient.delete(`/darkweb/sources/${key}`), onSuccess: refresh });

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-400">
        Where the monitor looks. Health is updated on every scan. Switch a source off to exclude it from <em>your</em> scans; admins
        can disable a source for everyone or add custom feeds. Telegram channels themselves are managed on the Telegram tab.
      </p>
      {isLoading ? (
        <p className="text-sm text-slate-400">Loading sources...</p>
      ) : (
        <div className="grid gap-3 lg:grid-cols-2">
          {sources.map((s) => {
            const status = STATUS_META[s.status] ?? STATUS_META.never;
            const StatusIcon = status.icon;
            return (
              <div key={s.key} className={`${card} flex flex-col gap-3`}>
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-semibold text-white light:text-slate-900">{s.name}</h3>
                      <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[11px] text-slate-300 light:bg-slate-100 light:text-slate-600">
                        {CATEGORY_LABEL[s.category] ?? s.category}
                      </span>
                      {!s.builtin && (
                        <span className="rounded-full bg-brand-600/20 px-2 py-0.5 text-[11px] text-brand-300 light:text-brand-700">Custom</span>
                      )}
                    </div>
                    {s.description && <p className="mt-1 text-sm text-slate-400">{s.description}</p>}
                  </div>
                  <span className={`inline-flex items-center gap-1 text-xs font-medium ${status.className}`}>
                    <StatusIcon className="h-4 w-4" /> {status.label}
                  </span>
                </div>

                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
                  <div><dt className="text-slate-500">Last fetch</dt><dd className="text-slate-300 light:text-slate-700">{when(s.last_fetch_at)}</dd></div>
                  <div><dt className="text-slate-500">Last success</dt><dd className="text-slate-300 light:text-slate-700">{when(s.last_success_at)}</dd></div>
                  <div><dt className="text-slate-500">Items</dt><dd className="text-slate-300 light:text-slate-700">{s.last_item_count ?? "-"}</dd></div>
                  <div><dt className="text-slate-500">Duration</dt><dd className="text-slate-300 light:text-slate-700">{s.last_duration_ms != null ? `${s.last_duration_ms} ms` : "-"}</dd></div>
                </dl>
                {s.last_error && s.status === "error" && (
                  <p className="break-words rounded-lg bg-red-950/40 p-2 text-xs text-red-300 light:bg-red-50 light:text-red-700">{s.last_error}</p>
                )}
                {isAdmin && s.config && (
                  <p className="truncate font-mono text-xs text-slate-500" title={s.config.url}>{s.config.format.toUpperCase()} · {s.config.url}</p>
                )}

                <div className="mt-auto flex flex-wrap items-center gap-4 border-t border-slate-800 pt-3 light:border-slate-200">
                  <Toggle
                    label="Use in my scans"
                    checked={s.user_enabled}
                    disabled={!s.is_enabled}
                    onChange={(enabled) => preference.mutate({ key: s.key, enabled })}
                  />
                  {isAdmin && (
                    <Toggle label="Enabled for everyone" checked={s.is_enabled} onChange={(enabled) => globalToggle.mutate({ key: s.key, enabled })} />
                  )}
                  <div className="ml-auto flex items-center gap-2">
                    {s.homepage && (
                      <a href={s.homepage} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-xs text-brand-400 hover:underline light:text-brand-600">
                        Website <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                    {isAdmin && !s.builtin && (
                      <button type="button" aria-label={`Delete ${s.name}`} onClick={() => remove.mutate(s.key)} className="rounded-lg p-1.5 text-slate-400 hover:bg-red-950/40 hover:text-red-400">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
      {isAdmin && <AddFeedForm onDone={refresh} />}
    </div>
  );
};

export default SourcesTab;
