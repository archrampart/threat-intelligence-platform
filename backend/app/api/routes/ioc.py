import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session
from loguru import logger

from app.api.routes.auth import get_current_user
from app.core.dependencies import require_role
from app.db.base import get_db
from app.models.user import UserRole
from app.schemas.auth import UserResponse
from app.schemas.ioc import (
    IOCQueryDetailResponse,
    IOCQueryHistoryListResponse,
    IOCQueryRequest,
    IOCQueryResponse,
)
from app.services.ioc_service import IOCService

router = APIRouter(tags=["ioc"])


@router.post(
    "/ioc/query",
    response_model=IOCQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="IOC sorgulama",
)
def query_ioc(
    payload: IOCQueryRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> IOCQueryResponse:
    """Query IOC across multiple threat intelligence sources."""
    # Validate IOC input
    from app.utils.input_validator import validate_ioc_value, sanitize_string
    
    sanitized_value = sanitize_string(payload.ioc_value, max_length=1000)
    is_valid, error_msg = validate_ioc_value(payload.ioc_type, sanitized_value)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg or "Invalid IOC value",
        )
    
    # Update payload with sanitized value
    payload.ioc_value = sanitized_value
    
    ioc_service = IOCService(db)
    return ioc_service.query_ioc(current_user.id, payload)


@router.get(
    "/ioc/history",
    response_model=IOCQueryHistoryListResponse,
    status_code=status.HTTP_200_OK,
    summary="IOC sorgu geçmişi",
)
def list_query_history(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),  # Allow all authenticated users
    ioc_type: Optional[str] = Query(None, description="IOC tipi filtresi"),
    ioc_value: Optional[str] = Query(None, description="IOC değeri arama (partial match)"),
    risk_level: Optional[str] = Query(None, description="Risk seviyesi filtresi (low, medium, high, critical, unknown)"),
    start_date: Optional[datetime] = Query(None, description="Başlangıç tarihi (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="Bitiş tarihi (ISO format)"),
    source: Optional[str] = Query(None, description="API kaynağı filtresi (partial match)"),
    watchlist_id: Optional[str] = Query(None, description="Watchlist ID filtresi"),
    page: int = Query(1, ge=1, description="Sayfa numarası"),
    page_size: int = Query(20, ge=1, le=100, description="Sayfa başına kayıt sayısı"),
) -> IOCQueryHistoryListResponse:
    """List IOC query history with filters and pagination.
    
    For admin/analyst: Returns all their own IOC queries.
    For viewer: Returns IOC queries from watchlists shared with them.
    """
    ioc_service = IOCService(db)
    # Convert role to string if it's an enum
    user_role_str = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    result = ioc_service.list_query_history(
        user_id=current_user.id,
        user_role=user_role_str,  # Pass user role to service
        ioc_type=ioc_type,
        ioc_value=ioc_value,
        risk_level=risk_level,
        start_date=start_date,
        end_date=end_date,
        source=source,
        watchlist_id=watchlist_id,
        page=page,
        page_size=page_size,
    )
    return IOCQueryHistoryListResponse(**result)


@router.get(
    "/ioc/history/{query_id}",
    response_model=IOCQueryDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="IOC sorgu detayı",
)
def get_query_detail(
    query_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_role([UserRole.ADMIN, UserRole.ANALYST])),
) -> IOCQueryDetailResponse:
    """Get detailed IOC query information. Viewer role cannot access query details."""
    ioc_service = IOCService(db)
    result = ioc_service.get_query_detail(query_id, current_user.id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="IOC query not found")
    return IOCQueryDetailResponse(**result)


@router.get(
    "/ioc/history/export",
    status_code=status.HTTP_200_OK,
    summary="IOC sorgu geçmişi export",
)
def export_query_history(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),  # Allow all authenticated users
    format: str = Query("json", regex="^(json)$", description="Export format: json"),
    ioc_type: Optional[str] = Query(None, description="IOC tipi filtresi"),
    ioc_value: Optional[str] = Query(None, description="IOC değeri arama (partial match)"),
    risk_level: Optional[str] = Query(None, description="Risk seviyesi filtresi"),
    start_date: Optional[datetime] = Query(None, description="Başlangıç tarihi (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="Bitiş tarihi (ISO format)"),
    source: Optional[str] = Query(None, description="API kaynağı filtresi (partial match)"),
    watchlist_id: Optional[str] = Query(None, description="Watchlist ID filtresi"),
) -> Response:
    """Export IOC query history as CSV or JSON.
    
    For admin/analyst: Exports all their own IOC queries.
    For viewer: Exports IOC queries from watchlists shared with them.
    """
    try:
        ioc_service = IOCService(db)
        
        # Get all matching records (no pagination for export)
        # Convert role to string if it's an enum
        user_role_str = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
        result = ioc_service.list_query_history(
            user_id=current_user.id,
            user_role=user_role_str,  # Pass user role to service
            ioc_type=ioc_type,
            ioc_value=ioc_value,
            risk_level=risk_level,
            start_date=start_date,
            end_date=end_date,
            source=source,
            watchlist_id=watchlist_id,
            page=1,
            page_size=10000,  # Large page size to get all records
        )
        
        items = result.get("items", [])
    except Exception as e:
        logger.error(f"Error exporting IOC query history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export query history: {str(e)}"
        )
    
    # Only JSON export is supported
    if format != "json":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JSON format is supported for export"
        )
    
    # JSON export
        try:
            json_content = json.dumps(items, indent=2, default=str)
            
            # Ensure content is encoded as UTF-8 bytes
            if isinstance(json_content, str):
                json_content = json_content.encode('utf-8')
            
            return Response(
                content=json_content,
                media_type="application/json; charset=utf-8",
                headers={
                    "Content-Disposition": f'attachment; filename="ioc_query_history_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"'
                },
            )
        except Exception as e:
            logger.error(f"Error creating JSON export: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create JSON export: {str(e)}"
            )
