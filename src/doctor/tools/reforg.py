"""
Reference Organizer (reforg) - Reorganize bibliography references

This module provides functionality to reorganize references.toml files
in various ways:
- By publication year/date
- By author (last name)
- By journal/publisher
- By entry type
- Custom sorting options

The reorganizer can also automatically rename section headers based on
reference metadata.
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

import toml

from doctor.models.bibliography import BibliographyEntry


class ReferenceOrganizer:
    """Organizes bibliography references in various ways."""

    SORT_OPTIONS = {
        "year": "Sort by publication year",
        "author": "Sort by author last name",
        "journal": "Sort by journal/publisher",
        "type": "Sort by entry type (article, book, etc.)",
        "title": "Sort by title alphabetically",
    }

    def __init__(self):
        self.entries: Dict[str, BibliographyEntry] = {}
        self.original_structure: Dict[str, Any] = {}

    def load_references(self, file_path: Path) -> None:
        """Load references from TOML file."""
        if not file_path.exists():
            raise FileNotFoundError(f"References file not found: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self.original_structure = toml.load(f)
        except Exception as e:
            raise ValueError(f"Error loading TOML file: {e}") from e

        # Parse entries using existing bibliography logic
        flattened_entries = self._flatten_toml_entries(self.original_structure)

        for key, entry_data in flattened_entries.items():
            # Extract fields for BibliographyEntry
            known_fields = {
                "title",
                "author",
                "year",
                "entry_type",
                "type",
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
                    if field == "type":
                        entry_fields["entry_type"] = value
                    elif field in ["volume", "number"] and isinstance(value, int):
                        entry_fields[field] = str(value)
                    else:
                        entry_fields[field] = value
                else:
                    extra_fields[field] = value

            entry_fields["extra_fields"] = extra_fields

            # Only create entry if we have required fields
            if "title" in entry_fields and "author" in entry_fields:
                self.entries[key] = BibliographyEntry(**entry_fields)

    def _flatten_toml_entries(self, data: Dict, prefix: str = "") -> Dict[str, Dict]:
        """Flatten nested TOML structure into dot notation keys."""
        entries = {}

        for key, value in data.items():
            current_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                if "title" in value and "author" in value:
                    entries[current_key] = value
                else:
                    entries.update(self._flatten_toml_entries(value, current_key))

        return entries

    def organize_by_year(self, reverse: bool = False) -> Dict[str, List[BibliographyEntry]]:
        """Organize entries by publication year."""
        organized = defaultdict(list)

        for entry in self.entries.values():
            year_key = str(entry.year)
            organized[year_key].append(entry)

        # Sort within each year by author
        for year_entries in organized.values():
            year_entries.sort(key=lambda e: self._get_author_sort_key(e.author))

        return dict(sorted(organized.items(), key=lambda x: int(x[0]), reverse=reverse))

    def organize_by_author(self, reverse: bool = False) -> Dict[str, List[BibliographyEntry]]:
        """Organize entries by author last name."""
        organized = defaultdict(list)

        for entry in self.entries.values():
            last_name = self._get_author_sort_key(entry.author)
            # Group by first letter of last name
            first_letter = last_name[0].upper() if last_name else "Z"
            organized[first_letter].append(entry)

        # Sort within each group by full author name then year
        for author_entries in organized.values():
            author_entries.sort(key=lambda e: (self._get_author_sort_key(e.author), e.year))

        return dict(sorted(organized.items(), reverse=reverse))

    def organize_by_journal(self, reverse: bool = False) -> Dict[str, List[BibliographyEntry]]:
        """Organize entries by journal/publisher."""
        organized = defaultdict(list)

        for entry in self.entries.values():
            venue = entry.journal or entry.publisher or "Other"
            organized[venue].append(entry)

        # Sort within each venue by year then author
        for venue_entries in organized.values():
            venue_entries.sort(key=lambda e: (e.year, self._get_author_sort_key(e.author)))

        return dict(sorted(organized.items(), reverse=reverse))

    def organize_by_type(self, reverse: bool = False) -> Dict[str, List[BibliographyEntry]]:
        """Organize entries by entry type."""
        organized = defaultdict(list)

        for entry in self.entries.values():
            entry_type = entry.entry_type or "misc"
            organized[entry_type.title()].append(entry)

        # Sort within each type by year then author
        for type_entries in organized.values():
            type_entries.sort(key=lambda e: (e.year, self._get_author_sort_key(e.author)))

        return dict(sorted(organized.items(), reverse=reverse))

    def organize_by_title(self, reverse: bool = False) -> Dict[str, List[BibliographyEntry]]:
        """Organize entries alphabetically by title."""
        organized = defaultdict(list)

        for entry in self.entries.values():
            # Group by first letter of title (ignoring articles)
            title = entry.title
            for article in ["The ", "A ", "An "]:
                if title.startswith(article):
                    title = title[len(article) :]
                    break
            first_letter = title[0].upper() if title else "Z"
            organized[first_letter].append(entry)

        # Sort within each group by title
        for title_entries in organized.values():
            title_entries.sort(key=lambda e: e.title.lower())

        return dict(sorted(organized.items(), reverse=reverse))

    def _get_author_sort_key(self, author: str) -> str:
        """Extract last name for sorting."""
        if not author:
            return "zzz"  # Put at end

        # Handle multiple authors - use first author
        first_author = author.split(" and ")[0].split(",")[0].strip()

        # Simple heuristic: last word is usually the last name
        parts = first_author.split()
        return parts[-1].lower() if parts else "zzz"

    def generate_toml_structure(
        self, organized_entries: Dict[str, List[BibliographyEntry]], sort_type: str
    ) -> Dict[str, Any]:
        """Generate new TOML structure from organized entries."""
        result = {}

        # Add header comment
        if sort_type == "year":
            f"# Bibliography organized by year ({len(self.entries)} entries)"
        elif sort_type == "author":
            f"# Bibliography organized by author ({len(self.entries)} entries)"
        elif sort_type == "journal":
            f"# Bibliography organized by journal/publisher ({len(self.entries)} entries)"
        elif sort_type == "type":
            f"# Bibliography organized by entry type ({len(self.entries)} entries)"
        else:
            f"# Bibliography organized by {sort_type} ({len(self.entries)} entries)"

        for section_key, entries in organized_entries.items():
            section_name = self._generate_section_name(section_key, sort_type, entries)
            section_dict = {}

            for entry in entries:
                entry_dict = {
                    "type": entry.entry_type,
                    "author": entry.author,
                    "title": entry.title,
                    "year": entry.year,
                }

                # Add optional fields if present
                optional_fields = [
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
                ]
                for field in optional_fields:
                    value = getattr(entry, field, None)
                    if value:
                        entry_dict[field] = value

                # Add extra fields
                if entry.extra_fields:
                    entry_dict.update(entry.extra_fields)

                section_dict[entry.key] = entry_dict

            result[section_name] = section_dict

        return result

    def _generate_section_name(self, key: str, sort_type: str, entries: List[BibliographyEntry]) -> str:
        """Generate descriptive section name based on organization type."""
        count = len(entries)

        if sort_type == "year":
            return f"{key} ({count} entries)"
        elif sort_type == "author":
            return f"Authors {key} ({count} entries)"
        elif sort_type == "journal":
            return f"{key} ({count} entries)"
        elif sort_type == "type":
            return f"{key} ({count} entries)"
        else:
            return f"{key} ({count} entries)"

    def save_to_toml(self, organized_structure: Dict[str, Any], output_path: Path) -> None:
        """Save organized structure to TOML file."""
        with open(output_path, "w", encoding="utf-8") as f:
            toml.dump(organized_structure, f)


class ReforgCommand:
    """Command-line interface for reference organization."""

    def __init__(self):
        self.organizer = ReferenceOrganizer()

    def create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser for reforg command."""
        parser = argparse.ArgumentParser(
            prog="doctor reforg", description="Reorganize references.toml file in various ways"
        )

        parser.add_argument("input_file", type=Path, help="Path to the references.toml file to reorganize")

        parser.add_argument(
            "--sort-by",
            choices=list(ReferenceOrganizer.SORT_OPTIONS.keys()),
            default="year",
            help="How to organize the references",
        )

        parser.add_argument("--reverse", action="store_true", help="Reverse the sort order")

        parser.add_argument(
            "--output",
            "-o",
            type=Path,
            help="Output file path (if not specified, prints to stdout and asks for confirmation)",
        )

        parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")

        parser.add_argument(
            "--verbose", "-v", action="store_true", help="Show detailed information about the reorganization"
        )

        return parser

    def run(self, args: List[str]) -> int:
        """Run the reforg command."""
        parser = self.create_parser()
        parsed_args = parser.parse_args(args)

        try:
            # Load references
            self.organizer.load_references(parsed_args.input_file)

            if parsed_args.verbose:
                print(f"Loaded {len(self.organizer.entries)} references from {parsed_args.input_file}")

            # Organize references
            if parsed_args.sort_by == "year":
                organized = self.organizer.organize_by_year(parsed_args.reverse)
            elif parsed_args.sort_by == "author":
                organized = self.organizer.organize_by_author(parsed_args.reverse)
            elif parsed_args.sort_by == "journal":
                organized = self.organizer.organize_by_journal(parsed_args.reverse)
            elif parsed_args.sort_by == "type":
                organized = self.organizer.organize_by_type(parsed_args.reverse)
            elif parsed_args.sort_by == "title":
                organized = self.organizer.organize_by_title(parsed_args.reverse)
            else:
                print(f"Unknown sort option: {parsed_args.sort_by}", file=sys.stderr)
                return 1

            # Generate new structure
            toml_structure = self.organizer.generate_toml_structure(organized, parsed_args.sort_by)

            if parsed_args.verbose:
                print(f"Organized into {len(organized)} sections:")
                for section, entries in organized.items():
                    print(f"  {section}: {len(entries)} entries")

            # Handle output
            if parsed_args.dry_run:
                print("DRY RUN - Would organize references as follows:")
                for section, entries in organized.items():
                    print(f"\n[{section}]")
                    for entry in entries[:3]:  # Show first 3 entries
                        print(f"  {entry.key}: {entry.author} ({entry.year}) - {entry.title[:60]}...")
                    if len(entries) > 3:
                        print(f"  ... and {len(entries) - 3} more entries")
                return 0

            # Generate TOML output
            toml_output = toml.dumps(toml_structure)

            if parsed_args.output:
                # Save to specified file
                self.organizer.save_to_toml(toml_structure, parsed_args.output)
                print(f"References organized and saved to: {parsed_args.output}")
            else:
                # Print to stdout and ask for confirmation
                print("Organized references.toml:")
                print("=" * 50)
                print(toml_output)
                print("=" * 50)

                response = input(f"\nReplace {parsed_args.input_file} with this organized version? (y/N): ")
                if response.lower() in ["y", "yes"]:
                    self.organizer.save_to_toml(toml_structure, parsed_args.input_file)
                    print(f"References reorganized and saved to: {parsed_args.input_file}")
                else:
                    print("Operation cancelled.")

            return 0

        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1


def main():
    """Main entry point for reforg command."""
    command = ReforgCommand()
    return command.run(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
