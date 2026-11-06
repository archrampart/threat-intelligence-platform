import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AtSign,
  Bug,
  CheckCheck,
  Database,
  ExternalLink,
  Globe,
  Loader2,
  Lock,
  MessageCircle,
  Plus,
  RefreshCw,
  Rss,
  Store,
  Skull,
  Tag,
  Trash2
} from "lucide-react";

import { apiClient } from "@/lib/api";
import SourcesTab from "@/features/darkweb/SourcesTab";
import type {
  AssetKind,
  DarkWebSummary,
  Mention,
  MentionList,
  MentionSource,
  MonitoredAsset,
  SuggestedChannel,
  TelegramAccountStatus,
  TelegramChannel
} from "@/features/darkweb/types";

const errorText = (e: any) => e?.response?.data?.detail || e?.message || "Request failed";

const SOURCE_META: Record<MentionSource, { label: string; icon: typeof Skull; hint: string }> = {
  ransomware: { label: "Ransomware leaks", icon: Skull, hint: "Victim posts on ransomware leak sites (ransomware.live, RansomLook)" },
  infostealer: { label: "Infostealer logs", icon: Bug, hint: "Machines infected by infostealers with credentials for your domain (Hudson Rock)" },
  breach: { label: "Breaches", icon: Database, hint: "Known data breaches of your domain (HIBP) and breach reporting" },
  forum: { label: "Forums & markets", icon: Store, hint: "Database sales, access listings and leak claims on dark web forums and Telegram" },
  telegram: { label: "Telegram", icon: MessageCircle, hint: "Mentions in the Telegram channels you monitor" },
  feed: { label: "News & custom feeds", icon: Rss, hint: "Security news feeds and custom feeds added by an administrator" }
};

const SEVERITY_CLASS: Record<string, string> = {
  critical: "border-red-700 bg-red-950/50 text-red-300 light:border-red-300 light:bg-red-50 light:text-red-700",
  high: "border-orange-700 bg-orange-950/40 text-orange-300 light:border-orange-300 light:bg-orange-50 light:text-orange-700",
  medium: "border-yellow-700 bg-yellow-950/30 text-yellow-300 light:border-yellow-300 light:bg-yellow-50 light:text-yellow-700",
  low: "border-slate-700 bg-slate-900/40 text-slate-300 light:border-slate-300 light:bg-slate-50 light:text-slate-700"
};

const KIND_META: Record<AssetKind, { label: string; icon: typeof Globe; placeholder: string; hint: string }> = {
  domain: { label: "Domain", icon: Globe, placeholder: "acme.com", hint: "Matches the domain and its subdomains" },
  keyword: { label: "Brand / keyword", icon: Tag, placeholder: "Acme Corp", hint: "Whole-word, case-insensitive" },
  email_domain: { label: "E-mail domain", icon: AtSign, placeholder: "acme.com", hint: "Matches leaked addresses like user@acme.com" }
};

const card = "rounded-2xl border border-slate-800 bg-slate-900/40 p-5 light:border-slate-200 light:bg-white";
const input =
  "w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-brand-500 focus:outline-hidden light:border-slate-300 light:bg-white light:text-slate-900";
const buttonPrimary =
  "inline-flex items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700 disabled:opacity-50";
const buttonGhost =
  "inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-1.5 text-sm text-slate-300 transition hover:bg-slate-800 disabled:opacity-50 light:border-slate-300 light:text-slate-700 light:hover:bg-slate-100";

// --------------------------------------------------------------------------- mentions

