"""Alert service - alert management and notifications."""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.models.alert import Alert, AlertSeverity, AlertType
from app.schemas.alert import (
    AlertCreate,
    AlertListResponse,
    AlertResponse,
    AlertStatsResponse,
    AlertUpdate,
)


class AlertService:
    """Alert service for managing alerts and notifications."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_alert(
        self,
        user_id: str,
        alert_data: AlertCreate,
    ) -> AlertResponse:
        """Create a new alert."""
        import json

        metadata_json_str = None
        if alert_data.metadata:
            try:
                metadata_json_str = json.dumps(alert_data.metadata)
            except (TypeError, ValueError):
                metadata_json_str = None

        alert = Alert(
            id=str(uuid4()),
            user_id=user_id,
            watchlist_id=alert_data.watchlist_id,
            asset_id=alert_data.asset_id,
            alert_type=alert_data.alert_type,
            severity=alert_data.severity,
            title=alert_data.title,
            message=alert_data.message,
            metadata_json=metadata_json_str,
            is_read=False,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return self._to_response(alert)

    def list_alerts(
        self,
        user_id: str,
        is_read: Optional[bool] = None,
        alert_type: Optional[AlertType] = None,
        severity: Optional[AlertSeverity] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> AlertListResponse:
        """List alerts for a user."""
        query = self.db.query(Alert).filter(Alert.user_id == user_id)

        if is_read is not None:
            query = query.filter(Alert.is_read == is_read)
        if alert_type:
            query = query.filter(Alert.alert_type == alert_type)
        if severity:
            query = query.filter(Alert.severity == severity)

        total = query.count()
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        alerts = (
            query.order_by(Alert.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return AlertListResponse(
            items=[self._to_response(alert) for alert in alerts],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def get_alert(self, alert_id: str, user_id: str) -> Optional[AlertResponse]:
        """Get alert by ID."""
        alert = (
            self.db.query(Alert)
            .filter(and_(Alert.id == alert_id, Alert.user_id == user_id))
            .first()
        )
        return self._to_response(alert) if alert else None

    def update_alert(
        self,
        alert_id: str,
        user_id: str,
        alert_data: AlertUpdate,
    ) -> Optional[AlertResponse]:
        """Update an alert."""
        alert = (
            self.db.query(Alert)
            .filter(and_(Alert.id == alert_id, Alert.user_id == user_id))
            .first()
        )
        if not alert:
            return None

        if alert_data.is_read is not None:
            alert.is_read = alert_data.is_read

        self.db.commit()
        self.db.refresh(alert)
        return self._to_response(alert)

    def mark_as_read(self, alert_id: str, user_id: str) -> Optional[AlertResponse]:
        """Mark an alert as read."""
        return self.update_alert(alert_id, user_id, AlertUpdate(is_read=True))

    def mark_as_unread(self, alert_id: str, user_id: str) -> Optional[AlertResponse]:
        """Mark an alert as unread."""
        return self.update_alert(alert_id, user_id, AlertUpdate(is_read=False))

    def mark_all_as_read(self, user_id: str) -> int:
        """Mark all alerts as read for a user."""
        from loguru import logger
        
        # Get count before update
        unread_count = (
            self.db.query(Alert)
            .filter(and_(Alert.user_id == user_id, Alert.is_read == False))
            .count()
        )
        
        logger.info(f"Marking all alerts as read for user {user_id}. Unread count: {unread_count}")
        
        # Update all unread alerts
        updated = (
            self.db.query(Alert)
            .filter(and_(Alert.user_id == user_id, Alert.is_read == False))
            .update({"is_read": True}, synchronize_session=False)
        )
        self.db.commit()
        
        logger.info(f"Marked {updated} alerts as read for user {user_id}")
        return updated

    def delete_alert(self, alert_id: str, user_id: str) -> bool:
        """Delete an alert."""
        alert = (
            self.db.query(Alert)
            .filter(and_(Alert.id == alert_id, Alert.user_id == user_id))
            .first()
        )
        if not alert:
            return False

        self.db.delete(alert)
        self.db.commit()
        return True

    def get_stats(self, user_id: str) -> AlertStatsResponse:
        """Get alert statistics for a user."""
        query = self.db.query(Alert).filter(Alert.user_id == user_id)

        total = query.count()
        unread = query.filter(Alert.is_read == False).count()

        # By severity
        by_severity = {}
        for severity in AlertSeverity:
            count = query.filter(Alert.severity == severity).count()
            by_severity[severity.value] = count

        # By type
        by_type = {}
        for alert_type in AlertType:
            count = query.filter(Alert.alert_type == alert_type).count()
            by_type[alert_type.value] = count

        return AlertStatsResponse(
            total=total,
            unread=unread,
            by_severity=by_severity,
            by_type=by_type,
        )

    def _to_response(self, alert: Alert) -> AlertResponse:
        """Convert Alert model to response schema."""
        import json

        metadata = None
        if alert.metadata_json:
            try:
                # metadata_json is already a JSON string, parse it
                if isinstance(alert.metadata_json, str):
                    metadata = json.loads(alert.metadata_json)
                else:
                    metadata = alert.metadata_json
            except (json.JSONDecodeError, TypeError) as e:
                # If parsing fails, return None
                metadata = None

        return AlertResponse(
            id=str(alert.id),
            user_id=str(alert.user_id),
            watchlist_id=str(alert.watchlist_id) if alert.watchlist_id else None,
            asset_id=str(alert.asset_id) if alert.asset_id else None,
            alert_type=alert.alert_type,
            severity=alert.severity,
            title=alert.title,
            message=alert.message,
            metadata=metadata,
            is_read=alert.is_read,
            created_at=alert.created_at,
        )

