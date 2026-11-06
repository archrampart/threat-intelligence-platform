from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CVSSv2(BaseModel):
    """CVSS v2 skor bilgileri."""

    version: str = "2.0"
    vector_string: Optional[str] = None
    base_score: Optional[float] = None
    severity: Optional[str] = None  # LOW, MEDIUM, HIGH


class CVSSv3(BaseModel):
    """CVSS v3 skor bilgileri."""

    version: str = "3.0"  # veya 3.1
    vector_string: Optional[str] = None
    base_score: Optional[float] = None
    base_severity: Optional[str] = None  # LOW, MEDIUM, HIGH, CRITICAL


class CVEReference(BaseModel):
    """CVE referans linki."""

    url: str
    source: Optional[str] = None
    tags: Optional[List[str]] = None


class AffectedProduct(BaseModel):
    """Etkilenen ürün/yazılım bilgisi."""

    vendor: Optional[str] = None
    product: Optional[str] = None
    version: Optional[str] = None


class CVEBase(BaseModel):
    """CVE temel bilgileri."""

    cve_id: str = Field(..., description="CVE ID (örn: CVE-2024-1234)")
    description: Optional[str] = None
    published_date: Optional[datetime] = None
    last_modified_date: Optional[datetime] = None
    cvss_v2: Optional[CVSSv2] = None
    cvss_v3: Optional[CVSSv3] = None
    cwe_id: Optional[str] = None
    affected_products: List[AffectedProduct] = Field(default_factory=list)
    references: List[CVEReference] = Field(default_factory=list)


class ExploitReference(BaseModel):
    """A public exploit, PoC or detection template for a CVE."""

    source: str  # github | exploitdb | nuclei | metasploit
    title: str
    url: Optional[str] = None
    stars: Optional[int] = None
    verified: Optional[bool] = None
    kind: Optional[str] = None


class ExploitIntel(BaseModel):
    """Exploitation signals: FIRST EPSS and CISA KEV."""

    epss_score: Optional[float] = Field(None, description="Probability of exploitation in the next 30 days")
    epss_percentile: Optional[float] = None
    epss_date: Optional[str] = None
    in_kev: bool = False
    kev_date_added: Optional[str] = None
    kev_due_date: Optional[str] = None
    kev_known_ransomware: Optional[bool] = None
    kev_required_action: Optional[str] = None
    kev_vulnerability_name: Optional[str] = None
    # Public exploit / PoC availability
    has_public_exploit: bool = False
    github_poc_count: int = 0
    github_pocs: List[ExploitReference] = Field(default_factory=list)
    exploitdb: List[ExploitReference] = Field(default_factory=list)
    nuclei_templates: List[ExploitReference] = Field(default_factory=list)
    metasploit_modules: List[ExploitReference] = Field(default_factory=list)


class CVE(CVEBase):
    """CVE detay modeli."""

    nvd_url: Optional[str] = None
    cached_at: Optional[datetime] = None
    exploit_intel: Optional[ExploitIntel] = None


class CVESearchRequest(BaseModel):
    """CVE arama isteği."""

    cve_id: Optional[str] = Field(None, description="CVE ID ile arama (örn: CVE-2024-1234)")
    keyword: Optional[str] = Field(None, description="Açıklamada keyword arama")
    cvss_v3_min: Optional[float] = Field(None, ge=0.0, le=10.0, description="Minimum CVSS v3 skoru")
    cvss_v3_max: Optional[float] = Field(None, ge=0.0, le=10.0, description="Maximum CVSS v3 skoru")
    severity: Optional[str] = Field(None, description="Severity filtreleme (LOW, MEDIUM, HIGH, CRITICAL)")
    year: Optional[int] = Field(None, description="Yıl filtresi (örn: 2024)")
    published_after: Optional[datetime] = Field(None, description="Bu tarihten sonra yayınlananlar")
    published_before: Optional[datetime] = Field(None, description="Bu tarihten önce yayınlananlar")
    limit: int = Field(default=20, ge=1, le=100, description="Sonuç sayısı")
    offset: int = Field(default=0, ge=0, description="Sayfalama offset")


class CVESearchResponse(BaseModel):
    """CVE arama sonucu."""

    total: int
    limit: int
    offset: int
    total_pages: Optional[int] = None
    cves: List[CVE]


class CVEDetailResponse(BaseModel):
    """CVE detay yanıtı."""

    cve: CVE

