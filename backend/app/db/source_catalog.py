"""Curated changes to the predefined threat intelligence source catalog.

Applied on top of the legacy list in ``seed_predefined_apis.py``:

* ``DEPRECATED_SOURCES`` - dead services, HTML pages or endpoints that cannot answer a
  per-IOC lookup. They are deactivated in the database (not deleted, so existing API
  key rows keep their foreign key).
* ``SOURCE_OVERRIDES``   - fixes for existing sources (auth changes, broken request
  bodies, risk score normalisation).
* ``NEW_SOURCES``        - additional sources. Every endpoint below was checked live
  on 2026-11-05 (HTTP status and response shape).
"""

from app.models.api_source import AuthenticationType

DEPRECATED_SOURCES: dict[str, str] = {
    "threatminer": "Service offline",
    "dnsgrep": "BufferOver API offline",
    "psbdmp": "Service offline",
    "bgpview": "Service offline",
    "keybase": "No e-mail lookup API",
    "sorbs": "SORBS DNSBL shut down (2024)",
    "spamcop": "HTML site, no lookup API",
    "multiproxy": "Static proxy list, discontinued",
    "dnsdumpster": "HTML site, no lookup API",
    "comodo_inspector": "HTML site, no lookup API",
    "malwarepatrol": "No public per-IOC API",
    "projectdiscovery_chaos": "HTML site, no lookup API",
    "honeypot_project": "Pointed to an HTML page",
    "spamhaus_zen": "HTML site, DNSBL needs DNS queries",
    "cleantalk_blacklist": "HTML site, no lookup API",
    "gravatar": "Returns an image, no threat intelligence",
    "debounce": "Not a threat intelligence source",
    "quad9_dns": "DoH requires DNS wire format",
    "adguard_dns": "DoH requires DNS wire format",
    "cleanbrowsing": "DoH requires DNS wire format",
    "cybercrime_tracker": "RSS feed, no lookup API",
    "viewdns": "HTML site, API needs key",
    "openphish": "Free feed now redirects (registration required)",
    "botvrij": "Feed URL returns 404",
    "coinblocker_lists": "Feed moved behind GitLab sign-in",
    "fortinet_blacklist": "Feed URL unreachable",
    "ripe_db": "inetnum lookup needs exact range; replaced by ripestat",
    "ransomwarelive": "v1 endpoint listed all groups, no per-domain lookup",
    "anyrun_public": "No public API",
    "dronebl": "Lookup page returns HTML",
    "phishstats": "API returned HTTP 502 on every check (2026-11-05)",
    "commoncrawl": "Web archive index, not threat intelligence (pinned to a 2024 crawl)",
}

_FORM = {"Content-Type": "application/x-www-form-urlencoded"}

