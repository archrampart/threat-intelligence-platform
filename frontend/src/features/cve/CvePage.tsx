import { useState, useEffect, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, ExternalLink, AlertTriangle, Shield, Calendar } from "lucide-react";

import { apiClient } from "@/lib/api";
import CVEDetailModal from "./CVEDetailModal";
import type { CVESearchRequest, CVESearchResponse, CVE } from "@/features/cve/types";

const CvePage = () => {
  const [searchQuery, setSearchQuery] = useState("");
  const [severityFilter, setSeverityFilter] = useState<string>("");
  const [yearFilter, setYearFilter] = useState<string>("");
  const [page, setPage] = useState(1);
  const [selectedCveId, setSelectedCveId] = useState<string | null>(null);
  const pageSize = 20;

  // Generate year options (current year down to 1999)
  const currentYear = new Date().getFullYear();
  const firstCveYear = 1999;
  const yearOptions = Array.from(
    { length: currentYear - firstCveYear + 1 },
    (_, i) => currentYear - i
  );

  // Memoize search request to prevent unnecessary re-renders
  const searchRequest: CVESearchRequest = useMemo(() => ({
    keyword: searchQuery || undefined,
    severity: severityFilter || undefined,
    year: yearFilter ? parseInt(yearFilter) : undefined,
    limit: pageSize,
    offset: (page - 1) * pageSize
  }), [searchQuery, severityFilter, yearFilter, page, pageSize]);

  const [hasSearched, setHasSearched] = useState(false);

  const { data, isLoading } = useQuery<CVESearchResponse>({
    queryKey: ["cves", searchQuery, severityFilter, yearFilter, page],
    queryFn: async () => {
      console.log("CVE Search Request:", searchRequest);
      const response = await apiClient.post<CVESearchResponse>("/cves/search", searchRequest);
      console.log("CVE Search Response:", response.data);
      return response.data;
    },
    enabled: hasSearched, // Only search when user clicks search
  });

  const handleSearch = () => {
    setPage(1);
    setHasSearched(true);
  };

  // Auto-search when filters change (if already searched)
  useEffect(() => {
    if (hasSearched) {
      setPage(1);
    }
  }, [yearFilter, severityFilter, searchQuery, hasSearched]);

  const getSeverityColor = (severity?: string) => {
    switch (severity?.toUpperCase()) {
      case "CRITICAL":
        return "text-red-400 dark:text-red-400 light:text-red-600 bg-red-950/30 dark:bg-red-950/30 light:bg-red-50 border-red-800 dark:border-red-800 light:border-red-300";
      case "HIGH":
        return "text-orange-400 dark:text-orange-400 light:text-orange-600 bg-orange-950/30 dark:bg-orange-950/30 light:bg-orange-50 border-orange-800 dark:border-orange-800 light:border-orange-300";
      case "MEDIUM":
        return "text-yellow-400 dark:text-yellow-400 light:text-yellow-600 bg-yellow-950/30 dark:bg-yellow-950/30 light:bg-yellow-50 border-yellow-800 dark:border-yellow-800 light:border-yellow-300";
      case "LOW":
        return "text-green-400 dark:text-green-400 light:text-green-600 bg-green-950/30 dark:bg-green-950/30 light:bg-green-50 border-green-800 dark:border-green-800 light:border-green-300";
      default:
        return "text-slate-400 dark:text-slate-400 light:text-slate-600 bg-slate-900/30 dark:bg-slate-900/30 light:bg-slate-50 border-slate-800 dark:border-slate-800 light:border-slate-200";
    }
  };

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-2xl font-semibold text-white dark:text-white light:text-slate-900">CVE Database</h2>
        <p className="text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">Search and filter NIST NVD vulnerabilities</p>
      </header>

      {/* Search Form */}
      <div className="rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/40 dark:bg-slate-900/40 light:bg-white p-6">
        <div className="grid gap-4 md:grid-cols-5">
          <div className="md:col-span-2">
            <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">Search</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                placeholder="CVE ID or keyword (e.g., CVE-2024-1234)"
                className="flex-1 rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 placeholder:text-slate-500 dark:placeholder:text-slate-500 light:placeholder:text-slate-400 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
              />
              <button
                onClick={handleSearch}
                disabled={isLoading}
                className="rounded-lg bg-brand-600 dark:bg-brand-600 light:bg-brand-500 px-4 py-2 font-medium text-white transition hover:bg-brand-700 dark:hover:bg-brand-700 light:hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Search className="h-4 w-4" />
              </button>
            </div>
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">Year</label>
            <select
              value={yearFilter}
              onChange={(e) => {
                setYearFilter(e.target.value);
                if (hasSearched) {
                  setPage(1);
                }
              }}
              className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
            >
              <option value="">All Years</option>
              {yearOptions.map((year) => (
                <option key={year} value={year.toString()}>
                  {year}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">Severity</label>
            <select
              value={severityFilter}
              onChange={(e) => {
                setSeverityFilter(e.target.value);
                if (hasSearched) {
                  setPage(1);
                }
              }}
              className="w-full rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white px-4 py-2 text-white dark:text-white light:text-slate-900 focus:border-brand-500 dark:focus:border-brand-500 light:focus:border-brand-600 focus:outline-none"
            >
              <option value="">All</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>
          </div>
          <div className="flex items-end">
            <button
              onClick={handleSearch}
              disabled={isLoading}
              className="w-full rounded-lg bg-brand-600 dark:bg-brand-600 light:bg-brand-500 px-4 py-2 font-medium text-white transition hover:bg-brand-700 dark:hover:bg-brand-700 light:hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isLoading ? "Searching..." : "Search"}
            </button>
          </div>
        </div>
      </div>

      {/* Results */}
      {isLoading && (
        <div className="rounded-2xl border border-dashed border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900/30 dark:bg-slate-900/30 light:bg-slate-50 p-12 text-center">
          <Shield className="mx-auto mb-4 h-12 w-12 text-slate-600 dark:text-slate-600 light:text-slate-400" />
          <p className="text-slate-400 dark:text-slate-400 light:text-slate-600">Searching CVEs...</p>
        </div>
      )}

      {data && !isLoading && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">
              Found {data.total} CVE(s) | Page {page} of {data.total_pages || 1}
            </p>
            {data.total_pages && data.total_pages > 1 && (
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white px-4 py-2 text-sm text-white dark:text-white light:text-slate-900 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage((p) => p + 1)}
                  disabled={page >= (data.total_pages || 1)}
                  className="rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white px-4 py-2 text-sm text-white dark:text-white light:text-slate-900 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            )}
          </div>

          {data.cves && data.cves.length > 0 ? (
            <div className="space-y-3">
              {data.cves.map((cve) => (
                <CVECard key={cve.cve_id} cve={cve} onClick={() => setSelectedCveId(cve.cve_id)} />
              ))}
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900/30 dark:bg-slate-900/30 light:bg-slate-50 p-12 text-center">
              <Shield className="mx-auto mb-4 h-12 w-12 text-slate-600 dark:text-slate-600 light:text-slate-400" />
              <p className="text-slate-400 dark:text-slate-400 light:text-slate-600">No CVEs found for the selected filters</p>
            </div>
          )}
        </div>
      )}

      {!data && !isLoading && hasSearched && (
        <div className="rounded-2xl border border-dashed border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900/30 dark:bg-slate-900/30 light:bg-slate-50 p-12 text-center">
          <Shield className="mx-auto mb-4 h-12 w-12 text-slate-600 dark:text-slate-600 light:text-slate-400" />
          <p className="text-slate-400 dark:text-slate-400 light:text-slate-600">No results found. Try different search criteria.</p>
        </div>
      )}

      {!data && !isLoading && !hasSearched && (
        <div className="rounded-2xl border border-dashed border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900/30 dark:bg-slate-900/30 light:bg-slate-50 p-12 text-center">
          <Shield className="mx-auto mb-4 h-12 w-12 text-slate-600 dark:text-slate-600 light:text-slate-400" />
          <p className="text-slate-400 dark:text-slate-400 light:text-slate-600">Search for CVEs using the form above</p>
        </div>
      )}

      {/* CVE Detail Modal */}
      {selectedCveId && (
        <CVEDetailModal
          cveId={selectedCveId}
          onClose={() => setSelectedCveId(null)}
        />
      )}
    </div>
  );
};

const CVECard = ({ cve, onClick }: { cve: CVE; onClick?: () => void }) => {
  const getSeverityColor = (severity?: string) => {
    switch (severity?.toUpperCase()) {
      case "CRITICAL":
        return "text-red-400 dark:text-red-400 light:text-red-600 bg-red-950/30 dark:bg-red-950/30 light:bg-red-50 border-red-800 dark:border-red-800 light:border-red-300";
      case "HIGH":
        return "text-orange-400 dark:text-orange-400 light:text-orange-600 bg-orange-950/30 dark:bg-orange-950/30 light:bg-orange-50 border-orange-800 dark:border-orange-800 light:border-orange-300";
      case "MEDIUM":
        return "text-yellow-400 dark:text-yellow-400 light:text-yellow-600 bg-yellow-950/30 dark:bg-yellow-950/30 light:bg-yellow-50 border-yellow-800 dark:border-yellow-800 light:border-yellow-300";
      case "LOW":
        return "text-green-400 dark:text-green-400 light:text-green-600 bg-green-950/30 dark:bg-green-950/30 light:bg-green-50 border-green-800 dark:border-green-800 light:border-green-300";
      default:
        return "text-slate-400 dark:text-slate-400 light:text-slate-600 bg-slate-900/30 dark:bg-slate-900/30 light:bg-slate-50 border-slate-800 dark:border-slate-800 light:border-slate-200";
    }
  };

  return (
    <div 
      onClick={onClick}
      className="rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/40 dark:bg-slate-900/40 light:bg-white p-4 transition hover:bg-slate-900/60 dark:hover:bg-slate-900/60 light:hover:bg-slate-50 cursor-pointer"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="mb-2 flex items-center gap-3">
            <h3 className="text-lg font-semibold text-white dark:text-white light:text-slate-900">{cve.cve_id}</h3>
            {cve.cvss_v3?.base_severity && (
              <span className={`rounded-full border px-3 py-0.5 text-xs font-medium ${getSeverityColor(cve.cvss_v3.base_severity)}`}>
                {cve.cvss_v3.base_severity}
              </span>
            )}
            {cve.cvss_v3?.base_score && (
              <span className="text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">CVSS: {cve.cvss_v3.base_score}</span>
            )}
          </div>
          {cve.description && (
            <p className="mb-3 text-sm text-slate-300 dark:text-slate-300 light:text-slate-700 line-clamp-2">{cve.description}</p>
          )}
          <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 dark:text-slate-500 light:text-slate-500">
            {cve.published_date && (
              <div className="flex items-center gap-1">
                <Calendar className="h-3 w-3" />
                <span>Published: {new Date(cve.published_date).toLocaleDateString()}</span>
              </div>
            )}
            {cve.cwe_id && (
              <div className="flex items-center gap-1">
                <AlertTriangle className="h-3 w-3" />
                <span>{cve.cwe_id}</span>
              </div>
            )}
            {cve.affected_products.length > 0 && (
              <span>{cve.affected_products.length} affected product(s)</span>
            )}
          </div>
        </div>
        <div className="ml-4 flex gap-2">
          {cve.nvd_url && (
            <a
              href={cve.nvd_url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-950 dark:bg-slate-950 light:bg-white p-2 text-slate-400 dark:text-slate-400 light:text-slate-600 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100 hover:text-white dark:hover:text-white light:hover:text-slate-900"
            >
              <ExternalLink className="h-4 w-4" />
            </a>
          )}
        </div>
      </div>
    </div>
  );
};

export default CvePage;
