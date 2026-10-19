"""
Export API endpoints.
GET /v1/runs/{run_id}/export - Export report in various formats
"""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, PlainTextResponse
from sqlalchemy.orm import Session

from app.db import get_db, RunRepository
from app.export import export_markdown, export_bibtex, export_html, export_pdf, export_json
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/runs", tags=["export"])


@router.get("/{run_id}/export")
async def export_run(
    run_id: str,
    format: Literal["markdown", "bibtex", "html", "pdf", "json"] = Query("markdown"),
    db: Session = Depends(get_db),
):
    """
    Export research run results in various formats.
    
    Formats:
    - markdown: Clean Markdown file
    - bibtex: BibTeX references for academic use
    - html: Styled HTML document
    - pdf: PDF document (requires weasyprint)
    - json: Structured JSON data
    """
    repo = RunRepository(db)
    run = repo.get(run_id)
    
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    if not run.final_report:
        raise HTTPException(status_code=400, detail="Run has no final report yet")
    
    sources = run.sources or []
    report = run.final_report
    
    if format == "markdown":
        content = export_markdown(report, sources)
        return PlainTextResponse(
            content=content,
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename=research_{run_id}.md"}
        )
    
    elif format == "bibtex":
        content = export_bibtex(sources)
        return PlainTextResponse(
            content=content,
            media_type="application/x-bibtex",
            headers={"Content-Disposition": f"attachment; filename=references_{run_id}.bib"}
        )
    
    elif format == "html":
        content = export_html(report)
        return Response(
            content=content,
            media_type="text/html",
            headers={"Content-Disposition": f"attachment; filename=research_{run_id}.html"}
        )
    
    elif format == "pdf":
        pdf_bytes = export_pdf(report)
        if pdf_bytes is None:
            raise HTTPException(
                status_code=501,
                detail="PDF export requires weasyprint. Install with: pip install weasyprint"
            )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=research_{run_id}.pdf"}
        )
    
    elif format == "json":
        data = export_json(
            report=report,
            sources=sources,
            metadata={
                "run_id": run_id,
                "objective": run.objective,
                "depth": run.depth,
                "created_at": run.created_at.isoformat() if run.created_at else None,
            }
        )
        return data
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown format: {format}")
