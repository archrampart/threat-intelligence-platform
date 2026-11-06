"""Report service - IOC query report generation."""

import json
from html import escape as _esc
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.ioc_query import IOCQuery, ThreatIntelligenceData
from app.models.report import Report, ReportFormat
from app.schemas.report import ReportCreate, ReportUpdate
from loguru import logger




def _csv_safe(value) -> str:
    """Neutralise spreadsheet formula injection (CWE-1236)."""
    text = "" if value is None else str(value)
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text

class ReportService:
    """Report service for creating and managing IOC query reports."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_report(self, user_id: str, report_data: ReportCreate) -> Report:
        """Create a new report from IOC queries."""
        try:
            # Validate format
            format_upper = report_data.format.upper()
            if format_upper not in [f.value for f in ReportFormat]:
                raise ValueError(f"Invalid report format: {report_data.format}. Must be one of: PDF, HTML, JSON")
            
            if report_data.report_type == "darkweb":
                return self._create_darkweb_report(user_id, report_data, format_upper)

            # Get IOC query IDs based on filters or provided IDs
            ioc_query_ids = report_data.ioc_query_ids or []
            
            # If filters are provided but no specific query IDs, fetch queries based on filters
            has_filters = (
                report_data.watchlist_id or 
                report_data.ioc_type or 
                report_data.risk_level or 
                report_data.start_date or 
                report_data.end_date or 
                report_data.source
            )
            
            if not ioc_query_ids and has_filters:
                from app.services.ioc_service import IOCService
                from app.models.user import User
                
                # Get user role
                user = self.db.query(User).filter(User.id == user_id).first()
                user_role = user.role.value if user and hasattr(user.role, 'value') else "admin"
                
                # Log filter parameters for debugging
                logger.info(f"Creating report with filters - user_id: {user_id}, risk_level: {report_data.risk_level}, "
                          f"ioc_type: {report_data.ioc_type}, watchlist_id: {report_data.watchlist_id}, "
                          f"start_date: {report_data.start_date}, end_date: {report_data.end_date}, source: {report_data.source}")
                
                # Use IOC service to get filtered queries
                ioc_service = IOCService(self.db)
                result = ioc_service.list_query_history(
                    user_id=user_id,
                    user_role=user_role,
                    ioc_type=report_data.ioc_type,
                    ioc_value=None,  # Not filtering by value in report creation
                    risk_level=report_data.risk_level,
                    start_date=report_data.start_date,
                    end_date=report_data.end_date,
                    source=report_data.source,
                    watchlist_id=report_data.watchlist_id,
                    page=1,
                    page_size=10000,  # Get all matching queries
                )
                
                # Extract query IDs from result
                ioc_query_ids = [item["id"] for item in result.get("items", [])]
                logger.info(f"Found {len(ioc_query_ids)} IOC queries matching filters")
            
            elif not ioc_query_ids:
                # No filters and no IDs provided - fetch recent history by default (limit 100)
                from app.services.ioc_service import IOCService
                from app.models.user import User
                
                user = self.db.query(User).filter(User.id == user_id).first()
                user_role = user.role.value if user and hasattr(user.role, 'value') else "admin"
                
                logger.info(f"No filters provided for report. Fetching last 100 queries for user {user_id}")
                
                ioc_service = IOCService(self.db)
                result = ioc_service.list_query_history(
                    user_id=user_id,
                    user_role=user_role,
                    page=1,
                    page_size=100, 
                )
                ioc_query_ids = [item["id"] for item in result.get("items", [])]
            
            # Generate report data (dict format)
            report_data_dict = self._generate_report_data(user_id, ioc_query_ids)
            
            # Add title and description to report data for HTML/PDF generation
            report_data_dict["title"] = report_data.title
            report_data_dict["description"] = report_data.description

            spec: dict = {"type": "ioc", "include_darkweb": bool(report_data.include_darkweb)}
            if report_data.include_darkweb:
                mention_ids = self._select_mentions(user_id, report_data)
                spec["darkweb"] = self._darkweb_spec(report_data, mention_ids)
                report_data_dict["darkweb"] = self._darkweb_data(user_id, spec["darkweb"])
            
            # Generate content based on format
            format_enum = ReportFormat(format_upper)
            if format_enum == ReportFormat.HTML:
                content = self._generate_html_content(report_data_dict)
            elif format_enum == ReportFormat.PDF:
                # For PDF, we'll store as base64 encoded string
                import base64
                pdf_bytes = self._generate_pdf_content(report_data_dict)
                content = base64.b64encode(pdf_bytes).decode('utf-8')
            else:  # JSON
                content = json.dumps(report_data_dict, indent=2)

            # Create report
            report = Report(
                id=str(uuid4()),
                user_id=user_id,
                title=report_data.title,
                description=report_data.description,
                content=content,
                format=format_enum,
                # Store the resolved ids so the report can be re-rendered in any format later
                ioc_query_ids=ioc_query_ids,
                report_spec=spec,
            )

            self.db.add(report)
            self.db.commit()
            self.db.refresh(report)

            return report
        except ValueError as e:
            self.db.rollback()
            logger.error(f"Validation error creating report: {e}")
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating report: {e}")
            raise

    def get_report(self, report_id: str, user_id: str) -> Optional[Report]:
        """Get a report by ID."""
        report = self.db.query(Report).filter(Report.id == report_id).first()
        if not report:
            return None

        # Check if user owns the report (or is admin)
        if report.user_id != user_id:
            from app.models.user import User

            user = self.db.query(User).filter(User.id == user_id).first()
            if not user or user.role.value != "admin":
                return None

        return report

    def list_reports(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> dict:
        """List reports for a user with pagination.
        
        For admin/analyst: Returns only their own reports.
        For viewer: Returns their own reports (if any) + reports shared with them.
        """
        from sqlalchemy import or_
        from app.models.user import UserRole

        # Get user role if not provided
        if user_role is None:
            from app.models.user import User
            user = self.db.query(User).filter(User.id == user_id).first()
            user_role = user.role.value if user else None

        # Base query
        query = self.db.query(Report)
        
        # For viewer users, include both their own reports and shared ones
        if user_role == UserRole.VIEWER.value:
            # Get reports where user is owner OR user is in shared_with_user_ids
            # For SQLite, we need to filter in Python since JSON array queries are complex
            # For PostgreSQL, we could use JSONB operators, but for simplicity, we'll use Python filtering for both
            import json
            all_reports = self.db.query(Report).all()
            reports = []
            for r in all_reports:
                # Check if user is owner
                if r.user_id == user_id:
                    reports.append(r)
                    continue
                
                # Check if user is in shared_with_user_ids
                shared_ids = r.shared_with_user_ids
                if shared_ids is not None:
                    # Handle both string (SQLite JSON) and list (already parsed) formats
                    if isinstance(shared_ids, str):
                        try:
                            shared_ids = json.loads(shared_ids)
                        except (json.JSONDecodeError, TypeError):
                            shared_ids = None
                    
                    if isinstance(shared_ids, list) and len(shared_ids) > 0 and user_id in shared_ids:
                        reports.append(r)
            # Apply search filter if provided
            if search:
                reports = [
                    r for r in reports
                    if search.lower() in (r.title or "").lower() or 
                    search.lower() in (r.description or "").lower()
                ]
            # Apply pagination
            total = len(reports)
            offset = (page - 1) * page_size
            paginated_reports = reports[offset:offset + page_size]
            total_pages = (total + page_size - 1) // page_size
            
            return {
                "items": [self._to_response(r) for r in paginated_reports],
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
            }
        else:
            # For admin/analyst, only show their own reports
            query = query.filter(Report.user_id == user_id)

        # Search filter
        if search:
            query = query.filter(
                or_(
                    Report.title.ilike(f"%{search}%"),
                    Report.description.ilike(f"%{search}%"),
                )
            )

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        reports = query.order_by(Report.created_at.desc()).offset(offset).limit(page_size).all()

        # Calculate total pages
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return {
            "items": [self._to_response(r) for r in reports],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    def update_report(self, report_id: str, user_id: str, report_data: ReportUpdate) -> Optional[Report]:
        """Update a report."""
        report = self.get_report(report_id, user_id)
        if not report:
            return None

        if report_data.title is not None:
            report.title = report_data.title
        if report_data.description is not None:
            report.description = report_data.description
        if report_data.format is not None:
            report.format = ReportFormat(report_data.format.upper())

        self.db.commit()
        self.db.refresh(report)

        return report

    def delete_report(self, report_id: str, user_id: str) -> bool:
        """Delete a report."""
        report = self.get_report(report_id, user_id)
        if not report:
            return False

        self.db.delete(report)
        self.db.commit()
        return True

    # ------------------------------------------------------------------ dark web

    def _select_mentions(self, user_id: str, report_data: ReportCreate) -> list[str]:
        from app.models.darkweb import DarkWebMention

        query = self.db.query(DarkWebMention.id).filter(DarkWebMention.user_id == user_id)
        if report_data.start_date:
            query = query.filter(DarkWebMention.created_at >= report_data.start_date)
        if report_data.end_date:
            query = query.filter(DarkWebMention.created_at <= report_data.end_date)
        if report_data.darkweb_sources:
            query = query.filter(DarkWebMention.source.in_(report_data.darkweb_sources))
        if report_data.darkweb_min_severity:
            order = ["critical", "high", "medium", "low"]
            allowed = order[: order.index(report_data.darkweb_min_severity) + 1]
            query = query.filter(DarkWebMention.severity.in_(allowed))
        return [mid for (mid,) in query.order_by(DarkWebMention.created_at.desc()).limit(2000).all()]

    @staticmethod
    def _darkweb_spec(report_data: ReportCreate, mention_ids: list[str]) -> dict:
        return {
            "mention_ids": mention_ids,
            "start": report_data.start_date.isoformat() if report_data.start_date else None,
            "end": report_data.end_date.isoformat() if report_data.end_date else None,
            "sources": report_data.darkweb_sources,
            "min_severity": report_data.darkweb_min_severity,
        }

    def _darkweb_data(self, owner_id: str, spec: dict) -> dict:
        """Serialised mentions + monitored assets of the report owner (for rendering and JSON export)."""
        from app.models.darkweb import DarkWebMention, MonitoredAsset

        ids = spec.get("mention_ids") or []
        mentions = (
            self.db.query(DarkWebMention).filter(DarkWebMention.user_id == owner_id, DarkWebMention.id.in_(ids)).all()
            if ids else []
        )
        assets = self.db.query(MonitoredAsset).filter(MonitoredAsset.user_id == owner_id).all()

        def iso(value):
            return value.isoformat() if value else None

        return {
            "start": spec.get("start"),
            "end": spec.get("end"),
            "assets": [{"kind": a.kind, "value": a.value} for a in assets],
            "mentions": [
                {
                    "id": m.id, "source": m.source, "severity": m.severity, "matched_term": m.matched_term,
                    "title": m.title, "snippet": m.snippet, "url": m.url, "actor": m.actor,
                    "published_at": iso(m.published_at), "created_at": iso(m.created_at), "is_read": m.is_read,
                }
                for m in mentions
            ],
        }

    def _create_darkweb_report(self, user_id: str, report_data: ReportCreate, format_upper: str) -> Report:
        import base64

        spec = {"type": "darkweb", "darkweb": self._darkweb_spec(report_data, self._select_mentions(user_id, report_data))}
        data = {
            "kind": "darkweb",
            "title": report_data.title,
            "description": report_data.description,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "darkweb": self._darkweb_data(user_id, spec["darkweb"]),
        }
        format_enum = ReportFormat(format_upper)
        if format_enum == ReportFormat.HTML:
            content = self._generate_html_content(data)
        elif format_enum == ReportFormat.PDF:
            content = base64.b64encode(self._generate_pdf_content(data)).decode("utf-8")
        else:
            content = json.dumps(data, indent=2, default=str)
        report = Report(
            id=str(uuid4()), user_id=user_id, title=report_data.title, description=report_data.description,
            content=content, format=format_enum, ioc_query_ids=[], report_spec=spec,
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def _report_data_for(self, report: Report) -> dict:
        """Rebuild the data of a stored report from its spec (works for every format)."""
        spec = report.report_spec or {}
        if spec.get("type") == "darkweb":
            data = {"kind": "darkweb", "generated_at": datetime.now(timezone.utc).isoformat(),
                    "darkweb": self._darkweb_data(report.user_id, spec.get("darkweb") or {})}
        elif report.ioc_query_ids:
            data = self._generate_report_data(report.user_id, report.ioc_query_ids)
            if spec.get("include_darkweb"):
                data["darkweb"] = self._darkweb_data(report.user_id, spec.get("darkweb") or {})
        else:
            data = {}
        return data

    def _generate_report_data(self, user_id: str, ioc_query_ids: list[str]) -> dict:
        """Generate report data dict from IOC queries."""
        if not ioc_query_ids:
            return {
                "message": "No IOC queries included in report",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "total_queries": 0,
                "queries": [],
            }

        # Get IOC queries
        queries = (
            self.db.query(IOCQuery)
            .filter(IOCQuery.id.in_(ioc_query_ids))
            .filter(IOCQuery.user_id == user_id)
            .all()
        )

        if not queries:
            return {
                "message": "No valid IOC queries found",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "total_queries": 0,
                "queries": [],
            }

        # Build report data
        report_data = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_queries": len(queries),
            "queries": [],
        }

        for query in queries:
            # Get threat intelligence data
            threat_data = (
                self.db.query(ThreatIntelligenceData)
                .filter(ThreatIntelligenceData.ioc_query_id == query.id)
                .all()
            )

            query_data = {
                "id": query.id,
                "ioc_type": query.ioc_type,
                "ioc_value": query.ioc_value,
                "query_date": query.query_date.isoformat() if query.query_date else None,
                "risk_score": query.risk_score,
                "status": query.status,
                "results": query.results_json,
                "threat_intelligence": [
                    {
                        "source": td.source_api,
                        "confidence_score": td.confidence_score,
                        "processed_data": td.processed_data_json,
                        "tags": td.tags,
                    }
                    for td in threat_data
                ],
            }

            report_data["queries"].append(query_data)

        return report_data

    def _source_names(self) -> dict[str, str]:
        from app.models.api_source import APISource

        return {name: display for name, display in self.db.query(APISource.name, APISource.display_name).all()}

    def _model(self, report_data: dict) -> dict:
        from app.services.report_builder import build_darkweb_model, build_model

        dw = report_data.get("darkweb")
        dw_model = (
            build_darkweb_model(dw.get("mentions", []), dw.get("assets", []), dw.get("start"), dw.get("end"))
            if dw else None
        )
        if report_data.get("kind") == "darkweb":
            return {
                "kind": "darkweb",
                "title": report_data.get("title") or "Dark Web Exposure Report",
                "description": report_data.get("description") or "",
                "generated_at": report_data.get("generated_at") or datetime.now(timezone.utc).isoformat(),
                "darkweb": dw_model,
            }
        model = build_model(report_data, self._source_names())
        if dw_model:
            model["darkweb"] = dw_model
        return model

    def _generate_html_content(self, report_data: dict) -> str:
        """Render the report as a standalone HTML document (all values escaped)."""
        from app.services.report_builder import render_html

        return render_html(self._model(report_data))

    def _to_response(self, report: Report) -> dict:
        """Convert Report model to response dict."""
        return {
            "id": report.id,
            "user_id": report.user_id,
            "title": report.title,
            "description": report.description,
            "content": report.content,
            "format": report.format.value,
            "shared_link": report.shared_link,
            "ioc_query_ids": report.ioc_query_ids or [],
            "report_type": (report.report_spec or {}).get("type", "ioc"),
            "include_darkweb": bool((report.report_spec or {}).get("include_darkweb")),
            "darkweb_mentions": len(((report.report_spec or {}).get("darkweb") or {}).get("mention_ids") or []),
            "created_at": report.created_at,
            "updated_at": report.updated_at,
        }

    def export_report(self, report_id: str, user_id: str, format: str, include_raw_data: bool = False) -> dict:
        """Export report in specified format."""
        report = self.get_report(report_id, user_id)
        if not report:
            return {"error": "Report not found"}

        format_upper = format.upper()
        
        # If exporting in the same format as stored, return stored content
        if format_upper == report.format.value:
            if format_upper == "PDF":
                # PDF is stored as base64 encoded string
                import base64
                try:
                    content = base64.b64decode(report.content) if report.content else b""
                    return {
                        "report_id": report_id,
                        "format": format.upper(),
                        "content": content,
                        "content_type": "application/pdf",
                        "filename": f"report_{report_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.pdf",
                    }
                except Exception as e:
                    logger.error(f"Error decoding PDF content: {e}")
                    # Fall through to regenerate
            elif format_upper == "HTML":
                # HTML is stored as string
                return {
                    "report_id": report_id,
                    "format": format.upper(),
                    "content": (report.content or "").encode('utf-8'),
                    "content_type": "text/html",
                    "filename": f"report_{report_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.html",
                }
            elif format_upper == "JSON":
                # JSON is stored as string
                return {
                    "report_id": report_id,
                    "format": format.upper(),
                    "content": (report.content or "").encode('utf-8'),
                    "content_type": "application/json",
                    "filename": f"report_{report_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json",
                }

        # Re-render from the underlying queries whenever possible (works for every stored format)
        report_data = self._report_data_for(report)
        if not report_data and report.format == ReportFormat.JSON:
            try:
                report_data = json.loads(report.content) if report.content else {}
            except json.JSONDecodeError:
                report_data = {}

        # Add metadata
        report_data["title"] = report.title
        report_data["description"] = report.description
        report_data["created_at"] = report.created_at.isoformat()
        report_data["updated_at"] = report.updated_at.isoformat()

        # Generate export content
        if format_upper == "HTML":
            export_content = self._generate_html_content(report_data)
            content_type = "text/html"
        elif format_upper == "JSON":
            export_content = json.dumps(report_data, indent=2)
            content_type = "application/json"
        elif format_upper == "CSV":
            export_content = self._generate_csv_content(report_data)
            content_type = "text/csv"
        elif format_upper == "PDF":
            export_content = self._generate_pdf_content(report_data)
            content_type = "application/pdf"
        else:
            # Default to JSON
            export_content = json.dumps(report_data, indent=2)
            content_type = "application/json"

        # PDF returns bytes, others return strings
        if format_upper == "PDF":
            # Content is already bytes
            content = export_content
        else:
            # Convert string to bytes
            content = export_content.encode('utf-8') if isinstance(export_content, str) else export_content

        return {
            "report_id": report_id,
            "format": format.upper(),
            "content": content,
            "content_type": content_type,
            "filename": f"report_{report_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.{format.lower()}",
        }

    def _generate_csv_content(self, report_data: dict) -> str:
        """One row per unique indicator (formula-injection safe)."""
        from app.services.report_builder import render_csv

        return render_csv(self._model(report_data))

    def _generate_pdf_content(self, report_data: dict) -> bytes:
        """Render the report as an A4 PDF (summary, findings with evidence, compact appendices)."""
        from app.services.report_builder import render_pdf

        return render_pdf(self._model(report_data))

    def share_report(self, report_id: str, user_id: str, shared_user_ids: list[str]) -> dict:
        """Share a report with specified users (viewers).
        
        Only admin/analyst can share reports. The shared_with_user_ids field
        will be updated with the list of user IDs.
        """
        report = self.get_report(report_id, user_id)
        if not report:
            raise ValueError("Report not found")
        
        # Verify that the current user is admin or analyst
        from app.models.user import User, UserRole
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or user.role not in [UserRole.ADMIN, UserRole.ANALYST]:
            raise ValueError("Only admin or analyst users can share reports")
        
        # Update shared_with_user_ids
        db_report = self.db.query(Report).filter(Report.id == report_id).first()
        db_report.shared_with_user_ids = shared_user_ids
        self.db.commit()
        self.db.refresh(db_report)
        
        return self._to_response(db_report)

