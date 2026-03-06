"""
Cross-Reference Tracking (I) → Reference Map (O)

Tracks and resolves cross-references within and between documents:
- Wikilink resolution [[Internal Link]]
- Figure reference tracking ![[image.png]]
- Equation reference resolution
- Cross-document link validation
- Asset dependency mapping
"""

from pathlib import Path
from typing import List, Optional

from doctor.models.content import FigureEmbed, WikiLink
from doctor.models.references import (
    AssetReference,
    ReferenceMap,
    ResolvedReference,
)
from doctor.models.structure import DocumentStructure


class CrossReferenceTracking:
    """
    Cross-Reference Tracking processor (I in architecture diagram).

    Resolves all cross-references from ParsedContent using DocumentStructure.
    """

    def __init__(self, project_root: Path):
        """
        Initialize cross-reference tracker.

        Args:
            project_root: Root directory of the project for resolving paths
        """
        self.project_root = project_root

    def track_references(self, document_structure: DocumentStructure) -> ReferenceMap:
        """
        Track and resolve all cross-references in the document structure.

        Args:
            document_structure: Complete document structure

        Returns:
            ReferenceMap: Map of all resolved references
        """
        resolved_refs = []
        asset_refs = []

        # Process each file
        for file_struct in document_structure.files:
            parsed_content = file_struct.parsed_content

            # Resolve wikilinks
            wikilink_refs = self._resolve_wikilinks(
                parsed_content.all_wiki_links, parsed_content.source_file.path, document_structure
            )
            resolved_refs.extend(wikilink_refs)

            # Resolve figure references
            figure_refs, figure_assets = self._resolve_figures(
                parsed_content.all_figure_embeds, parsed_content.source_file.path
            )
            resolved_refs.extend(figure_refs)
            asset_refs.extend(figure_assets)

            # TODO: Resolve equation references
            # TODO: Resolve section references

        # Calculate statistics
        total_refs = len(resolved_refs)
        valid_refs = len([ref for ref in resolved_refs if ref.is_valid])
        broken_refs = total_refs - valid_refs

        return ReferenceMap(
            resolved_references=resolved_refs,
            asset_references=asset_refs,
            total_references=total_refs,
            valid_references=valid_refs,
            broken_references=broken_refs,
        )

    def _resolve_wikilinks(
        self, wikilinks: List[WikiLink], source_file: Path, document_structure: DocumentStructure
    ) -> List[ResolvedReference]:
        """Resolve wikilink references [[page]]."""
        resolved = []

        for wikilink in wikilinks:
            # Try to find target file
            target_file = self._find_target_file(wikilink.target, document_structure)

            if target_file:
                resolved.append(
                    ResolvedReference(
                        source_file=source_file,
                        source_line=wikilink.line_number,
                        reference_type="wikilink",
                        original_text=f"[[{wikilink.target}]]",
                        target_file=target_file,
                        display_text=wikilink.display or wikilink.target,
                        is_valid=True,
                    )
                )
            else:
                resolved.append(
                    ResolvedReference(
                        source_file=source_file,
                        source_line=wikilink.line_number,
                        reference_type="wikilink",
                        original_text=f"[[{wikilink.target}]]",
                        display_text=wikilink.display or wikilink.target,
                        is_valid=False,
                        error_message=f"Target file not found: {wikilink.target}",
                    )
                )

        return resolved

    def _resolve_figures(
        self, figures: List[FigureEmbed], source_file: Path
    ) -> tuple[List[ResolvedReference], List[AssetReference]]:
        """Resolve figure embed references ![[image.png]]."""
        resolved_refs = []
        asset_refs = []

        for figure in figures:
            # Try to find figure file
            figure_path = self._find_figure_path(figure.path, source_file)

            # Create asset reference
            asset_ref = AssetReference(
                asset_path=Path(figure.path),
                asset_type="image",
                referenced_by=[source_file],
                exists=figure_path.exists() if figure_path else False,
            )
            asset_refs.append(asset_ref)

            # Create resolved reference
            if figure_path and figure_path.exists():
                resolved_refs.append(
                    ResolvedReference(
                        source_file=source_file,
                        source_line=figure.line_number,
                        reference_type="figure",
                        original_text=f"![[{figure.path}]]",
                        target_file=figure_path,
                        display_text=figure.caption or figure.path,
                        is_valid=True,
                    )
                )
            else:
                resolved_refs.append(
                    ResolvedReference(
                        source_file=source_file,
                        source_line=figure.line_number,
                        reference_type="figure",
                        original_text=f"![[{figure.path}]]",
                        display_text=figure.caption or figure.path,
                        is_valid=False,
                        error_message=f"Figure file not found: {figure.path}",
                    )
                )

        return resolved_refs, asset_refs

    def _find_target_file(self, target: str, document_structure: DocumentStructure) -> Optional[Path]:
        """Find target file for a wikilink."""
        # Simple implementation - look for file with matching name
        for file_struct in document_structure.files:
            if file_struct.file_path.stem.lower() == target.lower():
                return file_struct.file_path
        return None

    def _find_figure_path(self, figure_path: str, source_file: Path) -> Optional[Path]:
        """
        Find actual path to figure file using multiple search strategies.

        Search order:
        1. Relative to source file directory (handles local _figures/ directories)
        2. Relative to project root
        3. In common figure directories relative to source file
        4. In common figure directories at project root (with just filename)
        5. Current working directory
        """
        figure_path_obj = Path(figure_path)

        # 1. Try relative to source file directory first
        # This handles cases like "_figures/image.png" in the same directory as the source
        relative_to_source = source_file.parent / figure_path
        if relative_to_source.exists():
            return relative_to_source

        # 2. Try relative to project root
        relative_to_project = self.project_root / figure_path
        if relative_to_project.exists():
            return relative_to_project

        # 3. Try in common figure directories relative to source file directory
        # This checks for _figures/ in the same directory as the source file
        for fig_dir in ["_figures", "figures", "images", "assets"]:
            source_fig_path = source_file.parent / fig_dir / figure_path_obj.name
            if source_fig_path.exists():
                return source_fig_path

        # 4. Try in common figure directories at project root (with just the filename)
        # This strips any directory prefix from the figure path
        for fig_dir in ["_figures", "figures", "images", "assets"]:
            project_fig_path = self.project_root / fig_dir / figure_path_obj.name
            if project_fig_path.exists():
                return project_fig_path

        # 5. Try relative to current working directory
        cwd_path = Path.cwd() / figure_path
        if cwd_path.exists():
            return cwd_path

        return None