SOURCE_OVERRIDES: dict[str, dict] = {
    # --- risk normalisation for the major key-based sources
    "virustotal": {
        "request_config": {
            "method": "GET",
            "endpoint_template": "/{ioc_type}/{ioc_value}",
            "headers": {"x-apikey": "{api_key}"},
            "ioc_type_map": {"ip": "ip_addresses", "domain": "domains", "url": "urls", "hash": "files"},
            "ioc_value_transform": {"url": "base64url"},
        },
        "response_config": {
            "risk_score_path": "data.attributes.last_analysis_stats.malicious",
            "risk_score_max": 10,  # >= 10 engines -> 1.0
            "status_path": "data.attributes.last_analysis_stats",
            "data_path": "data",
            "not_found_ok": True,
        },
    },
    "abuseipdb": {
        "request_config": {
            "method": "GET",
            "endpoint_template": "/check",
            "headers": {"Key": "{api_key}"},  # key no longer sent in the query string
            "query_params": {"ipAddress": "{ioc_value}", "maxAgeInDays": "90"},
        },
        "response_config": {
            "risk_score_path": "data.abuseConfidencePercentage",
            "risk_score_max": 100,
            "status_path": "data.abuseConfidencePercentage",
            "data_path": "data",
        },
    },
    "otx": {
        "request_config": {
            "method": "GET",
            "endpoint_template": "/indicators/{ioc_type}/{ioc_value}/general",
            "headers": {"X-OTX-API-KEY": "{api_key}"},
            "ioc_type_map": {"ip": "IPv4", "domain": "domain", "url": "url", "hash": "file"},
        },
        "response_config": {
            # Pulse count is a weak signal: popular/benign domains appear in many pulses
            # (often marked "whitelisted"). OTX alone can reach "medium" at most.
            "risk_score_path": "pulse_info.count",
            "risk_score_max": 20,
            "risk_score_weight": 0.6,
            "status_path": "pulse_info.count",
            "data_path": "pulse_info",
            "not_found_ok": True,
        },
    },
    "shodan": {
        "response_config": {
            "risk_score_path": "vulns",
            "risk_score_max": 10,
            "risk_score_weight": 0.7,
            "status_path": "hostnames",
            "data_path": "$",
            "not_found_ok": True,
        },
    },
    "greynoise": {
        "response_config": {
            "risk_score_path": "classification",
            "risk_score_map": {"malicious": 0.9, "suspicious": 0.6, "unknown": 0.3, "benign": 0.0},
            "status_path": "noise",
            "data_path": "$",
            "not_found_ok": True,
        },
    },
    "hybrid_analysis": {
        "response_config": {
            "risk_score_path": "verdict",
            "risk_score_map": {
                "malicious": 0.9,
                "suspicious": 0.6,
                "no specific threat": 0.1,
                "whitelisted": 0.0,
                "no verdict": None,
            },
            "status_path": "verdict",
            "data_path": "$",
        },
    },
    "pulsedive": {
        "response_config": {
            "risk_score_path": "risk",
            "risk_score_map": {"critical": 1.0, "high": 0.8, "medium": 0.5, "low": 0.2, "none": 0.0, "unknown": None},
            "status_path": "risk",
            "data_path": "$",
            "not_found_ok": True,
        },
    },
    "kaspersky": {
        "response_config": {
            "risk_score_path": "Zone",
            "risk_score_map": {"red": 0.9, "orange": 0.7, "yellow": 0.6, "green": 0.0, "grey": None},
            "status_path": "Zone",
            "data_path": "$",
        },
    },
    "honeydb": {"response_config": {"risk_score_path": "threats", "risk_score_max": 10, "data_path": "$"}},
    "google_safe_browsing": {
        "response_config": {"risk_score_path": "matches", "risk_score_max": 1, "data_path": "$"},
    },
    "censys": {"response_config": {"data_path": "result"}},
    "ipqualityscore": {
        "response_config": {"risk_score_path": "fraud_score", "risk_score_max": 100, "data_path": "$"},
    },
    "securitytrails": {"response_config": {"status_path": "hostname", "data_path": "current_dns"}},
    "urlscan": {"response_config": {"status_path": "total", "data_path": "results[0]"}},
    "criminalip": {
        "response_config": {
            "risk_score_path": "score.inbound",
            "risk_score_map": {"critical": 1.0, "dangerous": 0.8, "moderate": 0.5, "low": 0.2, "safe": 0.0},
            "status_path": "status",
            "data_path": "$",
        },
    },
    "isc_dshield": {
        "response_config": {"risk_score_path": "ip.attacks", "risk_score_max": 50, "status_path": "ip.count",
                            "data_path": "ip"},
    },
    "arin_registry": {
        "base_url": "https://whois.arin.net/rest/ip",
        "request_config": {"method": "GET", "endpoint_template": "/{ioc_value}.json"},
        "response_config": {"data_path": "net"},
    },
    # --- legacy free sources whose "risk" path was not a risk signal
    "nist_nvd": {
        "response_config": {
            "risk_score_path": "vulnerabilities[0].cve.metrics.cvssMetricV31[0].cvssData.baseScore",
            "risk_score_max": 10,
            "data_path": "vulnerabilities[0].cve",
        },
    },
    "crtsh": {"response_config": {"data_path": "$"}},
    "robtex": {"response_config": {"data_path": "$"}},
    "hackertarget": {"response_config": {"data_path": "$"}},
    "archiveorg": {"response_config": {"data_path": "archived_snapshots"}},
    # --- abuse.ch APIs require a free Auth-Key since 2025 (unauthenticated calls -> 401)
    "urlhaus": {
        "authentication_type": AuthenticationType.API_KEY,
        "description": "URLhaus malware URL database (abuse.ch). Free Auth-Key: https://auth.abuse.ch/",
        "supported_ioc_types": ["url", "domain", "ip"],
        "request_config": {
            "method": "POST",
            "endpoint_template": "/host/",
            "headers": {**_FORM, "Auth-Key": "{api_key}"},
            "body": "host={ioc_value}",
        },
        "response_config": {
            "risk_score_path": "query_status",
            "risk_score_map": {"ok": 0.9, "no_results": None, "is_host": None},
            "status_path": "query_status",
            "data_path": "$",
        },
    },
    "malwarebazaar": {
        "authentication_type": AuthenticationType.API_KEY,
        "description": "MalwareBazaar malware sample database (abuse.ch). Free Auth-Key: https://auth.abuse.ch/",
        "request_config": {
            "method": "POST",
            "endpoint_template": "/",
            "headers": {**_FORM, "Auth-Key": "{api_key}"},
            "body": "query=get_info&hash={ioc_value}",
        },
        "response_config": {
            "risk_score_path": "query_status",
            "risk_score_map": {"ok": 1.0, "hash_not_found": None, "no_results": None},
            "status_path": "query_status",
            "data_path": "data",
        },
    },
    "threatfox": {
        "authentication_type": AuthenticationType.API_KEY,
        "description": "ThreatFox IOC database (abuse.ch). Free Auth-Key: https://auth.abuse.ch/",
        "request_config": {
            "method": "POST",
            "endpoint_template": "/",
            "headers": {"Content-Type": "application/json", "Auth-Key": "{api_key}"},
            "body": {"query": "search_ioc", "search_term": "{ioc_value}", "exact_match": True},
        },
        "response_config": {
            "risk_score_path": "query_status",
            "risk_score_map": {"ok": 0.9, "no_result": None, "no_results": None},
            "status_path": "query_status",
            "data_path": "data",
        },
    },
    # --- services that now require credentials
    "emailrep_io": {
        "authentication_type": AuthenticationType.API_KEY,
        "request_config": {"method": "GET", "endpoint_template": "/{ioc_value}", "headers": {"Key": "{api_key}"}},
        "response_config": {
            "risk_score_path": "suspicious",
            "risk_score_map": {"true": 0.7, "false": 0.0},
            "status_path": "reputation",
            "data_path": "details",
        },
    },
    "circl_passivedns": {"authentication_type": AuthenticationType.BASIC_AUTH,
                         "response_config": {"status_path": "time_last", "data_path": "$"}},
    "circl_passivessl": {"authentication_type": AuthenticationType.BASIC_AUTH,
                         "response_config": {"data_path": "$"}},
    "opendns_investigate": {"authentication_type": AuthenticationType.BEARER_TOKEN,
                            "response_config": {"data_path": "$"}},
    # --- blocklist feeds: real membership lookups instead of downloading the whole list
    "feodotracker": {
        "description": "Feodo Tracker botnet C2 IP blocklist (abuse.ch) - membership check",
        "base_url": "https://feodotracker.abuse.ch",
        "request_config": {"mode": "feed", "endpoint_template": "/downloads/ipblocklist_recommended.txt"},
        "response_config": {"listed_risk": 0.95, "feed_label": "Feodo Tracker C2 blocklist"},
    },
    "sslbl": {
        "description": "abuse.ch SSL Blacklist - malicious TLS certificate SHA1 fingerprints",
        "base_url": "https://sslbl.abuse.ch",
        "request_config": {"mode": "feed", "endpoint_template": "/blacklist/sslblacklist.csv",
                           "feed_format": "csv", "csv_column": 1},
        "response_config": {"listed_risk": 0.9, "feed_label": "SSLBL certificate blacklist"},
    },
    "blocklist_de": {
        "base_url": "https://lists.blocklist.de",
        "request_config": {"mode": "feed", "endpoint_template": "/lists/all.txt"},
        "response_config": {"listed_risk": 0.7, "feed_label": "blocklist.de attackers (48h)"},
    },
    "greensnow": {
        "request_config": {"mode": "feed", "endpoint_template": "/greensnow.txt"},
        "response_config": {"listed_risk": 0.7, "feed_label": "GreenSnow attackers"},
    },
    "emerging_threats": {
        "base_url": "https://rules.emergingthreats.net",
        "supported_ioc_types": ["ip"],
        "request_config": {"mode": "feed", "endpoint_template": "/blockrules/compromised-ips.txt"},
        "response_config": {"listed_risk": 0.8, "feed_label": "Proofpoint ET compromised IPs"},
    },
    "cins_army": {
        "base_url": "https://cinsscore.com",
        "request_config": {"mode": "feed", "endpoint_template": "/list/ci-badguys.txt"},
        "response_config": {"listed_risk": 0.7, "feed_label": "CINS Army bad actors"},
    },
}

