import json
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_user
from app.db.base import get_db
from app.schemas.auth import UserResponse
from app.schemas.watchlist import Watchlist, WatchlistCreate, WatchlistListResponse, WatchlistShareRequest
from app.services.watchlist_service import WatchlistService
from app.utils.ioc_detector import detect_ioc_type

router = APIRouter(prefix="/watchlists", tags=["watchlists"])


@router.get("/", response_model=WatchlistListResponse, summary="Watchlist listesi")
def list_watchlists(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> WatchlistListResponse:
    """List all watchlists for the current user.
    
    For admin/analyst: Returns only their own watchlists.
    For viewer: Returns their own watchlists (if any) + watchlists shared with them.
    """
    watchlist_service = WatchlistService(db)
    return watchlist_service.list_watchlists(current_user.id, user_role=current_user.role)


@router.post(
    "/",
    response_model=Watchlist,
    status_code=status.HTTP_201_CREATED,
    summary="Watchlist oluştur",
)
async def create_watchlist(
    name: str = Form(...),
    description: str = Form(None),
    check_interval: int = Form(60),
    notification_enabled: bool = Form(True),
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> Watchlist:
    """Create a new watchlist. Optionally upload IOCs from a TXT file."""
    from app.schemas.watchlist import WatchlistAsset
    from uuid import uuid4
    
    assets = []
    
    # If file is provided, parse it
    if file and file.filename:
        if not file.filename.endswith(('.txt', '.TXT')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only .txt files are supported"
            )
        
        try:
            content = await file.read()
            text_content = content.decode('utf-8')
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to read file: {str(e)}"
            )
        
        # Parse lines
        lines = [line.strip() for line in text_content.split('\n') if line.strip()]
        
        for line in lines:
            # Skip comments
            if line.startswith('#'):
                continue
            
            # Check if line contains multiple IOCs (e.g., "IP    domain" or "IP    hostname")
            parts = line.split()
            
            if len(parts) >= 2:
                # Try to parse as "IP    domain/hostname" format
                first_part = parts[0].strip()
                second_part = parts[1].strip()
                
                first_type = detect_ioc_type(first_part)
                second_type = detect_ioc_type(second_part)
                
                # If first is IP and second is domain, add both
                if first_type == "ip" and second_type == "domain":
                    # Add IP
                    ip_asset = WatchlistAsset(
                        id=str(uuid4()),
                        ioc_type="ip",
                        ioc_value=first_part,
                        description=f"Imported from file: {file.filename} (from line: {line[:50]})",
                        risk_threshold="medium",
                        is_active=True,
                    )
                    assets.append(ip_asset)
                    
                    # Add Domain
                    domain_asset = WatchlistAsset(
                        id=str(uuid4()),
                        ioc_type="domain",
                        ioc_value=second_part,
                        description=f"Imported from file: {file.filename} (from line: {line[:50]})",
                        risk_threshold="medium",
                        is_active=True,
                    )
                    assets.append(domain_asset)
                    continue
            
            # Detect IOC type for the whole line (single IOC)
            ioc_type = detect_ioc_type(line)
            
            if ioc_type and ioc_type != "unknown":
                asset = WatchlistAsset(
                    id=str(uuid4()),
                    ioc_type=ioc_type,
                    ioc_value=line,
                    description=f"Imported from file: {file.filename}",
                    risk_threshold="medium",
                    is_active=True,
                )
                assets.append(asset)
    
    # Create watchlist payload
    payload = WatchlistCreate(
        name=name,
        description=description,
        check_interval=check_interval,
        notification_enabled=notification_enabled,
        assets=assets,
    )
    
    watchlist_service = WatchlistService(db)
    return watchlist_service.create_watchlist(current_user.id, payload)


@router.get(
    "/{watchlist_id}",
    response_model=Watchlist,
    summary="Watchlist detayı",
)
def get_watchlist(
    watchlist_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> Watchlist:
    """Get watchlist details."""
    watchlist_service = WatchlistService(db)
    watchlist = watchlist_service.get_watchlist(watchlist_id, current_user.id)
    if not watchlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found")
    return watchlist


@router.put(
    "/{watchlist_id}",
    response_model=Watchlist,
    summary="Watchlist güncelle",
)
async def update_watchlist(
    watchlist_id: str,
    name: str = Form(...),
    description: str = Form(None),
    check_interval: int = Form(60),
    notification_enabled: bool = Form(True),
    is_active: bool = Form(True),
    assets_json: str = Form(None),  # JSON string of assets
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> Watchlist:
    """Update a watchlist. Optionally upload additional IOCs from a TXT file."""
    import json
    from app.schemas.watchlist import WatchlistAsset
    from uuid import uuid4
    
    # Get existing watchlist
    watchlist_service = WatchlistService(db)
    existing_watchlist = watchlist_service.get_watchlist(watchlist_id, current_user.id)
    if not existing_watchlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found")
    
    # Parse assets from JSON
    assets = []
    if assets_json:
        try:
            assets_data = json.loads(assets_json)
            assets = [WatchlistAsset(**asset) for asset in assets_data]
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid assets JSON: {str(e)}"
            )
    
    # If file is provided, parse it and add to assets
    if file and file.filename:
        if not file.filename.endswith(('.txt', '.TXT')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only .txt files are supported"
            )
        
        try:
            content = await file.read()
            text_content = content.decode('utf-8')
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to read file: {str(e)}"
            )
        
        # Parse lines
        lines = [line.strip() for line in text_content.split('\n') if line.strip()]
        
        for line in lines:
            # Skip comments
            if line.startswith('#'):
                continue
            
            # Check if line contains multiple IOCs (e.g., "IP    domain" or "IP    hostname")
            parts = line.split()
            
            if len(parts) >= 2:
                # Try to parse as "IP    domain/hostname" format
                first_part = parts[0].strip()
                second_part = parts[1].strip()
                
                first_type = detect_ioc_type(first_part)
                second_type = detect_ioc_type(second_part)
                
                # If first is IP and second is domain, add both
                if first_type == "ip" and second_type == "domain":
                    # Add IP
                    ip_asset = WatchlistAsset(
                        id=str(uuid4()),
                        ioc_type="ip",
                        ioc_value=first_part,
                        description=f"Imported from file: {file.filename} (from line: {line[:50]})",
                        risk_threshold="medium",
                        is_active=True,
                    )
                    assets.append(ip_asset)
                    
                    # Add Domain
                    domain_asset = WatchlistAsset(
                        id=str(uuid4()),
                        ioc_type="domain",
                        ioc_value=second_part,
                        description=f"Imported from file: {file.filename} (from line: {line[:50]})",
                        risk_threshold="medium",
                        is_active=True,
                    )
                    assets.append(domain_asset)
                    continue
            
            # Detect IOC type for the whole line (single IOC)
            ioc_type = detect_ioc_type(line)
            
            if ioc_type and ioc_type != "unknown":
                asset = WatchlistAsset(
                    id=str(uuid4()),
                    ioc_type=ioc_type,
                    ioc_value=line,
                    description=f"Imported from file: {file.filename}",
                    risk_threshold="medium",
                    is_active=True,
                )
                assets.append(asset)
    
    # Create watchlist payload
    payload = WatchlistCreate(
        name=name,
        description=description,
        check_interval=check_interval,
        notification_enabled=notification_enabled,
        assets=assets,
    )
    
    watchlist = watchlist_service.update_watchlist(watchlist_id, current_user.id, payload, is_active=is_active)
    if not watchlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found")
    return watchlist


@router.delete(
    "/{watchlist_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Watchlist sil",
)
def delete_watchlist(
    watchlist_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> None:
    """Delete a watchlist."""
    watchlist_service = WatchlistService(db)
    deleted = watchlist_service.delete_watchlist(watchlist_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found")


@router.post(
    "/{watchlist_id}/check",
    summary="Watchlist kontrolü",
    status_code=status.HTTP_200_OK,
)
def check_watchlist(
    watchlist_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> dict:
    """Manually check all active items in a watchlist."""
    watchlist_service = WatchlistService(db)
    result = watchlist_service.check_watchlist(watchlist_id, current_user.id)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
    return result


@router.post(
    "/check-all",
    summary="Tüm watchlist'leri kontrol et",
    status_code=status.HTTP_200_OK,
)
def check_all_watchlists(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> dict:
    """Manually check all active watchlists for the current user."""
    watchlist_service = WatchlistService(db)
    result = watchlist_service.check_all_watchlists(current_user.id)
    return result


@router.post(
    "/items/{item_id}/check",
    summary="Watchlist item kontrolü",
    status_code=status.HTTP_200_OK,
)
def check_watchlist_item(
    item_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> dict:
    """Manually check a single watchlist item."""
    watchlist_service = WatchlistService(db)
    result = watchlist_service.check_watchlist_item(item_id, current_user.id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist item not found")
    return result


@router.post(
    "/{watchlist_id}/upload",
    summary="TXT dosyasından toplu yükleme",
    status_code=status.HTTP_200_OK,
)
async def upload_watchlist_from_file(
    watchlist_id: str,
    file: UploadFile = File(..., description="TXT file with one IOC per line"),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> dict:
    """Upload IOCs from a TXT file to a watchlist. One IOC per line."""
    # Verify watchlist exists and belongs to user
    watchlist_service = WatchlistService(db)
    watchlist = watchlist_service.get_watchlist(watchlist_id, current_user.id)
    if not watchlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found")
    
    # Check file type
    if not file.filename.endswith(('.txt', '.TXT')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .txt files are supported"
        )
    
    # Read file content
    try:
        content = await file.read()
        text_content = content.decode('utf-8')
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read file: {str(e)}"
        )
    
    # Parse lines
    lines = [line.strip() for line in text_content.split('\n') if line.strip()]
    
    if not lines:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty or contains no valid IOCs"
        )
    
    # Parse IOCs
    from app.schemas.watchlist import WatchlistAsset
    from uuid import uuid4
    
    assets = []
    skipped = []
    
    for line_num, line in enumerate(lines, 1):
        # Skip comments (lines starting with #)
        if line.startswith('#'):
            continue
        
        # Check if line contains multiple IOCs (e.g., "IP    domain" or "IP    hostname")
        # Split by whitespace (space, tab, etc.)
        parts = line.split()
        
        if len(parts) >= 2:
            # Try to parse as "IP    domain/hostname" format
            first_part = parts[0].strip()
            second_part = parts[1].strip()
            
            first_type = detect_ioc_type(first_part)
            second_type = detect_ioc_type(second_part)
            
            # If first is IP and second is domain, add both
            if first_type == "ip" and second_type == "domain":
                # Add IP
                ip_asset = WatchlistAsset(
                    id=str(uuid4()),
                    ioc_type="ip",
                    ioc_value=first_part,
                    description=f"Imported from file: {file.filename} (from line: {line[:50]})",
                    risk_threshold="medium",
                    is_active=True,
                )
                assets.append(ip_asset)
                
                # Add Domain
                domain_asset = WatchlistAsset(
                    id=str(uuid4()),
                    ioc_type="domain",
                    ioc_value=second_part,
                    description=f"Imported from file: {file.filename} (from line: {line[:50]})",
                    risk_threshold="medium",
                    is_active=True,
                )
                assets.append(domain_asset)
                continue
        
        # Try to detect IOC type for the whole line (single IOC)
        ioc_type = detect_ioc_type(line)
        
        if not ioc_type or ioc_type == "unknown":
            skipped.append(f"Line {line_num}: Could not detect IOC type for '{line[:50]}'")
            continue
        
        # Create asset
        asset = WatchlistAsset(
            id=str(uuid4()),
            ioc_type=ioc_type,
            ioc_value=line.strip(),
            description=f"Imported from file: {file.filename}",
            risk_threshold="medium",
            is_active=True,
        )
        assets.append(asset)
    
    if not assets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid IOCs found in file"
        )
    
    # Add assets to watchlist
    try:
        result = watchlist_service.add_assets_to_watchlist(watchlist_id, current_user.id, assets)
        
        return {
            "success": True,
            "message": f"Successfully added {len(assets)} asset(s) to watchlist",
            "added": len(assets),
            "skipped": len(skipped),
            "skipped_items": skipped[:10],  # First 10 skipped items
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add assets: {str(e)}"
        )


@router.get(
    "/{watchlist_id}/export",
    summary="Watchlist export",
    status_code=status.HTTP_200_OK,
)
def export_watchlist(
    watchlist_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
    format: str = Query("json", regex="^(json)$", description="Export format: json"),
) -> Response:
    """Export watchlist assets as JSON."""
    watchlist_service = WatchlistService(db)
    watchlist = watchlist_service.get_watchlist(watchlist_id, current_user.id)
    
    if not watchlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found")
    
    # Only JSON export is supported
    if format != "json":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JSON format is supported for export"
        )
    
    # Create JSON content
    assets_data = []
    for asset in watchlist.assets:
        assets_data.append({
            "ioc_type": asset.ioc_type,
            "ioc_value": asset.ioc_value,
            "description": asset.description or "",
            "risk_threshold": asset.risk_threshold.value if asset.risk_threshold else None,
            "last_status": asset.last_status.value if asset.last_status else None,
            "last_check_date": asset.last_check_date.isoformat() if asset.last_check_date else None,
            "is_active": asset.is_active,
        })
    
    json_content = json.dumps(assets_data, indent=2, default=str)
    
    # Ensure content is encoded as UTF-8 bytes
    if isinstance(json_content, str):
        json_content = json_content.encode('utf-8')
    
    # Sanitize watchlist name for filename
    safe_name = "".join(c for c in watchlist.name if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_name = safe_name.replace(' ', '_')
    
    return Response(
        content=json_content,
        media_type="application/json; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="watchlist_{safe_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"'
        },
    )


@router.get(
    "/items/{item_id}/history",
    summary="Asset kontrol geçmişi",
    status_code=status.HTTP_200_OK,
)
def get_asset_check_history(
    item_id: str,
    limit: int = Query(50, ge=1, le=200, description="Maximum number of history entries"),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """Get check history for a watchlist asset."""
    from app.schemas.watchlist import AssetCheckHistoryListResponse
    
    watchlist_service = WatchlistService(db)
    history = watchlist_service.get_asset_check_history(item_id, current_user.id, limit)
    return history


@router.put(
    "/{watchlist_id}/share",
    response_model=Watchlist,
    summary="Watchlist'i kullanıcılarla paylaş",
)
def share_watchlist(
    watchlist_id: str,
    share_request: WatchlistShareRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> Watchlist:
    """Share a watchlist with specified users (viewers).
    
    Only admin/analyst users can share watchlists.
    """
    from app.models.user import UserRole
    
    # Only admin/analyst can share
    if current_user.role not in [UserRole.ADMIN.value, UserRole.ANALYST.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin or analyst users can share watchlists"
        )
    
    watchlist_service = WatchlistService(db)
    try:
        watchlist = watchlist_service.share_watchlist(
            watchlist_id, 
            current_user.id, 
            share_request.user_ids
        )
        return watchlist
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
