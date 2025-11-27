"""Report endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_user
from app.core.dependencies import require_role
from app.db.base import get_db
from app.models.user import UserRole
from app.schemas.auth import UserResponse
from app.schemas.report import (
    ReportCreate,
    ReportExportRequest,
    ReportListResponse,
    ReportResponse,
    ReportShareRequest,
    ReportUpdate,
)
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post(
    "/",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Rapor oluştur",
)
def create_report(
    payload: ReportCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_role([UserRole.ADMIN, UserRole.ANALYST])),
) -> ReportResponse:
    """Create a new report from IOC queries. Viewer role cannot create reports."""
    report_service = ReportService(db)
    report = report_service.create_report(current_user.id, payload)
    return ReportResponse(**report_service._to_response(report))


@router.get(
    "/",
    response_model=ReportListResponse,
    summary="Rapor listesi",
)
@router.get("/", response_model=ReportListResponse, summary="Rapor listesi")
def list_reports(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_role([UserRole.ADMIN, UserRole.ANALYST])),
    page: int = Query(1, ge=1, description="Sayfa numarası"),
    page_size: int = Query(20, ge=1, le=100, description="Sayfa başına kayıt sayısı"),
    search: Optional[str] = Query(None, description="Arama terimi (başlık veya açıklama)"),
) -> ReportListResponse:
    """List all reports for the current user. Viewer role cannot access reports."""
    report_service = ReportService(db)
    result = report_service.list_reports(
        current_user.id, 
        page=page, 
        page_size=page_size, 
        search=search,
        user_role=current_user.role
    )
    return ReportListResponse(**result)


@router.get(
    "/{report_id}",
    response_model=ReportResponse,
    summary="Rapor detayı",
)
def get_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_role([UserRole.ADMIN, UserRole.ANALYST])),
) -> ReportResponse:
    """Get report details. Viewer role cannot access reports."""
    report_service = ReportService(db)
    report = report_service.get_report(report_id, current_user.id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return ReportResponse(**report_service._to_response(report))


@router.put(
    "/{report_id}",
    response_model=ReportResponse,
    summary="Rapor güncelle",
)
def update_report(
    report_id: str,
    payload: ReportUpdate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_role([UserRole.ADMIN, UserRole.ANALYST])),
) -> ReportResponse:
    """Update a report. Viewer role cannot update reports."""
    report_service = ReportService(db)
    report = report_service.update_report(report_id, current_user.id, payload)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return ReportResponse(**report_service._to_response(report))


@router.delete(
    "/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Rapor sil",
)
def delete_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_role([UserRole.ADMIN, UserRole.ANALYST])),
) -> None:
    """Delete a report. Viewer role cannot delete reports."""
    report_service = ReportService(db)
    deleted = report_service.delete_report(report_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")


@router.post(
    "/{report_id}/export",
    summary="Rapor export",
    status_code=status.HTTP_200_OK,
)
def export_report(
    report_id: str,
    export_request: ReportExportRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_role([UserRole.ADMIN, UserRole.ANALYST])),
) -> Response:
    """Export report in specified format. Viewer role cannot export reports."""
    report_service = ReportService(db)
    result = report_service.export_report(
        report_id, current_user.id, export_request.format, export_request.include_raw_data
    )

    if "error" in result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])

    # Use content_type from result if available, otherwise determine from format
    content_type = result.get("content_type")
    if not content_type:
        content_type_map = {
            "PDF": "application/pdf",
            "HTML": "text/html",
            "JSON": "application/json",
            "CSV": "text/csv",
        }
        content_type = content_type_map.get(export_request.format.upper(), "application/octet-stream")
    
    # Get content and filename
    content = result.get("content", b"")
    filename = result.get("filename", f"report_{report_id}.{export_request.format.lower()}")
    
    # Ensure content is bytes
    if isinstance(content, str):
        content = content.encode('utf-8')
    
    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.put(
    "/{report_id}/share",
    response_model=ReportResponse,
    summary="Raporu kullanıcılarla paylaş",
)
def share_report(
    report_id: str,
    share_request: ReportShareRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_role([UserRole.ADMIN, UserRole.ANALYST])),
) -> ReportResponse:
    """Share a report with specified users (viewers).
    
    Only admin/analyst users can share reports.
    """
    report_service = ReportService(db)
    try:
        result = report_service.share_report(
            report_id,
            current_user.id,
            share_request.user_ids
        )
        return ReportResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return Response(
        content=result["content"],
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{result["filename"]}"'},
    )


@router.put(
    "/{report_id}/share",
    response_model=ReportResponse,
    summary="Raporu kullanıcılarla paylaş",
)
def share_report(
    report_id: str,
    share_request: ReportShareRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_role([UserRole.ADMIN, UserRole.ANALYST])),
) -> ReportResponse:
    """Share a report with specified users (viewers).
    
    Only admin/analyst users can share reports.
    """
    report_service = ReportService(db)
    try:
        result = report_service.share_report(
            report_id,
            current_user.id,
            share_request.user_ids
        )
        return ReportResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

