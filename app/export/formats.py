"""
Export formats: Markdown, PDF, BibTeX.
"""
import markdown
from typing import Optional
from datetime import datetime

from app.core.logging import get_logger

logger = get_logger(__name__)


def export_markdown(report: str, sources: list[dict] = None) -> str:
    """
    Export report as clean Markdown.
    
    Args:
        report: The report content
        sources: Optional list of sources
    
    Returns:
        Markdown string
    """
    # Add metadata header
    header = f"""---
generated: {datetime.utcnow().isoformat()}
format: markdown
---

"""
    return header + report


def export_bibtex(sources: list[dict]) -> str:
    """
    Export sources as BibTeX.
    
    Args:
        sources: List of source dictionaries
    
    Returns:
        BibTeX string
    """
    entries = []
    
    for i, source in enumerate(sources):
        # Generate cite key
        first_author = ""
        authors = source.get("authors", [])
        if authors:
            first_author = authors[0].split()[-1].lower()  # Last name
        year = source.get("year", "")
        cite_key = f"{first_author}{year}_{i}" if first_author else f"source{i}"
        
        # Format authors
        authors_str = " and ".join(authors) if authors else "Unknown"
        
        entry_type = "article"
        if source.get("source") == "wikipedia":
            entry_type = "misc"
        
        entry = f"""@{entry_type}{{{cite_key},
  title = {{{source.get('title', 'Untitled')}}},
  author = {{{authors_str}}},
  year = {{{year}}},
  url = {{{source.get('url', '')}}},
  abstract = {{{source.get('abstract', '')[:200]}...}}
}}"""
        entries.append(entry)
    
    header = f"""% BibTeX export from Hive Lite
% Generated: {datetime.utcnow().isoformat()}
% Total entries: {len(entries)}

"""
    return header + "\n\n".join(entries)


def export_html(report: str) -> str:
    """
    Export report as HTML.
    
    Args:
        report: Markdown report content
    
    Returns:
        HTML string
    """
    # Convert markdown to HTML
    html_content = markdown.markdown(
        report,
        extensions=['tables', 'fenced_code', 'toc']
    )
    
    # Wrap in HTML document
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Research Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }}
        h1, h2, h3 {{ color: #1a1a2e; }}
        h1 {{ border-bottom: 2px solid #4a4a8a; padding-bottom: 10px; }}
        h2 {{ border-bottom: 1px solid #ddd; padding-bottom: 5px; margin-top: 30px; }}
        a {{ color: #4a4a8a; }}
        code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }}
        pre {{ background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }}
        ul {{ padding-left: 20px; }}
        blockquote {{ border-left: 3px solid #4a4a8a; margin-left: 0; padding-left: 15px; color: #666; }}
        .meta {{ color: #888; font-size: 0.9em; margin-bottom: 30px; }}
    </style>
</head>
<body>
    <div class="meta">Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</div>
    {html_content}
</body>
</html>"""
    
    return html


def export_pdf(report: str) -> Optional[bytes]:
    """
    Export report as PDF.
    
    Args:
        report: Markdown report content
    
    Returns:
        PDF bytes or None if weasyprint not available
    """
    try:
        from weasyprint import HTML
        
        html_content = export_html(report)
        pdf_bytes = HTML(string=html_content).write_pdf()
        return pdf_bytes
        
    except ImportError:
        logger.warning("weasyprint not installed, PDF export unavailable")
        return None
    except Exception as e:
        logger.error(f"PDF export failed: {e}")
        return None


def export_json(report: str, sources: list[dict], metadata: dict = None) -> dict:
    """
    Export as structured JSON.
    
    Args:
        report: Report content
        sources: List of sources
        metadata: Optional additional metadata
    
    Returns:
        JSON-serializable dictionary
    """
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "report": report,
        "sources": sources,
        "metadata": metadata or {},
        "statistics": {
            "num_sources": len(sources),
            "report_length": len(report),
            "sources_by_type": _count_by_type(sources),
        }
    }


def _count_by_type(sources: list[dict]) -> dict[str, int]:
    """Count sources by type."""
    counts = {}
    for s in sources:
        source_type = s.get("source", "unknown")
        counts[source_type] = counts.get(source_type, 0) + 1
    return counts
