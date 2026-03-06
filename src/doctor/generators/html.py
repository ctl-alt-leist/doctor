"""
HTML document generator

Primary document generator using semantic HTML + CSS styling.
Produces clean, accessible HTML documents ready for web or PDF conversion.
"""

import time
from pathlib import Path
from typing import Dict, Optional

from jinja2 import Environment, FileSystemLoader, Template

from doctor.generators.base import BaseGenerator, GenerationResult, OutputFormat
from doctor.ingest.assembly import AssembledDocument


class HTMLGenerator(BaseGenerator):
    """
    HTML document generator.

    Generates semantic HTML documents with CSS styling from AssembledDocument objects.
    Uses Jinja2 templates for flexible document layout and styling.
    Supports both single-page and multi-page output modes.
    """

    def __init__(self, build_dir: Path, html_mode: str = "single", config=None):
        super().__init__(build_dir, OutputFormat.HTML, config)
        self.html_mode = html_mode  # "single" or "multi-page"
        self._setup_templates()

    def _setup_templates(self):
        """Initialize Jinja2 template environment."""
        template_dir = self._get_template_dir()

        # Create templates directory if it doesn't exist
        template_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=True,  # Auto-escape for security
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters for templates
        self.jinja_env.filters["sanitize"] = self._sanitize_filename
        self.jinja_env.filters["section_anchor"] = self._generate_section_anchor
        self.jinja_env.filters["markdown_to_html"] = self._markdown_to_html
        self.jinja_env.filters["match"] = self._regex_match_filter

        # Add custom tests
        self.jinja_env.tests["match"] = self._regex_match_test

    def generate(self, document: AssembledDocument, output_path: Path) -> GenerationResult:
        """Generate HTML document(s) based on html_mode."""
        # Reset counters and collections for new document
        self._current_footnotes = []
        self._citation_mapping = {}
        self._citation_counter = 0
        if self.html_mode == "multi-page":
            return self._generate_multi_page(document, output_path)
        else:
            return self._generate_single_page(document, output_path)

    def _generate_single_page(self, document: AssembledDocument, output_path: Path) -> GenerationResult:
        """Generate single-page HTML document."""
        start_time = time.time()
        result = self._create_result(output_path, success=False)

        # Validate document
        validation_errors = self.validate_document(document)
        if validation_errors:
            for error in validation_errors:
                result.add_error(error)
            return result

        try:
            # Load or create HTML template
            template = self._get_html_template()

            # Prepare template context
            context = self._build_template_context(document)

            # Render HTML
            html_content = template.render(**context)

            # Write to output file
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            # Copy shared resources (figures) for single-page HTML
            self._copy_shared_resources(document, output_path.parent)

            # Update result
            result.success = True
            result.generation_time = time.time() - start_time
            result.file_size = output_path.stat().st_size

            # Add warnings for any issues
            if document.broken_references:
                result.add_warning(f"Document has {len(document.broken_references)} broken references")
            if document.missing_citations:
                result.add_warning(f"Document has {len(document.missing_citations)} missing citations")

        except Exception as e:
            result.add_error(f"HTML generation failed: {str(e)}")

        return result

    def _generate_multi_page(self, document: AssembledDocument, output_path: Path) -> GenerationResult:
        """Generate multi-page HTML structure."""
        start_time = time.time()

        # Create directory structure
        base_name = output_path.stem
        output_dir = output_path.parent / base_name
        output_dir.mkdir(exist_ok=True)

        # Update result to point to the directory
        result = self._create_result(output_dir / "index.html", success=False)

        # Validate document
        validation_errors = self.validate_document(document)
        if validation_errors:
            for error in validation_errors:
                result.add_error(error)
            return result

        try:
            # Generate index page
            self._generate_index_page(document, output_dir)

            # Generate individual pages for each file
            self._generate_individual_pages(document, output_dir)

            # Copy shared resources (figures, etc.)
            self._copy_shared_resources(document, output_dir)

            # Update result
            result.success = True
            result.generation_time = time.time() - start_time

            # Calculate total size of all generated files
            total_size = sum(f.stat().st_size for f in output_dir.rglob("*") if f.is_file())
            result.file_size = total_size

            # Add warnings for any issues
            if document.broken_references:
                result.add_warning(f"Document has {len(document.broken_references)} broken references")
            if document.missing_citations:
                result.add_warning(f"Document has {len(document.missing_citations)} missing citations")

        except Exception as e:
            result.add_error(f"Multi-page HTML generation failed: {str(e)}")

        return result

    def _generate_index_page(self, document: AssembledDocument, output_dir: Path) -> None:
        """Generate the main index page with navigation."""
        template = self._get_index_template()
        context = self._build_template_context(document)

        # Add navigation data
        context["files"] = self._build_file_navigation(document)

        html_content = template.render(**context)
        index_path = output_dir / "index.html"

        with open(index_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    def _generate_individual_pages(self, document: AssembledDocument, output_dir: Path) -> None:
        """Generate individual HTML pages for each markdown file."""
        template = self._get_page_template()

        for file_struct in document.document_structure.files:
            # Create context for this specific file
            context = self._build_page_context(document, file_struct)

            # Render page
            html_content = template.render(**context)

            # Create filename from the file's display name
            safe_name = self._sanitize_filename(file_struct.display_name)
            page_path = output_dir / f"{safe_name}.html"

            with open(page_path, "w", encoding="utf-8") as f:
                f.write(html_content)

    def _copy_shared_resources(self, document: AssembledDocument, output_dir: Path) -> None:
        """
        Copy shared resources like figures to the output directory.

        Collects all figures from _figures directories throughout the project
        and consolidates them into a single _figures directory at the output location.
        """
        import shutil

        # Find the source directory containing the markdown files
        if not document.document_structure.files:
            return

        figures_dst = output_dir / "_figures"

        # Create destination figures directory if it doesn't exist
        figures_dst.mkdir(parents=True, exist_ok=True)

        # Collect all unique _figures directories from the project
        figures_dirs = set()

        # Get project root (common ancestor of all files)
        file_paths = [f.file_path for f in document.document_structure.files]
        if not file_paths:
            return

        # Find common ancestor directory
        common_ancestor = file_paths[0].parent
        for file_path in file_paths[1:]:
            # Walk up until we find a common ancestor
            while not str(file_path).startswith(str(common_ancestor)):
                common_ancestor = common_ancestor.parent
                if common_ancestor.parent == common_ancestor:  # Reached root
                    break

        # Search for all _figures directories under the project root
        try:
            for figures_dir in common_ancestor.rglob("_figures"):
                if figures_dir.is_dir():
                    # Skip if it's the output directory itself (avoid recursion)
                    if figures_dir != figures_dst and not str(figures_dst).startswith(str(figures_dir)):
                        figures_dirs.add(figures_dir)
        except Exception as e:
            print(f"Warning: Error searching for figures directories: {e}")

        # Also check each file's directory for _figures
        for file_struct in document.document_structure.files:
            file_dir = file_struct.file_path.parent
            local_figures = file_dir / "_figures"
            if local_figures.exists() and local_figures.is_dir():
                if local_figures != figures_dst:
                    figures_dirs.add(local_figures)

        # Copy all figures from all _figures directories
        copied_files = set()
        for src_dir in figures_dirs:
            try:
                for src_file in src_dir.iterdir():
                    if src_file.is_file():
                        dst_file = figures_dst / src_file.name

                        # Handle filename conflicts by keeping the first version found
                        if src_file.name not in copied_files:
                            shutil.copy2(src_file, dst_file)
                            copied_files.add(src_file.name)
                        # Could add warning here if same filename exists in multiple places

            except Exception as e:
                print(f"Warning: Failed to copy figures from {src_dir}: {e}")

    def _build_file_navigation(self, document: AssembledDocument) -> list:
        """Build navigation structure for multi-page layout."""
        nav_files = []
        for file_struct in document.document_structure.files:
            safe_name = self._sanitize_filename(file_struct.display_name)
            nav_files.append({
                "title": file_struct.display_name,
                "filename": f"{safe_name}.html",
                "sections": file_struct.parsed_content.sections,
            })
        return nav_files

    def _build_page_context(self, document: AssembledDocument, file_struct) -> dict:
        """Build context for individual page rendering."""
        context = self._build_template_context(document)
        context.update({
            "current_file": file_struct,
            "files": self._build_file_navigation(document),
            "page_title": file_struct.display_name,
        })
        return context

    def _get_index_template(self) -> Template:
        """Get template for index page."""
        try:
            return self.jinja_env.get_template("index.html")
        except Exception:
            return self._create_default_index_template()

    def _get_page_template(self) -> Template:
        """Get template for individual pages."""
        try:
            return self.jinja_env.get_template("page.html")
        except Exception:
            return self._create_default_page_template()

    def _create_default_index_template(self) -> Template:
        """Create default index template with professional title page."""
        index_template = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">
    <style>
        body {
            font-family: "Times New Roman", Georgia, serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            line-height: 1.6;
        }

        /* Professional Title Page */
        .title-page {
            text-align: center;
            padding: 4rem 2rem;
            margin-bottom: 4rem;
            border-bottom: 2px solid #000;
            page-break-after: always;
        }
        .main-title {
            font-size: 2.5rem;
            font-weight: bold;
            color: #000;
            margin-bottom: 2rem;
            line-height: 1.2;
        }
        .subtitle {
            font-size: 1.2rem;
            font-style: italic;
            margin-bottom: 3rem;
            color: #333;
        }
        .author {
            font-size: 1.1rem;
            font-weight: bold;
            margin-bottom: 1rem;
        }
        .date {
            font-size: 1rem;
            color: #666;
            margin-bottom: 2rem;
        }
        .institution {
            font-size: 1rem;
            font-style: italic;
            color: #666;
        }

        /* Table of Contents */
        .toc-section {
            margin: 3rem 0;
        }
        .toc-title {
            font-size: 1.8rem;
            font-weight: bold;
            text-align: center;
            margin-bottom: 2rem;
            color: #000;
        }
        .toc-group {
            margin: 2rem 0;
        }
        .toc-group-title {
            font-size: 1.2rem;
            font-weight: bold;
            color: #000;
            margin-bottom: 1rem;
            border-bottom: 1px solid #eee;
            padding-bottom: 0.5rem;
        }
        .file-link {
            display: block;
            padding: 0.75rem 1rem;
            margin: 0.5rem 0;
            text-decoration: none;
            color: #000;
            border-left: 3px solid transparent;
            transition: all 0.2s ease;
        }
        .file-link:hover {
            background: #f8f9fa;
            border-left-color: #0066cc;
            color: #0066cc;
        }
        .file-link.front-matter {
            font-style: italic;
            color: #666;
        }
        .file-link.front-matter:hover {
            color: #333;
        }

        @media print {
            .title-page {
                page-break-after: always;
            }
            body {
                max-width: none;
                margin: 0;
                padding: 1rem;
            }
        }
    </style>
</head>
<body>
    <!-- Professional Title Page -->
    <div class="title-page">
        <h1 class="main-title">{{ title }}</h1>
        {% if subtitle %}<div class="subtitle">{{ subtitle }}</div>{% endif %}

        {% if author %}
        <div class="author">{{ author }}</div>
        {% endif %}

        {% if date %}
        <div class="date">{{ date }}</div>
        {% endif %}

        {% if institution %}
        <div class="institution">{{ institution }}</div>
        {% endif %}
    </div>

    <!-- Table of Contents -->
    <div class="toc-section">
        <h2 class="toc-title">Table of Contents</h2>

        <!-- Dynamic categorization -->
        {% set front_matter_files = [] %}
        {% set main_files = [] %}
        {% set appendix_files = [] %}

        {% for file in files %}
            {% if is_front_matter(file.title) %}
                {% set _ = front_matter_files.append(file) %}
            {% elif is_appendix(file.title) %}
                {% set _ = appendix_files.append(file) %}
            {% else %}
                {% set _ = main_files.append(file) %}
            {% endif %}
        {% endfor %}

        <!-- Front Matter -->
        {% if front_matter_files %}
        <div class="toc-group">
            <div class="toc-group-title">Front Matter</div>
            {% for file in front_matter_files %}
            <a href="{{ file.filename }}" class="file-link front-matter">{{ file.title }}</a>
            {% endfor %}
        </div>
        {% endif %}

        <!-- Main Content -->
        {% if main_files %}
        <div class="toc-group">
            <div class="toc-group-title">Main Content</div>
            {% for file in main_files %}
            <a href="{{ file.filename }}" class="file-link">{{ file.title }}</a>
            {% endfor %}
        </div>
        {% endif %}

        <!-- Appendices -->
        {% if appendix_files %}
        <div class="toc-group">
            <div class="toc-group-title">Appendices</div>
            {% for file in appendix_files %}
            <a href="{{ file.filename }}" class="file-link">{{ file.title }}</a>
            {% endfor %}
        </div>
        {% endif %}
    </div>
</body>
</html>"""
        return self.jinja_env.from_string(index_template)

    def _create_default_page_template(self) -> Template:
        """Create default page template."""
        page_template = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ page_title }} - {{ title }}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">
    <style>
        body {
            font-family: "Times New Roman", Georgia, serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            line-height: 1.6;
            text-align: justify;
        }
        .nav-bar {
            border-bottom: 1px solid #333;
            padding-bottom: 1rem;
            margin-bottom: 2rem;
            font-size: 0.9em;
        }
        .nav-bar a {
            text-decoration: none;
            color: #0066cc;
            margin-right: 1rem;
        }
        .content {
            margin: 2rem 0;
        }
        /* Professional academic styling */
        h1, h2, h3, h4, h5, h6 {
            color: #000;
            font-family: "Times New Roman", Georgia, serif;
            font-weight: bold;
            margin-top: 2rem;
            margin-bottom: 1rem;
        }
        h1 {
            font-size: 1.8rem;
            text-align: center;
            margin-top: 3rem;
            margin-bottom: 2rem;
        }
        h2 {
            font-size: 1.4rem;
            margin-top: 2rem;
        }
        h3 {
            font-size: 1.2rem;
            margin-top: 1.5rem;
        }
        h4 {
            font-size: 1.1rem;
            margin-top: 1.2rem;
        }

        /* Front matter styling */
        .front-matter h1 {
            text-align: center;
            font-style: italic;
            font-size: 1.6rem;
            margin-bottom: 2rem;
        }
        .front-matter {
            text-align: justify;
            margin-bottom: 3rem;
        }
        .front-matter .content {
            font-style: normal;
        }

        /* Main content styling */
        .main-content h1 {
            text-align: center;
            font-size: 1.8rem;
            margin-top: 3rem;
            margin-bottom: 2rem;
            font-weight: bold;
        }

        img {
            max-width: 100%;
            height: auto;
            display: block;
            margin: 2rem auto;
        }

        /* Table styling */
        .markdown-table {
            border-collapse: collapse;
            width: 100%;
            margin: 1.5rem 0;
            font-size: 0.95em;
        }

        .markdown-table th {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            padding: 0.75rem;
            text-align: left;
            font-weight: 600;
        }

        .markdown-table td {
            border: 1px solid #dee2e6;
            padding: 0.75rem;
        }

        .markdown-table tr:nth-child(even) {
            background-color: #f8f9fa;
        }

        /* Citations and footnotes */
        .citation {
            color: #000;
            font-weight: normal;
        }

        .citation-link {
            color: #0066cc;
            text-decoration: none;
        }

        .citation-link:hover {
            text-decoration: underline;
        }

        /* Footnote styling */
        .footnote-ref {
            color: #0066cc;
            text-decoration: none;
            font-weight: bold;
        }

        .footnote-ref:hover {
            text-decoration: underline;
        }

        .footnotes {
            margin-top: 3rem;
            border-top: 1px solid #ccc;
            padding-top: 2rem;
            font-size: 0.9em;
        }

        .footnote {
            margin: 0.5rem 0;
            padding-left: 1.5rem;
            text-indent: -1.5rem;
        }

        .footnote-number {
            font-weight: bold;
            margin-right: 0.5rem;
        }

        .footnote-backref {
            margin-left: 0.5rem;
            font-size: 0.8em;
            color: #0066cc;
            text-decoration: none;
        }

        .footnote-backref:hover {
            text-decoration: underline;
        }

        /* Internal link styling */
        .internal-link {
            color: #0066cc;
            font-weight: normal;
            font-style: italic;
        }

        /* Missing citation styling */
        .citation.missing {
            color: #cc0000;
            font-weight: bold;
        }

        /* PDF page break styling */
        @media print {
            .page-break {
                page-break-before: always;
            }
            .front-matter {
                page-break-after: always;
            }
            body {
                max-width: none;
                margin: 0;
                padding: 1rem;
            }
        }
    </style>
</head>
<body>
    <div class="nav-bar">
        <a href="index.html">← Back to Contents</a>
        <span style="float: right;">
            {% for file in files %}
                {% if file.title == page_title %}
                    <strong>{{ file.title }}</strong>
                {% else %}
                    <a href="{{ file.filename }}">{{ file.title }}</a>
                {% endif %}
                {% if not loop.last %} | {% endif %}
            {% endfor %}
        </span>
    </div>

    {% set front_matter_class = 'front-matter' if is_front_matter(current_file) else 'main-content' %}
    {% set page_break_class = ' page-break' if is_new_part(current_file) else '' %}
    <div class="content {{ front_matter_class }}{{ page_break_class }}">
        <h1>{{ page_title }}</h1>
        {% for section in current_file.parsed_content.sections %}
        <section id="{{ section.id }}">
            <h{{ section.level + 1 }}>{{ section.title }}</h{{ section.level + 1 }}>
            {% set section_data = process_section_content(section.content) %}
            <div>{{ section_data.content | markdown_to_html | safe }}</div>
            {% if section_data.footnotes %}
            <div class="section-footnotes">
                {% for footnote in section_data.footnotes %}
                <div class="footnote-item">
                    <sup>{{ footnote.number }}</sup> {{ footnote.content | markdown_to_html | safe }}
                </div>
                {% endfor %}
            </div>
            {% endif %}
        </section>
        {% endfor %}
    </div>

    <script src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/contrib/auto-render.min.js"></script>
    <script>
        document.addEventListener("DOMContentLoaded", function() {
            renderMathInElement(document.body, {
                delimiters: [
                    {left: '$$', right: '$$', display: true},
                    {left: '$', right: '$', display: false}
                ],
                throwOnError: false,
                processEscapes: true,
                processEnvironments: true
            });
        });
    </script>
</body>
</html>"""
        return self.jinja_env.from_string(page_template)

    def _get_html_template(self) -> Template:
        """Get or create the main HTML template."""
        try:
            return self.jinja_env.get_template("document.html")
        except Exception:
            # Create a default template if none exists
            return self._create_default_template()

    def _create_default_template(self) -> Template:
        """Create a basic default HTML template."""
        default_template = r"""{% macro render_sections(sections) %}
{% for section in sections %}
<section class="section" id="{{ section.id | section_anchor }}">
    <h{{ section.level }}>{{ section.title }}</h{{ section.level }}>
    <div class="section-content">
        {% set section_data = process_section_content(section.content) %}
        {{ section_data.content | markdown_to_html | safe }}
        {% if section_data.footnotes %}
        <div class="section-footnotes">
            {% for footnote in section_data.footnotes %}
            <div class="footnote-item">
                <sup>{{ footnote.number }}</sup> {{ footnote.content | markdown_to_html | safe }}
            </div>
            {% endfor %}
        </div>
        {% endif %}
    </div>
    {{ render_sections(section.subsections) }}
</section>
{% endfor %}
{% endmacro %}

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>

    <!-- KaTeX CSS for math rendering -->
    <link rel="stylesheet"
          href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css"
          integrity="sha384-GvrOXuhMATgEsSwCs4smul74iXGOixntILdUW9XmUC6+HX0sLNAK3q71HotJqlAn"
          crossorigin="anonymous">

    <style>
        body {
            font-family: "Times New Roman", Georgia, serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            color: #000;
            text-align: justify;
        }

        h1, h2, h3, h4, h5, h6 {
            font-family: "Times New Roman", Georgia, serif;
            margin-top: 2rem;
            margin-bottom: 1rem;
            color: #000;
            font-weight: bold;
        }

        /* Chapter headers (h1) - centered */
        h1 {
            font-size: 1.8rem;
            text-align: center;
            margin-top: 3rem;
            margin-bottom: 2rem;
        }

        /* Section headers (h2) - left aligned */
        h2 {
            font-size: 1.4rem;
            text-align: left;
            margin-top: 2rem;
            margin-bottom: 1rem;
        }

        /* Subsection headers (h3+) - left aligned */
        h3 {
            font-size: 1.2rem;
            text-align: left;
            margin-top: 1.5rem;
            margin-bottom: 0.8rem;
        }

        h4 {
            font-size: 1.1rem;
            text-align: left;
            margin-top: 1.2rem;
            margin-bottom: 0.6rem;
        }

        h5 {
            font-size: 1.05rem;
            text-align: left;
            margin-top: 1rem;
            margin-bottom: 0.5rem;
        }

        h6 {
            font-size: 1rem;
            text-align: left;
            margin-top: 1rem;
            margin-bottom: 0.5rem;
        }

        /* Professional Title Page */
        .title-page {
            text-align: center;
            padding: 4rem 2rem;
            margin-bottom: 4rem;
            border-bottom: 2px solid #000;
            page-break-after: always;
        }
        .main-title {
            font-size: 2.5rem;
            font-weight: bold;
            color: #000;
            margin-bottom: 2rem;
            line-height: 1.2;
        }
        .subtitle {
            font-size: 1.2rem;
            font-style: italic;
            margin-bottom: 3rem;
            color: #333;
        }
        .author {
            font-size: 1.1rem;
            font-weight: bold;
            margin-bottom: 1rem;
        }
        .date {
            font-size: 1rem;
            color: #666;
            margin-bottom: 2rem;
        }
        .institution {
            font-size: 1rem;
            font-style: italic;
            color: #666;
        }

        /* Chapter Title Page - for Roman numeral chapters */
        .chapter-title-page {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            min-height: 80vh;
            text-align: center;
            page-break-before: always;
            page-break-after: always;
        }

        .chapter-title-page h1 {
            font-size: 2.2rem;
            font-weight: bold;
            color: #000;
            margin: 0;
            padding: 0;
        }

        @media print {
            .chapter-title-page {
                height: 100vh;
                page-break-before: always;
                page-break-after: always;
            }
        }

        .table-of-contents {
            margin: 3rem 0;
            padding: 0;
            page-break-after: always; /* Ensure TOC gets its own page */
        }

        .table-of-contents h2 {
            text-align: center;
            margin-top: 0;
            margin-bottom: 3rem;
            color: #000;
            font-size: 1.8rem;
            font-weight: bold;
        }

        .toc-entry {
            margin: 0.2rem 0;
            line-height: 1.4;
        }

        .toc-entry a {
            text-decoration: none;
            color: #000;
            display: block;
            padding: 0.1rem 0;
        }

        .toc-entry a:hover {
            color: #0066cc;
            text-decoration: none;
        }

        /* Book-style TOC formatting */
        .toc-level-1 {
            margin-left: 0;
            font-weight: bold;
            font-size: 1.1rem;
            margin-top: 0.8rem;
            margin-bottom: 0.3rem;
        }

        .toc-level-2 {
            margin-left: 1rem;
            font-weight: normal;
            font-size: 1rem;
            margin-top: 0.2rem;
        }

        .toc-level-3 {
            margin-left: 2rem;
            font-weight: normal;
            font-size: 0.95rem;
            margin-top: 0.1rem;
        }

        .toc-level-4 {
            display: none; /* Hide level 4+ for book TOC */
        }

        .section {
            margin: 2rem 0;
        }

        .section-content {
            margin: 1rem 0;
        }

        code {
            font-family: "Courier New", "Courier", monospace;
            font-size: 0.9em;
            background: none;
            border: none;
            padding: 0;
        }

        pre {
            font-family: "Courier New", "Courier", monospace;
            background: none;
            border: 1px solid #000;
            padding: 1rem;
            overflow-x: auto;
            margin: 1rem 0;
        }

        pre code {
            background: none;
            border: none;
            padding: 0;
        }

        /* List styling */
        ol, ul {
            margin: 1rem 0;
            padding-left: 2rem;
        }

        li {
            margin: 0.5rem 0;
            line-height: 1.6;
        }

        ol li {
            list-style-type: decimal;
        }

        ul li {
            list-style-type: disc;
        }

        /* Table styling */
        .markdown-table {
            border-collapse: collapse;
            width: 100%;
            margin: 1.5rem 0;
            font-size: 0.95em;
        }

        .markdown-table th {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            padding: 0.75rem;
            text-align: left;
            font-weight: 600;
        }

        .markdown-table td {
            border: 1px solid #dee2e6;
            padding: 0.75rem;
        }

        .markdown-table tr:nth-child(even) {
            background-color: #f8f9fa;
        }

        .citation {
            color: #000;
            font-weight: normal;
        }

        .citation-link {
            color: #0066cc;
            text-decoration: none;
        }

        .citation-link:hover {
            text-decoration: underline;
        }

        /* Footnote styling */
        .footnote-ref {
            color: #0066cc;
            text-decoration: none;
            font-weight: bold;
        }

        .footnote-ref:hover {
            text-decoration: underline;
        }

        .footnotes {
            margin-top: 3rem;
            border-top: 1px solid #ccc;
            padding-top: 2rem;
            font-size: 0.9em;
        }

        .footnote {
            margin: 0.5rem 0;
            padding-left: 1.5rem;
            text-indent: -1.5rem;
        }

        .footnote-number {
            font-weight: bold;
            margin-right: 0.5rem;
        }

        .footnote-backref {
            margin-left: 0.5rem;
            font-size: 0.8em;
            color: #0066cc;
            text-decoration: none;
        }

        .footnote-backref:hover {
            text-decoration: underline;
        }

        /* Internal link styling */
        .internal-link {
            color: #0066cc;
            font-weight: normal;
            font-style: italic;
        }

        /* Missing citation styling */
        .citation.missing {
            color: #cc0000;
            font-weight: bold;
        }

        .broken-reference {
            color: #000;
            font-weight: bold;
            text-decoration: underline;
        }

        .bibliography {
            margin-top: 3rem;
            border-top: 1px solid #000;
            padding-top: 2rem;
        }

        .bibliography h2 {
            text-align: center;
        }

        .bib-entry {
            margin: 1rem 0;
            padding-left: 2rem;
            text-indent: -2rem;
        }

        /* Section-level footnotes */
        .section-footnotes {
            margin-top: 1.5em;
            padding-top: 1em;
            border-top: 1px solid #ddd;
            font-size: 0.9em;
            line-height: 1.3;
        }

        .section-footnotes .footnote-item {
            margin-bottom: 0.5em;
            display: block;
        }

        .section-footnotes .footnote-item sup {
            font-weight: bold;
            color: #666;
            margin-right: 0.3em;
        }

        .section-footnotes .footnote-item p {
            display: inline;
        }

        /* KaTeX equation styling */
        .katex-display {
            margin: 1.5rem 0;
            text-align: center;
        }

        .katex {
            font-size: 1.1em;
        }

        .katex-display .katex {
            font-size: 1.2em;
        }

        /* File content styling */
        .file-content {
            margin: 2rem 0;
        }

        /* Professional page breaks for PDF */
        .page-break {
            page-break-before: always;
        }

        .front-matter {
            page-break-after: always;
        }

        .front-matter h2 {
            font-style: italic;
            text-align: center;
            font-size: 1.6rem;
        }

        @media print {
            body {
                max-width: none;
                margin: 0;
                padding: 1rem;
                counter-reset: frontmatter-page chapter-page;
            }

            .page-break { page-break-before: always; }

            /* Title page */
            .title-page {
                page-break-after: always;
                page: title-page;
            }

            /* TOC and front matter use roman numerals */
            .table-of-contents {
                counter-increment: frontmatter-page;
                page: frontmatter;
            }

            .front-matter {
                counter-increment: frontmatter-page;
                page: frontmatter;
            }

            /* First main content section resets and starts arabic numbering */
            .main-content:first-of-type {
                counter-reset: chapter-page;
                counter-increment: chapter-page;
                page: chapter;
            }

            /* Subsequent main content continues arabic numbering */
            .main-content:not(:first-of-type) {
                counter-increment: chapter-page;
                page: chapter;
            }

            /* Page layouts */
            @page {
                margin: 1in;
            }

            /* Title page - no page number */
            @page title-page {
                @bottom-center { content: none; }
            }

            /* Front matter pages - roman numerals */
            @page frontmatter {
                @bottom-center {
                    content: counter(frontmatter-page, lower-roman);
                    font-size: 10pt;
                }
            }

            /* Chapter pages - arabic numerals starting from 1 */
            @page chapter {
                @bottom-center {
                    content: counter(chapter-page, decimal);
                    font-size: 10pt;
                }
            }
        }
    </style>
</head>
<body>
    <!-- Professional Title Page -->
    <div class="title-page">
        <h1 class="main-title">{{ title }}</h1>
        {% if subtitle %}<div class="subtitle">{{ subtitle }}</div>{% endif %}
        {% if author %}<div class="author">{{ author }}</div>{% endif %}
        {% if date %}<div class="date">{{ date }}</div>{% endif %}
        {% if institution %}<div class="institution">{{ institution }}</div>{% endif %}
    </div>

    {% if table_of_contents %}
    <nav class="table-of-contents">
        <h2>Table of Contents</h2>
        {% for entry in table_of_contents %}
        <div class="toc-entry toc-level-{{ entry.level }}">
            <a href="#{{ entry.id | section_anchor }}">{{ entry.number }} {{ entry.title }}</a>
        </div>
        {% endfor %}
    </nav>
    {% endif %}

    <main class="document-body">
        {% for file_struct in document_structure.files %}
        {% set is_fm = is_front_matter(file_struct) %}
        {% set fm_class = ' front-matter' if is_fm else ' main-content' %}
        {% set pb_class = ' page-break' if is_new_part(file_struct) else '' %}
        {% if file_struct.is_first_in_chapter and file_struct.chapter_title %}
        <!-- Chapter Title Page -->
        <div class="chapter-title-page">
            <h1>{{ file_struct.chapter_title }}</h1>
        </div>
        {% endif %}
        <div class="file-content{{ fm_class }}{{ pb_class }}">
            {{ render_sections(file_struct.parsed_content.sections) }}
        </div>
        {% endfor %}
    </main>

    {% if footnotes %}
    <section class="footnotes">
        <h2>Footnotes</h2>
        {% for footnote in footnotes %}
        <div id="fn{{ footnote.number }}" class="footnote">
            <span class="footnote-number">{{ footnote.number }}.</span>
            {{ footnote.content }}
            <a href="#fnref{{ footnote.number }}" class="footnote-backref">↩</a>
        </div>
        {% endfor %}
    </section>
    {% endif %}

    {% if bibliography %}
    <section class="bibliography">
        <h2>References</h2>
        {% for entry in bibliography %}
        <div id="ref-{{ entry.key }}" class="bib-entry">
            [{{ loop.index }}] {{ entry.author }} ({{ entry.year }}).
            <em>{{ entry.title }}</em>.
            {% if entry.journal %}{{ entry.journal }}.{% endif %}
        </div>
        {% endfor %}
    </section>
    {% endif %}


    <!-- KaTeX JavaScript for math rendering -->
    <script defer
            src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.js"
            integrity="sha384-cpW21h6RZv/phavutF+AuVYrr+dA8xD9zs6FwLpaCct6O9ctzYFfFr4dgmgccOTx"
            crossorigin="anonymous"></script>
    <script defer
            src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/contrib/auto-render.min.js"
            integrity="sha384-+VBxd3r6XgURycqtZ117nYw44OOcIax56Z4dCRWbxyPt0Koah1uHoK0o4+/RRE05"
            crossorigin="anonymous"></script>
    <script>
        document.addEventListener("DOMContentLoaded", function() {
            renderMathInElement(document.body, {
                // Delimiters for inline and display math
                delimiters: [
                    {left: '$$', right: '$$', display: true},
                    {left: '$', right: '$', display: false},
                    {left: '\\(', right: '\\)', display: false},
                    {left: '\\[', right: '\\]', display: true}
                ],
                // Skip text nodes inside these tags
                ignoredTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code'],
                // Options for math rendering
                throwOnError: false,
                errorColor: '#cc0000',
                // More precise processing options
                processEscapes: true,
                processEnvironments: true,
                // Trust KaTeX to properly distinguish \( from (
                trust: false,
                strict: 'warn',
                // Disable automatic equation numbering
                fleqn: false,
                leqno: false
            });
        });
    </script>
</body>
</html>"""

        return self.jinja_env.from_string(default_template)

    def _build_template_context(self, document: AssembledDocument) -> Dict:
        """Build the context dictionary for template rendering."""
        # Collect all footnotes from document
        footnotes = self._build_footnotes_context(document)

        return {
            "title": document.title,
            "author": document.author,
            "date": document.date,
            "abstract": document.abstract,
            "table_of_contents": document.table_of_contents,
            "document_structure": document.document_structure,
            "bibliography": document.bibliography,
            "reference_map": document.reference_map,
            "citation_database": document.citation_database,
            "footnotes": footnotes,  # Add footnotes to context
            # Statistics
            "stats": {
                "total_files": document.total_files,
                "total_sections": document.total_sections,
                "total_references": document.total_references,
                "total_citations": document.total_citations,
            },
            # Warnings and errors for debugging
            "issues": {
                "broken_references": len(document.broken_references),
                "missing_citations": len(document.missing_citations),
                "warnings": len(document.validation_warnings),
            },
            # Helper functions for document structure
            "is_front_matter": self._is_front_matter,
            "is_appendix": self._is_appendix,
            "is_new_part": self._is_new_part,
            "process_section_content": lambda content: self._process_section_content_and_footnotes(content, footnotes),
        }

    def _generate_section_anchor(self, section_id: str) -> str:
        """Generate URL-safe anchor for section linking."""
        return section_id.lower().replace(" ", "-")

    def _get_citation_number(self, key: str) -> Optional[int]:
        """Get the citation number for a bibliography key based on order of appearance."""
        # Initialize citation mapping if not exists
        if not hasattr(self, "_citation_mapping"):
            self._citation_mapping = {}
            self._citation_counter = 0

        # If we've seen this key before, return its number
        if key in self._citation_mapping:
            return self._citation_mapping[key]

        # Otherwise, assign a new number
        self._citation_counter += 1
        self._citation_mapping[key] = self._citation_counter
        return self._citation_counter

    def _regex_match_filter(self, text: str, pattern: str) -> bool:
        """Jinja2 filter for regex matching."""
        import re

        return bool(re.match(pattern, text))

    def _regex_match_test(self, text: str, pattern: str) -> bool:
        """Jinja2 test for regex matching."""
        import re

        return bool(re.match(pattern, text))

    def _is_front_matter(self, file_or_title) -> bool:
        """Check if a file or title is front matter."""
        # Extract title from file struct or use as string
        if hasattr(file_or_title, "display_name"):
            title = file_or_title.display_name
            file_path = str(file_or_title.relative_path)
        else:
            title = str(file_or_title)
            file_path = title

        # Check if file is in front matter directory (starts with "0." or contains "Front Matter")
        if "0." in file_path or "Front Matter" in file_path:
            return True

        # Check if title matches common front matter patterns
        front_matter_titles = {"preface", "overview", "abstract", "foreword", "introduction"}
        if title.lower() in front_matter_titles:
            return True

        # Check if title starts with roman numerals
        import re

        if re.match(r"^(i{1,3}v?|iv|v|vi{0,3}|ix|x)\.?\s", title.lower()):
            return True

        return False

    def _is_appendix(self, file_or_title) -> bool:
        """Check if a file or title is an appendix based on latin letter prefix."""
        # Extract title from file struct or use as string
        if hasattr(file_or_title, "display_name"):
            title = file_or_title.display_name
            file_path = str(file_or_title.relative_path)
        else:
            title = str(file_or_title)
            file_path = title

        # Check if file is in appendix/appendices directory
        import re

        if re.search(r"[/\\][Aa]ppendix|[Aa]ppendices", file_path):
            return True

        # Check if title starts with latin letters (A., B., C., etc.)
        if re.match(r"^[A-Za-z]\.?\s", title):
            return True

        # Check if title contains common appendix words
        appendix_patterns = {"appendix", "literature", "bibliography", "references"}
        if any(pattern in title.lower() for pattern in appendix_patterns):
            return True

        return False

    def _is_new_part(self, file_or_title) -> bool:
        """Check if a file or title starts a new major part."""
        # Extract title and path from file struct or use as string
        if hasattr(file_or_title, "display_name"):
            title = file_or_title.display_name
            file_path = str(file_or_title.relative_path)
        else:
            title = str(file_or_title)
            file_path = title

        # Check if this is the first file in a numbered directory
        import re

        # Pattern: directory starting with number or letter, file starting with "1."
        if re.search(r"[/\\][0-9A-Z]\.[^/\\]+[/\\]1\.[^/\\]+\.md$", file_path):
            return True

        # Check if file is in appendix directory
        if re.search(r"[/\\][A-Z]\.[^/\\]*[Aa]ppendix[^/\\]*[/\\]", file_path):
            return True

        return False

    def _markdown_to_html(self, markdown_content: str) -> str:
        """Convert markdown content to HTML while preserving LaTeX equations."""
        import re

        html = markdown_content

        # Convert numbered LaTeX environments to unnumbered ones BEFORE protecting math blocks
        html = re.sub(r"\\begin\{align\}", r"\\begin{aligned}", html)
        html = re.sub(r"\\end\{align\}", r"\\end{aligned}", html)
        html = re.sub(r"\\begin\{gather\}", r"\\begin{gathered}", html)
        html = re.sub(r"\\end\{gather\}", r"\\end{gathered}", html)
        html = re.sub(r"\\begin\{equation\}", r"", html)
        html = re.sub(r"\\end\{equation\}", r"", html)

        # First, protect LaTeX equations, code blocks, and HTML tags from processing
        # Find display math $$...$$ and inline math $...$
        protected_blocks = []
        block_counter = 0

        # Protect fenced code blocks FIRST (before math, since ``` can contain $)
        def replace_code_block(match):
            nonlocal block_counter
            match.group(1) or ""  # Optional language identifier
            code_content = match.group(2)
            # Convert to HTML code block
            html_code = f"<pre><code>{code_content}</code></pre>"
            placeholder = f"⟦CODEBLOCK{block_counter}⟧"
            protected_blocks.append((placeholder, html_code))
            block_counter += 1
            return placeholder

        # Match ```language\ncode\n``` or ```\ncode\n```
        html = re.sub(r"```(\w+)?\n(.*?)```", replace_code_block, html, flags=re.DOTALL)
        # Also handle ~~~ style code blocks
        html = re.sub(r"~~~(\w+)?\n(.*?)~~~", replace_code_block, html, flags=re.DOTALL)

        # Protect display math ($$...$$)
        def replace_display_math(match):
            nonlocal block_counter
            placeholder = f"⟦MATHBLOCK{block_counter}⟧"
            protected_blocks.append((placeholder, match.group(0)))
            block_counter += 1
            return placeholder

        html = re.sub(r"\$\$(.*?)\$\$", replace_display_math, html, flags=re.DOTALL)

        # Protect inline math ($...$) - but not escaped \$ or double $$
        def replace_inline_math(match):
            nonlocal block_counter
            placeholder = f"⟦MATHBLOCK{block_counter}⟧"
            protected_blocks.append((placeholder, match.group(0)))
            block_counter += 1
            return placeholder

        html = re.sub(r"(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)", replace_inline_math, html)

        # Protect HTML tags from markdown processing
        def replace_html_tags(match):
            nonlocal block_counter
            placeholder = f"⟦HTMLBLOCK{block_counter}⟧"
            protected_blocks.append((placeholder, match.group(0)))
            block_counter += 1
            return placeholder

        html = re.sub(r"<[^>]+>", replace_html_tags, html)

        # Process markdown tables before lists and paragraphs
        html = self._process_tables(html)

        # Process lists before paragraph processing
        html = self._process_lists(html)

        # Convert **bold** to <strong>
        html = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", html)

        # Convert _italic_ to <em>
        html = re.sub(r"_([^_]+?)_", r"<em>\1</em>", html)

        # Convert *italic* to <em> (but avoid ** patterns)
        html = re.sub(r"(?<!\*)\*(?!\*)([^*]+?)\*(?!\*)", r"<em>\1</em>", html)

        # Convert `code` to <code>
        html = re.sub(r"`([^`]+)`", r"<code>\1</code>", html)

        # Process footnotes with [^{#}] syntax
        footnote_counter = 0
        footnotes = []

        def process_footnote(match):
            nonlocal footnote_counter
            footnote_counter += 1
            footnote_id = match.group(1)
            footnotes.append({"id": footnote_id, "number": footnote_counter, "content": footnote_id})
            return (
                f'<sup><a href="#fn{footnote_counter}" id="fnref{footnote_counter}" '
                f'class="footnote-ref">{footnote_counter}</a></sup>'
            )

        html = re.sub(r"\[\^\{([^}]+)\}\]", process_footnote, html)

        # Store footnotes for later use (could be added to document context)
        if hasattr(self, "_current_footnotes"):
            self._current_footnotes.extend(footnotes)
        else:
            self._current_footnotes = footnotes

        # Process all citation formats with a single, comprehensive approach
        def process_citation(match):
            """Process any citation format: [@key], [@key1; @key2], or @key"""
            citation_text = match.group(1) or match.group(2)  # Handle both bracketed and standalone

            # Extract keys - handle semicolon and comma separation
            if ";" in citation_text:
                keys = [k.strip().lstrip("@") for k in citation_text.split(";")]
            elif "," in citation_text:
                keys = [k.strip().lstrip("@") for k in citation_text.split(",")]
            else:
                keys = [citation_text.lstrip("@")]

            # Convert keys to citation links
            citation_links = []
            for key in keys:
                key = key.strip()
                if key:
                    citation_number = self._get_citation_number(key)
                    if citation_number:
                        citation_links.append(f'<a href="#ref-{key}" class="citation-link">{citation_number}</a>')
                    else:
                        citation_links.append(f'<a href="#ref-{key}" class="citation-link missing">{key}</a>')

            if not citation_links:
                return match.group(0)  # Return original if no valid keys

            # Join multiple citations with commas and wrap in brackets
            citation_content = ", ".join(citation_links)
            return f'<span class="citation">[{citation_content}]</span>'

        # Process all citation formats in one pass
        # Matches: [@key1; @key2] or [@key] or @key (but not @key inside words)
        html = re.sub(r"\[(@[^]]+)\]|@([a-zA-Z][a-zA-Z0-9-_:]*)(?![a-zA-Z0-9-_:])", process_citation, html)

        # Handle [[wikilinks]] - only for internal links now
        def process_wikilink(match):
            content = match.group(1)
            return f'<span class="internal-link">{content}</span>'

        html = re.sub(r"\[\[([^\]]+)\]\]", process_wikilink, html)

        # Convert paragraphs (double newlines), but preserve list HTML
        paragraphs = html.split("\n\n")
        processed_paragraphs = []

        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
            # Don't wrap lists or tables in paragraph tags
            if (
                p.startswith("<ol>")
                or p.startswith("<ul>")
                or p.startswith("</ol>")
                or p.startswith("</ul>")
                or p.startswith("<table")
            ):
                processed_paragraphs.append(p)
            else:
                # Convert single newlines to <br> within paragraphs
                p = p.replace("\n", "<br>")
                processed_paragraphs.append(f"<p>{p}</p>")

        html = "".join(processed_paragraphs)

        # Restore LaTeX equations and HTML tags
        for placeholder, protected_expr in protected_blocks:
            html = html.replace(placeholder, protected_expr)

        return html

    def _process_lists(self, text: str) -> str:
        """Process markdown lists and convert them to proper HTML lists."""
        import re

        lines = text.split("\n")
        result_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # Check for numbered list
            if re.match(r"^\d+\.\s+", line):
                list_html, i = self._process_ordered_list(lines, i)
                result_lines.append(list_html)
            # Check for bulleted list
            elif re.match(r"^[-*]\s+", line):
                list_html, i = self._process_unordered_list(lines, i)
                result_lines.append(list_html)
            else:
                result_lines.append(line)
                i += 1

        return "\n".join(result_lines)

    def _process_ordered_list(self, lines, start_index):
        """Process a numbered list starting at start_index."""
        import re

        list_items = []
        i = start_index

        while i < len(lines):
            line = lines[i]
            if re.match(r"^\d+\.\s+", line):
                # Extract list item content
                content = re.sub(r"^\d+\.\s+", "", line)
                list_items.append(f"<li>{content}</li>")
                i += 1

                # Skip empty lines after list items
                while i < len(lines) and lines[i].strip() == "":
                    i += 1
                # Check if next line is also a list item, if not, end the list
                if i >= len(lines) or not re.match(r"^\d+\.\s+", lines[i]):
                    break
            else:
                # End of list
                break

        html = "<ol>" + "".join(list_items) + "</ol>"
        return html, i

    def _process_unordered_list(self, lines, start_index):
        """Process a bulleted list starting at start_index."""
        import re

        list_items = []
        i = start_index

        while i < len(lines):
            line = lines[i]
            if re.match(r"^[-*]\s+", line):
                # Extract list item content
                content = re.sub(r"^[-*]\s+", "", line)
                list_items.append(f"<li>{content}</li>")
                i += 1

                # Skip empty lines after list items
                while i < len(lines) and lines[i].strip() == "":
                    i += 1
                # Check if next line is also a list item, if not, end the list
                if i >= len(lines) or not re.match(r"^[-*]\s+", lines[i]):
                    break
            else:
                # End of list
                break

        html = "<ul>" + "".join(list_items) + "</ul>"
        return html, i

    def _process_tables(self, text: str) -> str:
        """Process markdown tables and convert them to HTML tables."""
        import re

        lines = text.split("\n")
        result_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # Check if this line looks like a table (starts with |)
            if line.strip().startswith("|") and i + 1 < len(lines):
                # Look ahead to see if next line is a separator (|---|---|)
                next_line = lines[i + 1].strip()
                if re.match(r"^\|[\s\-:|]+\|$", next_line):
                    # This is a table! Process it
                    table_html, new_i = self._process_single_table(lines, i)
                    result_lines.append(table_html)
                    i = new_i
                else:
                    result_lines.append(line)
                    i += 1
            else:
                result_lines.append(line)
                i += 1

        return "\n".join(result_lines)

    def _process_single_table(self, lines, start_index):
        """Process a single markdown table starting at start_index."""

        i = start_index
        header_line = lines[i].strip()
        lines[i + 1].strip() if i + 1 < len(lines) else ""

        # Parse header
        header_cells = [cell.strip() for cell in header_line.split("|")[1:-1]]

        # Skip separator line
        i += 2

        # Parse table rows
        table_rows = []
        while i < len(lines):
            line = lines[i].strip()
            if not line.startswith("|"):
                break

            # Parse row cells
            cells = [cell.strip() for cell in line.split("|")[1:-1]]
            table_rows.append(cells)
            i += 1

        # Build HTML table
        html_parts = ['<table class="markdown-table">']

        # Add header
        html_parts.append("<thead>")
        html_parts.append("<tr>")
        for cell in header_cells:
            html_parts.append(f"<th>{cell}</th>")
        html_parts.append("</tr>")
        html_parts.append("</thead>")

        # Add body
        if table_rows:
            html_parts.append("<tbody>")
            for row in table_rows:
                html_parts.append("<tr>")
                for cell in row:
                    html_parts.append(f"<td>{cell}</td>")
                html_parts.append("</tr>")
            html_parts.append("</tbody>")

        html_parts.append("</table>")

        return "\n".join(html_parts), i

    def _build_footnotes_context(self, document: AssembledDocument) -> Dict:
        """Build footnotes context from AssembledDocument."""
        footnotes = {}

        # Build mapping from identifier to definition
        for footnote_def in document.footnote_definitions:
            footnotes[footnote_def.identifier] = {
                "number": footnote_def.number,
                "content": footnote_def.content,
                "identifier": footnote_def.identifier,
            }

        return footnotes

    def _process_footnotes_in_content(self, content: str, footnotes: Dict) -> tuple[str, list]:
        """Process footnote references in content, returning processed content and section footnotes."""
        import re

        section_footnotes = []

        def replace_footnote_ref(match):
            identifier = match.group(1)
            if identifier in footnotes:
                footnote = footnotes[identifier]
                # Track this footnote for the current section
                section_footnotes.append(footnote)
                # Simple superscript number
                return f"<sup>{footnote['number']}</sup>"
            else:
                # Keep original if no definition found
                return match.group(0)

        # Replace footnote references [^id] with simple superscript numbers
        footnote_ref_pattern = re.compile(r"\[\^([^\]]+)\]")
        processed_content = footnote_ref_pattern.sub(replace_footnote_ref, content)

        # Remove footnote definitions [^id]: content from the main text completely
        footnote_def_pattern = re.compile(r"^\[\^([^\]]+)\]:\s*(.*?)(?=^\[\^|\Z)", re.MULTILINE | re.DOTALL)
        processed_content = footnote_def_pattern.sub("", processed_content)

        # Clean up extra whitespace left by removed definitions
        processed_content = re.sub(r"\n\s*\n\s*\n", "\n\n", processed_content)

        return processed_content, section_footnotes

    def _process_section_content_and_footnotes(self, content: str, global_footnotes: Dict) -> Dict:
        """Process a section's content independently for footnotes."""
        import re

        section_footnotes = []
        footnote_counter = 1

        # First, find and extract all footnote definitions [^id]: content
        footnote_defs = {}
        def_pattern = re.compile(r"^\[\^([^\]]+)\]:\s*(.*?)(?=^\[\^|\Z)", re.MULTILINE | re.DOTALL)
        for match in def_pattern.finditer(content):
            identifier = match.group(1).strip()
            definition = match.group(2).strip()
            footnote_defs[identifier] = definition

        # Remove all footnote definitions from content first
        processed_content = def_pattern.sub("", content)

        # Now find standalone footnote references [^id] (not part of definitions)
        ref_pattern = re.compile(r"\[\^([^\]]+)\]")

        # Process each standalone reference
        for match in ref_pattern.finditer(processed_content):
            ref_id = match.group(1).strip()
            if ref_id in footnote_defs:
                # Add to section footnotes if not already added
                if not any(fn["identifier"] == ref_id for fn in section_footnotes):
                    section_footnotes.append({
                        "identifier": ref_id,
                        "number": footnote_counter,
                        "content": footnote_defs[ref_id],
                    })
                    footnote_counter += 1

        # Replace all standalone references with superscript numbers
        def replace_ref(match):
            ref_id = match.group(1).strip()
            # Find the footnote number for this identifier
            for footnote in section_footnotes:
                if footnote["identifier"] == ref_id:
                    return f"<sup>{footnote['number']}</sup>"
            return match.group(0)  # Keep original if no definition found

        processed_content = ref_pattern.sub(replace_ref, processed_content)

        # Clean up extra whitespace
        processed_content = re.sub(r"\n\s*\n\s*\n", "\n\n", processed_content)

        return {"content": processed_content, "footnotes": section_footnotes}
