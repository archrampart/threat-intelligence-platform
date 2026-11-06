import { useRef, useState } from "react";
import { ClipboardList, Download, Loader2, Play, Square, Wand2 } from "lucide-react";

import { apiClient } from "@/lib/api";
import type { IOCQueryResponse } from "@/features/ioc/types";

interface ExtractedIoc {
  ioc_type: string;
  ioc_value: string;
}

interface BulkRow extends ExtractedIoc {
  selected: boolean;
  state: "pending" | "running" | "done" | "error";
  result?: IOCQueryResponse;
  error?: string;
}

const QUERYABLE = new Set(["ip", "domain", "url", "hash", "email", "cve"]);
const MAX_BATCH = 100;

const riskTone = (risk?: string | null) => {
  switch (risk) {
    case "high":
      return "text-red-400 light:text-red-600";
    case "medium":
      return "text-orange-400 light:text-orange-600";
    case "low":
      return "text-yellow-400 light:text-yellow-600";
    case "clean":
      return "text-emerald-400 light:text-emerald-600";
    default:
      return "text-slate-400";
  }
};

const signals = (result?: IOCQueryResponse) =>
  (result?.queried_sources ?? [])
    .filter((s) => s.status === "success" && s.risk_score !== null && s.risk_score !== undefined && s.risk_score > 0)
    .sort((a, b) => (b.risk_score ?? 0) - (a.risk_score ?? 0))
    .map((s) => s.source);

