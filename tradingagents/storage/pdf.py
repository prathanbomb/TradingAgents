"""PDF conversion for markdown reports."""

from pathlib import Path
from typing import List

import markdown
from weasyprint import HTML


def convert_reports_to_pdf(report_dir: Path) -> List[Path]:
    """Convert all markdown files in directory to PDF.

    Args:
        report_dir: Directory containing markdown files

    Returns:
        List of paths to generated PDF files
    """
    pdf_paths = []

    for md_file in report_dir.glob("*.md"):
        try:
            # Convert markdown to HTML
            md_content = md_file.read_text(encoding="utf-8")
            html_content = markdown.markdown(
                md_content,
                extensions=["tables", "fenced_code"],
            )

            # Wrap in basic HTML structure with styling
            full_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        line-height: 1.6;
                        max-width: 800px;
                        margin: 40px auto;
                        padding: 20px;
                        color: #333;
                    }}
                    h1, h2, h3 {{ color: #2c3e50; }}
                    table {{
                        border-collapse: collapse;
                        width: 100%;
                        margin: 20px 0;
                    }}
                    th, td {{
                        border: 1px solid #ddd;
                        padding: 8px;
                        text-align: left;
                    }}
                    th {{ background-color: #f4f4f4; }}
                    code {{
                        background-color: #f4f4f4;
                        padding: 2px 6px;
                        border-radius: 3px;
                    }}
                    pre {{
                        background-color: #f4f4f4;
                        padding: 15px;
                        border-radius: 5px;
                        overflow-x: auto;
                    }}
                </style>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """

            # Convert to PDF
            pdf_path = md_file.with_suffix(".pdf")
            HTML(string=full_html).write_pdf(str(pdf_path))
            pdf_paths.append(pdf_path)

        except Exception as e:
            print(f"  Warning: Failed to convert {md_file.name} to PDF: {e}")

    return pdf_paths
