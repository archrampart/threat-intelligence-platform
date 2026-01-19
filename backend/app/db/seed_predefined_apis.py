"""Seed predefined API sources to database."""

from app.db.base import SessionLocal
from app.models.api_source import APISource, APIType, AuthenticationType


def seed_predefined_apis() -> None:
    """Seed predefined threat intelligence API sources."""
    db = SessionLocal()

    try:
        predefined_apis = [
            {
                "name": "virustotal",
                "display_name": "VirusTotal",
                "description": "File, URL, IP address and domain analysis",
                "base_url": "https://www.virustotal.com/api/v3",
                "documentation_url": "https://developers.virustotal.com/reference",
                "supported_ioc_types": ["ip", "domain", "url", "hash"],
                "authentication_type": AuthenticationType.API_KEY,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/{ioc_type}/{ioc_value}",
                    "headers": {"x-apikey": "{api_key}"},
                },
                "response_config": {
                    "risk_score_path": "data.attributes.last_analysis_stats.malicious",
                    "status_path": "data.attributes.last_analysis_stats",
                    "data_path": "data",
                },
                "rate_limit_config": {
                    "limit": 500,
                    "period": "day",
                },
            },
            {
                "name": "abuseipdb",
                "display_name": "AbuseIPDB",
                "description": "IP address abuse reports and blacklist checking",
                "base_url": "https://api.abuseipdb.com/api/v2",
                "documentation_url": "https://www.abuseipdb.com/api",
                "supported_ioc_types": ["ip"],
                "authentication_type": AuthenticationType.API_KEY,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/check",
                    "query_params": {"ipAddress": "{ioc_value}", "key": "{api_key}"},
                },
                "response_config": {
                    "risk_score_path": "data.abuseConfidencePercentage",
                    "status_path": "data.abuseConfidencePercentage",
                    "data_path": "data",
                },
                "rate_limit_config": {
                    "limit": 1000,
                    "period": "day",
                },
            },
            {
                "name": "otx",
                "display_name": "OTX (AlienVault)",
                "description": "Community-based threat intelligence platform",
                "base_url": "https://otx.alienvault.com/api/v1",
                "documentation_url": "https://otx.alienvault.com/api",
                "supported_ioc_types": ["ip", "domain", "url", "hash"],
                "authentication_type": AuthenticationType.API_KEY,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/indicators/{ioc_type}/{ioc_value}/general",
                    "headers": {"X-OTX-API-KEY": "{api_key}"},
                },
                "response_config": {
                    "risk_score_path": "pulse_info.count",
                    "status_path": "pulse_info.count",
                    "data_path": "pulse_info",
                },
                "rate_limit_config": {
                    "limit": 10000,
                    "period": "day",
                },
            },
            {
                "name": "nist_nvd",
                "display_name": "NIST NVD",
                "description": "NIST National Vulnerability Database - CVE information",
                "base_url": "https://services.nvd.nist.gov/rest/json",
                "documentation_url": "https://nvd.nist.gov/developers/vulnerabilities",
                "supported_ioc_types": ["cve"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/cves/2.0?cveId={ioc_value}",
                },
                "response_config": {
                    "risk_score_path": "vulnerabilities[0].cve.metrics.cvssMetricV31[0].cvssData.baseScore",
                    "status_path": "vulnerabilities[0].cve.metrics",
                    "data_path": "vulnerabilities",
                },
                "rate_limit_config": {
                    "limit": 5,
                    "period": "30_seconds",
                },
            },
            {
                "name": "urlhaus",
                "display_name": "URLhaus (abuse.ch)",
                "description": "Malware URL database - Free and open source",
                "base_url": "https://urlhaus-api.abuse.ch/v1",
                "documentation_url": "https://urlhaus.abuse.ch/api/",
                "supported_ioc_types": ["url", "domain"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "POST",
                    "endpoint_template": "/url/",
                    "headers": {"Content-Type": "application/x-www-form-urlencoded"},
                    "body": "url={ioc_value}",
                },
                "response_config": {
                    "risk_score_path": "query_status",
                    "status_path": "query_status",
                    "data_path": "urlhaus_reference",
                },
                "rate_limit_config": {
                    "limit": 1000,
                    "period": "day",
                },
            },
            {
                "name": "shodan",
                "display_name": "Shodan",
                "description": "Internet-connected device and service scanning",
                "base_url": "https://api.shodan.io",
                "documentation_url": "https://developer.shodan.io/api",
                "supported_ioc_types": ["ip", "domain"],
                "authentication_type": AuthenticationType.API_KEY,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/shodan/host/{ioc_value}",
                    "query_params": {"key": "{api_key}"},
                },
                "response_config": {
                    "risk_score_path": "vulns",
                    "status_path": "hostnames",
                    "data_path": "data",
                },
                "rate_limit_config": {
                    "limit": 100,
                    "period": "month",
                },
            },
            {
                "name": "greynoise",
                "display_name": "GreyNoise",
                "description": "IP reputation and internet-wide scan data",
                "base_url": "https://api.greynoise.io/v3",
                "documentation_url": "https://docs.greynoise.io/reference/get_v3-community-ip",
                "supported_ioc_types": ["ip"],
                "authentication_type": AuthenticationType.API_KEY,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/community/{ioc_value}",
                    "headers": {"key": "{api_key}"},
                },
                "response_config": {
                    "risk_score_path": "classification",
                    "status_path": "noise",
                    "data_path": "riot",
                },
                "rate_limit_config": {
                    "limit": 1000,
                    "period": "day",
                },
            },
            {
                "name": "hybrid_analysis",
                "display_name": "Hybrid Analysis",
                "description": "Malware analysis sandbox - File hash and URL analysis",
                "base_url": "https://www.hybrid-analysis.com/api/v2",
                "documentation_url": "https://www.hybrid-analysis.com/docs/api/v2",
                "supported_ioc_types": ["hash", "url"],
                "authentication_type": AuthenticationType.API_KEY,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/search?query={ioc_value}",
                    "headers": {"api-key": "{api_key}"},
                },
                "response_config": {
                    "risk_score_path": "verdict",
                    "status_path": "verdict",
                    "data_path": "result",
                },
                "rate_limit_config": {
                    "limit": 100,
                    "period": "day",
                },
            },
            {
                "name": "phishtank",
                "display_name": "PhishTank",
                "description": "Phishing URL database - Free and open source",
                "base_url": "http://checkurl.phishtank.com/checkurl",
                "documentation_url": "https://www.phishtank.com/api_info.php",
                "supported_ioc_types": ["url"],
                "authentication_type": AuthenticationType.API_KEY,
                "request_config": {
                    "method": "POST",
                    "endpoint_template": "/",
                    "headers": {"Content-Type": "application/x-www-form-urlencoded"},
                    "body": "url={ioc_value}&format=json&app_key={api_key}",
                },
                "response_config": {
                    "risk_score_path": "results.in_database",
                    "status_path": "results.verified",
                    "data_path": "results",
                },
                "rate_limit_config": {
                    "limit": 10000,
                    "period": "day",
                },
            },
            {
                "name": "malwarebazaar",
                "display_name": "MalwareBazaar (abuse.ch)",
                "description": "Malware sample database - Free and open source",
                "base_url": "https://mb-api.abuse.ch/api/v1",
                "documentation_url": "https://bazaar.abuse.ch/api/",
                "supported_ioc_types": ["hash"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "POST",
                    "endpoint_template": "/",
                    "headers": {"Content-Type": "application/x-www-form-urlencoded"},
                    "body": "query=get_info&hash={ioc_value}",
                },
                "response_config": {
                    "risk_score_path": "query_status",
                    "status_path": "query_status",
                    "data_path": "data",
                },
                "rate_limit_config": {
                    "limit": 1000,
                    "period": "day",
                },
            },
            {
                "name": "threatfox",
                "display_name": "ThreatFox (abuse.ch)",
                "description": "IOC database - Free and open source",
                "base_url": "https://threatfox-api.abuse.ch/api/v1",
                "documentation_url": "https://threatfox.abuse.ch/api/",
                "supported_ioc_types": ["ip", "domain", "url", "hash"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "POST",
                    "endpoint_template": "/",
                    "headers": {"Content-Type": "application/x-www-form-urlencoded"},
                    "body": "query=search_ioc&search_term={ioc_value}",
                },
                "response_config": {
                    "risk_score_path": "query_status",
                    "status_path": "query_status",
                    "data_path": "data",
                },
                "rate_limit_config": {
                    "limit": 1000,
                    "period": "day",
                },
            },
            {
                "name": "kaspersky",
                "display_name": "Kaspersky Threat Intelligence",
                "description": "Kaspersky OpenTIP - IP, Domain, URL, and Hash threat intelligence",
                "base_url": "https://opentip.kaspersky.com/api/v1",
                "documentation_url": "https://support.kaspersky.com/opentip/api",
                "supported_ioc_types": ["ip", "domain", "url", "hash"],
                "authentication_type": AuthenticationType.API_KEY,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/lookup",
                    "query_params": {
                        "iocType": "{ioc_type}",
                        "iocValue": "{ioc_value}"
                    },
                    "headers": {"X-API-KEY": "{api_key}"},
                },
                "response_config": {
                    "risk_score_path": "Zone",
                    "status_path": "Zone",
                    "data_path": "Zone",
                },
                "rate_limit_config": {
                    "limit": 1000,
                    "period": "day",
                },
            },
            {
                "name": "honeydb",
                "display_name": "HoneyDB",
                "description": "HoneyDB - Honeypot threat intelligence and bad host detection",
                "base_url": "https://api.honeydb.io",
                "documentation_url": "https://docs.honeypotdb.com/rest_api/usage/",
                "supported_ioc_types": ["ip", "domain"],
                "authentication_type": AuthenticationType.API_KEY,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/api/threats/{ioc_type}/{ioc_value}",
                    "headers": {"X-HoneyDB-API-Key": "{api_key}"},
                },
                "response_config": {
                    "risk_score_path": "threats",
                    "status_path": "threats",
                    "data_path": "threats",
                },
                "rate_limit_config": {
                    "limit": 1500,
                    "period": "month",
                },
            },
            {
                "name": "pulsedive",
                "display_name": "Pulsedive",
                "description": "Pulsedive - Threat intelligence platform for IP, Domain, URL, and Hash analysis",
                "base_url": "https://pulsedive.com/api",
                "documentation_url": "https://pulsedive.com/api/",
                "supported_ioc_types": ["ip", "domain", "url", "hash"],
                "authentication_type": AuthenticationType.API_KEY,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/info.php",
                    "query_params": {
                        "value": "{ioc_value}",
                        "key": "{api_key}"
                    },
                },
                "response_config": {
                    "risk_score_path": "risk",
                    "status_path": "risk",
                    "data_path": "data",
                },
                "rate_limit_config": {
                    "limit": 1000,
                    "period": "day",
                },
            },
            {
                "name": "google_safe_browsing",
                "display_name": "Google Safe Browsing",
                "description": "Google Safe Browsing API - URL threat detection and malware/phishing protection",
                "base_url": "https://safebrowsing.googleapis.com/v4",
                "documentation_url": "https://developers.google.com/safe-browsing/v4",
                "supported_ioc_types": ["url"],
                "authentication_type": AuthenticationType.API_KEY,
                "request_config": {
                    "method": "POST",
                    "endpoint_template": "/threatMatches:find",
                    "query_params": {
                        "key": "{api_key}"
                    },
                    "headers": {"Content-Type": "application/json"},
                    "body": {
                        "client": {
                            "clientId": "pentest-report-tool",
                            "clientVersion": "1.0"
                        },
                        "threatInfo": {
                            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
                            "platformTypes": ["ANY_PLATFORM"],
                            "threatEntryTypes": ["URL"],
                            "threatEntries": [
                                {
                                    "url": "{ioc_value}"
                                }
                            ]
                        }
                    },
                },
                "response_config": {
                    "risk_score_path": "matches",
                    "status_path": "matches",
                    "data_path": "matches",
                },
                "rate_limit_config": {
                    "limit": 10000,
                    "period": "day",
                },
            },
            {
                "name": "censys",
                "display_name": "Censys",
                "description": "Internet-wide scan data - Host and certificate search engine (similar to Shodan)",
                "base_url": "https://search.censys.io/api/v2",
                "documentation_url": "https://search.censys.io/api",
                "supported_ioc_types": ["ip", "domain"],
                "authentication_type": AuthenticationType.API_KEY,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/hosts/{ioc_value}",
                    "headers": {
                        "Authorization": "Basic {api_key}",
                        "Accept": "application/json"
                    },
                },
                "response_config": {
                    "risk_score_path": "result.services",
                    "status_path": "result.services",
                    "data_path": "result",
                },
                "rate_limit_config": {
                    "limit": 250,
                    "period": "month",
                },
            },
            {
                "name": "ipqualityscore",
                "display_name": "IPQualityScore",
                "description": "IP, URL, and Email fraud detection and risk scoring",
                "base_url": "https://ipqualityscore.com/api/json",
                "documentation_url": "https://www.ipqualityscore.com/documentation/overview",
                "supported_ioc_types": ["ip", "url", "domain"],
                "authentication_type": AuthenticationType.API_KEY,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/ip/{api_key}/{ioc_value}",
                    "query_params": {
                        "strictness": "1",
                        "allow_public_access_points": "true"
                    },
                },
                "response_config": {
                    "risk_score_path": "fraud_score",
                    "status_path": "success",
                    "data_path": "data",
                },
                "rate_limit_config": {
                    "limit": 200,
                    "period": "day",
                },
            },
            {
                "name": "feodotracker",
                "display_name": "Feodo Tracker (abuse.ch)",
                "description": "Botnet C2 server tracking - Free and open source",
                "base_url": "https://feodotracker.abuse.ch/downloads",
                "documentation_url": "https://feodotracker.abuse.ch/",
                "supported_ioc_types": ["ip"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/ipblocklist_recommended.json",
                },
                "response_config": {
                    "risk_score_path": "ip_address",
                    "status_path": "ip_address",
                    "data_path": "data",
                },
                "rate_limit_config": {
                    "limit": 1000,
                    "period": "day",
                },
            },
            {
                "name": "sslbl",
                "display_name": "SSL Blacklist (abuse.ch)",
                "description": "Malicious SSL certificate fingerprints - Botnet C2 detection",
                "base_url": "https://sslbl.abuse.ch/blacklist",
                "documentation_url": "https://sslbl.abuse.ch/",
                "supported_ioc_types": ["hash"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/sslblacklist.json",
                },
                "response_config": {
                    "risk_score_path": "sha1",
                    "status_path": "sha1",
                    "data_path": "data",
                },
                "rate_limit_config": {
                    "limit": 1000,
                    "period": "day",
                },
            },
            {
                "name": "securitytrails",
                "display_name": "SecurityTrails",
                "description": "DNS history, subdomain discovery, and domain intelligence",
                "base_url": "https://api.securitytrails.com/v1",
                "documentation_url": "https://securitytrails.com/corp/api",
                "supported_ioc_types": ["domain", "ip"],
                "authentication_type": AuthenticationType.API_KEY,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/domain/{ioc_value}",
                    "headers": {
                        "APIKEY": "{api_key}",
                        "Accept": "application/json"
                    },
                },
                "response_config": {
                    "risk_score_path": "alexa_rank",
                    "status_path": "hostname",
                    "data_path": "current_dns",
                },
                "rate_limit_config": {
                    "limit": 50,
                    "period": "day",
                },
            },
            # ==================== FREE SOURCES (NO API KEY) ====================
            {
                "name": "blocklist_de",
                "display_name": "Blocklist.de",
                "description": "Real-time blacklist - SSH/Mail/FTP brute-force attacks",
                "base_url": "http://lists.blocklist.de/lists",
                "documentation_url": "https://www.blocklist.de/en/index.html",
                "supported_ioc_types": ["ip"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/all.txt",
                },
                "response_config": {
                    "risk_score_path": "found",  # Custom parser needed
                    "status_path": "found",
                    "data_path": "list",
                },
                "rate_limit_config": {
                    "limit": 100,
                    "period": "hour",
                },
            },
            {
                "name": "greensnow",
                "display_name": "GreenSnow",
                "description": "Spam/brute-force IP blacklist",
                "base_url": "https://blocklist.greensnow.co",
                "documentation_url": "https://greensnow.co/",
                "supported_ioc_types": ["ip"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/greensnow.txt",
                },
                "response_config": {
                    "risk_score_path": "found",
                    "status_path": "found",
                    "data_path": "list",
                },
                "rate_limit_config": {
                    "limit": 50,
                    "period": "hour",
                },
            },
            {
                "name": "openphish",
                "display_name": "OpenPhish",
                "description": "Phishing URL feed - Free community edition",
                "base_url": "https://openphish.com",
                "documentation_url": "https://openphish.com/",
                "supported_ioc_types": ["url", "domain"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/feed.txt",
                },
                "response_config": {
                    "risk_score_path": "found",
                    "status_path": "found",
                    "data_path": "list",
                },
                "rate_limit_config": {
                    "limit": 100,
                    "period": "day",
                },
            },
            {
                "name": "phishtank",
                "display_name": "PhishTank",
                "description": "Community phishing URL database",
                "base_url": "http://data.phishtank.com",
                "documentation_url": "https://www.phishtank.com/",
                "supported_ioc_types": ["url", "domain"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/data/online-valid.json",
                },
                "response_config": {
                    "risk_score_path": "verified",
                    "status_path": "verified",
                    "data_path": "url",
                },
                "rate_limit_config": {
                    "limit": 100,
                    "period": "hour",
                },
            },
            {
                "name": "circl_passivedns",
                "display_name": "CIRCL Passive DNS",
                "description": "CIRCL.LU Passive DNS database - DNS query history",
                "base_url": "https://www.circl.lu/pdns/query",
                "documentation_url": "https://www.circl.lu/services/passive-dns/",
                "supported_ioc_types": ["domain", "ip"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/{ioc_value}",
                },
                "response_config": {
                    "risk_score_path": "count",
                    "status_path": "time_last",
                    "data_path": "rrname",
                },
                "rate_limit_config": {
                    "limit": 200,
                    "period": "day",
                },
            },
            {
                "name": "bgpview",
                "display_name": "BGPView",
                "description": "AS/BGP/IP prefix information - Network intelligence",
                "base_url": "https://api.bgpview.io",
                "documentation_url": "https://bgpview.docs.apiary.io/",
                "supported_ioc_types": ["ip"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/ip/{ioc_value}",
                },
                "response_config": {
                    "risk_score_path": "data.prefixes",
                    "status_path": "status",
                    "data_path": "data",
                },
                "rate_limit_config": {
                    "limit": 120,
                    "period": "hour",
                },
            },
            {
                "name": "emailrep_io",
                "display_name": "EmailRep.io",
                "description": "Email reputation score - No API key required",
                "base_url": "https://emailrep.io",
                "documentation_url": "https://emailrep.io/docs/",
                "supported_ioc_types": ["email"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/{ioc_value}",
                },
                "response_config": {
                    "risk_score_path": "reputation.score",
                    "status_path": "reputation.status",
                    "data_path": "details",
                },
                "rate_limit_config": {
                    "limit": 300,
                    "period": "day",
                },
            },
            {
                "name": "crtsh",
                "display_name": "CRT.sh (Certificate Transparency)",
                "description": "SSL Certificate Transparency logs",
                "base_url": "https://crt.sh",
                "documentation_url": "https://crt.sh/",
                "supported_ioc_types": ["domain"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/?q={ioc_value}&output=json",
                },
                "response_config": {
                    "risk_score_path": "issuer_name",
                    "status_path": "id",
                    "data_path": "common_name",
                },
                "rate_limit_config": {
                    "limit": 500,
                    "period": "hour",
                },
            },
            {
                "name": "emerging_threats",
                "display_name": "Emerging Threats (Proofpoint)",
                "description": "Malware/botnet IOC feed - Community rules",
                "base_url": "https://rules.emergingthreats.net/blockrules",
                "documentation_url": "https://community.emergingthreats.net/",
                "supported_ioc_types": ["ip", "domain"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/compromised-ips.txt",
                },
                "response_config": {
                    "risk_score_path": "found",
                    "status_path": "found",
                    "data_path": "list",
                },
                "rate_limit_config": {
                    "limit": 100,
                    "period": "day",
                },
            },
            {
                "name": "dnsgrep",
                "display_name": "DNSGrep",
                "description": "Rapid7 Sonar DNS dataset search",
                "base_url": "https://dns.bufferover.run/dns",
                "documentation_url": "https://github.com/erbbysam/DNSGrep",
                "supported_ioc_types": ["domain"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "?q={ioc_value}",
                },
                "response_config": {
                    "risk_score_path": "FDNS_A",
                    "status_path": "Meta",
                    "data_path": "FDNS_A",
                },
                "rate_limit_config": {
                    "limit": 200,
                    "period": "day",
                },
            },
            {
                "name": "robtex",
                "display_name": "Robtex",
                "description": "DNS/IP network intelligence mapping",
                "base_url": "https://freeapi.robtex.com",
                "documentation_url": "https://www.robtex.com/api/",
                "supported_ioc_types": ["ip", "domain"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/ipquery/{ioc_value}",
                },
                "response_config": {
                    "risk_score_path": "status",
                    "status_path": "status",
                    "data_path": "pas",
                },
                "rate_limit_config": {
                    "limit": 100,
                    "period": "day",
                },
            },
            {
                "name": "phishstats",
                "display_name": "PhishStats",
                "description": "Phishing tracker - Active phishing URLs",
                "base_url": "https://phishstats.info/api",
                "documentation_url": "https://phishstats.info/",
                "supported_ioc_types": ["url", "domain"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/phishing",
                },
                "response_config": {
                    "risk_score_path": "score",
                    "status_path": "url",
                    "data_path": "url",
                },
                "rate_limit_config": {
                    "limit": 100,
                    "period": "hour",
                },
            },
            {
                "name": "sorbs",
                "display_name": "SORBS (Spam/Proxy Blacklist)",
                "description": "Multi-category IP blacklist - DNSBL",
                "base_url": "http://dnsbl.sorbs.net",
                "documentation_url": "http://www.sorbs.net/",
                "supported_ioc_types": ["ip"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/",  # DNS-based lookup
                },
                "response_config": {
                    "risk_score_path": "found",
                    "status_path": "found",
                    "data_path": "list",
                },
                "rate_limit_config": {
                    "limit": 1000,
                    "period": "day",
                },
            },
            {
                "name": "urlscan",
                "display_name": "URLScan.io",
                "description": "Website scanner for suspicious and malicious URLs",
                "base_url": "https://urlscan.io/api/v1",
                "documentation_url": "https://urlscan.io/docs/api/",
                "supported_ioc_types": ["url", "domain", "ip"],
                "authentication_type": AuthenticationType.API_KEY,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/search/",
                    "query_params": {
                        "q": "{ioc_value}",
                        "size": "1"
                    },
                    "headers": {"API-Key": "{api_key}"},
                },
                "response_config": {
                    "risk_score_path": "results[0].page.status",  # Not direct risk score, but indicates status
                    "status_path": "results[0].task.time",
                    "data_path": "results[0]",
                },
                "rate_limit_config": {
                    "limit": 5000,
                    "period": "day",
                },
            },
            {
                "name": "cleanbrowsing",
                "display_name": "CleanBrowsing",
                "description": "Malicious domain DNS filtering",
                "base_url": "https://doh.cleanbrowsing.org",
                "documentation_url": "https://cleanbrowsing.org/",
                "supported_ioc_types": ["domain"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/doh/security-filter/",
                },
                "response_config": {
                    "risk_score_path": "Status",
                    "status_path": "Status",
                    "data_path": "Answer",
                },
                "rate_limit_config": {
                    "limit": 500,
                    "period": "day",
                },
            },
            {
                "name": "cins_army",
                "display_name": "CINS Army (SANS)",
                "description": "Brute-force IP blacklist - SANS ISC supported",
                "base_url": "http://cinsscore.com/list",
                "documentation_url": "http://cinsscore.com/",
                "supported_ioc_types": ["ip"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/ci-badguys.txt",
                },
                "response_config": {
                    "risk_score_path": "found",
                    "status_path": "found",
                    "data_path": "list",
                },
                "rate_limit_config": {
                    "limit": 100,
                    "period": "day",
                },
            },
            # ==================== ADDITIONAL FREE SOURCES (30+) ====================
            {
                "name": "dronebl",
                "display_name": "DroneBL (IRC Abuse)",
                "description": "IRC/DDoS/proxy abuse IP blacklist",
                "base_url": "https://dronebl.org",
                "documentation_url": "https://dronebl.org/docs/howtouse",
                "supported_ioc_types": ["ip"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/lookup?ip={ioc_value}",
                },
                "response_config": {
                    "risk_score_path": "listed",
                    "status_path": "listed",
                    "data_path": "result",
                },
                "rate_limit_config": {
                    "limit": 1000,
                    "period": "day",
                },
            },
            {
                "name": "spamcop",
                "display_name": "Spamcop Blacklist",
                "description": "Spam source IP blacklist - DNSBL",
                "base_url": "http://www.spamcop.net",
                "documentation_url": "https://www.spamcop.net/bl.shtml",
                "supported_ioc_types": ["ip"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/",  # DNS lookup
                },
                "response_config": {
                    "risk_score_path": "found",
                    "status_path": "found",
                    "data_path": "list",
                },
                "rate_limit_config": {
                    "limit": 500,
                    "period": "day",
                },
            },
            {
                "name": "multiproxy",
                "display_name": "Multiproxy.org",
                "description": "Open proxy IP list",
                "base_url": "https://multiproxy.org",
                "documentation_url": "https://multiproxy.org/",
                "supported_ioc_types": ["ip"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/txt_all/proxy.txt",
                },
                "response_config": {
                    "risk_score_path": "found",
                    "status_path": "found",
                    "data_path": "list",
                },
                "rate_limit_config": {
                    "limit": 100,
                    "period": "day",
                },
            },
            {
                "name": "viewdns",
                "display_name": "ViewDNS.info",
                "description": "DNS tools - reverse IP, DNS records, etc.",
                "base_url": "https://viewdns.info",
                "documentation_url": "https://viewdns.info/",
                "supported_ioc_types": ["domain", "ip"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/reverseip/?host={ioc_value}&t=1",
                },
                "response_config": {
                    "risk_score_path": "domain_count",
                    "status_path": "response",
                    "data_path": "domains",
                },
                "rate_limit_config": {
                    "limit": 250,
                    "period": "day",
                },
            },
            {
                "name": "hackertarget",
                "display_name": "HackerTarget",
                "description": "Free security and DNS tools",
                "base_url": "https://api.hackertarget.com",
                "documentation_url": "https://hackertarget.com/",
                "supported_ioc_types": ["domain", "ip"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/dnslookup/?q={ioc_value}",
                },
                "response_config": {
                    "risk_score_path": "records",
                    "status_path": "status",
                    "data_path": "results",
                },
                "rate_limit_config": {
                    "limit": 100,
                    "period": "day",
                },
            },
            {
                "name": "cybercrime_tracker",
                "display_name": "CyberCrime Tracker",
                "description": "Active C2 server tracker",
                "base_url": "http://cybercrime-tracker.net",
                "documentation_url": "http://cybercrime-tracker.net/",
                "supported_ioc_types": ["ip", "domain"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/ccam_rss.php",
                },
                "response_config": {
                    "risk_score_path": "found",
                    "status_path": "found",
                    "data_path": "items",
                },
                "rate_limit_config": {
                    "limit": 50,
                    "period": "day",
                },
            },
            {
                "name": "psbdmp",
                "display_name": "Psbdmp (Pastebin Dumps)",
                "description": "Pastebin paste search and monitoring",
                "base_url": "https://psbdmp.ws",
                "documentation_url": "https://psbdmp.ws/api",
                "supported_ioc_types": ["email", "hash"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/api/search/{ioc_value}",
                },
                "response_config": {
                    "risk_score_path": "count",
                    "status_path": "data",
                    "data_path": "data",
                },
                "rate_limit_config": {
                    "limit": 100,
                    "period": "hour",
                },
            },
            {
                "name": "dnsdumpster",
                "display_name": "DNS Dumpster",
                "description": "DNS reconnaissance and subdomain discovery",
                "base_url": "https://dnsdumpster.com",
                "documentation_url": "https://dnsdumpster.com/",
                "supported_ioc_types": ["domain"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/",
                },
                "response_config": {
                    "risk_score_path": "subdomains",
                    "status_path": "results",
                    "data_path": "dns_records",
                },
                "rate_limit_config": {
                    "limit": 50,
                    "period": "day",
                },
            },
            {
                "name": "gravatar",
                "display_name": "Gravatar",
                "description": "Email to profile image lookup",
                "base_url": "https://www.gravatar.com",
                "documentation_url": "https://en.gravatar.com/site/implement/",
                "supported_ioc_types": ["email"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/avatar/{ioc_value}",
                },
                "response_config": {
                    "risk_score_path": "exists",
                    "status_path": "found",
                    "data_path": "profile",
                },
                "rate_limit_config": {
                    "limit": 500,
                    "period": "hour",
                },
            },
            {
                "name": "keybase",
                "display_name": "Keybase",
                "description": "Cryptocurrency identity verification",
                "base_url": "https://keybase.io",
                "documentation_url": "https://keybase.io/docs/api/1.0",
                "supported_ioc_types": ["email"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/_/api/1.0/user/lookup.json?email={ioc_value}",
                },
                "response_config": {
                    "risk_score_path": "status",
                    "status_path": "status.code",
                    "data_path": "them",
                },
                "rate_limit_config": {
                    "limit": 100,
                    "period": "day",
                },
            },
            {
                "name": "debounce",
                "display_name": "Debounce.io",
                "description": "Disposable/temporary email detection",
                "base_url": "https://disposable.debounce.io",
                "documentation_url": "https://debounce.io/",
                "supported_ioc_types": ["email"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/?email={ioc_value}",
                },
                "response_config": {
                    "risk_score_path": "disposable",
                    "status_path": "disposable",
                    "data_path": "result",
                },
                "rate_limit_config": {
                    "limit": 100,
                    "period": "day",
                },
            },
            {
                "name": "quad9_dns",
                "display_name": "Quad9 DNS",
                "description": "Quad9 threat blocking DNS lookup",
                "base_url": "https://dns.quad9.net",
                "documentation_url": "https://www.quad9.net/",
                "supported_ioc_types": ["domain"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/dns-query?name={ioc_value}",
                },
                "response_config": {
                    "risk_score_path": "Status",
                    "status_path": "Status",
                    "data_path": "Answer",
                },
                "rate_limit_config": {
                    "limit": 500,
                    "period": "day",
                },
            },
            {
                "name": "adguard_dns",
                "display_name": "AdGuard DNS",
                "description": "AdGuard malware/ad blocking DNS",
                "base_url": "https://dns.adguard.com",
                "documentation_url": "https://adguard.com/en/adguard-dns/overview.html",
                "supported_ioc_types": ["domain"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/dns-query?name={ioc_value}",
                },
                "response_config": {
                    "risk_score_path": "blocked",
                    "status_path": "Status",
                    "data_path": "Answer",
                },
                "rate_limit_config": {
                    "limit": 500,
                    "period": "day",
                },
            },
            {
                "name": "ripe_db",
                "display_name": "RIPE Database",
                "description": "European IP/AS registry",
                "base_url": "https://rest.db.ripe.net",
                "documentation_url": "https://www.ripe.net/",
                "supported_ioc_types": ["ip"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/ripe/inetnum/{ioc_value}.json",
                },
                "response_config": {
                    "risk_score_path": "objects",
                    "status_path": "status",
                    "data_path": "objects",
                },
                "rate_limit_config": {
                    "limit": 200,
                    "period": "day",
                },
            },
            {
                "name": "arin_registry",
                "display_name": "ARIN Registry",
                "description": "American IP registry",
                "base_url": "https://whois.arin.net",
                "documentation_url": "https://www.arin.net/",
                "supported_ioc_types": ["ip"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/rest/ip/{ioc_value}",
                },
                "response_config": {
                    "risk_score_path": "net",
                    "status_path": "net",
                    "data_path": "net",
                },
                "rate_limit_config": {
                    "limit": 100,
                    "period": "day",
                },
            },
            {
                "name": "circl_passivessl",
                "display_name": "CIRCL Passive SSL",
                "description": "CIRCL.LU SSL certificate database",
                "base_url": "https://www.circl.lu/pssl/query",
                "documentation_url": "https://www.circl.lu/services/passive-ssl/",
                "supported_ioc_types": ["domain", "ip"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/{ioc_value}",
                },
                "response_config": {
                    "risk_score_path": "certificates",
                    "status_path": "certificates",
                    "data_path": "subjects",
                },
                "rate_limit_config": {
                    "limit": 200,
                    "period": "day",
                },
            },
            {
                "name": "commoncrawl",
                "display_name": "Common Crawl",
                "description": "Web crawl data archive",
                "base_url": "https://index.commoncrawl.org",
                "documentation_url": "https://commoncrawl.org/",
                "supported_ioc_types": ["domain", "url"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/CC-MAIN-2024-10-index?url={ioc_value}",
                },
                "response_config": {
                    "risk_score_path": "found",
                    "status_path": "status",
                    "data_path": "captures",
                },
                "rate_limit_config": {
                    "limit": 100,
                    "period": "day",
                },
            },
            {
                "name": "archiveorg",
                "display_name": "Archive.org (Wayback Machine)",
                "description": "Historical web page snapshots",
                "base_url": "https://archive.org/wayback",
                "documentation_url": "https://archive.org/help/wayback_api.php",
                "supported_ioc_types": ["url", "domain"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/available?url={ioc_value}",
                },
                "response_config": {
                    "risk_score_path": "archived_snapshots",
                    "status_path": "archived_snapshots.closest.available",
                    "data_path": "archived_snapshots",
                },
                "rate_limit_config": {
                    "limit": 500,
                    "period": "day",
                },
            },
            {
                "name": "botvrij",
                "display_name": "BotVrij.eu",
                "description": "IRC botnet IP blacklist",
                "base_url": "https://www.botvrij.eu",
                "documentation_url": "https://www.botvrij.eu/",
                "supported_ioc_types": ["ip"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/data/irc/latest.txt",
                },
                "response_config": {
                    "risk_score_path": "found",
                    "status_path": "found",
                    "data_path": "list",
                },
                "rate_limit_config": {
                    "limit": 50,
                    "period": "day",
                },
            },
            {
                "name": "honeypot_project",
                "display_name": "Honeypot Project",
                "description": "Honeypot attacker IP collection",
                "base_url": "https://threatfox.abuse.ch",
                "documentation_url": "https://threatfox.abuse.ch/",
                "supported_ioc_types": ["ip"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/browse/",
                },
                "response_config": {
                    "risk_score_path": "found",
                    "status_path": "data",
                    "data_path": "data",
                },
                "rate_limit_config": {
                    "limit": 100,
                    "period": "day",
                },
            },
            {
                "name": "isc_dshield",
                "display_name": "ISC SANS DShield",
                "description": "SANS Internet Storm Center threat data",
                "base_url": "https://isc.sans.edu/api",
                "documentation_url": "https://isc.sans.edu/api/",
                "supported_ioc_types": ["ip"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/ip/{ioc_value}?json",
                },
                "response_config": {
                    "risk_score_path": "attacks",
                    "status_path": "count",
                    "data_path": "ip",
                },
                "rate_limit_config": {
                    "limit": 500,
                    "period": "day",
                },
            },
            {
                "name": "comodo_inspector",
                "display_name": "Comodo Site Inspector",
                "description": "Website malware scanner",
                "base_url": "https://siteinspector.comodo.com",
                "documentation_url": "https://siteinspector.comodo.com/",
                "supported_ioc_types": ["url", "domain"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/",
                },
                "response_config": {
                    "risk_score_path": "verdict",
                    "status_path": "scanned",
                    "data_path": "result",
                },
                "rate_limit_config": {
                    "limit": 50,
                    "period": "day",
                },
            },
            {
                "name": "malwarepatrol",
                "display_name": "Malware Patrol",
                "description": "Malware domain/IP database",
                "base_url": "https://www.malware.com.br",
                "documentation_url": "https://www.malware.com.br/",
                "supported_ioc_types": ["domain", "ip"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/cgi/submit?action=list_cdr",
                },
                "response_config": {
                    "risk_score_path": "found",
                    "status_path": "result",
                    "data_path": "list",
                },
                "rate_limit_config": {
                    "limit": 100,
                    "period": "day",
                },
            },
            {
                "name": "projectdiscovery_chaos",
                "display_name": "ProjectDiscovery Chaos",
                "description": "Public bug bounty subdomain data",
                "base_url": "https://chaos-data.projectdiscovery.io",
                "documentation_url": "https://chaos.projectdiscovery.io/",
                "supported_ioc_types": ["domain"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/",
                },
                "response_config": {
                    "risk_score_path": "subdomains",
                    "status_path": "count",
                    "data_path": "subdomains",
                },
                "rate_limit_config": {
                    "limit": 100,
                    "period": "day",
                },
            },
            {
                "name": "cleantalk_blacklist",
                "display_name": "CleanTalk",
                "description": "Spam IP database",
                "base_url": "https://cleantalk.org",
                "documentation_url": "https://cleantalk.org/blacklists",
                "supported_ioc_types": ["ip"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/blacklists/{ioc_value}",
                },
                "response_config": {
                    "risk_score_path": "appears",
                    "status_path": "in_bl",
                    "data_path": "result",
                },
                "rate_limit_config": {
                    "limit": 100,
                    "period": "day",
                },
            },
            {
                "name": "coinblocker_lists",
                "display_name": "Coinblocker Lists",
                "description": "Cryptocurrency miner IP/domain blacklist",
                "base_url": "https://gitlab.com/ZeroDot1/CoinBlockerLists",
                "documentation_url": "https://zerodot1.gitlab.io/CoinBlockerLists/",
                "supported_ioc_types": ["domain", "ip"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/raw/master/list.txt",
                },
                "response_config": {
                    "risk_score_path": "found",
                    "status_path": "found",
                    "data_path": "list",
                },
                "rate_limit_config": {
                    "limit": 50,
                    "period": "day",
                },
            },
            {
                "name": "fortinet_blacklist",
                "display_name": "Fortinet Threat Feed",
                "description": "Fortinet public threat IP list",
                "base_url": "https://threatfeeds.fortiguard.com",
                "documentation_url": "https://www.fortiguard.com/",
                "supported_ioc_types": ["ip"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/malicious.txt",
                },
                "response_config": {
                    "risk_score_path": "found",
                    "status_path": "found",
                    "data_path": "list",
                },
                "rate_limit_config": {
                    "limit": 100,
                    "period": "day",
                },
            },
            {
                "name": "opendns_investigate",
                "display_name": "OpenDNS (Cisco Umbrella)",
                "description": "DNS security and threat intelligence",
                "base_url": "https://investigate.api.umbrella.com",
                "documentation_url": "https://docs.umbrella.com/",
                "supported_ioc_types": ["domain"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/domains/categorization/{ioc_value}",
                },
                "response_config": {
                    "risk_score_path": "status",
                    "status_path": "status",
                    "data_path": "results",
                },
                "rate_limit_config": {
                    "limit": 500,
                    "period": "day",
                },
            },
            # ==================== NEW FREE SOURCES ====================
            {
                "name": "threatminer",
                "display_name": "ThreatMiner",
                "description": "Open threat intelligence platform - IP, Domain, Hash analysis",
                "base_url": "https://api.threatminer.org/v2",
                "documentation_url": "https://www.threatminer.org/api.php",
                "supported_ioc_types": ["ip", "domain", "hash"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/{ioc_type}.php",
                    "query_params": {
                        "q": "{ioc_value}",
                        "rt": "1"
                    },
                },
                "response_config": {
                    "risk_score_path": "status_code",
                    "status_path": "status_code",
                    "data_path": "results",
                },
                "rate_limit_config": {
                    "limit": 10,
                    "period": "minute",
                },
            },
            {
                "name": "criminalip",
                "display_name": "CriminalIP",
                "description": "Cybersecurity threat intelligence - IP reputation and vulnerability data",
                "base_url": "https://api.criminalip.io/v1",
                "documentation_url": "https://www.criminalip.io/developer/api/get-ip-data",
                "supported_ioc_types": ["ip", "domain"],
                "authentication_type": AuthenticationType.API_KEY,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/ip/data",
                    "query_params": {
                        "ip": "{ioc_value}"
                    },
                    "headers": {"x-api-key": "{api_key}"},
                },
                "response_config": {
                    "risk_score_path": "score",
                    "status_path": "status",
                    "data_path": "data",
                },
                "rate_limit_config": {
                    "limit": 100,
                    "period": "day",
                },
            },
            {
                "name": "ransomwarelive",
                "display_name": "Ransomware.live",
                "description": "Ransomware group tracking - Victim and leak site monitoring",
                "base_url": "https://api.ransomware.live/v1",
                "documentation_url": "https://www.ransomware.live/",
                "supported_ioc_types": ["domain"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/groups",
                },
                "response_config": {
                    "risk_score_path": "name",
                    "status_path": "name",
                    "data_path": "data",
                },
                "rate_limit_config": {
                    "limit": 100,
                    "period": "day",
                },
            },
            {
                "name": "spamhaus_zen",
                "display_name": "Spamhaus ZEN",
                "description": "Combined spam/malware IP blocklist (DNSBL lookup)",
                "base_url": "https://check.spamhaus.org",
                "documentation_url": "https://www.spamhaus.org/zen/",
                "supported_ioc_types": ["ip"],
                "authentication_type": AuthenticationType.NONE,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/",  # DNSBL requires custom logic
                },
                "response_config": {
                    "risk_score_path": "listed",
                    "status_path": "listed",
                    "data_path": "data",
                },
                "rate_limit_config": {
                    "limit": 100,
                    "period": "hour",
                },
            },
            {
                "name": "anyrun_public",
                "display_name": "ANY.RUN (Public)",
                "description": "Interactive malware sandbox - Public submission search",
                "base_url": "https://api.any.run/v1",
                "documentation_url": "https://any.run/api-documentation/",
                "supported_ioc_types": ["hash", "url", "domain"],
                "authentication_type": AuthenticationType.API_KEY,
                "request_config": {
                    "method": "GET",
                    "endpoint_template": "/analysis",
                    "query_params": {
                        "hash": "{ioc_value}"
                    },
                    "headers": {"Authorization": "API-Key {api_key}"},
                },
                "response_config": {
                    "risk_score_path": "data.scores.verdict.score",
                    "status_path": "data.status",
                    "data_path": "data",
                },
                "rate_limit_config": {
                    "limit": 100,
                    "period": "day",
                },
            },
        ]

        added_count = 0
        updated_count = 0
        
        for api_data in predefined_apis:
            api_id = f"predefined-{api_data['name']}"
            existing = db.query(APISource).filter(APISource.id == api_id).first()
            
            if existing:
                # Update existing API source
                existing.display_name = api_data["display_name"]
                existing.description = api_data["description"]
                existing.base_url = api_data["base_url"]
                existing.documentation_url = api_data.get("documentation_url")
                existing.supported_ioc_types = api_data["supported_ioc_types"]
                existing.authentication_type = api_data["authentication_type"]
                existing.request_config = api_data.get("request_config")
                existing.response_config = api_data.get("response_config")
                existing.rate_limit_config = api_data.get("rate_limit_config")
                existing.is_active = True
                updated_count += 1
            else:
                # Create new API source
                api_source = APISource(
                    id=api_id,
                    name=api_data["name"],
                    display_name=api_data["display_name"],
                    description=api_data["description"],
                    api_type=APIType.PREDEFINED,
                    base_url=api_data["base_url"],
                    documentation_url=api_data.get("documentation_url"),
                    supported_ioc_types=api_data["supported_ioc_types"],
                    authentication_type=api_data["authentication_type"],
                    request_config=api_data.get("request_config"),
                    response_config=api_data.get("response_config"),
                    rate_limit_config=api_data.get("rate_limit_config"),
                    is_active=True,
                    created_by=None,  # System created
                )
                db.add(api_source)
                added_count += 1

        db.commit()
        print(f"Successfully processed {len(predefined_apis)} predefined API sources.")
        print(f"  - Added: {added_count} new API sources")
        print(f"  - Updated: {updated_count} existing API sources")
    except Exception as e:
        db.rollback()
        print(f"Error seeding predefined APIs: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_predefined_apis()

