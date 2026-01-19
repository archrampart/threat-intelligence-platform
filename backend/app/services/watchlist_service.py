"""Watchlist Service - Database integration with IOC checking."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.models.watchlist import AssetWatchlist, AssetWatchlistItem, AssetCheckHistory as AssetCheckHistoryModel, IOCStatus, RiskThreshold
from app.schemas.watchlist import Watchlist, WatchlistCreate, WatchlistListResponse, WatchlistAsset, AssetCheckHistoryListResponse, AssetCheckHistory
from loguru import logger


class WatchlistService:
    """Watchlist service with database integration."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_watchlists(self, user_id: str, user_role: Optional[str] = None) -> WatchlistListResponse:
        """List all watchlists for a user.
        
        For admin/analyst: Returns only their own watchlists.
        For viewer: Returns their own watchlists (if any) + watchlists shared with them.
        """
        from sqlalchemy import or_
        from app.models.user import UserRole
        
        # Get user role if not provided
        if user_role is None:
            from app.models.user import User
            user = self.db.query(User).filter(User.id == user_id).first()
            user_role = user.role.value if user else None
        
        # Base query
        query = self.db.query(AssetWatchlist)
        
        # For viewer users, include both their own watchlists and shared ones
        if user_role == UserRole.VIEWER.value:
            # Get watchlists where user is owner OR user is in shared_with_user_ids
            # For SQLite, we need to filter in Python since JSON array queries are complex
            # For PostgreSQL, we could use JSONB operators, but for simplicity, we'll use Python filtering for both
            import json
            all_watchlists = self.db.query(AssetWatchlist).all()
            watchlists = []
            for w in all_watchlists:
                # Check if user is owner
                if w.user_id == user_id:
                    watchlists.append(w)
                    continue
                
                # Check if user is in shared_with_user_ids
                shared_ids = w.shared_with_user_ids
                if shared_ids is not None:
                    # Handle both string (SQLite JSON) and list (already parsed) formats
                    if isinstance(shared_ids, str):
                        try:
                            shared_ids = json.loads(shared_ids)
                        except (json.JSONDecodeError, TypeError):
                            shared_ids = None
                    
                    if isinstance(shared_ids, list) and len(shared_ids) > 0 and user_id in shared_ids:
                        watchlists.append(w)
            
            return WatchlistListResponse(
                watchlists=[self._to_watchlist_response(w) for w in watchlists]
            )
        else:
            # For admin/analyst, only show their own watchlists
            query = query.filter(AssetWatchlist.user_id == user_id)
        
        watchlists = query.all()
        return WatchlistListResponse(
            watchlists=[self._to_watchlist_response(w) for w in watchlists]
        )

    def create_watchlist(self, user_id: str, payload: WatchlistCreate) -> Watchlist:
        """Create a new watchlist."""
        watchlist = AssetWatchlist(
            id=str(uuid4()),
            user_id=user_id,
            name=payload.name,
            description=payload.description,
            is_active=True,
            notification_enabled=payload.notification_enabled,
            check_interval=payload.check_interval,
        )
        self.db.add(watchlist)
        self.db.flush()

        # Add assets
        for asset in payload.assets:
            risk_threshold = RiskThreshold(asset.risk_threshold) if asset.risk_threshold else None
            item = AssetWatchlistItem(
                id=str(uuid4()),
                watchlist_id=watchlist.id,
                ioc_type=asset.ioc_type,
                ioc_value=asset.ioc_value,
                description=asset.description,
                risk_threshold=risk_threshold,
                is_active=asset.is_active,
            )
            self.db.add(item)

        self.db.commit()
        self.db.refresh(watchlist)
        return self._to_watchlist_response(watchlist)

    def get_watchlist(self, watchlist_id: str, user_id: str) -> Optional[Watchlist]:
        """Get a watchlist by ID.
        
        For admin/analyst: Returns watchlist if user owns it.
        For viewer: Returns watchlist if user owns it OR watchlist is shared with user.
        """
        watchlist = self.db.query(AssetWatchlist).filter(AssetWatchlist.id == watchlist_id).first()
        if not watchlist:
            return None

        # Check if user owns the watchlist
        if watchlist.user_id == user_id:
            return self._to_watchlist_response(watchlist)
        
        # Check if user is admin
        from app.models.user import User, UserRole
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        if user.role == UserRole.ADMIN:
            return self._to_watchlist_response(watchlist)
        
        # For viewer users, check if watchlist is shared with them
        if user.role == UserRole.VIEWER:
            import json
            shared_ids = watchlist.shared_with_user_ids
            if shared_ids is not None:
                if isinstance(shared_ids, str):
                    try:
                        shared_ids = json.loads(shared_ids)
                    except (json.JSONDecodeError, TypeError):
                        shared_ids = None
                
                if isinstance(shared_ids, list) and len(shared_ids) > 0 and user_id in shared_ids:
                    return self._to_watchlist_response(watchlist)
        
        return None

    def update_watchlist(self, watchlist_id: str, user_id: str, payload: WatchlistCreate, is_active: Optional[bool] = None) -> Optional[Watchlist]:
        """Update a watchlist."""
        watchlist = self.get_watchlist(watchlist_id, user_id)
        if not watchlist:
            return None

        db_watchlist = self.db.query(AssetWatchlist).filter(AssetWatchlist.id == watchlist_id).first()
        db_watchlist.name = payload.name
        db_watchlist.description = payload.description
        db_watchlist.notification_enabled = payload.notification_enabled
        db_watchlist.check_interval = payload.check_interval
        
        # Update is_active if provided
        if is_active is not None:
            db_watchlist.is_active = is_active

        # Update assets - delete existing and create new ones
        self.db.query(AssetWatchlistItem).filter(AssetWatchlistItem.watchlist_id == watchlist_id).delete()

        for asset in payload.assets:
            risk_threshold = RiskThreshold(asset.risk_threshold) if asset.risk_threshold else None
            item = AssetWatchlistItem(
                id=str(uuid4()),
                watchlist_id=watchlist_id,
                ioc_type=asset.ioc_type,
                ioc_value=asset.ioc_value,
                description=asset.description,
                risk_threshold=risk_threshold,
                is_active=asset.is_active,
            )
            self.db.add(item)

        self.db.commit()
        self.db.refresh(db_watchlist)
        return self._to_watchlist_response(db_watchlist)

    def add_assets_to_watchlist(
        self, watchlist_id: str, user_id: str, assets: list[WatchlistAsset]
    ) -> Watchlist:
        """Add assets to an existing watchlist."""
        watchlist = self.get_watchlist(watchlist_id, user_id)
        if not watchlist:
            raise ValueError("Watchlist not found")

        db_watchlist = self.db.query(AssetWatchlist).filter(AssetWatchlist.id == watchlist_id).first()

        # Add new assets
        for asset in assets:
            risk_threshold = RiskThreshold(asset.risk_threshold) if asset.risk_threshold else None
            item = AssetWatchlistItem(
                id=str(uuid4()),
                watchlist_id=watchlist_id,
                ioc_type=asset.ioc_type,
                ioc_value=asset.ioc_value,
                description=asset.description,
                risk_threshold=risk_threshold,
                is_active=asset.is_active,
            )
            self.db.add(item)

        self.db.commit()
        self.db.refresh(db_watchlist)
        return self._to_watchlist_response(db_watchlist)

    def delete_watchlist(self, watchlist_id: str, user_id: str) -> bool:
        """Delete a watchlist."""
        watchlist = self.get_watchlist(watchlist_id, user_id)
        if not watchlist:
            return False

        db_watchlist = self.db.query(AssetWatchlist).filter(AssetWatchlist.id == watchlist_id).first()
        self.db.delete(db_watchlist)
        self.db.commit()
        return True

    def check_watchlist_item(self, item_id: str, user_id: str) -> Optional[dict]:
        """Manually check a watchlist item using IOC service.
        
        For admin/analyst: Can check items in their own watchlists.
        For viewer: Can check items in watchlists shared with them (read-only check).
        """
        from app.services.ioc_service import IOCService
        from app.schemas.ioc import IOCQueryRequest

        # Get watchlist item
        item = self.db.query(AssetWatchlistItem).filter(AssetWatchlistItem.id == item_id).first()
        if not item:
            return None

        # Check if user has access to the watchlist
        watchlist = self.db.query(AssetWatchlist).filter(AssetWatchlist.id == item.watchlist_id).first()
        if not watchlist:
            return None
        
        # Check if user owns the watchlist
        if watchlist.user_id == user_id:
            pass  # User owns it, allow
        else:
            from app.models.user import User, UserRole
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            
            # Admin can check any watchlist
            if user.role == UserRole.ADMIN:
                pass  # Admin, allow
            # Viewer can check shared watchlists
            elif user.role == UserRole.VIEWER:
                import json
                shared_ids = watchlist.shared_with_user_ids
                if shared_ids is not None:
                    if isinstance(shared_ids, str):
                        try:
                            shared_ids = json.loads(shared_ids)
                        except (json.JSONDecodeError, TypeError):
                            shared_ids = None
                    
                    if isinstance(shared_ids, list) and len(shared_ids) > 0 and user_id in shared_ids:
                        pass  # Shared with viewer, allow
                    else:
                        return None  # Not shared, deny
                else:
                    return None  # Not shared, deny
            else:
                return None  # Analyst can only check their own

        # Query IOC using IOC service
        ioc_service = IOCService(self.db)
        ioc_request = IOCQueryRequest(ioc_type=item.ioc_type, ioc_value=item.ioc_value)
        ioc_response = ioc_service.query_ioc(user_id, ioc_request)

        # Update watchlist item
        item.last_check_date = datetime.now(timezone.utc)
        item.last_risk_score = ioc_response.overall_risk
        item.last_status = self._convert_risk_to_status(ioc_response.overall_risk)

        # Create check history
        check_history = AssetCheckHistoryModel(
            id=str(uuid4()),
            watchlist_item_id=item.id,
            check_date=datetime.now(timezone.utc),
            risk_score=ioc_response.overall_risk,
            status=self._convert_risk_to_status(ioc_response.overall_risk),
            threat_intelligence_data={
                "overall_risk": ioc_response.overall_risk,
                "queried_sources": [r.dict() for r in ioc_response.queried_sources],
            },
            sources_checked=[r.source for r in ioc_response.queried_sources],
            alert_triggered=self._should_trigger_alert(item.risk_threshold, ioc_response.overall_risk),
        )
        self.db.add(check_history)
        self.db.flush()

        # Create alert if threshold is exceeded and watchlist has notifications enabled
        if check_history.alert_triggered and watchlist.notification_enabled:
            from app.models.alert import Alert, AlertSeverity, AlertType
            from app.schemas.alert import AlertCreate
            from app.services.alert_service import AlertService
            
            # Determine severity based on risk level
            severity_map = {
                "low": AlertSeverity.LOW,
                "medium": AlertSeverity.MEDIUM,
                "high": AlertSeverity.HIGH,
                "critical": AlertSeverity.HIGH,
            }
            risk_level_for_alert = (ioc_response.overall_risk or "unknown").lower()
            alert_severity = severity_map.get(risk_level_for_alert, AlertSeverity.MEDIUM)
            
            alert_service = AlertService(self.db)
            alert_data = AlertCreate(
                alert_type=AlertType.WATCHLIST,
                severity=alert_severity,
                title=f"High Risk Detected: {item.ioc_type.upper()} - {item.ioc_value}",
                message=f"Watchlist asset '{item.ioc_value}' detected with {ioc_response.overall_risk or 'unknown'} risk level.",
                watchlist_id=watchlist.id,
                asset_id=item.id,
                metadata={
                    "ioc_type": item.ioc_type,
                    "ioc_value": item.ioc_value,
                    "risk_score": ioc_response.overall_risk,
                    "status": item.last_status.value if item.last_status else None,
                    "queried_sources": [r.dict() for r in ioc_response.queried_sources],
                },
            )
            alert_service.create_alert(user_id, alert_data)

        self.db.commit()

        return {
            "item_id": item.id,
            "ioc_type": item.ioc_type,
            "ioc_value": item.ioc_value,
            "risk_score": ioc_response.overall_risk,
            "status": item.last_status.value if item.last_status else None,
            "check_date": item.last_check_date,
            "sources_checked": [r.source for r in ioc_response.queried_sources],
            "alert_triggered": check_history.alert_triggered,
        }

    def check_watchlist(self, watchlist_id: str, user_id: str) -> dict:
        """Check all active items in a watchlist.
        
        For admin/analyst: Can check their own watchlists.
        For viewer: Can check their own watchlists + watchlists shared with them.
        """
        from app.models.user import User, UserRole
        
        # Direct watchlist query to check access
        watchlist_model = self.db.query(AssetWatchlist).filter(AssetWatchlist.id == watchlist_id).first()
        if not watchlist_model:
            return {"error": "Watchlist not found"}
        
        # Check access permissions
        has_access = False
        if watchlist_model.user_id == user_id:
            has_access = True  # User owns it
        else:
            user = self.db.query(User).filter(User.id == user_id).first()
            if user:
                if user.role == UserRole.ADMIN:
                    has_access = True  # Admin can check any watchlist
                elif user.role == UserRole.VIEWER:
                    # Viewer can check shared watchlists
                    import json
                    shared_ids = watchlist_model.shared_with_user_ids
                    if shared_ids is not None:
                        if isinstance(shared_ids, str):
                            try:
                                shared_ids = json.loads(shared_ids)
                            except (json.JSONDecodeError, TypeError):
                                shared_ids = None
                        if isinstance(shared_ids, list) and len(shared_ids) > 0 and user_id in shared_ids:
                            has_access = True
        
        if not has_access:
            return {"error": "Watchlist not found or access denied"}

        # Get all active items
        items = (
            self.db.query(AssetWatchlistItem)
            .filter(AssetWatchlistItem.watchlist_id == watchlist_id)
            .filter(AssetWatchlistItem.is_active == True)
            .all()
        )

        results = []
        for item in items:
            result = self.check_watchlist_item(item.id, user_id)
            if result:
                results.append(result)

        return {
            "watchlist_id": watchlist_id,
            "checked_items": len(results),
            "results": results,
        }

    def check_all_watchlists(self, user_id: str) -> dict:
        """Check all active watchlists for a user.
        
        For admin/analyst: Checks only their own watchlists.
        For viewer: Checks their own watchlists (if any) + watchlists shared with them.
        """
        from app.models.user import User, UserRole
        
        # Get user role
        user = self.db.query(User).filter(User.id == user_id).first()
        user_role = user.role.value if user else None
        
        # Get watchlists based on user role
        if user_role == UserRole.VIEWER.value:
            # For viewer users, include both their own watchlists and shared ones
            import json
            all_watchlists = self.db.query(AssetWatchlist).filter(
                AssetWatchlist.is_active == True
            ).all()
            
            watchlists = []
            for w in all_watchlists:
                # Check if user is owner
                if w.user_id == user_id:
                    watchlists.append(w)
                    continue
                
                # Check if user is in shared_with_user_ids
                shared_ids = w.shared_with_user_ids
                if shared_ids is not None:
                    # Handle both string (SQLite JSON) and list (already parsed) formats
                    if isinstance(shared_ids, str):
                        try:
                            shared_ids = json.loads(shared_ids)
                        except (json.JSONDecodeError, TypeError):
                            shared_ids = None
                    
                    if isinstance(shared_ids, list) and len(shared_ids) > 0 and user_id in shared_ids:
                        watchlists.append(w)
        else:
            # For admin/analyst, only check their own watchlists
            watchlists = (
                self.db.query(AssetWatchlist)
                .filter(AssetWatchlist.user_id == user_id)
                .filter(AssetWatchlist.is_active == True)
                .all()
            )

        total_checked = 0
        results = []
        
        for watchlist in watchlists:
            try:
                result = self.check_watchlist(watchlist.id, user_id)
                if "checked_items" in result:
                    total_checked += result["checked_items"]
                    results.append({
                        "watchlist_id": watchlist.id,
                        "watchlist_name": watchlist.name,
                        "checked_items": result["checked_items"],
                    })
            except Exception as e:
                logger.error(f"Error checking watchlist {watchlist.id}: {e}")
                results.append({
                    "watchlist_id": watchlist.id,
                    "watchlist_name": watchlist.name,
                    "error": str(e),
                })

        return {
            "total_watchlists": len(watchlists),
            "total_checked_items": total_checked,
            "results": results,
        }

    def _convert_risk_to_status(self, risk_level: Optional[str]) -> Optional[IOCStatus]:
        """Convert risk level to IOC status."""
        if not risk_level:
            return None
        risk_map = {
            "high": IOCStatus.MALICIOUS,
            "medium": IOCStatus.SUSPICIOUS,
            "low": IOCStatus.SUSPICIOUS,
            "clean": IOCStatus.CLEAN,
        }
        return risk_map.get(risk_level.lower())

    def _should_trigger_alert(self, risk_threshold: Optional[RiskThreshold], risk_level: Optional[str]) -> bool:
        """Check if alert should be triggered based on risk threshold."""
        if not risk_threshold or not risk_level:
            return False

        threshold_map = {
            RiskThreshold.LOW: ["low", "medium", "high"],
            RiskThreshold.MEDIUM: ["medium", "high"],
            RiskThreshold.HIGH: ["high"],
            RiskThreshold.CRITICAL: ["high"],
        }

        return risk_level.lower() in threshold_map.get(risk_threshold, [])

    def get_asset_check_history(self, item_id: str, user_id: str, limit: int = 50) -> AssetCheckHistoryListResponse:
        """Get check history for an asset.
        
        For admin/analyst: Returns history for items in their own watchlists.
        For viewer: Returns history for items in watchlists shared with them.
        """
        # Verify item exists and user has access
        item = self.db.query(AssetWatchlistItem).filter(AssetWatchlistItem.id == item_id).first()
        if not item:
            return AssetCheckHistoryListResponse(items=[], total=0)
        
        watchlist = self.db.query(AssetWatchlist).filter(AssetWatchlist.id == item.watchlist_id).first()
        if not watchlist:
            return AssetCheckHistoryListResponse(items=[], total=0)
        
        # Check if user owns the watchlist
        if watchlist.user_id == user_id:
            pass  # User owns it, allow
        else:
            from app.models.user import User, UserRole
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return AssetCheckHistoryListResponse(items=[], total=0)
            
            # Admin can see any watchlist history
            if user.role == UserRole.ADMIN:
                pass  # Admin, allow
            # Viewer can see shared watchlist history
            elif user.role == UserRole.VIEWER:
                import json
                shared_ids = watchlist.shared_with_user_ids
                if shared_ids is not None:
                    if isinstance(shared_ids, str):
                        try:
                            shared_ids = json.loads(shared_ids)
                        except (json.JSONDecodeError, TypeError):
                            shared_ids = None
                    
                    if isinstance(shared_ids, list) and len(shared_ids) > 0 and user_id in shared_ids:
                        pass  # Shared with viewer, allow
                    else:
                        return AssetCheckHistoryListResponse(items=[], total=0)  # Not shared, deny
                else:
                    return AssetCheckHistoryListResponse(items=[], total=0)  # Not shared, deny
            else:
                return AssetCheckHistoryListResponse(items=[], total=0)  # Analyst can only see their own
        
        # Get check history
        history_items = (
            self.db.query(AssetCheckHistoryModel)
            .filter(AssetCheckHistoryModel.watchlist_item_id == item_id)
            .order_by(AssetCheckHistoryModel.check_date.desc())
            .limit(limit)
            .all()
        )
        
        items = [
            AssetCheckHistory(
                id=history.id,
                check_date=history.check_date,
                risk_score=history.risk_score,
                status=history.status.value if history.status else None,
                threat_intelligence_data=history.threat_intelligence_data,
                sources_checked=history.sources_checked,
                alert_triggered=history.alert_triggered,
            )
            for history in history_items
        ]
        
        total = self.db.query(AssetCheckHistoryModel).filter(AssetCheckHistoryModel.watchlist_item_id == item_id).count()
        
        return AssetCheckHistoryListResponse(items=items, total=total)

    def _to_watchlist_response(self, watchlist: AssetWatchlist) -> Watchlist:
        """Convert database model to response schema."""
        items = (
            self.db.query(AssetWatchlistItem)
            .filter(AssetWatchlistItem.watchlist_id == watchlist.id)
            .all()
        )

        assets = [
            WatchlistAsset(
                id=UUID(item.id),
                ioc_type=item.ioc_type,
                ioc_value=item.ioc_value,
                description=item.description,
                risk_threshold=item.risk_threshold.value if item.risk_threshold else None,
                is_active=item.is_active,
                created_at=item.created_at,
            )
            for item in items
        ]

        return Watchlist(
            id=UUID(watchlist.id),
            name=watchlist.name,
            description=watchlist.description,
            check_interval=watchlist.check_interval,
            notification_enabled=watchlist.notification_enabled,
            is_active=watchlist.is_active,
            created_at=watchlist.created_at,
            updated_at=watchlist.updated_at,
            assets=assets,
            shared_with_user_ids=watchlist.shared_with_user_ids if watchlist.shared_with_user_ids else None,
        )

    def share_watchlist(self, watchlist_id: str, user_id: str, shared_user_ids: list[str]) -> Watchlist:
        """Share a watchlist with specified users (viewers).
        
        Only admin/analyst can share watchlists. The shared_with_user_ids field
        will be updated with the list of user IDs.
        """
        watchlist = self.get_watchlist(watchlist_id, user_id)
        if not watchlist:
            raise ValueError("Watchlist not found")
        
        # Verify that the current user is admin or analyst
        from app.models.user import User, UserRole
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or user.role not in [UserRole.ADMIN, UserRole.ANALYST]:
            raise ValueError("Only admin or analyst users can share watchlists")
        
        # Update shared_with_user_ids
        db_watchlist = self.db.query(AssetWatchlist).filter(AssetWatchlist.id == watchlist_id).first()
        db_watchlist.shared_with_user_ids = shared_user_ids
        self.db.commit()
        self.db.refresh(db_watchlist)
        
        return self._to_watchlist_response(db_watchlist)
