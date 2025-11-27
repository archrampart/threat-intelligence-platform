import { useQuery } from "@tanstack/react-query";
import { X, ExternalLink, Shield, Calendar, AlertTriangle, Package, Link2, Info } from "lucide-react";
import { apiClient } from "@/lib/api";
import type { CVE } from "./types";

// CVSS Vector String Parser
const parseCVSSVector = (vectorString?: string): Record<string, string> | null => {
  if (!vectorString || !vectorString.trim()) return null;
  
  const metrics: Record<string, string> = {};
  
  // Remove CVSS version prefix (e.g., "CVSS:3.1/" or "CVSS:3.0/")
  let cleanVector = vectorString.trim();
  cleanVector = cleanVector.replace(/^CVSS:\d+\.\d+\//, '');
  
  // Split by '/' to get individual metrics
  const parts = cleanVector.split('/').filter(part => part.trim());
  
  parts.forEach(part => {
    part = part.trim();
    // Split by ':' to get key:value
    const colonIndex = part.indexOf(':');
    if (colonIndex > 0 && colonIndex < part.length - 1) {
      const key = part.substring(0, colonIndex).trim();
      const value = part.substring(colonIndex + 1).trim();
      if (key && value) {
        metrics[key] = value;
      }
    }
  });
  
  return Object.keys(metrics).length > 0 ? metrics : null;
};

// CVSS Metric Labels
const CVSS_LABELS: Record<string, Record<string, string>> = {
  'AV': { 'N': 'Network', 'A': 'Adjacent Network', 'L': 'Local', 'P': 'Physical' },
  'AC': { 'L': 'Low', 'H': 'High' },
  'PR': { 'N': 'None', 'L': 'Low', 'H': 'High' },
  'UI': { 'N': 'None', 'R': 'Required' },
  'S': { 'U': 'Unchanged', 'C': 'Changed' },
  'C': { 'N': 'None', 'L': 'Low', 'H': 'High' },
  'I': { 'N': 'None', 'L': 'Low', 'H': 'High' },
  'A': { 'N': 'None', 'L': 'Low', 'H': 'High' },
};

const CVSS_METRIC_NAMES: Record<string, string> = {
  'AV': 'Attack Vector',
  'AC': 'Attack Complexity',
  'PR': 'Privileges Required',
  'UI': 'User Interaction',
  'S': 'Scope',
  'C': 'Confidentiality Impact',
  'I': 'Integrity Impact',
  'A': 'Availability Impact',
};

interface CVEDetailModalProps {
  cveId: string;
  onClose: () => void;
}

const CVEDetailModal = ({ cveId, onClose }: CVEDetailModalProps) => {
  const { data, isLoading, error } = useQuery<{ cve: CVE }>({
    queryKey: ["cve-detail", cveId],
    queryFn: async () => {
      const response = await apiClient.get(`/cves/${cveId}`);
      return response.data;
    },
    enabled: !!cveId,
  });

  const cve = data?.cve;

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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/50 light:bg-black/30 p-4">
      <div className="relative w-full max-w-4xl max-h-[90vh] overflow-y-auto rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900 dark:bg-slate-900 light:bg-white">
        {/* Header */}
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-950 dark:bg-slate-950 light:bg-slate-50 px-6 py-4">
          <div className="flex items-center gap-3">
            <Shield className="h-6 w-6 text-brand-400 dark:text-brand-400 light:text-brand-600" />
            <h2 className="text-xl font-bold text-white dark:text-white light:text-slate-900">
              {cve?.cve_id || cveId}
            </h2>
            {cve?.cvss_v3?.base_severity && (
              <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${getSeverityColor(cve.cvss_v3.base_severity)}`}>
                {cve.cvss_v3.base_severity}
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 dark:text-slate-400 light:text-slate-600 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100 hover:text-white dark:hover:text-white light:hover:text-slate-900"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {isLoading && (
            <div className="py-12 text-center">
              <p className="text-slate-400 dark:text-slate-400 light:text-slate-600">Loading CVE details...</p>
            </div>
          )}

          {error && (
            <div className="rounded-lg border border-red-800 dark:border-red-800 light:border-red-300 bg-red-950/20 dark:bg-red-950/20 light:bg-red-50 p-4">
              <p className="text-red-400 dark:text-red-400 light:text-red-700">
                Failed to load CVE details. Please try again.
              </p>
            </div>
          )}

          {cve && (
            <>
              {/* Description */}
              <div>
                <h3 className="mb-2 text-lg font-semibold text-white dark:text-white light:text-slate-900">Description</h3>
                <p className="text-slate-300 dark:text-slate-300 light:text-slate-700 leading-relaxed">
                  {cve.description || "No description available."}
                </p>
              </div>

              {/* CVSS Scores */}
              <div className="space-y-4">
                {cve.cvss_v3 && (
                  <div className="rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-950/60 dark:bg-slate-950/60 light:bg-slate-50 p-4">
                    <div className="mb-4 flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-brand-400 dark:text-brand-400 light:text-brand-600" />
                      <h4 className="font-semibold text-white dark:text-white light:text-slate-900">CVSS v3.{cve.cvss_v3.version?.split('.')[1] || '1'}</h4>
                    </div>
                    <div className="mb-4 grid gap-3 md:grid-cols-2">
                      <div className="flex items-center justify-between rounded-lg bg-slate-900/40 dark:bg-slate-900/40 light:bg-slate-100 p-2">
                        <span className="text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">Base Score</span>
                        <span className="text-xl font-bold text-white dark:text-white light:text-slate-900">
                          {cve.cvss_v3.base_score?.toFixed(1) || "N/A"}
                        </span>
                      </div>
                      {cve.cvss_v3.base_severity && (
                        <div className="flex items-center justify-between rounded-lg bg-slate-900/40 dark:bg-slate-900/40 light:bg-slate-100 p-2">
                          <span className="text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">Severity</span>
                          <span className={`text-sm font-semibold px-2 py-1 rounded ${getSeverityColor(cve.cvss_v3.base_severity)}`}>
                            {cve.cvss_v3.base_severity}
                          </span>
                        </div>
                      )}
                    </div>
                    
                    {cve.cvss_v3.vector_string && (
                      <>
                        <div className="mb-3 flex items-center gap-2">
                          <Info className="h-4 w-4 text-slate-400 dark:text-slate-400 light:text-slate-600" />
                          <h5 className="text-sm font-semibold text-white dark:text-white light:text-slate-900">CVSS Metrics</h5>
                        </div>
                        <div className="mb-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                          {(() => {
                            const metrics = parseCVSSVector(cve.cvss_v3.vector_string);
                            console.log('CVSS v3 Vector String:', cve.cvss_v3.vector_string);
                            console.log('Parsed Metrics:', metrics);
                            
                            if (!metrics || Object.keys(metrics).length === 0) {
                              return (
                                <div className="col-span-full rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/30 dark:bg-slate-900/30 light:bg-slate-50 p-2">
                                  <p className="text-xs text-slate-500 dark:text-slate-500 light:text-slate-500">
                                    Could not parse vector string. Raw: {cve.cvss_v3.vector_string}
                                  </p>
                                </div>
                              );
                            }
                            
                            return Object.entries(metrics).map(([key, value]) => {
                              const metricName = CVSS_METRIC_NAMES[key] || key;
                              const metricValue = CVSS_LABELS[key]?.[value] || value;
                              return (
                                <div key={key} className="rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/30 dark:bg-slate-900/30 light:bg-slate-50 p-2">
                                  <p className="text-xs text-slate-500 dark:text-slate-500 light:text-slate-500">{metricName}</p>
                                  <p className="text-sm font-medium text-white dark:text-white light:text-slate-900">{metricValue}</p>
                                  <p className="text-xs font-mono text-slate-500 dark:text-slate-500 light:text-slate-500">{key}:{value}</p>
                                </div>
                              );
                            });
                          })()}
                        </div>
                        <div className="rounded-lg bg-slate-900/40 dark:bg-slate-900/40 light:bg-slate-100 p-3">
                          <p className="mb-1 text-xs font-medium text-slate-400 dark:text-slate-400 light:text-slate-600">Vector String</p>
                          <code className="text-xs text-slate-300 dark:text-slate-300 light:text-slate-700 font-mono break-all">
                            {cve.cvss_v3.vector_string}
                          </code>
                        </div>
                      </>
                    )}
                  </div>
                )}

                {cve.cvss_v2 && (
                  <div className="rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-950/60 dark:bg-slate-950/60 light:bg-slate-50 p-4">
                    <div className="mb-4 flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-brand-400 dark:text-brand-400 light:text-brand-600" />
                      <h4 className="font-semibold text-white dark:text-white light:text-slate-900">CVSS v2.0</h4>
                    </div>
                    <div className="mb-4 grid gap-3 md:grid-cols-2">
                      <div className="flex items-center justify-between rounded-lg bg-slate-900/40 dark:bg-slate-900/40 light:bg-slate-100 p-2">
                        <span className="text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">Base Score</span>
                        <span className="text-xl font-bold text-white dark:text-white light:text-slate-900">
                          {cve.cvss_v2.base_score?.toFixed(1) || "N/A"}
                        </span>
                      </div>
                      {cve.cvss_v2.severity && (
                        <div className="flex items-center justify-between rounded-lg bg-slate-900/40 dark:bg-slate-900/40 light:bg-slate-100 p-2">
                          <span className="text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">Severity</span>
                          <span className={`text-sm font-semibold px-2 py-1 rounded ${getSeverityColor(cve.cvss_v2.severity)}`}>
                            {cve.cvss_v2.severity}
                          </span>
                        </div>
                      )}
                    </div>
                    
                    {cve.cvss_v2.vector_string && (
                      <>
                        <div className="mb-3 flex items-center gap-2">
                          <Info className="h-4 w-4 text-slate-400 dark:text-slate-400 light:text-slate-600" />
                          <h5 className="text-sm font-semibold text-white dark:text-white light:text-slate-900">CVSS Metrics</h5>
                        </div>
                        <div className="mb-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                          {(() => {
                            const metrics = parseCVSSVector(cve.cvss_v2.vector_string);
                            console.log('CVSS v2 Vector String:', cve.cvss_v2.vector_string);
                            console.log('Parsed Metrics:', metrics);
                            
                            if (!metrics || Object.keys(metrics).length === 0) {
                              return (
                                <div className="col-span-full rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/30 dark:bg-slate-900/30 light:bg-slate-50 p-2">
                                  <p className="text-xs text-slate-500 dark:text-slate-500 light:text-slate-500">
                                    Could not parse vector string. Raw: {cve.cvss_v2.vector_string}
                                  </p>
                                </div>
                              );
                            }
                            
                            return Object.entries(metrics).map(([key, value]) => {
                              const metricName = CVSS_METRIC_NAMES[key] || key;
                              const metricValue = CVSS_LABELS[key]?.[value] || value;
                              return (
                                <div key={key} className="rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/30 dark:bg-slate-900/30 light:bg-slate-50 p-2">
                                  <p className="text-xs text-slate-500 dark:text-slate-500 light:text-slate-500">{metricName}</p>
                                  <p className="text-sm font-medium text-white dark:text-white light:text-slate-900">{metricValue}</p>
                                  <p className="text-xs font-mono text-slate-500 dark:text-slate-500 light:text-slate-500">{key}:{value}</p>
                                </div>
                              );
                            });
                          })()}
                        </div>
                        <div className="rounded-lg bg-slate-900/40 dark:bg-slate-900/40 light:bg-slate-100 p-3">
                          <p className="mb-1 text-xs font-medium text-slate-400 dark:text-slate-400 light:text-slate-600">Vector String</p>
                          <code className="text-xs text-slate-300 dark:text-slate-300 light:text-slate-700 font-mono break-all">
                            {cve.cvss_v2.vector_string}
                          </code>
                        </div>
                      </>
                    )}
                  </div>
                )}
              </div>

              {/* Dates */}
              <div className="grid gap-4 md:grid-cols-2">
                {cve.published_date && (
                  <div className="flex items-center gap-3 rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-950/60 dark:bg-slate-950/60 light:bg-slate-50 p-3">
                    <Calendar className="h-4 w-4 text-slate-400 dark:text-slate-400 light:text-slate-600" />
                    <div>
                      <p className="text-xs text-slate-500 dark:text-slate-500 light:text-slate-500">Published</p>
                      <p className="text-sm font-medium text-white dark:text-white light:text-slate-900">
                        {new Date(cve.published_date).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                )}
                {cve.last_modified_date && (
                  <div className="flex items-center gap-3 rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-950/60 dark:bg-slate-950/60 light:bg-slate-50 p-3">
                    <Calendar className="h-4 w-4 text-slate-400 dark:text-slate-400 light:text-slate-600" />
                    <div>
                      <p className="text-xs text-slate-500 dark:text-slate-500 light:text-slate-500">Last Modified</p>
                      <p className="text-sm font-medium text-white dark:text-white light:text-slate-900">
                        {new Date(cve.last_modified_date).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* CWE */}
              {cve.cwe_id && (
                <div>
                  <h3 className="mb-2 text-lg font-semibold text-white dark:text-white light:text-slate-900">CWE</h3>
                  <div className="rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-950/60 dark:bg-slate-950/60 light:bg-slate-50 p-3">
                    <code className="text-sm text-brand-400 dark:text-brand-400 light:text-brand-600">
                      {cve.cwe_id}
                    </code>
                  </div>
                </div>
              )}

              {/* Affected Products */}
              {cve.affected_products && cve.affected_products.length > 0 && (
                <div>
                  <div className="mb-2 flex items-center gap-2">
                    <Package className="h-5 w-5 text-brand-400 dark:text-brand-400 light:text-brand-600" />
                    <h3 className="text-lg font-semibold text-white dark:text-white light:text-slate-900">Affected Products</h3>
                  </div>
                  <div className="space-y-2">
                    {cve.affected_products.map((product, index) => (
                      <div
                        key={index}
                        className="rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-950/60 dark:bg-slate-950/60 light:bg-slate-50 p-3"
                      >
                        <p className="text-sm text-white dark:text-white light:text-slate-900">
                          {[product.vendor, product.product, product.version].filter(Boolean).join(" ")}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* References */}
              {cve.references && cve.references.length > 0 && (
                <div>
                  <div className="mb-2 flex items-center gap-2">
                    <Link2 className="h-5 w-5 text-brand-400 dark:text-brand-400 light:text-brand-600" />
                    <h3 className="text-lg font-semibold text-white dark:text-white light:text-slate-900">References</h3>
                  </div>
                  <div className="space-y-2">
                    {cve.references.map((ref, index) => (
                      <a
                        key={index}
                        href={ref.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-950/60 dark:bg-slate-950/60 light:bg-slate-50 p-3 text-sm text-brand-400 dark:text-brand-400 light:text-brand-600 transition hover:bg-slate-900 dark:hover:bg-slate-900 light:hover:bg-slate-100"
                      >
                        <ExternalLink className="h-4 w-4" />
                        <span className="flex-1 truncate">{ref.url}</span>
                        {ref.source && (
                          <span className="text-xs text-slate-500 dark:text-slate-500 light:text-slate-500">
                            {ref.source}
                          </span>
                        )}
                      </a>
                    ))}
                  </div>
                </div>
              )}

              {/* NVD Link */}
              {cve.nvd_url && (
                <div>
                  <a
                    href={cve.nvd_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 rounded-lg bg-brand-600 hover:bg-brand-700 text-white dark:text-white light:text-white px-4 py-2 text-sm font-medium transition"
                  >
                    <ExternalLink className="h-4 w-4" />
                    View on NIST NVD
                  </a>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default CVEDetailModal;