NEW_SOURCES: list[dict] = [
    {
        "name": "shodan_internetdb",
        "display_name": "Shodan InternetDB",
        "description": "Free Shodan summary: open ports, CPEs, tags and known CVEs for an IP (no key)",
        "base_url": "https://internetdb.shodan.io",
        "documentation_url": "https://internetdb.shodan.io/docs",
        "supported_ioc_types": ["ip"],
        "authentication_type": AuthenticationType.NONE,
        "request_config": {"method": "GET", "endpoint_template": "/{ioc_value}"},
        "response_config": {"risk_score_path": "vulns", "risk_score_max": 10, "risk_score_weight": 0.6,
                            "status_path": "ports", "data_path": "$", "not_found_ok": True},
        "rate_limit_config": {"limit": 1, "period": "second"},
    },
    {
        "name": "greynoise_community",
        "display_name": "GreyNoise Community (free)",
        "description": "Internet background noise / scanner classification without API key (rate limited)",
        "base_url": "https://api.greynoise.io/v3",
        "documentation_url": "https://docs.greynoise.io/reference/get_v3-community-ip",
        "supported_ioc_types": ["ip"],
        "authentication_type": AuthenticationType.NONE,
        "request_config": {"method": "GET", "endpoint_template": "/community/{ioc_value}"},
        "response_config": {
            "risk_score_path": "classification",
            "risk_score_map": {"malicious": 0.9, "suspicious": 0.6, "unknown": 0.3, "benign": 0.0},
            "status_path": "noise",
            "data_path": "$",
            "not_found_ok": True,
        },
        "rate_limit_config": {"limit": 50, "period": "week"},
    },
    {
        "name": "ipapi_is",
        "display_name": "ipapi.is",
        "description": "IP enrichment: ASN, company, abuse contact, geolocation (free tier)",
        "base_url": "https://api.ipapi.is",
        "documentation_url": "https://ipapi.is/developers.html",
        "supported_ioc_types": ["ip"],
        "authentication_type": AuthenticationType.NONE,
        "request_config": {"method": "GET", "endpoint_template": "/", "query_params": {"q": "{ioc_value}"}},
        # Unauthenticated responses omit the is_* abuse flags -> enrichment only (ASN, company, geo)
        "response_config": {"status_path": "company", "data_path": "$"},
        "rate_limit_config": {"limit": 1000, "period": "day"},
    },
    {
        "name": "tor_exit_nodes",
        "display_name": "Tor Exit Nodes",
        "description": "Official Tor Project bulk exit node list - membership check",
        "base_url": "https://check.torproject.org",
        "documentation_url": "https://check.torproject.org/torbulkexitlist",
        "supported_ioc_types": ["ip"],
        "authentication_type": AuthenticationType.NONE,
        "request_config": {"mode": "feed", "endpoint_template": "/torbulkexitlist"},
        "response_config": {"listed_risk": 0.5, "feed_label": "Tor exit node list"},
    },
    {
        "name": "spamhaus_drop",
        "display_name": "Spamhaus DROP",
        "description": "Spamhaus Don't Route Or Peer list (hijacked / criminal netblocks) - CIDR match",
        "base_url": "https://www.spamhaus.org",
        "documentation_url": "https://www.spamhaus.org/blocklists/do-not-route-or-peer/",
        "supported_ioc_types": ["ip"],
        "authentication_type": AuthenticationType.NONE,
        "request_config": {"mode": "feed", "endpoint_template": "/drop/drop_v4.json", "feed_format": "jsonl",
                           "json_field": "cidr"},
        "response_config": {"listed_risk": 0.95, "feed_label": "Spamhaus DROP"},
    },
    {
        "name": "c2intel_feeds",
        "display_name": "C2IntelFeeds",
        "description": "Community C2 server IPs (Cobalt Strike, Sliver, Havoc...) seen in the last 30 days",
        "base_url": "https://raw.githubusercontent.com",
        "documentation_url": "https://github.com/drb-ra/C2IntelFeeds",
        "supported_ioc_types": ["ip"],
        "authentication_type": AuthenticationType.NONE,
        "request_config": {"mode": "feed", "endpoint_template": "/drb-ra/C2IntelFeeds/master/feeds/IPC2s-30day.csv",
                           "feed_format": "csv", "csv_column": 0},
        "response_config": {"listed_risk": 0.9, "feed_label": "C2IntelFeeds (30 days)"},
    },
    {
        "name": "circl_hashlookup",
        "display_name": "CIRCL hashlookup",
        "description": "Known-good file hash database (NSRL and others). A hit indicates a benign file.",
        "base_url": "https://hashlookup.circl.lu",
        "documentation_url": "https://www.circl.lu/services/hashlookup/",
        "supported_ioc_types": ["hash"],
        "authentication_type": AuthenticationType.NONE,
        "request_config": {"method": "GET", "endpoint_template": "/lookup/{hash_type}/{ioc_value}"},
        "response_config": {"status_path": "FileName", "data_path": "$", "not_found_ok": True},
    },
    {
        "name": "yaraify",
        "display_name": "YARAify (abuse.ch)",
        "description": "YARA scan results for file hashes. Free Auth-Key: https://auth.abuse.ch/",
        "base_url": "https://yaraify-api.abuse.ch/api/v1",
        "documentation_url": "https://yaraify.abuse.ch/api/",
        "supported_ioc_types": ["hash"],
        "authentication_type": AuthenticationType.API_KEY,
        "request_config": {
            "method": "POST",
            "endpoint_template": "/",
            "headers": {"Content-Type": "application/json", "Auth-Key": "{api_key}"},
            "body": {"query": "lookup_hash", "search_term": "{ioc_value}"},
        },
        "response_config": {"risk_score_path": "query_status",
                            "risk_score_map": {"ok": 0.8, "no_results": None, "hash_not_found": None},
                            "status_path": "query_status", "data_path": "data"},
    },
    {
        "name": "ripestat",
        "display_name": "RIPEstat",
        "description": "Prefix, ASN and holder information for an IP address",
        "base_url": "https://stat.ripe.net/data",
        "documentation_url": "https://stat.ripe.net/docs/data-api/",
        "supported_ioc_types": ["ip"],
        "authentication_type": AuthenticationType.NONE,
        "request_config": {"method": "GET", "endpoint_template": "/prefix-overview/data.json",
                           "query_params": {"resource": "{ioc_value}"}},
        "response_config": {"data_path": "data"},
    },
    {
        "name": "first_epss",
        "display_name": "FIRST EPSS",
        "description": "Exploit Prediction Scoring System - probability of exploitation in the next 30 days",
        "base_url": "https://api.first.org/data/v1",
        "documentation_url": "https://www.first.org/epss/api",
        "supported_ioc_types": ["cve"],
        "authentication_type": AuthenticationType.NONE,
        "request_config": {"method": "GET", "endpoint_template": "/epss", "query_params": {"cve": "{ioc_value}"}},
        "response_config": {"risk_score_path": "data[0].epss", "risk_score_max": 1, "data_path": "data[0]"},
    },
]


