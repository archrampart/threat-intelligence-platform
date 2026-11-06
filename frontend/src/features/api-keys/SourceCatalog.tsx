import { useMemo, useState } from "react";
import { CheckCircle, ExternalLink, Library } from "lucide-react";

import type { APISourceResponse, SourceAccess } from "@/features/api-sources/types";

export const ACCESS_META: Record<SourceAccess, { label: string; hint: string; className: string }> = {
  none: {
    label: "No key",
    hint: "Works without an API key",
    className: "border-emerald-700 bg-emerald-950/40 text-emerald-300 light:border-emerald-300 light:bg-emerald-50 light:text-emerald-700"
  },
  free_key: {
    label: "Free key",
    hint: "Create a free account to get your own key",
    className: "border-sky-700 bg-sky-950/40 text-sky-300 light:border-sky-300 light:bg-sky-50 light:text-sky-700"
  },
  freemium: {
    label: "Free tier",
    hint: "Free key with tight limits, paid plans for heavier use",
    className: "border-amber-700 bg-amber-950/30 text-amber-300 light:border-amber-300 light:bg-amber-50 light:text-amber-700"
  },
  on_request: {
    label: "On request",
    hint: "Access is granted manually by the provider",
    className: "border-violet-700 bg-violet-950/30 text-violet-300 light:border-violet-300 light:bg-violet-50 light:text-violet-700"
  },
  paid: {
    label: "Paid",
    hint: "Commercial subscription required",
    className: "border-rose-700 bg-rose-950/30 text-rose-300 light:border-rose-300 light:bg-rose-50 light:text-rose-700"
  },
  unknown: {
    label: "Key",
    hint: "Requires an API key",
    className: "border-slate-700 bg-slate-900/40 text-slate-300 light:border-slate-300 light:bg-slate-50 light:text-slate-600"
  }
};

export const AccessBadge = ({ access }: { access?: SourceAccess }) => {
  const meta = ACCESS_META[access ?? "unknown"] ?? ACCESS_META.unknown;
  return (
    <span title={meta.hint} className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${meta.className}`}>
      {meta.label}
    </span>
  );
};

/** Shown in the "Add API key" form once a source is selected. */
export const SourceAccessInfo = ({ source }: { source?: APISourceResponse }) => {
  if (!source) return null;
  const meta = ACCESS_META[source.access ?? "unknown"] ?? ACCESS_META.unknown;
  return (
    <div className="mt-2 rounded-lg border border-slate-800 bg-slate-900/50 p-3 text-xs text-slate-400 light:border-slate-200 light:bg-slate-50 light:text-slate-600">
      <div className="mb-1 flex flex-wrap items-center gap-2">
        <AccessBadge access={source.access} />
        <span>{meta.hint}</span>
      </div>
      {source.description && <p className="mb-1">{source.description}</p>}
      {source.key_signup_url && (
        <a
          href={source.key_signup_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 font-medium text-brand-400 hover:underline light:text-brand-600"
        >
          Get your own key <ExternalLink className="h-3 w-3" />
        </a>
      )}
    </div>
  );
};

const FILTERS: { key: "all" | SourceAccess; label: string }[] = [
  { key: "all", label: "All" },
  { key: "none", label: "No key" },
  { key: "free_key", label: "Free key" },
  { key: "freemium", label: "Free tier" },
  { key: "on_request", label: "On request" },
  { key: "paid", label: "Paid" }
];

/** Overview of every active source, what it costs and whether the user already added it. */
const SourceCatalog = ({
  sources,
  configuredSourceIds,
  onAdd
}: {
  sources: APISourceResponse[];
  configuredSourceIds: Set<string>;
  onAdd: (sourceId: string) => void;
}) => {
  const [filter, setFilter] = useState<"all" | SourceAccess>("all");
  const visible = useMemo(
    () =>
      [...sources]
        .filter((s) => filter === "all" || s.access === filter)
        .sort((a, b) => a.display_name.localeCompare(b.display_name)),
    [sources, filter]
  );

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 light:border-slate-200 light:bg-white">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Library className="h-4 w-4 text-brand-400 light:text-brand-600" />
          <h3 className="text-lg font-semibold text-white light:text-slate-900">Source catalog</h3>
          <span className="text-xs text-slate-500">{sources.length} active sources · keys are personal</span>
        </div>
        <div className="flex flex-wrap gap-1" role="tablist" aria-label="Filter by access">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              type="button"
              role="tab"
              aria-selected={filter === f.key}
              onClick={() => setFilter(f.key)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                filter === f.key
                  ? "bg-brand-600 text-white"
                  : "bg-slate-800 text-slate-300 hover:bg-slate-700 light:bg-slate-100 light:text-slate-700 light:hover:bg-slate-200"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>
      <div className="grid max-h-[26rem] gap-2 overflow-y-auto pr-1 sm:grid-cols-2 xl:grid-cols-3">
        {visible.map((source) => {
          const configured = configuredSourceIds.has(source.id);
          return (
            <div
              key={source.id}
              className="flex flex-col justify-between gap-2 rounded-lg border border-slate-800 bg-slate-950/50 p-3 light:border-slate-200 light:bg-slate-50"
            >
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-white light:text-slate-900">{source.display_name}</span>
                  <AccessBadge access={source.access} />
                </div>
                <p className="mt-1 text-xs text-slate-500">{(source.supported_ioc_types ?? []).join(", ") || "—"}</p>
              </div>
              <div className="flex items-center justify-between text-xs">
                {source.key_signup_url ? (
                  <a
                    href={source.key_signup_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-brand-400 hover:underline light:text-brand-600"
                  >
                    Get key <ExternalLink className="h-3 w-3" />
                  </a>
                ) : (
                  <span />
                )}
                {configured ? (
                  <span className="inline-flex items-center gap-1 text-emerald-400 light:text-emerald-600">
                    <CheckCircle className="h-3 w-3" /> Added
                  </span>
                ) : (
                  <button
                    type="button"
                    onClick={() => onAdd(source.id)}
                    className="rounded-md border border-slate-700 px-2 py-0.5 text-slate-300 hover:bg-slate-800 light:border-slate-300 light:text-slate-700 light:hover:bg-slate-100"
                  >
                    Add
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
};

export default SourceCatalog;
