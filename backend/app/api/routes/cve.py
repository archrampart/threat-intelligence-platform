from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_user
from app.db.base import get_db
from app.schemas.auth import UserResponse
from app.schemas.cve import CVEDetailResponse, CVESearchRequest, CVESearchResponse
from app.services.cve_service import CVEService
from app.services.exploit_intel import enrich_cves

router = APIRouter(prefix="/cves", tags=["cves"])


@router.post(
    "/search",
    response_model=CVESearchResponse,
    summary="CVE arama ve filtreleme",
)
def search_cves(
    request: CVESearchRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> CVESearchResponse:
    """CVE veritabanında arama yap ve filtrele - NIST NVD API."""
    cve_service = CVEService(db)
    response = cve_service.search_cves(request)
    enrich_cves(response.cves)
    return response


@router.get(
    "/{cve_id}",
    response_model=CVEDetailResponse,
    summary="CVE detayı",
)
def get_cve(
    cve_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> CVEDetailResponse:
    """CVE ID ile detay bilgisi getir - NIST NVD API."""
    cve_service = CVEService(db)
    cve = cve_service.get_cve(cve_id)
    if not cve:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CVE not found: {cve_id}",
        )
    enrich_cves([cve])
    return CVEDetailResponse(cve=cve)

