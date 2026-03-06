"""
Cross-reference data models.

These models represent resolved cross-references within documents:
- Wikilink resolution
- Figure references
- Asset dependencies
"""

from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


class ResolvedReference(BaseModel):
    """A resolved cross-reference with target information."""

    source_file: Path
    source_line: int
    reference_type: str  # "wikilink", "figure", "equation", "section"

    # Original reference
    original_text: str

    # Resolution result
    target_file: Optional[Path] = None
    target_id: Optional[str] = None
    display_text: Optional[str] = None
    is_valid: bool = False
    error_message: Optional[str] = None


# TODO: The `asset_type` below should be an Enum model `AssetType`


class AssetReference(BaseModel):
    """Reference to an external asset (image, table, etc.)."""

    asset_path: Path
    asset_type: str  # "image", "table", "data"
    referenced_by: List[Path] = Field(default_factory=list)
    exists: bool = False
    file_size: Optional[int] = None


class ReferenceMap(BaseModel):
    """
    Complete map of all cross-references in the document.

    This is the main output of Cross-Reference Tracking (I).
    """

    resolved_references: List[ResolvedReference] = Field(default_factory=list)
    asset_references: List[AssetReference] = Field(default_factory=list)

    # Reference statistics
    total_references: int = 0
    valid_references: int = 0
    broken_references: int = 0

    def get_references_for_file(self, file_path: Path) -> List[ResolvedReference]:
        """Get all references originating from a specific file."""
        return [ref for ref in self.resolved_references if ref.source_file == file_path]

    def get_broken_references(self) -> List[ResolvedReference]:
        """Get all broken/invalid references."""
        return [ref for ref in self.resolved_references if not ref.is_valid]

    def get_asset_dependencies(self, file_path: Path) -> List[AssetReference]:
        """Get all assets referenced by a specific file."""
        return [asset for asset in self.asset_references if file_path in asset.referenced_by]
