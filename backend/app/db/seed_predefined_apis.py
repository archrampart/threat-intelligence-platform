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

