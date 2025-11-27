from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.schemas.cve import CVEDetailResponse, CVESearchRequest, CVESearchResponse
from app.services.cve_service import CVEService

router = APIRouter(prefix="/cves", tags=["cves"])


@router.post(
    "/search",
    response_model=CVESearchResponse,
    summary="CVE arama ve filtreleme",
)
def search_cves(
    request: CVESearchRequest,
    db: Session = Depends(get_db),
) -> CVESearchResponse:
    """CVE veritabanında arama yap ve filtrele - NIST NVD API."""
    cve_service = CVEService(db)
    return cve_service.search_cves(request)


@router.get(
    "/{cve_id}",
    response_model=CVEDetailResponse,
    summary="CVE detayı",
)
def get_cve(
    cve_id: str,
    db: Session = Depends(get_db),
) -> CVEDetailResponse:
    """CVE ID ile detay bilgisi getir - NIST NVD API."""
    cve_service = CVEService(db)
    cve = cve_service.get_cve(cve_id)
    if not cve:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CVE not found: {cve_id}",
        )
    return CVEDetailResponse(cve=cve)

