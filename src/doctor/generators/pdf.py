"""
PDF Document Generator

Generates PDF documents from AssembledDocument objects using HTML-to-PDF conversion.
Uses WeasyPrint for high-quality academic document rendering with CSS styling.
"""

import time
from pathlib import Path

from doctor.generators.base import BaseGenerator, GenerationResult, OutputFormat
from doctor.generators.html import HTMLGenerator
from doctor.ingest.assembly import AssembledDocument


class PDFGenerator(BaseGenerator):
    """
    PDF document generator using HTML-to-PDF conversion.

    Leverages the existing HTMLGenerator to create high-quality HTML,
    then converts it to PDF using WeasyPrint for academic document output.
    """

    def __init__(self, build_dir: Path, config=None):
        super().__init__(build_dir, OutputFormat.PDF, config)
        self.html_generator = HTMLGenerator(build_dir, "single", config)  # Always use single-page for PDF

    def generate(self, document: AssembledDocument, output_path: Path) -> GenerationResult:
        """Generate PDF document via HTML-to-PDF conversion."""
        start_time = time.time()
        result = self._create_result(output_path, success=False)

        # Validate document
        validation_errors = self.validate_document(document)
        if validation_errors:
            for error in validation_errors:
                result.add_error(error)
            return result

        try:
            # Generate PDF using Playwright
            try:
                pdf_generated = self._generate_pdf_playwright(document, output_path)
            except ImportError:
                result.add_error("PDF generation requires Playwright. Install with: uv add playwright")
                return result
            except Exception as e:
                result.add_error(f"PDF generation failed: {str(e)}")
                return result

            if pdf_generated:
                # Update result
                result.success = True
                result.generation_time = time.time() - start_time
                result.file_size = output_path.stat().st_size

                # Add warnings for any issues
                if document.broken_references:
                    result.add_warning(f"Document has {len(document.broken_references)} broken references")
                if document.missing_citations:
                    result.add_warning(f"Document has {len(document.missing_citations)} missing citations")
            else:
                result.add_error("Failed to generate PDF")

        except Exception as e:
            result.add_error(f"PDF generation failed: {str(e)}")

        return result

    def _generate_pdf_playwright(self, document: AssembledDocument, output_path: Path) -> bool:
        """Generate PDF using Playwright browser automation."""
        try:
            from playwright.sync_api import sync_playwright

            # Generate intermediate HTML
            html_path = self.build_dir / f"{output_path.stem}_temp.html"
            html_result = self.html_generator.generate(document, html_path)

            if not html_result.success:
                return False

            # Add PDF-optimized CSS to the HTML
            pdf_css = self._create_pdf_css()

            # Read the HTML and inject PDF CSS
            with open(html_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            # Inject CSS before closing </head> tag
            css_injection = f"<style>{pdf_css}</style></head>"
            html_content = html_content.replace("</head>", css_injection)

            # Write updated HTML
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            # Use Playwright to generate PDF
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()

                # Load HTML file
                page.goto(f"file://{html_path.absolute()}")

                # Wait for any async content (like KaTeX) to load
                page.wait_for_timeout(2000)

                # Generate PDF with configured paper settings
                pdf_format = "A4"  # Default fallback
                margins = {"top": "2.5cm", "bottom": "2.5cm", "left": "2cm", "right": "2cm"}

                if self.config and self.config.layout:
                    pdf_format = self.config.layout.get_playwright_format()
                    # Use configured margins
                    layout_margins = self.config.layout.margins
                    margins = {
                        "top": layout_margins.top,
                        "bottom": layout_margins.bottom,
                        "left": layout_margins.left,
                        "right": layout_margins.right,
                    }

                page.pdf(
                    path=str(output_path),
                    format=pdf_format,
                    margin=margins,
                    print_background=True,
                    display_header_footer=False,
                )

                browser.close()

            # Clean up temporary HTML file
            if html_path.exists():
                html_path.unlink()

            return True

        except Exception:
            # Clean up on error
            html_path = self.build_dir / f"{output_path.stem}_temp.html"
            if html_path.exists():
                html_path.unlink()
            raise

    def _create_pdf_css(self) -> str:
        """Create CSS optimized for PDF output, using config styling values."""
        # Get paper size and margins from configuration
        page_size = "A4"
        margins = "2.5cm 2cm"
        base_font_size = "11pt"
        line_height = "1.5"

        # Color defaults
        text_color = "#1a1a1a"
        heading_color = "#1a3a5c"
        accent_color = "#4a7298"

        # Font defaults
        serif_fonts = "Georgia, serif"
        sans_fonts = "Helvetica Neue, Arial, sans-serif"
        mono_fonts = "Consolas, Monaco, monospace"

        if self.config:
            # Layout settings
            if self.config.layout:
                page_size = self.config.layout.get_css_page_size()
                layout_margins = self.config.layout.margins
                margins = f"{layout_margins.top} {layout_margins.right} {layout_margins.bottom} {layout_margins.left}"

                # Adjust font size based on paper size for better proportions
                if self.config.layout.paper_size.value in ["a5", "a6", "a7"]:
                    base_font_size = "10pt"
                elif self.config.layout.paper_size.value in ["a0", "a1", "a2"]:
                    base_font_size = "12pt"

            # Typography settings
            if self.config.typography:
                base_font_size = self.config.typography.base_size
                line_height = str(self.config.typography.line_height)

                if self.config.typography.fonts:
                    serif_fonts = ", ".join(self.config.typography.fonts.serif)
                    sans_fonts = ", ".join(self.config.typography.fonts.sans)
                    mono_fonts = ", ".join(self.config.typography.fonts.mono)

            # Styling/color settings
            if self.config.styling:
                styling = self.config.styling
                if styling.text_color:
                    text_color = styling.text_color
                if styling.primary_color:
                    heading_color = styling.primary_color
                if styling.accent_color:
                    accent_color = styling.accent_color

            # Typography heading color override (takes precedence over styling.primary_color)
            if self.config.typography.headings:
                headings = self.config.typography.headings
                if headings.heading_color:
                    heading_color = headings.heading_color

        return f"""
        /* PDF-specific styling */
        @page {{
            size: {page_size};
            margin: {margins};

            @top-center {{
                content: string(chapter);
                font-family: {serif_fonts};
                font-size: 10pt;
                color: #666;
            }}

            @bottom-center {{
                content: counter(page);
                font-family: {serif_fonts};
                font-size: 10pt;
            }}
        }}

        @page :first {{
            @top-center {{ content: ""; }}
            @bottom-center {{ content: ""; }}
        }}

        body {{
            font-family: {serif_fonts};
            font-size: {base_font_size};
            line-height: {line_height};
            color: {text_color};
            hyphens: auto;
        }}

        /* Heading styling with config colors */
        h1, h2, h3, h4, h5, h6 {{
            font-family: {sans_fonts};
            color: {heading_color};
            page-break-after: avoid;
            break-after: avoid-page;
        }}

        /* Avoid breaking figures */
        figure, .figure {{
            page-break-inside: avoid;
            break-inside: avoid;
        }}

        /* Math styling for print */
        .katex {{
            font-size: 1em;
        }}

        .katex-display {{
            page-break-inside: avoid;
            break-inside: avoid;
        }}

        .katex-display .katex {{
            font-size: 1em;
        }}

        /* Citation styling */
        .citation {{
            font-weight: normal;
        }}

        .citation-link {{
            color: {accent_color};
            text-decoration: none;
        }}

        /* Table styling for print */
        table {{
            page-break-inside: avoid;
            break-inside: avoid;
        }}

        /* Code blocks */
        code, pre {{
            font-family: {mono_fonts};
            font-size: 9pt;
        }}

        pre {{
            page-break-inside: avoid;
            break-inside: avoid;
        }}

        /* Links in print */
        a {{
            color: {accent_color};
            text-decoration: none;
        }}

        /* Table of Contents styling for PDF */
        .table-of-contents {{
            page-break-after: always;
            margin-bottom: 2rem;
        }}

        .table-of-contents h2 {{
            text-align: center;
            margin-bottom: 2rem;
            font-size: 18pt;
            color: {heading_color};
        }}

        .toc-entry {{
            margin: 8pt 0;
            line-height: 1.4;
        }}

        .toc-entry a {{
            color: {text_color};
            text-decoration: none;
        }}

        .toc-level-1 {{
            font-weight: bold;
            font-size: 12pt;
            margin-top: 12pt;
        }}

        .toc-level-2 {{
            font-weight: bold;
            font-size: 11pt;
            margin-top: 8pt;
        }}

        .toc-level-3 {{
            margin-left: 24pt;
            font-size: 10pt;
        }}

        .toc-level-4 {{
            margin-left: 36pt;
            font-size: 10pt;
        }}

        /* Simple footnote styling */
        sup {{
            font-size: 0.8em;
            vertical-align: super;
            line-height: 0;
        }}

        /* Footnotes section styling */
        .footnotes {{
            margin-top: 2em;
            border-top: 1px solid {heading_color};
            padding-top: 1em;
            font-size: 0.85em;
            line-height: 1.2;
            page-break-inside: avoid;
        }}

        .footnotes h2 {{
            font-size: 1.1em;
            margin-bottom: 1em;
            font-weight: bold;
            color: {heading_color};
        }}

        .footnote-item {{
            margin-bottom: 0.5em;
            text-indent: -1.5em;
            padding-left: 1.5em;
            page-break-inside: avoid;
        }}

        .footnote-marker {{
            font-weight: bold;
            font-size: 0.9em;
        }}
        """

    def validate_document(self, document: AssembledDocument) -> list[str]:
        """Validate document for PDF generation."""
        errors = []

        if not document.title:
            errors.append("Document title is required for PDF generation")

        if not document.document_structure.files:
            errors.append("No content files found in document")

        return errors
