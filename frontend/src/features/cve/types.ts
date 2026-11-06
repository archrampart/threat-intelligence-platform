export interface CVSSv2 {
  version: string;
  vector_string?: string;
  base_score?: number;
  severity?: string;
}

export interface CVSSv3 {
  version: string;
  vector_string?: string;
  base_score?: number;
  base_severity?: string;
}

export interface CVEReference {
  url: string;
  source?: string;
  tags?: string[];
}

export interface AffectedProduct {
  vendor?: string;
  product?: string;
  version?: string;
}

export interface ExploitReference {
  source: "github" | "exploitdb" | "nuclei" | "metasploit" | string;
  title: string;
  url?: string | null;
  stars?: number | null;
  verified?: boolean | null;
  kind?: string | null;
}

export interface ExploitIntel {
  epss_score?: number | null;
  epss_percentile?: number | null;
  epss_date?: string | null;
  in_kev: boolean;
  kev_date_added?: string | null;
  kev_due_date?: string | null;
  kev_known_ransomware?: boolean | null;
  kev_required_action?: string | null;
  kev_vulnerability_name?: string | null;
  has_public_exploit?: boolean;
  github_poc_count?: number;
  github_pocs?: ExploitReference[];
  exploitdb?: ExploitReference[];
  nuclei_templates?: ExploitReference[];
  metasploit_modules?: ExploitReference[];
}

export interface CVE {
  cve_id: string;
  description?: string;
  published_date?: string;
  last_modified_date?: string;
  cvss_v2?: CVSSv2;
  cvss_v3?: CVSSv3;
  cwe_id?: string;
  affected_products: AffectedProduct[];
  references: CVEReference[];
  nvd_url?: string;
  cached_at?: string;
  exploit_intel?: ExploitIntel | null;
}

export interface CVESearchRequest {
  cve_id?: string;
  keyword?: string;
  cvss_v3_min?: number;
  cvss_v3_max?: number;
  severity?: string;
  year?: number;
  published_after?: string;
  published_before?: string;
  limit?: number;
  offset?: number;
}

export interface CVESearchResponse {
  total: number;
  limit: number;
  offset: number;
  total_pages?: number;
  cves: CVE[];
}

export interface CVEDetailResponse {
  cve: CVE;
}