const BulkIocPanel = () => {
  const [text, setText] = useState("");
  const [rows, setRows] = useState<BulkRow[]>([]);
  const [truncated, setTruncated] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const stopRef = useRef(false);

  const extract = async () => {
    setExtracting(true);
    setError(null);
    try {
      const { data } = await apiClient.post<{ iocs: ExtractedIoc[]; truncated: boolean }>("/ioc/extract", { text });
      setRows(
        data.iocs.map((ioc) => ({ ...ioc, selected: QUERYABLE.has(ioc.ioc_type), state: "pending" as const }))
      );
      setTruncated(data.truncated);
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || "Extraction failed");
    } finally {
      setExtracting(false);
    }
  };

  const run = async () => {
    stopRef.current = false;
    setRunning(true);
    const targets = rows
      .map((row, index) => ({ row, index }))
      .filter(({ row }) => row.selected && row.state !== "done")
      .slice(0, MAX_BATCH);
    // Sequential on purpose: sources are already queried in parallel per IOC and this
    // keeps API quotas and rate limits predictable.
    for (const { row, index } of targets) {
      if (stopRef.current) break;
      setRows((prev) => prev.map((r, i) => (i === index ? { ...r, state: "running" } : r)));
      try {
        const { data } = await apiClient.post<IOCQueryResponse>(
          "/ioc/query",
          { ioc_type: row.ioc_type, ioc_value: row.ioc_value },
          { timeout: 120000 }
        );
        setRows((prev) => prev.map((r, i) => (i === index ? { ...r, state: "done", result: data } : r)));
      } catch (e: any) {
        const detail = e?.response?.data?.detail || e?.message || "Query failed";
        setRows((prev) => prev.map((r, i) => (i === index ? { ...r, state: "error", error: String(detail) } : r)));
        if (e?.response?.status === 429) {
          setError("Rate limit reached - stopped. Wait a minute and press Run again to continue.");
          break;
        }
      }
    }
    setRunning(false);
  };

  const exportCsv = () => {
    const quote = (v: string) => {
      const safe = /^[=+\-@\t\r]/.test(v) ? `'${v}` : v; // spreadsheet formula injection
      return `"${safe.replace(/"/g, '""')}"`;
    };
    const lines = [
      ["ioc_type", "ioc_value", "overall_risk", "signals"].join(","),
      ...rows
        .filter((r) => r.state === "done")
        .map((r) =>
          [r.ioc_type, r.ioc_value, r.result?.overall_risk ?? "unknown", signals(r.result).join(" ")].map(quote).join(",")
        )
    ];
    const url = URL.createObjectURL(new Blob([lines.join("\n")], { type: "text/csv" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `bulk_ioc_results_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const selected = rows.filter((r) => r.selected).length;
  const done = rows.filter((r) => r.state === "done" || r.state === "error").length;
  const total = rows.filter((r) => r.selected).length;

  return (
    <section className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900/40 p-6 light:border-slate-200 light:bg-white">
      <div>
        <label htmlFor="bulk-ioc-text" className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-300 light:text-slate-700">
          <ClipboardList className="h-4 w-4" /> Paste a report, log, e-mail or list
        </label>
        <textarea
          id="bulk-ioc-text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={7}
          placeholder={"Defanged values are fine: hxxps://evil[.]com/gate.php, 185.220.101[.]7, CVE-2024-3400 ..."}
          className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 font-mono text-sm text-white focus:border-brand-500 focus:outline-hidden light:border-slate-300 light:bg-white light:text-slate-900"
        />
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={extract}
            disabled={!text.trim() || extracting || running}
            className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700 disabled:opacity-50"
          >
            {extracting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wand2 className="h-4 w-4" />} Extract IOCs
          </button>
          {rows.length > 0 && (
            <span className="text-xs text-slate-400">
              {rows.length} unique IOCs found{truncated ? " (truncated)" : ""} · {selected} selected
            </span>
          )}
        </div>
      </div>

      {error && <p className="rounded-lg border border-red-800 bg-red-950/40 p-3 text-sm text-red-300">{error}</p>}

      {rows.length > 0 && (
        <>
          <div className="flex flex-wrap items-center gap-3">
            {running ? (
              <button
                type="button"
                onClick={() => (stopRef.current = true)}
                className="inline-flex items-center gap-2 rounded-lg bg-slate-700 px-4 py-2 text-sm font-medium text-white hover:bg-slate-600"
              >
                <Square className="h-4 w-4" /> Stop
              </button>
            ) : (
              <button
                type="button"
                onClick={run}
                disabled={selected === 0}
                className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                <Play className="h-4 w-4" /> Query {Math.min(selected, MAX_BATCH)} IOC{selected === 1 ? "" : "s"}
              </button>
            )}
            <button
              type="button"
              onClick={exportCsv}
              disabled={!rows.some((r) => r.state === "done")}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800 disabled:opacity-50 light:border-slate-300 light:text-slate-700 light:hover:bg-slate-100"
            >
              <Download className="h-4 w-4" /> Export CSV
            </button>
            {(running || done > 0) && total > 0 && (
              <div className="flex min-w-40 flex-1 items-center gap-2">
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-800 light:bg-slate-200">
                  <div className="h-full bg-brand-500 transition-all" style={{ width: `${(done / total) * 100}%` }} />
                </div>
                <span className="text-xs text-slate-400">
                  {done}/{total}
                </span>
              </div>
            )}
          </div>

          <div className="overflow-x-auto rounded-lg border border-slate-800 light:border-slate-200">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-900/60 text-xs uppercase text-slate-400 light:bg-slate-50">
                <tr>
                  <th className="px-3 py-2">
                    <input
                      type="checkbox"
                      aria-label="Select all"
                      checked={selected === rows.length}
                      onChange={(e) => setRows((prev) => prev.map((r) => ({ ...r, selected: e.target.checked })))}
                    />
                  </th>
                  <th className="px-3 py-2">Type</th>
                  <th className="px-3 py-2">Value</th>
                  <th className="px-3 py-2">Risk</th>
                  <th className="px-3 py-2">Signals</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 light:divide-slate-200">
                {rows.map((row, index) => (
                  <tr key={`${row.ioc_type}:${row.ioc_value}`} className="align-top">
                    <td className="px-3 py-2">
                      <input
                        type="checkbox"
                        aria-label={`Select ${row.ioc_value}`}
                        checked={row.selected}
                        disabled={running}
                        onChange={(e) =>
                          setRows((prev) => prev.map((r, i) => (i === index ? { ...r, selected: e.target.checked } : r)))
                        }
                      />
                    </td>
                    <td className="px-3 py-2 text-xs uppercase text-slate-400">{row.ioc_type}</td>
                    <td className="max-w-xs break-all px-3 py-2 font-mono text-xs text-white light:text-slate-900">{row.ioc_value}</td>
                    <td className="px-3 py-2 text-xs font-semibold">
                      {row.state === "running" && <Loader2 className="h-4 w-4 animate-spin text-brand-400" />}
                      {row.state === "done" && (
                        <span className={`uppercase ${riskTone(row.result?.overall_risk)}`}>{row.result?.overall_risk ?? "unknown"}</span>
                      )}
                      {row.state === "error" && (
                        <span className="text-red-400" title={row.error}>
                          error
                        </span>
                      )}
                      {row.state === "pending" && <span className="text-slate-600">—</span>}
                    </td>
                    <td className="px-3 py-2 text-xs text-slate-400">{signals(row.result).join(", ") || ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
};

export default BulkIocPanel;
