"""
Bibliography Processing (J) → Citation Database (P)

Processes citations and bibliography entries:
- Citation parsing [@key] and [@key1; @key2]
- Bibliography loading from references.toml
- Citation validation and formatting
- Bibliography ordering and numbering
- Multiple citation style support
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import toml

from doctor.models.bibliography import (
    BibliographyEntry,
    CitationDatabase,
    ProcessedCitation,
)
from doctor.models.content import Citation, ParsedContent


logger = logging.getLogger(__name__)


class BibliographyProcessing:
    """
    Bibliography Processing processor (J in architecture diagram).

    Processes citations from ParsedContent and matches with bibliography database.
    """

    def __init__(self, citation_style: str = "numeric"):
        """
        Initialize bibliography processor.

        Args:
            citation_style: Citation style ("numeric", "author-year", "alpha")
        """
        self.citation_style = citation_style
        self.citation_counter = 0

    def process_bibliography(
        self, parsed_files: List[ParsedContent], references_file: Optional[Path] = None
    ) -> CitationDatabase:
        """
        Process all citations and build citation database.

        Args:
            parsed_files: List of ParsedContent objects with citations
            references_file: Path to references.toml file

        Returns:
            CitationDatabase: Complete citation and bibliography database
        """
        # Load bibliography entries
        bib_entries = self._load_bibliography(references_file) if references_file else {}

        # Process citations from all files
        processed_citations = []
        citation_order = []

        for parsed_content in parsed_files:
            file_citations = self._process_file_citations(parsed_content, bib_entries, citation_order)
            processed_citations.extend(file_citations)

        # Calculate statistics
        total_citations = len(processed_citations)
        missing_citations = len([cit for cit in processed_citations if not cit.is_valid])

        # Log summary
        logger.info(f"Bibliography processing complete: {len(bib_entries)} entries, {total_citations} citations")
        if missing_citations > 0:
            logger.warning(f"Found {missing_citations} unresolved citations")
        else:
            logger.info("All citations successfully resolved")

        return CitationDatabase(
            entries=bib_entries,
            citations=processed_citations,
            citation_order=citation_order,
            total_entries=len(bib_entries),
            total_citations=total_citations,
            missing_citations=missing_citations,
        )

    def _load_bibliography(self, references_file: Path) -> Dict[str, BibliographyEntry]:
        """Load bibliography entries from references.toml."""
        if not references_file.exists():
            return {}

        try:
            with open(references_file, "r", encoding="utf-8") as f:
                data = toml.load(f)

            entries = {}

            # Check if this is the new [[papers]] array format
            if "papers" in data and isinstance(data["papers"], list):
                entries = self._load_papers_array_format(data["papers"])
            else:
                # Fall back to old nested TOML format
                entries = self._load_nested_toml_format(data)

            return entries

        except Exception as e:
            raise ValueError(f"Error loading bibliography from {references_file}: {e}") from e

    def _load_papers_array_format(self, papers: List[Dict[str, Any]]) -> Dict[str, BibliographyEntry]:
        """
        Load bibliography entries from [[papers]] array format.

        New format fields:
        - handle: citation key
        - authors: author name(s)
        - publication: journal/venue name
        - file_name: local PDF filename
        - tags: list of tags
        - local: whether file is stored locally
        """
        entries = {}

        # Field mapping from new format to BibliographyEntry
        field_mapping = {
            "handle": "key",
            "authors": "author",
            "publication": "journal",
        }

        known_fields = {
            "handle",
            "title",
            "authors",
            "author",  # Accept both
            "year",
            "entry_type",
            "type",
            "publication",
            "journal",  # Accept both
            "volume",
            "number",
            "pages",
            "publisher",
            "doi",
            "url",
            "isbn",
            "arxiv",
            "abstract",
            "keywords",
            "tags",  # Map to keywords
        }

        for paper in papers:
            if "handle" not in paper:
                logger.warning("Skipping paper entry without 'handle' field")
                continue

            key = paper["handle"]
            entry_fields = {"key": key}
            extra_fields = {}

            for field, value in paper.items():
                # Apply field mapping
                mapped_field = field_mapping.get(field, field)

                if field in known_fields or mapped_field in known_fields:
                    # Handle specific mappings
                    if field == "handle":
                        continue  # Already used as key
                    elif field == "authors":
                        entry_fields["author"] = value
                    elif field == "publication":
                        entry_fields["journal"] = value
                    elif field == "tags":
                        entry_fields["keywords"] = value
                    elif field == "type":
                        entry_fields["entry_type"] = value
                    elif field in ["volume", "number"] and isinstance(value, int):
                        entry_fields[field] = str(value)
                    else:
                        entry_fields[mapped_field] = value
                else:
                    # Store unknown fields (file_name, local, etc.) in extra_fields
                    extra_fields[field] = value

            entry_fields["extra_fields"] = extra_fields

            # Ensure required fields
            if "title" in entry_fields and "author" in entry_fields:
                entries[key] = BibliographyEntry(**entry_fields)
                logger.debug(f"Loaded bibliography entry: {key}")
            else:
                logger.warning(f"Skipping incomplete bibliography entry '{key}': missing title or author")

        return entries

    def _load_nested_toml_format(self, data: Dict[str, Any]) -> Dict[str, BibliographyEntry]:
        """Load bibliography entries from nested TOML format (original format)."""
        entries = {}

        # Flatten nested TOML structure into dot notation
        flattened_entries = self._flatten_toml_entries(data)

        # Process each entry
        for key, entry_data in flattened_entries.items():
            # Extract known fields
            known_fields = {
                "title",
                "author",
                "year",
                "entry_type",
                "type",  # Accept 'type' as well as 'entry_type'
                "journal",
                "volume",
                "number",
                "pages",
                "publisher",
                "doi",
                "url",
                "isbn",
                "arxiv",
                "abstract",
                "keywords",
            }

            entry_fields = {"key": key}
            extra_fields = {}

            for field, value in entry_data.items():
                if field in known_fields:
                    # Handle type/entry_type mapping
                    if field == "type":
                        entry_fields["entry_type"] = value
                    # Convert numeric fields to strings
                    elif field in ["volume", "number"] and isinstance(value, int):
                        entry_fields[field] = str(value)
                    else:
                        entry_fields[field] = value
                else:
                    extra_fields[field] = value

            entry_fields["extra_fields"] = extra_fields

            # Ensure required fields
            if "title" in entry_fields and "author" in entry_fields:
                entries[key] = BibliographyEntry(**entry_fields)
                logger.debug(f"Loaded bibliography entry: {key}")
            else:
                logger.warning(f"Skipping incomplete bibliography entry '{key}': missing title or author")

        return entries

    def _flatten_toml_entries(self, data: Dict, prefix: str = "") -> Dict[str, Dict]:
        """
        Flatten nested TOML structure into dot notation keys.

        Args:
            data: The TOML data dictionary
            prefix: Current prefix for nested keys

        Returns:
            Dictionary with flattened keys and their entry data
        """
        entries = {}

        for key, value in data.items():
            current_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                # Check if this dict contains bibliography fields (has title and author)
                if "title" in value and "author" in value:
                    # This is a bibliography entry
                    entries[current_key] = value
                else:
                    # This is a nested structure, continue flattening
                    entries.update(self._flatten_toml_entries(value, current_key))

        return entries

    def _fuzzy_match_citation_key(self, key: str, bib_entries: Dict[str, BibliographyEntry]) -> Optional[str]:
        """
        Attempt fuzzy matching for citation keys.

        Tries matching strategies in order:
        1. Strip trailing -a, -b, -c, etc. suffix
        2. Try adding common suffixes (-a, -b, -c)
        3. Try without any suffix variations

        Args:
            key: Citation key to match
            bib_entries: Dictionary of bibliography entries

        Returns:
            Matched key from bib_entries, or None if no match found
        """
        import re

        # Strategy 1: Strip -a, -b, -c, etc. suffix (single letter after last hyphen)
        match = re.match(r"^(.+)-([a-z])$", key)
        if match:
            base_key = match.group(1)
            if base_key in bib_entries:
                return base_key

        # Strategy 2: Try adding common suffixes (-a, -b, -c)
        # This handles cases where citation doesn't have suffix but ref does
        for suffix in ["a", "b", "c", "d"]:
            suffixed_key = f"{key}-{suffix}"
            if suffixed_key in bib_entries:
                return suffixed_key

        # Strategy 3: Try without any suffix variations
        # Match patterns like "author-year-suffix" and try "author-year"
        match = re.match(r"^(.+-\d{4})-[a-z]+$", key)
        if match:
            base_key = match.group(1)
            if base_key in bib_entries:
                return base_key

        return None

    def _process_file_citations(
        self, parsed_content: ParsedContent, bib_entries: Dict[str, BibliographyEntry], citation_order: List[str]
    ) -> List[ProcessedCitation]:
        """Process citations from a single file."""
        processed = []

        for citation in parsed_content.all_citations:
            processed_citation = self._process_single_citation(
                citation, parsed_content.source_file.path, bib_entries, citation_order
            )
            processed.append(processed_citation)

        return processed

    def _process_single_citation(
        self,
        citation: Citation,
        source_file: Path,
        bib_entries: Dict[str, BibliographyEntry],
        citation_order: List[str],
    ) -> ProcessedCitation:
        """Process a single citation reference."""
        entries = []
        missing_keys = []

        # Resolve each citation key
        for key in citation.keys:
            # Try exact match first
            matched_key = None
            if key in bib_entries:
                matched_key = key
            else:
                # Try fuzzy matching: strip -a, -b, -c, etc. suffix
                matched_key = self._fuzzy_match_citation_key(key, bib_entries)

            if matched_key:
                entries.append(bib_entries[matched_key])
                # Add to citation order if first occurrence
                if matched_key not in citation_order:
                    citation_order.append(matched_key)
                    logger.debug(f"Added citation key '{matched_key}' to citation order")
                if matched_key != key:
                    logger.debug(f"Fuzzy matched citation key '{key}' to '{matched_key}'")
            else:
                missing_keys.append(key)
                logger.warning(
                    f"Missing bibliography entry for key '{key}' in {source_file.name}:{citation.line_number}. "
                    f"Context: {citation.context[:80]}{'...' if len(citation.context) > 80 else ''}"
                )

        # Generate citation number/label
        citation_number = None
        formatted_citation = None

        if self.citation_style == "numeric" and entries:
            # Use position in citation order
            citation_number = min(citation_order.index(entry.key) + 1 for entry in entries)
            formatted_citation = f"[{citation_number}]"

        elif self.citation_style == "author-year" and entries:
            # Format as (Author, Year)
            if len(entries) == 1:
                entry = entries[0]
                formatted_citation = f"({entry.author.split()[-1]}, {entry.year})"
            else:
                # Multiple citations
                author_years = [f"{entry.author.split()[-1]}, {entry.year}" for entry in entries]
                formatted_citation = f"({'; '.join(author_years)})"

        return ProcessedCitation(
            source_file=source_file,
            line_number=citation.line_number,
            original_keys=citation.keys,
            context=citation.context,
            entries=entries,
            missing_keys=missing_keys,
            citation_number=citation_number,
            formatted_citation=formatted_citation,
            is_valid=len(missing_keys) == 0,
        )
