"""IOC Service - Real API integration for threat intelligence queries."""

import asyncio
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.encryption import decrypt_value
from app.models.api_source import APISource, APIKey, UpdateMode, AuthenticationType
from app.models.ioc_query import IOCQuery, ThreatIntelligenceData
from app.schemas.ioc import IOCQueryRequest, IOCQueryResponse, IOCSourceResult
from app.services.cache import ioc_cache
from app.services.redis_cache import redis_cache
from app.services.dynamic_api_client import DynamicAPIClient
from loguru import logger


class IOCService:
    """Service for IOC queries with real API integrations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _get_risk_score_from_level(self, risk_level: Optional[str]) -> Optional[float]:
        """Convert risk level string to numeric score."""
        if not risk_level:
            return None
        risk_map = {"high": 0.9, "medium": 0.6, "low": 0.3, "clean": 0.1, "unknown": 0.5}
        return risk_map.get(risk_level.lower())

    def _calculate_overall_risk(self, results: list[IOCSourceResult]) -> Optional[str]:
        """Calculate overall risk score from source results."""
        if not results:
            return None

        # Filter out None risk scores and non-success statuses
        valid_results = [r for r in results if r.risk_score is not None and r.status == "success"]
        if not valid_results:
            # If no valid results, check if any non-success responses occurred (error, timeout, etc.)
            non_success_results = [r for r in results if r.status != "success"]
            if non_success_results:
                return "unknown"  # Can't determine risk due to unsuccessful queries
            return None

        # Calculate average risk score
        risk_scores = [r.risk_score for r in valid_results]
        avg_score = sum(risk_scores) / len(risk_scores)

        # Convert to risk level
        if avg_score >= 0.8:
            return "high"
        elif avg_score >= 0.5:
            return "medium"
        elif avg_score >= 0.2:
            return "low"
        else:
            return "clean"

    def _get_active_api_keys(self, sources: Optional[list[str]] = None, auto_mode_only: bool = False) -> list[tuple[APIKey, APISource]]:
        """Get active API keys for specified sources (or all active sources).
        
        Args:
            sources: Optional list of source names to filter by
            auto_mode_only: If True, only return API keys with update_mode='auto'. 
                          Used for scheduled/automatic queries to respect user preferences.
        """
        query = (
            self.db.query(APIKey, APISource)
            .join(APISource, APIKey.api_source_id == APISource.id)
            .filter(APIKey.is_active == True)
            .filter(APISource.is_active == True)
        )
        
        # For automatic/scheduled queries, only use API keys with update_mode='auto'
        # This prevents API quota exhaustion for keys that should only be used manually
        if auto_mode_only:
            query = query.filter(APIKey.update_mode == UpdateMode.AUTO)

        if sources:
            # Filter by source names (case-insensitive)
            source_names = [s.lower() for s in sources]
            query = query.filter(APISource.name.in_([s for s in source_names]))

        return query.all()

    def _get_sources_without_auth(self, sources: Optional[list[str]] = None) -> list[APISource]:
        """Get active API sources that don't require authentication (no API key needed).
        
        Args:
            sources: Optional list of source names to filter by
        """
        query = (
            self.db.query(APISource)
            .filter(APISource.is_active == True)
            .filter(APISource.authentication_type == AuthenticationType.NONE)
        )

        if sources:
            # Filter by source names (case-insensitive)
            source_names = [s.lower() for s in sources]
            query = query.filter(APISource.name.in_([s for s in source_names]))

        return query.all()

    def _query_single_source(
        self, api_key: APIKey, api_source: APISource, ioc_type: str, ioc_value: str
    ) -> IOCSourceResult:
        """Query a single threat intelligence source."""
        try:
            # Check if IOC type is supported
            if api_source.supported_ioc_types and ioc_type.lower() not in [
                t.lower() for t in api_source.supported_ioc_types
            ]:
                return IOCSourceResult(
                    source=api_source.name,
                    status="skipped",
                    risk_score=None,
                    description=f"IOC type '{ioc_type}' not supported by {api_source.display_name}",
                    raw=None,
                )

            # Decrypt API key (only if authentication is required)
            # Check authentication_type from the enum value
            auth_type_value = api_source.authentication_type.value if hasattr(api_source.authentication_type, 'value') else str(api_source.authentication_type)
            requires_auth = auth_type_value.lower() != "none"
            decrypted_key = None
            
            if requires_auth:
                # Only decrypt if API key exists and is not empty
                if api_key.api_key and api_key.api_key.strip():
                    decrypted_key = decrypt_value(api_key.api_key)
                    # Check if decryption was successful (decrypted value should not be empty for auth-required APIs)
                    if not decrypted_key or not decrypted_key.strip():
                        return IOCSourceResult(
                            source=api_source.name,
                            status="error",
                            risk_score=None,
                            description="Failed to decrypt API key or API key is empty",
                            raw=None,
                        )
                else:
                    return IOCSourceResult(
                        source=api_source.name,
                        status="error",
                        risk_score=None,
                        description="API key is required for this API source",
                        raw=None,
                    )
            else:
                # For APIs that don't require authentication, use empty string
                # Don't try to decrypt, just use empty string
                # Even if there's an encrypted empty string in the database, we ignore it
                decrypted_key = ""

            # Decrypt username and password if available
            # Only decrypt if they exist and are not empty
            decrypted_username = None
            if api_key.username and api_key.username.strip():
                try:
                    decrypted_username = decrypt_value(api_key.username)
                    # If decrypted value is empty, set to None
                    if not decrypted_username or not decrypted_username.strip():
                        decrypted_username = None
                except Exception as e:
                    logger.warning(f"Failed to decrypt username for {api_source.name}: {e}")
                    decrypted_username = None
            
            decrypted_password = None
            if api_key.password and api_key.password.strip():
                try:
                    decrypted_password = decrypt_value(api_key.password)
                    # If decrypted value is empty, set to None
                    if not decrypted_password or not decrypted_password.strip():
                        decrypted_password = None
                except Exception as e:
                    logger.warning(f"Failed to decrypt password for {api_source.name}: {e}")
                    decrypted_password = None

            # Create dynamic API client
            client = DynamicAPIClient(
                api_source=api_source,
                api_key=decrypted_key,
                username=decrypted_username,
                password=decrypted_password,
                api_url_override=api_key.api_url,
            )

            # Make API call
            result = client.query(ioc_type=ioc_type, ioc_value=ioc_value, timeout=30)

            # Update API key last_used timestamp
            api_key.last_used = datetime.now(timezone.utc)
            self.db.commit()

            # Extract data from result
            status = result.get("status", "error")
            risk_score = result.get("risk_score")
            raw_data = result.get("raw")
            data = result.get("data", {})
            
            # Special handling for Kaspersky API - convert Zone to risk score
            if api_source.name == "kaspersky" and isinstance(risk_score, str):
                zone_to_score = {
                    "Red": 0.9,      # High risk
                    "Yellow": 0.6,   # Medium risk
                    "Green": 0.3,    # Low risk
                    "White": 0.1,    # Clean
                    "Grey": 0.1,     # Clean/Unknown
                }
                risk_score = zone_to_score.get(risk_score, 0.5)  # Default to 0.5 for unknown zones

            # Build description from data
            description = None
            if isinstance(data, dict):
                # Try to extract meaningful description
                description_parts = []
                if "description" in data:
                    description_parts.append(str(data["description"]))
                if "status" in data:
                    description_parts.append(f"Status: {data['status']}")
                if description_parts:
                    description = " | ".join(description_parts)

            return IOCSourceResult(
                source=api_source.name,
                status=status,
                risk_score=float(risk_score) if risk_score is not None else None,
                description=description or f"Query completed with status: {status}",
                raw=raw_data,
            )

        except Exception as e:
            logger.error(f"Error querying {api_source.name} for {ioc_type}:{ioc_value}: {e}")
            return IOCSourceResult(
                source=api_source.name,
                status="error",
                risk_score=None,
                description=f"Error: {str(e)}",
                raw=None,
            )

    def _query_single_source_without_key(
        self, api_source: APISource, ioc_type: str, ioc_value: str
    ) -> IOCSourceResult:
        """Query a single threat intelligence source without API key (for APIs that don't require authentication)."""
        try:
            # Check if IOC type is supported
            if api_source.supported_ioc_types and ioc_type.lower() not in [
                t.lower() for t in api_source.supported_ioc_types
            ]:
                return IOCSourceResult(
                    source=api_source.name,
                    status="skipped",
                    risk_score=None,
                    description=f"IOC type '{ioc_type}' not supported by {api_source.display_name}",
                    raw=None,
                )

            # For APIs that don't require authentication, use empty string as API key
            decrypted_key = ""
            decrypted_username = None
            decrypted_password = None

            # Create dynamic API client
            client = DynamicAPIClient(
                api_source=api_source,
                api_key=decrypted_key,
                username=decrypted_username,
                password=decrypted_password,
                api_url_override=None,
            )

            # Make API call
            result = client.query(ioc_type=ioc_type, ioc_value=ioc_value, timeout=30)

            # Extract data from result
            status = result.get("status", "error")
            risk_score = result.get("risk_score")
            raw_data = result.get("raw")
            data = result.get("data", {})

            # Build description from data
            description = None
            if isinstance(data, dict):
                # Try to extract meaningful description
                description_parts = []
                if "description" in data:
                    description_parts.append(str(data["description"]))
                if "status" in data:
                    description_parts.append(f"Status: {data['status']}")
                if description_parts:
                    description = " | ".join(description_parts)

            return IOCSourceResult(
                source=api_source.name,
                status=status,
                risk_score=float(risk_score) if risk_score is not None else None,
                description=description or f"Query completed with status: {status}",
                raw=raw_data,
            )

        except Exception as e:
            logger.error(f"Error querying {api_source.name} for {ioc_type}:{ioc_value}: {e}")
            return IOCSourceResult(
                source=api_source.name,
                status="error",
                risk_score=None,
                description=f"Error: {str(e)}",
                raw=None,
            )

    def query_ioc(self, user_id: str, payload: IOCQueryRequest, auto_mode_only: bool = False) -> IOCQueryResponse:
        """Query IOC across multiple threat intelligence sources.
        
        Args:
            user_id: User ID performing the query
            payload: IOC query request
            auto_mode_only: If True, only use API keys with update_mode='auto'. 
                          Used for scheduled/automatic queries to respect user preferences.
        """
        # Check Redis cache first
        redis_key = f"ioc:{payload.ioc_type.lower()}:{payload.ioc_value.lower()}"
        cached_data = redis_cache.get(redis_key)
        if cached_data:
            logger.info(f"Redis cache hit for {payload.ioc_type}:{payload.ioc_value}")
            try:
                return IOCQueryResponse(**cached_data)
            except Exception as e:
                logger.warning(f"Failed to parse cached IOC data: {e}")
        
        # Check in-memory cache as fallback
        cached_response = ioc_cache.get(payload.ioc_type, payload.ioc_value)
        if cached_response:
            logger.info(f"In-memory cache hit for {payload.ioc_type}:{payload.ioc_value}")
            # Save to Redis cache for future use
            try:
                redis_cache.set(redis_key, cached_response.dict(), ttl=300)  # 5 minutes
            except Exception as e:
                logger.warning(f"Failed to save IOC to Redis cache: {e}")
            return cached_response

        # Get active API keys for requested sources
        # For automatic queries, only use keys with update_mode='auto' to prevent quota exhaustion
        api_key_sources = self._get_active_api_keys(payload.sources, auto_mode_only=auto_mode_only)

        # Also get API sources that don't require authentication (no API key needed)
        sources_without_keys = self._get_sources_without_auth(payload.sources)
        
        # Combine both: sources with API keys and sources without authentication
        all_sources_to_query: list[tuple[APIKey | None, APISource]] = []
        
        # Add sources with API keys
        for api_key, api_source in api_key_sources:
            all_sources_to_query.append((api_key, api_source))
        
        # Add sources without authentication (no API key needed)
        for api_source in sources_without_keys:
            # Check if this source is already in the list (to avoid duplicates)
            if not any(source.id == api_source.id for _, source in all_sources_to_query):
                all_sources_to_query.append((None, api_source))

        if not all_sources_to_query:
            # No active API keys or sources found
            return IOCQueryResponse(
                ioc_type=payload.ioc_type,
                ioc_value=payload.ioc_value,
                overall_risk=None,
                queried_sources=[
                    IOCSourceResult(
                        source="system",
                        status="error",
                        risk_score=None,
                        description="No active API keys or sources found for the requested sources",
                        raw=None,
                    )
                ],
                queried_at=datetime.now(timezone.utc),
            )

        # Query all sources
        results: list[IOCSourceResult] = []
        for api_key, api_source in all_sources_to_query:
            if api_key is None:
                # For sources without authentication, create a dummy API key object
                # We'll handle this in _query_single_source
                result = self._query_single_source_without_key(api_source, payload.ioc_type, payload.ioc_value)
            else:
                result = self._query_single_source(api_key, api_source, payload.ioc_type, payload.ioc_value)
            results.append(result)

        # Calculate overall risk
        overall_risk = self._calculate_overall_risk(results)

        # Build response
        response = IOCQueryResponse(
            ioc_type=payload.ioc_type,
            ioc_value=payload.ioc_value,
            overall_risk=overall_risk,
            queried_sources=results,
            queried_at=datetime.now(timezone.utc),
        )

        # Cache the response
        ioc_cache.set(response)
        # Save to Redis cache
        try:
            redis_cache.set(redis_key, response.dict(), ttl=300)  # 5 minutes
        except Exception as e:
            logger.warning(f"Failed to save IOC to Redis cache: {e}")

        # Save to database
        self._save_query_to_db(user_id, payload, response)

        return response

    def _save_query_to_db(self, user_id: str, payload: IOCQueryRequest, response: IOCQueryResponse) -> None:
        """Save IOC query results to database."""
        try:
            # Create IOCQuery record
            ioc_query = IOCQuery(
                id=str(uuid4()),
                user_id=user_id,
                ioc_type=payload.ioc_type,
                ioc_value=payload.ioc_value,
                query_date=response.queried_at,
                results_json={
                    "overall_risk": response.overall_risk,
                    "queried_sources": [r.dict() for r in response.queried_sources],
                },
                risk_score=self._get_risk_score_from_level(response.overall_risk) if response.overall_risk else None,
                status=response.overall_risk or "pending",
            )
            self.db.add(ioc_query)
            self.db.flush()  # Flush to get the ID

            # Create ThreatIntelligenceData records for each source
            for source_result in response.queried_sources:
                # Get API source for this result
                api_source = self.db.query(APISource).filter(APISource.name == source_result.source).first()
                if not api_source:
                    continue

                threat_data = ThreatIntelligenceData(
                    id=str(uuid4()),
                    ioc_query_id=ioc_query.id,
                    source_api=source_result.source,
                    raw_data_json=source_result.raw,
                    processed_data_json={
                        "status": source_result.status,
                        "risk_score": source_result.risk_score,
                        "description": source_result.description,
                    },
                    confidence_score=source_result.risk_score,
                    tags=None,  # Can be extracted from raw_data_json in the future
                )
                self.db.add(threat_data)

            self.db.commit()
            logger.info(f"Saved IOC query to database: {payload.ioc_type}:{payload.ioc_value}")

        except Exception as e:
            logger.error(f"Failed to save IOC query to database: {e}")
            self.db.rollback()

    def list_query_history(
        self,
        user_id: str,
        user_role: Optional[str] = None,
        ioc_type: Optional[str] = None,
        ioc_value: Optional[str] = None,
        risk_level: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        source: Optional[str] = None,
        watchlist_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """List IOC query history with filters and pagination.
        
        For admin/analyst: Returns all their own IOC queries.
        For viewer: Returns IOC queries from watchlists shared with them.
        """
        from sqlalchemy import and_, or_, distinct
        from sqlalchemy.orm import Query
        from app.models.ioc_query import ThreatIntelligenceData, IOCQuery
        from app.models.watchlist import AssetWatchlistItem, AssetWatchlist
        from app.models.user import UserRole
        import json

        # For viewer users, we need to get IOC queries from shared watchlists
        # We'll get watchlist items from shared watchlists and match them with IOC queries
        if user_role == UserRole.VIEWER.value:
            # Get shared watchlists for viewer
            all_watchlists = self.db.query(AssetWatchlist).filter(
                AssetWatchlist.is_active == True
            ).all()
            
            shared_watchlist_ids = []
            for w in all_watchlists:
                # Check if user is owner
                if w.user_id == user_id:
                    shared_watchlist_ids.append(w.id)
                    continue
                
                # Check if user is in shared_with_user_ids
                shared_ids = w.shared_with_user_ids
                if shared_ids is not None:
                    if isinstance(shared_ids, str):
                        try:
                            shared_ids = json.loads(shared_ids)
                        except (json.JSONDecodeError, TypeError):
                            shared_ids = None
                    
                    if isinstance(shared_ids, list) and len(shared_ids) > 0 and user_id in shared_ids:
                        shared_watchlist_ids.append(w.id)
            
            # Get IOC queries from watchlist check history for shared watchlists
            # We'll use AssetWatchlistItem to find IOC values, then match with IOCQuery
            if shared_watchlist_ids:
                watchlist_items = (
                    self.db.query(AssetWatchlistItem)
                    .filter(AssetWatchlistItem.watchlist_id.in_(shared_watchlist_ids))
                    .all()
                )
                
                # Create list of (ioc_type, ioc_value) tuples
                ioc_pairs = [(item.ioc_type, item.ioc_value) for item in watchlist_items]
                
                if ioc_pairs:
                    # Build OR conditions for matching IOC queries
                    or_conditions = [
                        and_(
                            IOCQuery.ioc_type == ioc_type,
                            IOCQuery.ioc_value == ioc_value
                        )
                        for ioc_type, ioc_value in ioc_pairs
                    ]
                    
                    # Base query for viewer - IOC queries matching shared watchlist items
                    # Use or_ with conditions, or return empty if no conditions
                    if or_conditions:
                        base_query = self.db.query(IOCQuery).filter(or_(*or_conditions))
                    else:
                        # No conditions, return empty result
                        return {
                            "items": [],
                            "total": 0,
                            "page": page,
                            "page_size": page_size,
                            "total_pages": 0,
                        }
                else:
                    # No watchlist items, return empty result
                    return {
                        "items": [],
                        "total": 0,
                        "page": page,
                        "page_size": page_size,
                        "total_pages": 0,
                    }
            else:
                # No shared watchlists, return empty result
                return {
                    "items": [],
                    "total": 0,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": 0,
                }
        else:
            # For admin/analyst, use existing logic - only user's own queries
            base_query = self.db.query(IOCQuery).filter(IOCQuery.user_id == user_id)

        # Apply filters based on source and watchlist_id
        # For viewer, base_query is already filtered to shared watchlist IOC queries
        # For admin/analyst, base_query is filtered to user's own queries
        if source and watchlist_id:
            # Both source and watchlist filters
            query = (
                base_query
                .join(
                    ThreatIntelligenceData,
                    IOCQuery.id == ThreatIntelligenceData.ioc_query_id
                )
                .join(
                    AssetWatchlistItem,
                    and_(
                        IOCQuery.ioc_type == AssetWatchlistItem.ioc_type,
                        IOCQuery.ioc_value == AssetWatchlistItem.ioc_value
                    )
                )
                .filter(ThreatIntelligenceData.source_api.ilike(f"%{source}%"))
                .filter(AssetWatchlistItem.watchlist_id == watchlist_id)
                .distinct()
            )
        elif source:
            query = (
                base_query
                .join(
                    ThreatIntelligenceData,
                    IOCQuery.id == ThreatIntelligenceData.ioc_query_id
                )
                .filter(ThreatIntelligenceData.source_api.ilike(f"%{source}%"))
                .distinct()
            )
        elif watchlist_id:
            # Join with watchlist items to filter by watchlist
            # For viewer, also check if watchlist is shared with them
            if user_role == UserRole.VIEWER.value:
                # Verify watchlist is shared with viewer
                watchlist = self.db.query(AssetWatchlist).filter(
                    AssetWatchlist.id == watchlist_id
                ).first()
                if not watchlist:
                    return {
                        "items": [],
                        "total": 0,
                        "page": page,
                        "page_size": page_size,
                        "total_pages": 0,
                    }
                
                # Check if watchlist is shared with viewer
                is_shared = False
                if watchlist.user_id == user_id:
                    is_shared = True
                else:
                    shared_ids = watchlist.shared_with_user_ids
                    if shared_ids is not None:
                        if isinstance(shared_ids, str):
                            try:
                                shared_ids = json.loads(shared_ids)
                            except (json.JSONDecodeError, TypeError):
                                shared_ids = None
                        
                        if isinstance(shared_ids, list) and len(shared_ids) > 0 and user_id in shared_ids:
                            is_shared = True
                
                if not is_shared:
                    return {
                        "items": [],
                        "total": 0,
                        "page": page,
                        "page_size": page_size,
                        "total_pages": 0,
                    }
            
            query = (
                base_query
                .join(
                    AssetWatchlistItem,
                    and_(
                        IOCQuery.ioc_type == AssetWatchlistItem.ioc_type,
                        IOCQuery.ioc_value == AssetWatchlistItem.ioc_value
                    )
                )
                .filter(AssetWatchlistItem.watchlist_id == watchlist_id)
                .distinct()
            )
        else:
            # Use base_query which is already filtered for viewer/admin/analyst
            query = base_query

        # Apply filters
        if ioc_type:
            query = query.filter(IOCQuery.ioc_type == ioc_type.lower())
        if ioc_value:
            query = query.filter(IOCQuery.ioc_value.ilike(f"%{ioc_value}%"))
        if risk_level:
            # Filter by risk level - check both status field and risk_score ranges
            # status field stores the risk level (high, medium, low, clean, unknown, pending)
            # risk_score is numeric (0.0-1.0)
            risk_level_lower = risk_level.lower()
            
            if risk_level_lower == "critical":
                # Critical: risk_score >= 0.8 OR status = "high" OR status = "critical"
                query = query.filter(
                    or_(
                        IOCQuery.risk_score >= 0.8,
                        IOCQuery.status.ilike("high"),
                        IOCQuery.status.ilike("critical")
                    )
                )
            elif risk_level_lower == "high":
                # High: risk_score >= 0.5 AND risk_score < 0.8 OR status = "high"
                query = query.filter(
                    or_(
                        and_(IOCQuery.risk_score >= 0.5, IOCQuery.risk_score < 0.8),
                        IOCQuery.status.ilike("high")
                    )
                )
            elif risk_level_lower == "medium":
                # Medium: risk_score >= 0.2 AND risk_score < 0.5 OR status = "medium"
                query = query.filter(
                    or_(
                        and_(IOCQuery.risk_score >= 0.2, IOCQuery.risk_score < 0.5),
                        IOCQuery.status.ilike("medium")
                    )
                )
            elif risk_level_lower == "low":
                # Low: risk_score >= 0.0 AND risk_score < 0.2 OR status = "low" OR status = "clean"
                query = query.filter(
                    or_(
                        and_(IOCQuery.risk_score >= 0.0, IOCQuery.risk_score < 0.2),
                        IOCQuery.status.ilike("low"),
                        IOCQuery.status.ilike("clean")
                    )
                )
            elif risk_level_lower == "unknown":
                # Unknown: risk_score IS NULL OR status = "unknown" OR status = "pending"
                query = query.filter(
                    or_(
                        IOCQuery.risk_score.is_(None),
                        IOCQuery.status.ilike("unknown"),
                        IOCQuery.status.ilike("pending")
                    )
                )
            else:
                # Fallback: try status field match
                query = query.filter(IOCQuery.status.ilike(risk_level_lower))
        if start_date:
            query = query.filter(IOCQuery.query_date >= start_date)
        if end_date:
            query = query.filter(IOCQuery.query_date <= end_date)

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        queries = query.order_by(IOCQuery.query_date.desc()).offset(offset).limit(page_size).all()

        # Calculate total pages
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        # Convert to response format
        items = []
        for q in queries:
            # Extract queried_sources from results_json
            queried_sources = None
            if q.results_json and isinstance(q.results_json, dict):
                sources_data = q.results_json.get("queried_sources", [])
                if sources_data:
                    queried_sources = [IOCSourceResult(**source) for source in sources_data if isinstance(source, dict)]
            
            items.append({
                "id": q.id,
                "ioc_type": q.ioc_type,
                "ioc_value": q.ioc_value,
                "risk_score": q.risk_score,
                "status": q.status,
                "query_date": q.query_date,
                "created_at": q.created_at,
                "queried_sources": queried_sources,
            })

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    def get_query_detail(self, query_id: str, user_id: str) -> Optional[dict]:
        """Get detailed IOC query information."""
        # Get query
        query = self.db.query(IOCQuery).filter(IOCQuery.id == query_id).first()
        if not query:
            return None

        # Check if user owns the query (or is admin)
        if query.user_id != user_id:
            # Check if user is admin
            from app.models.user import User
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user or user.role.value != "admin":
                return None

        # Get threat intelligence data
        threat_data = (
            self.db.query(ThreatIntelligenceData)
            .filter(ThreatIntelligenceData.ioc_query_id == query_id)
            .all()
        )

        return {
            "id": query.id,
            "ioc_type": query.ioc_type,
            "ioc_value": query.ioc_value,
            "risk_score": query.risk_score,
            "status": query.status,
            "query_date": query.query_date,
            "results": query.results_json or {},
            "threat_intelligence_data": [
                {
                    "id": td.id,
                    "source_api": td.source_api,
                    "raw_data_json": td.raw_data_json,
                    "processed_data_json": td.processed_data_json,
                    "confidence_score": td.confidence_score,
                    "tags": td.tags,
                    "created_at": td.created_at,
                }
                for td in threat_data
            ],
            "created_at": query.created_at,
        }