# Access model shown in the UI. "none": no key; "free_key": free account gives a key;
# "freemium": free tier with tight limits, paid plans for real use; "on_request": access
# is granted manually by the provider; "paid": commercial only.
# The URL is where a user obtains their own key.
SOURCE_ACCESS: dict[str, tuple[str, str | None]] = {
    "otx": ("free_key", "https://otx.alienvault.com/settings"),
    "urlhaus": ("free_key", "https://auth.abuse.ch/"),
    "threatfox": ("free_key", "https://auth.abuse.ch/"),
    "malwarebazaar": ("free_key", "https://auth.abuse.ch/"),
    "yaraify": ("free_key", "https://auth.abuse.ch/"),
    "urlscan": ("free_key", "https://urlscan.io/user/signup"),
    "pulsedive": ("free_key", "https://pulsedive.com/register"),
    "greynoise": ("free_key", "https://viz.greynoise.io/signup"),
    "hybrid_analysis": ("free_key", "https://www.hybrid-analysis.com/signup"),
    "kaspersky": ("free_key", "https://opentip.kaspersky.com/"),
    "honeydb": ("free_key", "https://honeydb.io/"),
    "google_safe_browsing": ("free_key", "https://developers.google.com/safe-browsing/v4/get-started"),
    "virustotal": ("freemium", "https://www.virustotal.com/gui/join-us"),
    "abuseipdb": ("freemium", "https://www.abuseipdb.com/register"),
    "shodan": ("freemium", "https://account.shodan.io/register"),
    "censys": ("freemium", "https://accounts.censys.io/register"),
    "criminalip": ("freemium", "https://www.criminalip.io/register"),
    "ipqualityscore": ("freemium", "https://www.ipqualityscore.com/create-account"),
    "securitytrails": ("freemium", "https://securitytrails.com/app/signup"),
    "emailrep_io": ("on_request", "https://emailrep.io/key"),
    "circl_passivedns": ("on_request", "https://www.circl.lu/services/passive-dns/"),
    "circl_passivessl": ("on_request", "https://www.circl.lu/services/passive-ssl/"),
    "phishtank": ("on_request", "https://www.phishtank.com/"),
    "opendns_investigate": ("paid", "https://umbrella.cisco.com/"),
}


def source_access(name: str, authentication_type: str) -> tuple[str, str | None]:
    """Return (access tier, key signup URL) for a source."""
    if name in SOURCE_ACCESS:
        return SOURCE_ACCESS[name]
    if str(authentication_type).lower().endswith("none"):
        return "none", None
    return "unknown", None


def apply_catalog(predefined: list[dict]) -> tuple[list[dict], set[str]]:
    """Return (active source definitions, deprecated names)."""
    seen: set[str] = set()
    result: list[dict] = []
    for api in predefined:
        name = api["name"]
        if name in seen or name in DEPRECATED_SOURCES:
            continue  # drop duplicates (legacy list had two "phishtank" entries) and dead sources
        seen.add(name)
        override = SOURCE_OVERRIDES.get(name)
        if override:
            api = {**api, **override}
        result.append(api)
    for api in NEW_SOURCES:
        if api["name"] not in seen:
            seen.add(api["name"])
            result.append(api)
    return result, set(DEPRECATED_SOURCES)
