"""
Base document generator interface and common utilities
"""

from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

from pydantic import BaseModel

from doctor.ingest.assembly import AssembledDocument


if TYPE_CHECKING:
    from doctor.configs.models import Config


class OutputFormat(str, Enum):
    """Supported output formats."""

    HTML = "html"
    PDF = "pdf"
    DOCX = "docx"
    SLIDES = "slides"


class GenerationResult(BaseModel):
    """Result of document generation."""

    success: bool
    output_path: Path
    format: OutputFormat
    file_size: int = 0
    generation_time: float = 0.0
    warnings: List[str] = []
    errors: List[str] = []

    @property
    def is_valid(self) -> bool:
        """Check if generation was successful with no errors."""
        return self.success and len(self.errors) == 0

    def add_warning(self, message: str):
        """Add a warning message."""
        self.warnings.append(message)

    def add_error(self, message: str):
        """Add an error message."""
        self.errors.append(message)
        self.success = False


class BaseGenerator(ABC):
    """
    Abstract base class for all document generators.

    Provides common interface and utilities for generating documents
    from AssembledDocument objects.
    """

    def __init__(self, build_dir: Path, output_format: OutputFormat, config: Optional["Config"] = None):
        self.build_dir = build_dir
        self.format = output_format
        self.config = config
        self.build_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def generate(self, document: AssembledDocument, output_path: Path) -> GenerationResult:
        """
        Generate document in the target format.

        Args:
            document: Assembled document from ingestion pipeline
            output_path: Path where generated document should be saved

        Returns:
            GenerationResult: Result with success status and metadata
        """
        pass

    def _create_result(self, output_path: Path, success: bool = True) -> GenerationResult:
        """Create a GenerationResult with basic information."""
        file_size = output_path.stat().st_size if output_path.exists() else 0

        return GenerationResult(
            success=success,
            output_path=output_path,
            format=self.format,
            file_size=file_size,
        )

    def _get_template_dir(self) -> Path:
        """Get the templates directory path."""
        # Templates will be in src/doctor/generators/templates/
        return Path(__file__).parent / "templates"

    def _get_assets_dir(self) -> Path:
        """Get the assets directory path."""
        # Assets will be in src/doctor/generators/assets/
        return Path(__file__).parent / "assets"

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem safety."""
        import re

        # Replace unsafe characters with underscores
        sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename)
        # Remove multiple underscores and trailing dots
        sanitized = re.sub(r"_+", "_", sanitized).strip("._")
        return sanitized or "document"

    def validate_document(self, document: AssembledDocument) -> List[str]:
        """
        Validate document is suitable for generation.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if not document.title or not document.title.strip():
            errors.append("Document has no title")

        if not document.document_structure.files:
            errors.append("Document has no content files")

        if document.total_sections == 0:
            errors.append("Document has no sections")

        return errors