const MentionsTab = ({ summary }: { summary?: DarkWebSummary }) => {
  const queryClient = useQueryClient();
  const [source, setSource] = useState<MentionSource | "">("");
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery<MentionList>({
    queryKey: ["darkweb-mentions", source, unreadOnly, page],
    queryFn: async () => {
      const params = new URLSearchParams({ page: String(page), page_size: "25" });
      if (source) params.set("source", source);
      if (unreadOnly) params.set("unread_only", "true");
      return (await apiClient.get<MentionList>(`/darkweb/mentions?${params}`)).data;
    }
  });

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["darkweb-mentions"] });
    queryClient.invalidateQueries({ queryKey: ["darkweb-summary"] });
  };
  const markRead = useMutation({
    mutationFn: async (m: Mention) => apiClient.put(`/darkweb/mentions/${m.id}`, { is_read: !m.is_read }),
    onSuccess: refresh
  });
  const readAll = useMutation({ mutationFn: async () => apiClient.post("/darkweb/mentions/read-all"), onSuccess: refresh });

  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {(Object.keys(SOURCE_META) as MentionSource[]).map((key) => {
          const meta = SOURCE_META[key];
          const Icon = meta.icon;
          const active = source === key;
          return (
            <button
              key={key}
              type="button"
              title={meta.hint}
              onClick={() => {
                setSource(active ? "" : key);
                setPage(1);
              }}
              className={`${card} flex items-center justify-between text-left transition ${active ? "ring-2 ring-brand-500" : "hover:border-slate-600"}`}
            >
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-400">{meta.label}</p>
                <p className="text-2xl font-semibold text-white light:text-slate-900">{summary?.by_source[key] ?? 0}</p>
              </div>
              <Icon className="h-6 w-6 text-slate-500" />
            </button>
          );
        })}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <label className="inline-flex items-center gap-2 text-sm text-slate-300 light:text-slate-700">
          <input type="checkbox" className="h-4 w-4 accent-brand-500" checked={unreadOnly} onChange={(e) => { setUnreadOnly(e.target.checked); setPage(1); }} />
          Unread only ({summary?.unread ?? 0})
        </label>
        {source && (
          <button type="button" className={buttonGhost} onClick={() => setSource("")}>
            Clear filter: {SOURCE_META[source].label}
          </button>
        )}
        <button type="button" className={`${buttonGhost} ml-auto`} disabled={!summary?.unread} onClick={() => readAll.mutate()}>
          <CheckCheck className="h-4 w-4" /> Mark all read
        </button>
      </div>

      {isLoading ? (
        <p className="text-sm text-slate-400">Loading mentions...</p>
      ) : !data || data.items.length === 0 ? (
        <div className={`${card} text-center text-sm text-slate-400`}>
          No mentions yet. Add monitored assets and run a scan - scans also run automatically every hour.
        </div>
      ) : (
        <div className="space-y-2">
          {data.items.map((m) => {
            const Icon = SOURCE_META[m.source]?.icon ?? Skull;
            return (
              <article
                key={m.id}
                className={`${card} flex flex-col gap-2 ${m.is_read ? "opacity-70" : "border-l-4 border-l-brand-500"}`}
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="flex min-w-0 items-start gap-3">
                    <Icon className="mt-0.5 h-5 w-5 shrink-0 text-slate-400" />
                    <div className="min-w-0">
                      <h3 className="font-semibold text-white light:text-slate-900">{m.title}</h3>
                      <p className="text-xs text-slate-500">
                        {SOURCE_META[m.source]?.label} · matched <span className="font-mono text-slate-300 light:text-slate-700">{m.matched_term}</span>
                        {m.actor ? ` · ${m.actor}` : ""}
                        {m.published_at ? ` · ${new Date(m.published_at).toLocaleString()}` : ""}
                      </p>
                    </div>
                  </div>
                  <span className={`rounded-full border px-2.5 py-0.5 text-xs font-semibold uppercase ${SEVERITY_CLASS[m.severity] ?? SEVERITY_CLASS.low}`}>
                    {m.severity}
                  </span>
                </div>
                {m.snippet && (
                  <p className="whitespace-pre-wrap break-words rounded-lg bg-slate-950/60 p-3 text-sm text-slate-300 light:bg-slate-50 light:text-slate-700">
                    {m.snippet}
                  </p>
                )}
                <div className="flex flex-wrap items-center gap-3 text-xs">
                  {m.url && (
                    <a href={m.url} target="_blank" rel="noopener noreferrer nofollow" className="inline-flex items-center gap-1 text-brand-400 hover:underline light:text-brand-600">
                      Open source <ExternalLink className="h-3 w-3" />
                    </a>
                  )}
                  <button type="button" onClick={() => markRead.mutate(m)} className="text-slate-400 hover:text-white light:hover:text-slate-900">
                    Mark as {m.is_read ? "unread" : "read"}
                  </button>
                  <span className="ml-auto text-slate-500">found {new Date(m.created_at).toLocaleString()}</span>
                </div>
              </article>
            );
          })}
          {pages > 1 && (
            <div className="flex items-center justify-end gap-2 pt-2 text-sm text-slate-400">
              <button type="button" className={buttonGhost} disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Previous</button>
              <span>Page {page} of {pages}</span>
              <button type="button" className={buttonGhost} disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>Next</button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// --------------------------------------------------------------------------- assets

const AssetsTab = () => {
  const queryClient = useQueryClient();
  const [kind, setKind] = useState<AssetKind>("domain");
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: assets = [] } = useQuery<MonitoredAsset[]>({
    queryKey: ["darkweb-assets"],
    queryFn: async () => (await apiClient.get<MonitoredAsset[]>("/darkweb/assets")).data
  });
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["darkweb-assets"] });
    queryClient.invalidateQueries({ queryKey: ["darkweb-summary"] });
  };
  const add = useMutation({
    mutationFn: async () => apiClient.post("/darkweb/assets", { kind, value }),
    onSuccess: () => {
      setValue("");
      setError(null);
      invalidate();
    },
    onError: (e) => setError(errorText(e))
  });
  const remove = useMutation({ mutationFn: async (id: string) => apiClient.delete(`/darkweb/assets/${id}`), onSuccess: invalidate });

  return (
    <div className="space-y-4">
      <form
        className={`${card} grid gap-3 md:grid-cols-[12rem_1fr_auto]`}
        onSubmit={(e) => {
          e.preventDefault();
          add.mutate();
        }}
      >
        <select aria-label="Asset type" value={kind} onChange={(e) => setKind(e.target.value as AssetKind)} className={input}>
          {(Object.keys(KIND_META) as AssetKind[]).map((k) => (
            <option key={k} value={k}>{KIND_META[k].label}</option>
          ))}
        </select>
        <div>
          <input aria-label="Value" value={value} onChange={(e) => setValue(e.target.value)} placeholder={KIND_META[kind].placeholder} className={input} />
          <p className="mt-1 text-xs text-slate-500">{KIND_META[kind].hint}</p>
        </div>
        <button type="submit" className={buttonPrimary} disabled={!value.trim() || add.isPending}>
          <Plus className="h-4 w-4" /> Add
        </button>
        {error && <p className="text-sm text-red-400 md:col-span-3">{error}</p>}
      </form>

      {assets.length === 0 ? (
        <div className={`${card} text-sm text-slate-400`}>
          Add the domains, e-mail domains and brand names you want to watch. Every scan checks them against ransomware
          leak sites, infostealer data, breach catalogs and your Telegram channels.
        </div>
      ) : (
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
          {assets.map((a) => {
            const Icon = KIND_META[a.kind as AssetKind]?.icon ?? Tag;
            return (
              <div key={a.id} className={`${card} flex items-center justify-between gap-3 p-4`}>
                <div className="flex min-w-0 items-center gap-3">
                  <Icon className="h-4 w-4 shrink-0 text-brand-400" />
                  <div className="min-w-0">
                    <p className="truncate font-mono text-sm text-white light:text-slate-900">{a.value}</p>
                    <p className="text-xs text-slate-500">{KIND_META[a.kind as AssetKind]?.label}</p>
                  </div>
                </div>
                <button type="button" aria-label={`Remove ${a.value}`} onClick={() => remove.mutate(a.id)} className="rounded-lg p-2 text-slate-400 hover:bg-red-950/40 hover:text-red-400">
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

// --------------------------------------------------------------------------- telegram

const TelegramAccountCard = ({ account }: { account?: TelegramAccountStatus }) => {
  const queryClient = useQueryClient();
  const [apiId, setApiId] = useState("");
  const [apiHash, setApiHash] = useState("");
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["darkweb-tg-account"] });

  const start = useMutation({
    mutationFn: async () => apiClient.post("/darkweb/telegram-account/start", { api_id: Number(apiId), api_hash: apiHash, phone }, { timeout: 60000 }),
    onSuccess: () => { setError(null); refresh(); },
    onError: (e) => setError(errorText(e))
  });
  const verify = useMutation({
    mutationFn: async () => apiClient.post("/darkweb/telegram-account/verify", { code, password: password || undefined }, { timeout: 60000 }),
    onSuccess: () => { setError(null); setCode(""); setPassword(""); refresh(); },
    onError: (e) => setError(errorText(e))
  });
  const disconnect = useMutation({
    mutationFn: async () => apiClient.delete("/darkweb/telegram-account"),
    onSuccess: () => { refresh(); queryClient.invalidateQueries({ queryKey: ["darkweb-channels"] }); }
  });

  return (
    <section className={card}>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h3 className="flex items-center gap-2 font-semibold text-white light:text-slate-900">
          <Lock className="h-4 w-4 text-brand-400" /> Telegram account (optional)
        </h3>
        {account?.status === "connected" && (
          <span className="rounded-full border border-emerald-700 bg-emerald-950/40 px-2.5 py-0.5 text-xs text-emerald-300">
            Connected: {account.display_name} {account.phone}
          </span>
        )}
      </div>
      <p className="mb-3 text-sm text-slate-400">
        Needed only for private channels or groups you have joined. Create an API ID and hash at{" "}
        <a href="https://my.telegram.org/apps" target="_blank" rel="noopener noreferrer" className="text-brand-400 hover:underline">my.telegram.org/apps</a>.
        The session is stored encrypted and is only used to read messages. Use a dedicated research account.
      </p>

      {account?.status === "connected" ? (
        <button type="button" className={buttonGhost} onClick={() => disconnect.mutate()}>Disconnect account</button>
      ) : account?.status === "pending" ? (
        <form className="grid gap-3 md:grid-cols-3" onSubmit={(e) => { e.preventDefault(); verify.mutate(); }}>
          <input aria-label="Login code" value={code} onChange={(e) => setCode(e.target.value)} placeholder={`Code sent to ${account.phone ?? "your Telegram"}`} className={input} inputMode="numeric" autoComplete="one-time-code" />
          <input aria-label="Two-step verification password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="2FA password (if enabled)" className={input} autoComplete="off" />
          <div className="flex gap-2">
            <button type="submit" className={buttonPrimary} disabled={!code || verify.isPending}>
              {verify.isPending && <Loader2 className="h-4 w-4 animate-spin" />} Verify
            </button>
            <button type="button" className={buttonGhost} onClick={() => disconnect.mutate()}>Cancel</button>
          </div>
        </form>
      ) : (
        <form className="grid gap-3 md:grid-cols-4" onSubmit={(e) => { e.preventDefault(); start.mutate(); }}>
          <input aria-label="API ID" value={apiId} onChange={(e) => setApiId(e.target.value.replace(/\D/g, ""))} placeholder="API ID" className={input} inputMode="numeric" />
          <input aria-label="API hash" value={apiHash} onChange={(e) => setApiHash(e.target.value.trim())} placeholder="API hash" className={input} autoComplete="off" />
          <input aria-label="Phone number" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+90 5xx xxx xx xx" className={input} inputMode="tel" />
          <button type="submit" className={buttonPrimary} disabled={!apiId || apiHash.length < 16 || phone.length < 6 || start.isPending}>
            {start.isPending && <Loader2 className="h-4 w-4 animate-spin" />} Send login code
          </button>
        </form>
      )}
      {error && <p className="mt-2 text-sm text-red-400">{error}</p>}
    </section>
  );
};

const TelegramTab = () => {
  const queryClient = useQueryClient();
  const [username, setUsername] = useState("");
  const [mode, setMode] = useState<"public" | "account">("public");
  const [error, setError] = useState<string | null>(null);

  const { data: channels = [] } = useQuery<TelegramChannel[]>({
    queryKey: ["darkweb-channels"],
    queryFn: async () => (await apiClient.get<TelegramChannel[]>("/darkweb/channels")).data
  });
  const { data: account } = useQuery<TelegramAccountStatus>({
    queryKey: ["darkweb-tg-account"],
    queryFn: async () => (await apiClient.get<TelegramAccountStatus>("/darkweb/telegram-account")).data
  });
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["darkweb-channels"] });
    queryClient.invalidateQueries({ queryKey: ["darkweb-summary"] });
  };
  const add = useMutation({
    mutationFn: async () => apiClient.post("/darkweb/channels", { username, mode }),
    onSuccess: () => { setUsername(""); setError(null); invalidate(); },
    onError: (e) => setError(errorText(e))
  });
  const remove = useMutation({ mutationFn: async (id: string) => apiClient.delete(`/darkweb/channels/${id}`), onSuccess: invalidate });
  const { data: suggested = [] } = useQuery<SuggestedChannel[]>({
    queryKey: ["darkweb-suggested", channels.length],
    queryFn: async () => (await apiClient.get<SuggestedChannel[]>("/darkweb/channels/suggested")).data
  });
  const addSuggested = useMutation({
    mutationFn: async (username: string) => apiClient.post("/darkweb/channels", { username, mode: "public" }),
    onSuccess: () => { setError(null); invalidate(); },
    onError: (e) => setError(errorText(e))
  });

  return (
    <div className="space-y-4">
      {suggested.some((c) => !c.added) && (
        <div className={`${card} p-4`}>
          <p className="mb-2 text-sm font-medium text-white light:text-slate-900">Suggested public channels</p>
          <div className="flex flex-wrap gap-2">
            {suggested.filter((c) => !c.added).map((c) => (
              <button
                key={c.username}
                type="button"
                title={c.why}
                disabled={addSuggested.isPending}
                onClick={() => addSuggested.mutate(c.username)}
                className={buttonGhost}
              >
                <Plus className="h-4 w-4" /> {c.title} <span className="text-xs text-slate-500">@{c.username} · {c.why}</span>
              </button>
            ))}
          </div>
        </div>
      )}
      <form className={`${card} grid gap-3 md:grid-cols-[1fr_14rem_auto]`} onSubmit={(e) => { e.preventDefault(); add.mutate(); }}>
        <div>
          <input aria-label="Channel" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="@channel or https://t.me/channel" className={input} />
          <p className="mt-1 text-xs text-slate-500">
            Public channels are read through Telegram's web preview - no account needed. Message text only; files are never downloaded.
          </p>
        </div>
        <select aria-label="Read mode" value={mode} onChange={(e) => setMode(e.target.value as "public" | "account")} className={input}>
          <option value="public">Public preview</option>
          <option value="account" disabled={account?.status !== "connected"}>
            My Telegram account{account?.status !== "connected" ? " (connect first)" : ""}
          </option>
        </select>
        <button type="submit" className={buttonPrimary} disabled={!username.trim() || add.isPending}>
          {add.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />} Add channel
        </button>
        {error && <p className="text-sm text-red-400 md:col-span-3">{error}</p>}
      </form>

      {channels.length > 0 && (
        <div className="overflow-x-auto rounded-2xl border border-slate-800 light:border-slate-200">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-900/60 text-xs uppercase text-slate-400 light:bg-slate-50">
              <tr>
                <th className="px-4 py-2">Channel</th>
                <th className="px-4 py-2">Mode</th>
                <th className="px-4 py-2">Last checked</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 light:divide-slate-200">
              {channels.map((c) => (
                <tr key={c.id}>
                  <td className="px-4 py-2">
                    <p className="font-medium text-white light:text-slate-900">{c.title || c.username}</p>
                    <p className="font-mono text-xs text-slate-500">@{c.username}</p>
                  </td>
                  <td className="px-4 py-2 text-slate-400">{c.mode === "public" ? "Public preview" : "Account"}</td>
                  <td className="px-4 py-2 text-slate-400">{c.last_checked_at ? new Date(c.last_checked_at).toLocaleString() : "Not yet"}</td>
                  <td className="px-4 py-2">
                    {c.last_error ? (
                      <span className="text-xs text-red-400" title={c.last_error}>Error: {c.last_error.slice(0, 60)}</span>
                    ) : !c.is_active ? (
                      <span className="text-xs text-slate-500">Paused</span>
                    ) : (
                      <span className="text-xs text-emerald-400">OK</span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <button type="button" aria-label={`Remove ${c.username}`} onClick={() => remove.mutate(c.id)} className="rounded-lg p-2 text-slate-400 hover:bg-red-950/40 hover:text-red-400">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <TelegramAccountCard account={account} />
    </div>
  );
};

// --------------------------------------------------------------------------- page

const TABS = [
  { key: "mentions", label: "Mentions" },
  { key: "assets", label: "Monitored assets" },
  { key: "telegram", label: "Telegram" },
  { key: "sources", label: "Sources" }
] as const;

const DarkWebPage = () => {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<(typeof TABS)[number]["key"]>("mentions");
  const [scanMessage, setScanMessage] = useState<string | null>(null);

  const { data: summary } = useQuery<DarkWebSummary>({
    queryKey: ["darkweb-summary"],
    queryFn: async () => (await apiClient.get<DarkWebSummary>("/darkweb/summary")).data
  });

  const scan = useMutation({
    mutationFn: async () => (await apiClient.post("/darkweb/scan", undefined, { timeout: 180000 })).data,
    onSuccess: (r: any) => {
      setScanMessage(
        r.status === "no_assets"
          ? "Add monitored assets first."
          : `Scan finished: ${r.new_mentions} new mention${r.new_mentions === 1 ? "" : "s"} (${r.leak_posts_checked} leak posts checked).`
      );
      queryClient.invalidateQueries({ queryKey: ["darkweb-mentions"] });
      queryClient.invalidateQueries({ queryKey: ["darkweb-summary"] });
      queryClient.invalidateQueries({ queryKey: ["darkweb-channels"] });
    },
    onError: (e) => setScanMessage(errorText(e))
  });

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-white light:text-slate-900">Dark Web Monitoring</h2>
          <p className="text-sm text-slate-400 light:text-slate-600">
            Ransomware leak sites, infostealer logs, breach catalogs and Telegram channels checked against your assets.
          </p>
        </div>
        <button type="button" className={buttonPrimary} onClick={() => scan.mutate()} disabled={scan.isPending}>
          {scan.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          {scan.isPending ? "Scanning..." : "Scan now"}
        </button>
      </header>

      {scanMessage && <p className="rounded-lg border border-slate-800 bg-slate-900/60 p-3 text-sm text-slate-300 light:border-slate-200 light:bg-slate-50 light:text-slate-700">{scanMessage}</p>}

      <div className="inline-flex max-w-full overflow-x-auto rounded-lg border border-slate-700 p-1 light:border-slate-300" role="tablist" aria-label="Dark web sections">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            role="tab"
            aria-selected={tab === t.key}
            onClick={() => setTab(t.key)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${tab === t.key ? "bg-brand-600 text-white" : "text-slate-400 hover:text-white light:text-slate-600 light:hover:text-slate-900"}`}
          >
            {t.label}
            {t.key === "mentions" && summary?.unread ? ` (${summary.unread})` : ""}
            {t.key === "assets" && summary ? ` (${summary.assets})` : ""}
            {t.key === "telegram" && summary ? ` (${summary.channels})` : ""}
          </button>
        ))}
      </div>

      {tab === "mentions" && <MentionsTab summary={summary} />}
      {tab === "assets" && <AssetsTab />}
      {tab === "telegram" && <TelegramTab />}
      {tab === "sources" && <SourcesTab />}
    </div>
  );
};

export default DarkWebPage;
