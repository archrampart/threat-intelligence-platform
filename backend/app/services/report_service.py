"""Report service - IOC query report generation."""

import json
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.ioc_query import IOCQuery, ThreatIntelligenceData
from app.models.report import Report, ReportFormat
from app.schemas.report import ReportCreate, ReportUpdate
from loguru import logger


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
                ioc_query_ids=report_data.ioc_query_ids or [],
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

    def _generate_html_content(self, report_data: dict) -> str:
        """Generate HTML content from report data."""
        title = report_data.get('title', 'Threat Intelligence Report')
        description = report_data.get('description', '')
        
        # Calculate summary statistics
        total_queries = report_data.get('total_queries', 0)
        high_risk_count = 0
        medium_risk_count = 0
        low_risk_count = 0
        unknown_risk_count = 0
        total_risk_score = 0
        valid_risk_scores = 0
        
        queries = report_data.get("queries", [])
        for query in queries:
            score = query.get("risk_score")
            if score is not None:
                total_risk_score += score
                valid_risk_scores += 1
                if score >= 0.8:
                    high_risk_count += 1
                elif score >= 0.4:
                    medium_risk_count += 1
                else:
                    low_risk_count += 1
            else:
                unknown_risk_count += 1
                
        avg_risk_score = (total_risk_score / valid_risk_scores) if valid_risk_scores > 0 else 0
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{title}</title>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 40px; background-color: #f8f9fa; color: #333; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 40px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); border-radius: 8px; }}
                h1 {{ color: #1a1a1a; margin-top: 0; border-bottom: 2px solid #eee; padding-bottom: 20px; }}
                .meta-info {{ color: #666; font-size: 0.9em; margin-bottom: 30px; }}
                .summary-cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 40px; }}
                .card {{ padding: 20px; border-radius: 8px; color: white; text-align: center; }}
                .card-title {{ font-size: 0.9em; opacity: 0.9; margin-bottom: 5px; }}
                .card-value {{ font-size: 2.5em; font-weight: bold; }}
                .bg-blue {{ background: linear-gradient(135deg, #2193b0, #6dd5ed); }}
                .bg-red {{ background: linear-gradient(135deg, #cb2d3e, #ef473a); }}
                .bg-orange {{ background: linear-gradient(135deg, #f12711, #f5af19); }}
                .bg-green {{ background: linear-gradient(135deg, #11998e, #38ef7d); }}
                
                table {{ border-collapse: collapse; width: 100%; margin-top: 20px; font-size: 0.95em; }}
                th {{ background-color: #f1f3f5; color: #495057; font-weight: 600; text-align: left; padding: 12px; border-bottom: 2px solid #dee2e6; }}
                td {{ padding: 12px; border-bottom: 1px solid #dee2e6; vertical-align: top; }}
                tr:last-child td {{ border-bottom: none; }}
                
                .badge {{ padding: 4px 8px; border-radius: 4px; font-size: 0.8em; font-weight: 500; display: inline-block; }}
                .badge-critical {{ background-color: #ffe3e3; color: #c92a2a; }}
                .badge-high {{ background-color: #ffe3e3; color: #c92a2a; }}
                .badge-medium {{ background-color: #fff3bf; color: #f08c00; }}
                .badge-low {{ background-color: #d3f9d8; color: #2b8a3e; }}
                .badge-unknown {{ background-color: #f8f9fa; color: #868e96; border: 1px solid #dee2e6; }}
                
                .findings-list {{ list-style: none; padding: 0; margin: 0; }}
                .finding-item {{ margin-bottom: 8px; font-size: 0.9em; }}
                .source-name {{ font-weight: 600; color: #495057; }}
                .tag {{ background-color: #e7f5ff; color: #1c7ed6; padding: 2px 6px; border-radius: 3px; font-size: 0.85em; margin-left: 4px; }}
                .malicious-tag {{ background-color: #ffe3e3; color: #c92a2a; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>{title}</h1>
                <div class="meta-info">
                    <p>{description}</p>
                    <p>Generated at: {report_data.get('generated_at', 'N/A')} | Total Queries: {total_queries}</p>
                </div>

                <div class="summary-cards">
                    <div class="card bg-blue">
                        <div class="card-title">Total IOCs</div>
                        <div class="card-value">{total_queries}</div>
                    </div>
                    <div class="card bg-red">
                        <div class="card-title">High/Critical Risk</div>
                        <div class="card-value">{high_risk_count}</div>
                    </div>
                    <div class="card bg-orange">
                        <div class="card-title">Medium Risk</div>
                        <div class="card-value">{medium_risk_count}</div>
                    </div>
                    <div class="card bg-green">
                        <div class="card-title">Avg Risk Score</div>
                        <div class="card-value">{avg_risk_score:.2f}</div>
                    </div>
                </div>
                
                <h2>Detailed Findings</h2>
                <table>
                    <thead>
                        <tr>
                            <th style="width: 15%">IOC Type</th>
                            <th style="width: 25%">IOC Value</th>
                            <th style="width: 10%">Risk Score</th>
                            <th style="width: 50%">Detailed Findings</th>
                        </tr>
                    </thead>
                    <tbody>
        """

        for query in queries:
            risk_badge = "badge-unknown"
            score = query.get("risk_score")
            
            if score is not None:
                if score >= 0.8: risk_badge = "badge-critical"
                elif score >= 0.4: risk_badge = "badge-medium"
                else: risk_badge = "badge-low"
                score_display = f"{score:.2f}"
            else:
                score_display = "N/A"

            # Process threat intelligence findings
            findings_html = '<ul class="findings-list">'
            threat_intelligence = query.get("threat_intelligence", [])
            
            if not threat_intelligence:
                findings_html += '<li class="finding-item" style="color: #868e96; font-style: italic;">No specific threat intelligence details available.</li>'
            else:
                for ti in threat_intelligence:
                    source = ti.get("source", "Unknown Source")
                    conf = ti.get("confidence_score")
                    tags = ti.get("tags", [])
                    
                    # Determine if finding is malicious based on tags or confidence
                    is_malicious = False
                    if conf and conf > 0.5: is_malicious = True
                    
                    tags_html = ""
                    if tags:
                        # Handle if tags is a string or list
                        if isinstance(tags, str):
                            tags_list = [t.strip() for t in tags.split(',')]
                        else:
                            tags_list = tags
                            
                        for tag in tags_list:
                            tag_str = str(tag) if tag is not None else ""
                            tag_class = "tag malicious-tag" if tag_str.lower() in ['malicious', 'phishing', 'malware', 'botnet'] else "tag"
                            tags_html += f'<span class="{tag_class}">{tag_str}</span>'
                    
                    conf_display = f" | Confidence: {int(conf * 100)}%" if conf is not None else ""
                    
                    findings_html += f"""
                        <li class="finding-item">
                            <span class="source-name">{source}</span>{conf_display}
                            {tags_html}
                        </li>
                    """
            findings_html += "</ul>"

            html += f"""
                <tr>
                    <td><span class="badge" style="background: #e9ecef; color: #495057;">{query.get('ioc_type', 'N/A')}</span></td>
                    <td style="font-family: monospace; font-size: 1.1em;">{query.get('ioc_value', 'N/A')}</td>
                    <td><span class="badge {risk_badge}">{score_display}</span></td>
                    <td>{findings_html}</td>
                </tr>
            """

        html += """
                    </tbody>
                </table>
                <div style="margin-top: 40px; text-align: center; color: #868e96; font-size: 0.8em;">
                    <p>Generated by ArchRampart Threat Intelligence Platform</p>
                </div>
            </div>
        </body>
        </html>
        """

        return html

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

        # Parse report content to regenerate in different format
        report_data = {}
        if report.format == ReportFormat.JSON:
            try:
                report_data = json.loads(report.content) if report.content else {}
            except json.JSONDecodeError:
                report_data = {}
        elif report.format == ReportFormat.HTML:
            # Try to extract data from HTML or use stored data
            report_data = {"content": report.content}
        elif report.format == ReportFormat.PDF:
            # For PDF, we need to regenerate from stored data
            # Try to get from IOC queries
            if report.ioc_query_ids:
                report_data = self._generate_report_data(user_id, report.ioc_query_ids)
            else:
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
        """Generate CSV content from report data."""
        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(["IOC Type", "IOC Value", "Risk Score", "Status", "Query Date", "Sources"])

        # Data rows
        for query in report_data.get("queries", []):
            sources = ", ".join([ti.get("source", "") for ti in query.get("threat_intelligence", [])])
            writer.writerow(
                [
                    query.get("ioc_type", ""),
                    query.get("ioc_value", ""),
                    query.get("risk_score", ""),
                    query.get("status", ""),
                    query.get("query_date", ""),
                    sources,
                ]
            )

        return output.getvalue()

    def _generate_pdf_content(self, report_data: dict) -> bytes:
        """Generate PDF content from report data using reportlab."""
        try:
            # Use reportlab (more reliable, fewer dependencies)
            from reportlab.lib.pagesizes import letter, landscape
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
            from reportlab.lib import colors
            from reportlab.lib.units import inch
            from io import BytesIO
            
            buffer = BytesIO()
            # USE LANDSCAPE for better width availability
            doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), 
                                  rightMargin=0.5*inch, leftMargin=0.5*inch,
                                  topMargin=0.5*inch, bottomMargin=0.5*inch)
            styles = getSampleStyleSheet()
            story = []
            
            # Custom Styles
            styles.add(ParagraphStyle(name='RiskHigh', parent=styles['Normal'], textColor=colors.red))
            styles.add(ParagraphStyle(name='RiskMedium', parent=styles['Normal'], textColor=colors.orange))
            styles.add(ParagraphStyle(name='RiskLow', parent=styles['Normal'], textColor=colors.green))
            styles.add(ParagraphStyle(name='TagMalicious', parent=styles['Normal'], fontSize=8, textColor=colors.red, backColor=colors.mistyrose, borderPadding=2))
            styles.add(ParagraphStyle(name='TagNormal', parent=styles['Normal'], fontSize=8, textColor=colors.blue, backColor=colors.aliceblue, borderPadding=2))
            
            # --- Statistics Calculation ---
            total_queries = report_data.get('total_queries', 0)
            high_risk_count = 0
            medium_risk_count = 0
            total_risk_score = 0
            valid_risk_scores = 0
            
            for query in report_data.get("queries", []):
                score = query.get("risk_score")
                if score is not None:
                    total_risk_score += score
                    valid_risk_scores += 1
                    if score >= 0.8: high_risk_count += 1
                    elif score >= 0.4: medium_risk_count += 1
            
            avg_risk_score = (total_risk_score / valid_risk_scores) if valid_risk_scores > 0 else 0
            
            # --- Document Header ---
            title = Paragraph(f"<b>{report_data.get('title', 'Threat Intelligence Report')}</b>", styles['Title'])
            story.append(title)
            story.append(Spacer(1, 12))
            
            if report_data.get('description'):
                desc = Paragraph(f"<i>{report_data.get('description')}</i>", styles['Normal'])
                story.append(desc)
                story.append(Spacer(1, 12))
            
            meta_text = f"<b>Generated at:</b> {report_data.get('generated_at', 'N/A')[:19].replace('T', ' ')}"
            story.append(Paragraph(meta_text, styles['Normal']))
            story.append(Spacer(1, 20))
            
            # --- Executive Summary Table ---
            summary_data = [
                ['Total IOCs', 'High/Critical Risk', 'Medium Risk', 'Avg Risk Score'],
                [str(total_queries), str(high_risk_count), str(medium_risk_count), f"{avg_risk_score:.2f}"]
            ]
            
            summary_table = Table(summary_data, colWidths=[2.5*inch, 2.5*inch, 2.5*inch, 2.5*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d253f')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                
                ('BACKGROUND', (0, 1), (-1, 1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, 1), colors.black),
                ('FONTSIZE', (0, 1), (-1, 1), 14),
                ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#0d253f')),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
                
                # Colorize values
                ('TEXTCOLOR', (1, 1), (1, 1), colors.red),  # High Risk count
                ('TEXTCOLOR', (2, 1), (2, 1), colors.orange),  # Medium Risk count
            ]))
            story.append(summary_table)
            story.append(Spacer(1, 24))
            
            # --- Detailed Findings Section ---
            story.append(Paragraph("<b>Detailed Findings</b>", styles['Heading2']))
            story.append(Spacer(1, 12))
            
            # Define styles for findings
            finding_header_style = styles['Heading3']
            finding_header_style.fontSize = 11
            finding_header_style.textColor = colors.HexColor('#2c3e50')
            finding_header_style.spaceAfter = 4
            
            meta_style = styles['Normal']
            meta_style.fontSize = 9
            meta_style.textColor = colors.HexColor('#576574')
            
            # Loop through queries and create a section for each
            for i, query in enumerate(report_data.get('queries', [])):
                # 1. IOC Header Block
                ioc_type = query.get('ioc_type', 'N/A')
                ioc_value = query.get('ioc_value', 'N/A')
                risk_score = query.get('risk_score', 'N/A')
                
                # Risk Score Formatting and Color
                risk_color = "black"
                if isinstance(risk_score, (int, float)):
                    if risk_score >= 0.8: risk_color = "red"
                    elif risk_score >= 0.4: risk_color = "orange"
                    elif risk_score > 0: risk_color = "green"
                    risk_display = f"{risk_score:.2f}"
                else:
                    risk_display = "N/A"
                
                # Header Line: [TYPE] Value (Risk: X.XX)
                header_text = f"<b>[{ioc_type.upper()}]</b> <font face='Courier'>{ioc_value}</font> <font color='{risk_color}' size='9'>(Risk Score: {risk_display})</font>"
                story.append(Paragraph(header_text, finding_header_style))
                
                # 2. Details Table for this IOC
                threat_intelligence = query.get("threat_intelligence", [])
                
                if not threat_intelligence:
                    story.append(Paragraph("<i>No specific threat intelligence details available.</i>", meta_style))
                else:
                    # Create a mini-table for findings
                    findings_data = [['Source', 'Confidence', 'Tags']]
                    
                    for ti in threat_intelligence:
                        source = ti.get("source", "Unknown")
                        conf = ti.get("confidence_score")
                        tags = ti.get("tags", [])
                        
                        conf_str = f"{int(conf * 100)}%" if conf is not None else "-"
                        
                        # Process tags
                        tags_str = "-"
                        if tags:
                            if isinstance(tags, str): tags = [t.strip() for t in tags.split(',')]
                            # Defensive check and string conversion
                            clean_tags = []
                            for t in tags:
                                if t: clean_tags.append(str(t))
                            tags_str = ", ".join(clean_tags)
                        
                        findings_data.append([source, conf_str, Paragraph(tags_str, meta_style)])
                    
                    # Style the mini-table
                    ft = Table(findings_data, colWidths=[2.5*inch, 1.5*inch, 5.0*inch])
                    ft.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f2f6')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 9),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#ced6e0')),
                        ('FONTSIZE', (0, 1), (-1, -1), 8),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ]))
                    story.append(ft)
                
                # Add spacing/separator between IOCs
                story.append(Spacer(1, 15))
                # Add a light line separator
                from reportlab.platypus import Flowable
                class Separator(Flowable):
                    def __init__(self, width, color):
                        Flowable.__init__(self)
                        self.width = width
                        self.color = color
                    def draw(self):
                        self.canv.setStrokeColor(self.color)
                        self.canv.line(0, 0, self.width, 0)
                
                story.append(Separator(9*inch, colors.HexColor('#dfe4ea')))
                story.append(Spacer(1, 15))
            
            # --- Footer ---
            # (SimpleDocTemplate handles page numbers automatically if configured, or we can leave it simple)
            # Build PDF
            doc.build(story)
            buffer.seek(0)
            return buffer.getvalue()
            
        except Exception as e:
            # Catch ALL exceptions to prevent 500 errors
            # Fallback: Generate a simple PDF error page instead of HTML bytes
            from loguru import logger
            logger.error(f"PDF generation failed with ReportLab: {e}")
            
            try:
                from reportlab.pdfgen import canvas
                from reportlab.lib.pagesizes import letter
                
                buffer = BytesIO()
                c = canvas.Canvas(buffer, pagesize=letter)
                c.setFont("Helvetica-Bold", 14)
                c.drawString(50, 750, "Report Generation Error")
                c.setFont("Helvetica", 12)
                c.drawString(50, 720, "A technical error occurred while generating the detailed PDF layout.")
                c.drawString(50, 700, "Please try viewing the HTML version in the application.")
                c.setFont("Helvetica-Oblique", 10)
                c.drawString(50, 650, f"Error details: {str(e)[:100]}...")
                c.save()
                buffer.seek(0)
                return buffer.getvalue()
            except Exception as e2:
                # Absolute last resort: minimal valid PDF header
                logger.error(f"Even fallback PDF generation failed: {e2}")
                return b"%PDF-1.4\n%EOF"

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

