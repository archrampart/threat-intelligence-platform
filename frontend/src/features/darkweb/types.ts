export type AssetKind = "domain" | "keyword" | "email_domain";
export type MentionSource = "ransomware" | "infostealer" | "breach" | "forum" | "telegram" | "feed";
export type Severity = "critical" | "high" | "medium" | "low";

export interface MonitoredAsset {
  id: string;
  kind: AssetKind;
  value: string;
  is_active: boolean;
  created_at: string;
}

export interface TelegramChannel {
  id: string;
  username: string;
  title?: string | null;
  mode: "public" | "account";
  is_active: boolean;
  last_checked_at?: string | null;
  last_error?: string | null;
  last_message_id: number;
}

export interface TelegramAccountStatus {
  status: "not_connected" | "pending" | "connected";
  phone?: string | null;
  display_name?: string | null;
}

export interface Mention {
  id: string;
  source: MentionSource;
  severity: Severity;
  matched_term: string;
  title: string;
  snippet?: string | null;
  url?: string | null;
  actor?: string | null;
  published_at?: string | null;
  details?: Record<string, unknown> | null;
  is_read: boolean;
  created_at: string;
}

export interface MentionList {
  items: Mention[];
  total: number;
  page: number;
  page_size: number;
}

export interface DarkWebSummary {
  by_source: Partial<Record<MentionSource, number>>;
  unread: number;
  assets: number;
  channels: number;
}

export interface FeedConfig {
  url: string;
  format: "json" | "rss";
  items_path?: string;
  title_path?: string;
  text_path?: string;
  url_path?: string;
  date_path?: string;
  severity: Severity;
}

export interface DarkWebSource {
  key: string;
  name: string;
  description?: string | null;
  category: "ransomware" | "infostealer" | "breach" | "telegram" | "forum" | "news" | "feed";
  builtin: boolean;
  homepage?: string | null;
  is_enabled: boolean;
  user_enabled: boolean;
  status: "ok" | "error" | "never" | "disabled";
  last_fetch_at?: string | null;
  last_success_at?: string | null;
  last_item_count?: number | null;
  last_duration_ms?: number | null;
  last_error?: string | null;
  config?: FeedConfig | null;
}

export interface FeedPreview {
  count: number;
  items: { title: string; text: string; url: string; published_at?: string | null }[];
}

export interface SuggestedChannel {
  username: string;
  title: string;
  why: string;
  added: boolean;
}
