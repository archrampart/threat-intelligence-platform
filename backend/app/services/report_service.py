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
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .high-risk {{ color: #d32f2f; font-weight: bold; }}
                .medium-risk {{ color: #f57c00; }}
                .low-risk {{ color: #388e3c; }}
            </style>
        </head>
        <body>
            <h1>{title}</h1>
            {f'<p><strong>Description:</strong> {description}</p>' if description else ''}
            <p><strong>Generated at:</strong> {report_data.get('generated_at', 'N/A')}</p>
            <p><strong>Total IOC Queries:</strong> {report_data.get('total_queries', 0)}</p>
            
            <h2>IOC Queries</h2>
            <table>
                <tr>
                    <th>IOC Type</th>
                    <th>IOC Value</th>
                    <th>Risk Score</th>
                    <th>Status</th>
                    <th>Query Date</th>
                </tr>
        """

        for query in report_data.get("queries", []):
            risk_class = "low-risk"
            if query.get("risk_score") and query["risk_score"] >= 0.8:
                risk_class = "high-risk"
            elif query.get("risk_score") and query["risk_score"] >= 0.5:
                risk_class = "medium-risk"

            html += f"""
                <tr>
                    <td>{query.get('ioc_type', 'N/A')}</td>
                    <td>{query.get('ioc_value', 'N/A')}</td>
                    <td class="{risk_class}">{query.get('risk_score', 'N/A')}</td>
                    <td>{query.get('status', 'N/A')}</td>
                    <td>{query.get('query_date', 'N/A')}</td>
                </tr>
            """

        html += """
            </table>
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
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
            from reportlab.lib import colors
            from reportlab.lib.units import inch
            from io import BytesIO
            
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter, 
                                  rightMargin=0.75*inch, leftMargin=0.75*inch,
                                  topMargin=0.75*inch, bottomMargin=0.75*inch)
            styles = getSampleStyleSheet()
            story = []
            
            # Title
            title = Paragraph(f"<b>{report_data.get('title', 'Threat Intelligence Report')}</b>", styles['Title'])
            story.append(title)
            story.append(Spacer(1, 12))
            
            # Metadata
            if report_data.get('description'):
                desc = Paragraph(f"<i>{report_data.get('description')}</i>", styles['Normal'])
                story.append(desc)
                story.append(Spacer(1, 12))
            
            generated_at = report_data.get('generated_at', 'N/A')
            story.append(Paragraph(f"<b>Generated at:</b> {generated_at}", styles['Normal']))
            story.append(Paragraph(f"<b>Total IOC Queries:</b> {report_data.get('total_queries', 0)}", styles['Normal']))
            story.append(Spacer(1, 20))
            
            # IOC Queries Table
            # Use Paragraph for text wrapping in cells
            header_style = styles['Heading2']
            normal_style = styles['Normal']
            normal_style.fontSize = 8
            normal_style.leading = 10
            
            data = [[
                Paragraph('<b>IOC Type</b>', header_style),
                Paragraph('<b>IOC Value</b>', header_style),
                Paragraph('<b>Risk Score</b>', header_style),
                Paragraph('<b>Status</b>', header_style),
                Paragraph('<b>Query Date</b>', header_style)
            ]]
            
            for query in report_data.get('queries', []):
                risk_score = query.get('risk_score', 'N/A')
                if isinstance(risk_score, (int, float)):
                    risk_score = f"{risk_score:.2f}"
                
                ioc_value = query.get('ioc_value', 'N/A')
                # Escape HTML special characters and wrap long values
                ioc_value_escaped = ioc_value.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                
                query_date = query.get('query_date', 'N/A')
                if query_date and query_date != 'N/A':
                    query_date = query_date[:10] if len(query_date) > 10 else query_date
                
                data.append([
                    Paragraph(query.get('ioc_type', 'N/A'), normal_style),
                    Paragraph(ioc_value_escaped, normal_style),
                    Paragraph(str(risk_score), normal_style),
                    Paragraph(query.get('status', 'N/A'), normal_style),
                    Paragraph(query_date, normal_style)
                ])
            
            # Create table with proper styling and adjusted column widths
            # Total page width: 8.5 inch - 2*0.75 inch margins = 7 inch
            table = Table(data, colWidths=[1.0*inch, 3.0*inch, 0.8*inch, 0.9*inch, 1.0*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F2F2F2')),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9F9F9')]),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('WORDWRAP', (0, 0), (-1, -1), True),  # Enable word wrapping
            ]))
            story.append(table)
            
            # Build PDF
            doc.build(story)
            buffer.seek(0)
            return buffer.getvalue()
        except ImportError:
            # Fallback: Try weasyprint if reportlab not available
            try:
                from weasyprint import HTML
                from weasyprint.text.fonts import FontConfiguration
                
                html_content = self._generate_html_content(report_data)
                font_config = FontConfiguration()
                pdf_bytes = HTML(string=html_content).write_pdf(font_config=font_config)
                return pdf_bytes
            except (ImportError, OSError) as e:
                # Last resort: Return HTML content as bytes (browser can convert)
                logger.warning(f"PDF generation failed: {e}. Returning HTML as PDF fallback.")
                html_content = self._generate_html_content(report_data)
                return html_content.encode('utf-8')

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

