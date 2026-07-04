"""
Slides PDF Generator

Generates presentation slides from a markdown file whose slides are separated by
``---`` on their own line. Each slide renders on a landscape 16:9 page, one page
per slide, with the body auto-shrunk to fit if it overflows (never enlarged).
"""

import re
import time
from pathlib import Path
from typing import List, Optional

from doctor.generators.base import BaseGenerator, GenerationResult, OutputFormat
from doctor.generators.mathbb_digits import inject_mathbb_digits


class SlidesGenerator(BaseGenerator):
    """
    Slides PDF generator for presentations.

    Takes a markdown file with ``---`` separators and generates a PDF with each
    slide on a landscape page. Content that would overflow is shrunk to fit.
    """

    # Standard 16:9 presentation dimensions (inches, for Playwright).
    SLIDE_WIDTH = "13.33in"
    SLIDE_HEIGHT = "7.5in"

    def __init__(self, build_dir: Path, config=None):
        super().__init__(build_dir, OutputFormat.SLIDES, config)

    def generate(self, markdown_path: Path, output_path: Path, title: Optional[str] = None) -> GenerationResult:
        """Generate a slides PDF from a markdown deck."""
        start_time = time.time()
        result = self._create_result(output_path, success=False)

        try:
            if not markdown_path.exists():
                result.add_error(f"Markdown file not found: {markdown_path}")
                return result

            markdown_content = markdown_path.read_text(encoding="utf-8")
            slides = self._parse_slides(markdown_content)

            if not slides:
                result.add_error("No slides found in markdown file")
                return result

            if not title:
                title = self._extract_title(slides[0])

            try:
                self._generate_slides_pdf(slides, output_path, title, markdown_path.parent)
            except ImportError:
                result.add_error("PDF generation requires Playwright. Install with: uv add playwright")
                return result
            except Exception as e:
                result.add_error(f"Slides generation failed: {str(e)}")
                return result

            result.success = True
            result.generation_time = time.time() - start_time
            result.file_size = output_path.stat().st_size

        except Exception as e:
            result.add_error(f"Slides generation failed: {str(e)}")

        return result

    def _parse_slides(self, markdown_content: str) -> List[str]:
        """
        Split markdown into slides on ``---`` lines, ignoring separators inside
        fenced code blocks. The final slide after the last separator is kept.
        """
        slides = []
        current_slide = []
        in_code_block = False

        for line in markdown_content.split("\n"):
            if line.strip().startswith("```"):
                in_code_block = not in_code_block

            if not in_code_block and re.match(r"^---\s*$", line):
                if current_slide:
                    slides.append("\n".join(current_slide).strip())
                current_slide = []
            else:
                current_slide.append(line)

        if current_slide:
            slide_content = "\n".join(current_slide).strip()
            if slide_content:
                slides.append(slide_content)

        return slides

    def _extract_title(self, first_slide: str) -> str:
        """Extract a title from the first slide's first H1/H2, else 'Presentation'."""
        for line in first_slide.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
            if line.startswith("## "):
                return line[3:].strip()

        return "Presentation"

    def _generate_slides_pdf(self, slides: List[str], output_path: Path, title: str, base_path: Path):
        """Render each slide independently with Playwright, then merge the pages."""
        from playwright.sync_api import sync_playwright

        self.build_dir.mkdir(parents=True, exist_ok=True)

        pdf_buffers = []

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()

            for i, slide_content in enumerate(slides):
                html_content = self._create_single_slide_html(slide_content, title, base_path, i + 1)
                html_path = self.build_dir / f"{output_path.stem}_slide_{i}_temp.html"
                html_path.write_text(html_content, encoding="utf-8")

                try:
                    page = browser.new_page(viewport={"width": 1280, "height": 720})
                    page.emulate_media(media="print")
                    page.goto(f"file://{html_path.absolute()}")

                    page.wait_for_timeout(1500)
                    page.wait_for_load_state("networkidle")

                    # Shrink the body (not the header) to fit, never enlarging.
                    page.evaluate("""
                        () => {
                            const slide = document.querySelector('.slide');
                            const header = slide?.querySelector('.slide-header');
                            const body = slide?.querySelector('.slide-body');
                            if (!slide || !body) return;

                            const slideRect = slide.getBoundingClientRect();
                            const headerHeight = header ? header.getBoundingClientRect().height : 0;

                            const availableWidth = slideRect.width - 120;
                            const availableHeight = slideRect.height - 150 - headerHeight;

                            let bodyHeight = body.scrollHeight;
                            let bodyWidth = body.scrollWidth;

                            const allElements = body.querySelectorAll('*');
                            allElements.forEach(el => {
                                const rect = el.getBoundingClientRect();
                                const bodyRect = body.getBoundingClientRect();
                                const bottom = rect.bottom - bodyRect.top;
                                const right = rect.right - bodyRect.left;
                                if (bottom > bodyHeight) bodyHeight = bottom;
                                if (right > bodyWidth) bodyWidth = right;
                            });

                            const scaleX = bodyWidth > availableWidth ? availableWidth / bodyWidth : 1;
                            const scaleY = bodyHeight > availableHeight ? availableHeight / bodyHeight : 1;
                            const scale = Math.min(scaleX, scaleY, 1);

                            if (scale < 1) {
                                body.style.transform = `scale(${scale})`;
                                body.style.transformOrigin = 'top left';
                            }
                        }
                    """)

                    page.wait_for_timeout(50)

                    pdf_bytes = page.pdf(
                        width=self.SLIDE_WIDTH,
                        height=self.SLIDE_HEIGHT,
                        print_background=True,
                        display_header_footer=False,
                    )
                    pdf_buffers.append(pdf_bytes)

                    page.close()
                finally:
                    if html_path.exists():
                        html_path.unlink()

            browser.close()

        self._merge_pdfs(pdf_buffers, output_path)

    def _protect_math(self, content: str) -> tuple[str, list[str]]:
        """Replace ``$$...$$`` and ``$...$`` with sentinels so markdown leaves them alone."""
        math_blocks = []

        def save_math(match):
            math_blocks.append(match.group(0))
            return f"MATH_PLACEHOLDER_{len(math_blocks) - 1}_END"

        protected = re.sub(r"\$\$[\s\S]*?\$\$", save_math, content)
        protected = re.sub(r"\$[^$\n]+\$", save_math, protected)

        return protected, math_blocks

    def _restore_math(self, content: str, math_blocks: list[str]) -> str:
        """Restore protected math spans after markdown rendering."""

        def restore_math(match):
            idx = int(match.group(1))
            if idx < len(math_blocks):
                return math_blocks[idx]
            return match.group(0)

        return re.sub(r"MATH_PLACEHOLDER_(\d+)_END", restore_math, content)

    def _extract_header_and_body(self, html: str) -> tuple[str, str]:
        """Split off the first h1/h2/h3 as the fixed header; the rest is the shrinkable body."""
        header_pattern = re.compile(r"^(\s*<h[123][^>]*>[\s\S]*?</h[123]>)", re.IGNORECASE)

        match = header_pattern.match(html)
        if match:
            header = match.group(1)
            body = html[match.end() :]
            return header, body

        return "", html

    def _create_single_slide_html(self, slide_content: str, title: str, base_path: Path, slide_num: int) -> str:
        """Build the standalone HTML document for one slide."""
        import markdown

        protected_content, math_blocks = self._protect_math(slide_content)

        md = markdown.Markdown(extensions=["tables", "fenced_code", "md_in_html"])
        slide_html = md.convert(protected_content)

        slide_html = self._restore_math(slide_html, math_blocks)
        slide_html = self._fix_image_paths(slide_html, base_path)

        header_html, body_html = self._extract_header_and_body(slide_html)
        css = self._create_slides_css()

        return inject_mathbb_digits(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{title} - Slide {slide_num}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"></script>
    <style>{css}</style>
</head>
<body>
    <div class="slide">
        <div class="slide-header">
            {header_html}
        </div>
        <div class="slide-body">
            {body_html}
        </div>
    </div>
    <script>
        document.addEventListener("DOMContentLoaded", function() {{
            renderMathInElement(document.body, {{
                delimiters: [
                    {{left: '$$', right: '$$', display: true}},
                    {{left: '$', right: '$', display: false}},
                    {{left: '\\\\[', right: '\\\\]', display: true}},
                    {{left: '\\\\(', right: '\\\\)', display: false}}
                ],
                throwOnError: false
            }});
        }});
    </script>
</body>
</html>""")

    def _merge_pdfs(self, pdf_buffers: List[bytes], output_path: Path):
        """Concatenate the per-slide PDF byte buffers into one file."""
        import io

        from pypdf import PdfReader, PdfWriter

        writer = PdfWriter()

        for pdf_bytes in pdf_buffers:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            for page in reader.pages:
                writer.add_page(page)

        with open(output_path, "wb") as f:
            writer.write(f)

    def _fix_image_paths(self, html: str, base_path: Path) -> str:
        """Rewrite relative image ``src`` paths to absolute ``file://`` URLs."""

        def replace_src(match):
            src = match.group(1)
            if src.startswith(("http://", "https://", "file://", "/")):
                return match.group(0)

            abs_path = (base_path / src).resolve()
            if abs_path.exists():
                return f'src="file://{abs_path}"'
            return match.group(0)

        return re.sub(r'src="([^"]+)"', replace_src, html)

    def _create_slides_css(self) -> str:
        """Assemble the slide CSS, drawing colors from the config where available."""
        heading_color = "#1a3a5c"
        text_color = "#1a1a1a"
        accent_color = "#4a7298"

        if self.config:
            if self.config.styling:
                if self.config.styling.text_color:
                    text_color = self.config.styling.text_color
                if self.config.styling.primary_color:
                    heading_color = self.config.styling.primary_color
                if self.config.styling.accent_color:
                    accent_color = self.config.styling.accent_color
            if self.config.typography and self.config.typography.headings:
                if self.config.typography.headings.heading_color:
                    heading_color = self.config.typography.headings.heading_color

        return f"""
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            @page {{
                size: {self.SLIDE_WIDTH} {self.SLIDE_HEIGHT};
                margin: 0;
            }}

            body {{
                margin: 0;
                padding: 0;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                font-size: 24px;
                line-height: 1.4;
                color: {text_color};
            }}

            .slide {{
                width: 100vw;
                height: 100vh;
                padding: 60px;
                page-break-after: always;
                page-break-inside: avoid;
                break-after: page;
                break-inside: avoid;
                position: relative;
                overflow: hidden;
                background: white;
                box-sizing: border-box;
                display: flex;
                flex-direction: column;
            }}

            .slide:last-child {{
                page-break-after: auto;
            }}

            @media print {{
                .slide {{
                    page-break-after: always !important;
                    break-after: page !important;
                }}
            }}

            .slide-header {{
                flex-shrink: 0;
            }}

            .slide-body {{
                flex: 1;
                overflow: visible;
            }}

            /* Two-column layout using explicit divs */
            .columns {{
                display: grid;
                grid-template-columns: var(--left, 50%) var(--right, 50%);
                gap: 2em;
                align-items: start;
                width: 100%;
            }}

            .columns > .left,
            .columns > .right {{
                min-width: 0;
            }}

            .columns figure {{
                margin: 0;
                width: 100%;
            }}

            .columns img {{
                width: 100%;
                height: auto;
                display: block;
            }}

            /* Typography */
            h1 {{
                font-size: 2.5em;
                font-weight: 600;
                color: {heading_color};
                margin-bottom: 0.5em;
                line-height: 1.2;
            }}

            h2 {{
                font-size: 2em;
                font-weight: 600;
                color: {heading_color};
                margin-bottom: 0.5em;
                line-height: 1.2;
            }}

            h3 {{
                font-size: 1.5em;
                font-weight: 600;
                color: {heading_color};
                margin-bottom: 0.4em;
                line-height: 1.2;
            }}

            h4, h5, h6 {{
                font-size: 1.2em;
                font-weight: 600;
                color: {heading_color};
                margin-bottom: 0.3em;
            }}

            p {{
                margin-bottom: 0.8em;
            }}

            ul, ol {{
                margin-left: 1.5em;
                margin-bottom: 0.8em;
            }}

            li {{
                margin-bottom: 0.4em;
            }}

            /* Tables */
            table {{
                border-collapse: collapse;
                margin: 1em 0;
                font-size: 0.9em;
            }}

            th, td {{
                border: 1px solid #ddd;
                padding: 0.5em 1em;
                text-align: left;
            }}

            th {{
                background-color: {heading_color};
                color: white;
                font-weight: 600;
            }}

            tr:nth-child(even) {{
                background-color: #f8f9fa;
            }}

            /* Code */
            code {{
                font-family: "SF Mono", Consolas, Monaco, "Courier New", monospace;
                font-size: 0.85em;
                background-color: #f6f8fa;
                padding: 0.2em 0.4em;
                border-radius: 3px;
            }}

            pre {{
                background-color: #f6f8fa;
                padding: 1em;
                border-radius: 6px;
                overflow-x: auto;
                margin: 1em 0;
            }}

            pre code {{
                background: none;
                padding: 0;
            }}

            /* Images and figures */
            img {{
                max-width: 100%;
                height: auto;
            }}

            figure {{
                margin: 1em 0;
                text-align: center;
            }}

            figcaption {{
                font-size: 0.8em;
                color: #666;
                margin-top: 0.5em;
                font-style: italic;
            }}

            /* Math */
            .katex-display {{
                margin: 0.8em 0;
            }}

            .katex {{
                font-size: 1.1em;
            }}

            /* Links */
            a {{
                color: {accent_color};
                text-decoration: none;
            }}

            /* Emphasis */
            strong {{
                font-weight: 600;
            }}

            em {{
                font-style: italic;
            }}

            /* Blockquotes */
            blockquote {{
                border-left: 4px solid {accent_color};
                padding-left: 1em;
                margin: 1em 0;
                color: #555;
            }}
        """
