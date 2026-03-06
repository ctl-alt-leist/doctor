"""
Doctor document generators

CSS/HTML-first approach to document generation:
- HTML Generator: Primary output format with semantic HTML + CSS
- PDF Generator: HTML-to-PDF conversion for print/submission
- Base templates and styling system
"""

from doctor.generators.base import BaseGenerator, GenerationResult
from doctor.generators.html import HTMLGenerator
from doctor.generators.pdf import PDFGenerator


__all__ = [
    "BaseGenerator",
    "GenerationResult",
    "HTMLGenerator",
    "PDFGenerator",
]
