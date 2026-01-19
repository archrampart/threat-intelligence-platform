"""CVE servisi - NIST NVD API v2 entegrasyonu."""

import time
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

import requests
from loguru import logger
from sqlalchemy.orm import Session

from app.models.cve import CVECache
from app.schemas.cve import (
    AffectedProduct,
    CVE,
    CVEReference,
    CVESearchRequest,
    CVESearchResponse,
    CVSSv2,
    CVSSv3,
)
from app.services.redis_cache import redis_cache


class CVEService:
    """CVE sorgulama ve arama servisi - NIST NVD API v2."""

    NVD_API_BASE_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    RATE_LIMIT_DELAY = 0.6  # NIST NVD API rate limit: 50 requests per 30 seconds

    def __init__(self, db: Session) -> None:
        self.db = db
        self._last_request_time = 0.0

    def _rate_limit(self) -> None:
        """NIST NVD API rate limiting."""
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time
        if time_since_last_request < self.RATE_LIMIT_DELAY:
            time.sleep(self.RATE_LIMIT_DELAY - time_since_last_request)
        self._last_request_time = time.time()

    def _check_cache(self, cve_id: Optional[str] = None) -> Optional[List[CVECache]]:
        """Check database cache for CVE data."""
        from datetime import timedelta

        cache_expiry = datetime.now(timezone.utc) - timedelta(hours=24)  # 24 hour cache

        if cve_id:
            cached = (
                self.db.query(CVECache)
                .filter(CVECache.cve_id == cve_id.upper())
                .filter(CVECache.cached_at >= cache_expiry)
                .first()
            )
            return [cached] if cached else None
        return None

    def _save_to_cache(self, cve: CVE) -> None:
        """Save CVE data to cache."""
        from datetime import timedelta

        cached = self.db.query(CVECache).filter(CVECache.cve_id == cve.cve_id.upper()).first()

        cache_data = {
            "cve_id": cve.cve_id.upper(),
            "description": cve.description,
            "cvss_v2_score": cve.cvss_v2.base_score if cve.cvss_v2 else None,
            "cvss_v2_severity": cve.cvss_v2.severity if cve.cvss_v2 else None,
            "cvss_v3_score": cve.cvss_v3.base_score if cve.cvss_v3 else None,
            "cvss_v3_severity": cve.cvss_v3.base_severity if cve.cvss_v3 else None,
            "published_date": cve.published_date.date() if cve.published_date else None,
            "modified_date": cve.last_modified_date.date() if cve.last_modified_date else None,
            "affected_products": [p.dict() for p in cve.affected_products],
            "references": [r.dict() for r in cve.references],
            "cwe": cve.cwe_id,
        }

        if cached:
            # Update existing cache
            for key, value in cache_data.items():
                setattr(cached, key, value)
            cached.cached_at = datetime.now(timezone.utc)
            cached.expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        else:
            # Create new cache entry
            cached = CVECache(
                id=str(uuid4()),
                **cache_data,
                cached_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            )
            self.db.add(cached)

        try:
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to save CVE to cache: {e}")
            self.db.rollback()

    def _parse_nvd_response(self, nvd_data: dict) -> CVE:
        """Parse NIST NVD API response to CVE schema."""
        cve_item = nvd_data.get("cve", {})
        cve_id = cve_item.get("id", "")

        # Description
        descriptions = cve_item.get("descriptions", [])
        description = None
        for desc in descriptions:
            if desc.get("lang") == "en":
                description = desc.get("value")
                break

        # Dates
        published_date = None
        last_modified_date = None
        if cve_item.get("published"):
            try:
                published_date = datetime.fromisoformat(cve_item["published"].replace("Z", "+00:00"))
            except Exception:
                pass
        if cve_item.get("lastModified"):
            try:
                last_modified_date = datetime.fromisoformat(cve_item["lastModified"].replace("Z", "+00:00"))
            except Exception:
                pass

        # CVSS v3
        cvss_v3 = None
        metrics = cve_item.get("metrics", {})
        cvss_v31 = metrics.get("cvssMetricV31", [])
        cvss_v30 = metrics.get("cvssMetricV30", [])

        if cvss_v31:
            cvss_data = cvss_v31[0].get("cvssData", {})
            cvss_v3 = CVSSv3(
                version="3.1",
                vector_string=cvss_data.get("vectorString"),
                base_score=cvss_data.get("baseScore"),
                base_severity=cvss_data.get("baseSeverity"),
            )
        elif cvss_v30:
            cvss_data = cvss_v30[0].get("cvssData", {})
            cvss_v3 = CVSSv3(
                version="3.0",
                vector_string=cvss_data.get("vectorString"),
                base_score=cvss_data.get("baseScore"),
                base_severity=cvss_data.get("baseSeverity"),
            )

        # CVSS v2
        cvss_v2 = None
        cvss_v2_list = metrics.get("cvssMetricV2", [])
        if cvss_v2_list:
            cvss_data = cvss_v2_list[0].get("cvssData", {})
            base_severity = cvss_v2_list[0].get("baseSeverity")
            cvss_v2 = CVSSv2(
                version="2.0",
                vector_string=cvss_data.get("vectorString"),
                base_score=cvss_data.get("baseScore"),
                severity=base_severity,
            )

        # CWE
        cwe_id = None
        weaknesses = cve_item.get("weaknesses", [])
        if weaknesses:
            cwe_list = weaknesses[0].get("description", [])
            if cwe_list:
                cwe_id = cwe_list[0].get("value", "")

        # Affected products
        affected_products = []
        configurations = cve_item.get("configurations", [])
        for config in configurations:
            nodes = config.get("nodes", [])
            for node in nodes:
                cpe_match = node.get("cpeMatch", [])
                for cpe in cpe_match:
                    cpe_string = cpe.get("criteria", "")
                    # Parse CPE string: cpe:2.3:a:vendor:product:version
                    parts = cpe_string.split(":")
                    if len(parts) >= 5:
                        affected_products.append(
                            AffectedProduct(
                                vendor=parts[3] if len(parts) > 3 else None,
                                product=parts[4] if len(parts) > 4 else None,
                                version=parts[5] if len(parts) > 5 else None,
                            )
                        )

        # References
        references = []
        refs = cve_item.get("references", [])
        for ref in refs:
            references.append(
                CVEReference(
                    url=ref.get("url", ""),
                    source=ref.get("source", ""),
                    tags=ref.get("tags", []),
                )
            )

        return CVE(
            cve_id=cve_id,
            description=description,
            published_date=published_date,
            last_modified_date=last_modified_date,
            cvss_v2=cvss_v2,
            cvss_v3=cvss_v3,
            cwe_id=cwe_id,
            affected_products=affected_products,
            references=references,
            nvd_url=f"https://nvd.nist.gov/vuln/detail/{cve_id}",
            cached_at=datetime.now(timezone.utc),
        )

    def search_cves(self, request: CVESearchRequest) -> CVESearchResponse:
        """CVE arama ve filtreleme - NIST NVD API."""
        # Check Redis cache for search results
        cache_key_parts = [
            "cve:search",
            request.keyword or "",
            request.severity or "",
            str(request.year) if request.year else "",
            str(request.offset),
            str(request.limit),
        ]
        redis_key = ":".join(filter(None, cache_key_parts))
        cached_data = redis_cache.get(redis_key)
        if cached_data:
            logger.info(f"Redis cache hit for CVE search: {redis_key}")
            try:
                return CVESearchResponse(**cached_data)
            except Exception as e:
                logger.warning(f"Failed to parse cached search results: {e}")
        
        self._rate_limit()

        try:
            # Build API request parameters
            params = {
                "resultsPerPage": min(request.limit, 100),  # NVD API max 100
                "startIndex": request.offset,
            }

            # CVE ID filter
            if request.cve_id:
                params["cveId"] = request.cve_id.upper()

            # Keyword search (in description)
            if request.keyword:
                params["keywordSearch"] = request.keyword

            # Severity filter (CVSS v3 severity)
            if request.severity:
                params["cvssV3Severity"] = request.severity.upper()

            # Year filter - Use CVE ID pattern instead of date range for better compatibility
            # NIST NVD API v2.0 date filters may not work reliably, so we filter by CVE ID pattern
            if request.year:
                # Use keyword search with CVE year pattern (e.g., "CVE-2024")
                # This is more reliable than date filters
                year_pattern = f"CVE-{request.year}"
                if request.keyword:
                    # Combine with existing keyword
                    params["keywordSearch"] = f"{request.keyword} {year_pattern}"
                else:
                    params["keywordSearch"] = year_pattern
            else:
                # Date filters
                if request.published_after:
                    if isinstance(request.published_after, datetime):
                        params["pubStartDate"] = request.published_after.strftime("%Y-%m-%dT%H:%M:%S.000Z")
                    else:
                        params["pubStartDate"] = request.published_after
                if request.published_before:
                    if isinstance(request.published_before, datetime):
                        params["pubEndDate"] = request.published_before.strftime("%Y-%m-%dT%H:%M:%S.000Z")
                    else:
                        params["pubEndDate"] = request.published_before

            # Make API request
            logger.info(f"NIST NVD API request: {self.NVD_API_BASE_URL} with params: {params}")
            response = requests.get(self.NVD_API_BASE_URL, params=params, timeout=30)
            logger.info(f"NIST NVD API response status: {response.status_code}")
            if response.status_code != 200:
                logger.error(f"NIST NVD API error: {response.status_code} - {response.text[:500]}")
            response.raise_for_status()

            data = response.json()
            vulnerabilities = data.get("vulnerabilities", [])

            # Parse CVE data
            cves = []
            for vuln in vulnerabilities:
                try:
                    cve = self._parse_nvd_response(vuln)
                    cves.append(cve)
                    # Save to cache
                    self._save_to_cache(cve)
                except Exception as e:
                    logger.warning(f"Failed to parse CVE data: {e}")
                    continue

            # Sort by published_date DESC (newest first)
            cves.sort(key=lambda x: x.published_date or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

            total = data.get("totalResults", len(cves))
            total_pages = (total + request.limit - 1) // request.limit if total > 0 else 1

            response = CVESearchResponse(
                total=total,
                limit=request.limit,
                offset=request.offset,
                total_pages=total_pages,
                cves=cves,
            )
            
            # Save to Redis cache (shorter TTL for search results - 1 hour)
            try:
                redis_cache.set(redis_key, response.dict(), ttl=3600)  # 1 hour
            except Exception as e:
                logger.warning(f"Failed to save search results to Redis cache: {e}")
            
            return response

        except requests.exceptions.RequestException as e:
            logger.error(f"NIST NVD API request failed: {e}")
            # Fallback to cache if available
            return CVESearchResponse(total=0, limit=request.limit, offset=request.offset, cves=[])
        except Exception as e:
            logger.error(f"Error searching CVEs: {e}")
            return CVESearchResponse(total=0, limit=request.limit, offset=request.offset, cves=[])

    def get_cve(self, cve_id: str) -> Optional[CVE]:
        """CVE ID ile detay getir - NIST NVD API."""
        cve_id_upper = cve_id.upper()
        
        # Check Redis cache first
        redis_key = f"cve:{cve_id_upper}"
        cached_data = redis_cache.get(redis_key)
        if cached_data:
            logger.info(f"Redis cache hit for CVE {cve_id_upper}")
            try:
                # Convert cached dict to CVE schema
                return CVE(**cached_data)
            except Exception as e:
                logger.warning(f"Failed to parse cached CVE data: {e}")
        
        # Check database cache
        cached = self._check_cache(cve_id)
        if cached and cached[0]:
            cache_entry = cached[0]
            # Convert cache to CVE schema
            cve = CVE(
                cve_id=cache_entry.cve_id,
                description=cache_entry.description,
                published_date=(
                    datetime.combine(cache_entry.published_date, datetime.min.time()).replace(tzinfo=timezone.utc)
                    if cache_entry.published_date
                    else None
                ),
                last_modified_date=(
                    datetime.combine(cache_entry.modified_date, datetime.min.time()).replace(tzinfo=timezone.utc)
                    if cache_entry.modified_date
                    else None
                ),
                cvss_v2=CVSSv2(
                    version="2.0",
                    base_score=cache_entry.cvss_v2_score,
                    severity=cache_entry.cvss_v2_severity,
                )
                if cache_entry.cvss_v2_score
                else None,
                cvss_v3=CVSSv3(
                    version="3.1",
                    base_score=cache_entry.cvss_v3_score,
                    base_severity=cache_entry.cvss_v3_severity,
                )
                if cache_entry.cvss_v3_score
                else None,
                cwe_id=cache_entry.cwe,
                affected_products=[AffectedProduct(**p) for p in (cache_entry.affected_products or [])],
                references=[CVEReference(**r) for r in (cache_entry.references or [])],
                nvd_url=f"https://nvd.nist.gov/vuln/detail/{cache_entry.cve_id}",
                cached_at=cache_entry.cached_at,
            )
            # Save to Redis cache for faster future access
            try:
                redis_cache.set(redis_key, cve.dict(), ttl=86400)  # 24 hours
            except Exception as e:
                logger.warning(f"Failed to save CVE to Redis cache: {e}")
            return cve

        # Fetch from API
        self._rate_limit()

        try:
            params = {"cveId": cve_id_upper}
            response = requests.get(self.NVD_API_BASE_URL, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            vulnerabilities = data.get("vulnerabilities", [])

            if not vulnerabilities:
                return None

            cve = self._parse_nvd_response(vulnerabilities[0])
            # Save to database cache
            self._save_to_cache(cve)
            # Save to Redis cache
            try:
                redis_cache.set(redis_key, cve.dict(), ttl=86400)  # 24 hours
            except Exception as e:
                logger.warning(f"Failed to save CVE to Redis cache: {e}")

            return cve

        except requests.exceptions.RequestException as e:
            logger.error(f"NIST NVD API request failed for {cve_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching CVE {cve_id}: {e}")
            return None


