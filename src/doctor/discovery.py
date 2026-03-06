"""
Doctor file discovery module
Discovers and organizes markdown files from project directories
"""

import re
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, computed_field, field_validator


# Roman numeral mappings for parsing
ROMAN_NUMERALS = {
    "I": 1,
    "V": 5,
    "X": 10,
    "L": 50,
    "C": 100,
    "D": 500,
    "M": 1000,
}


def roman_to_int(roman: str) -> Optional[int]:
    """
    Convert a Roman numeral string to an integer.
    Returns None if the string is not a valid Roman numeral.

    Supports standard numerals (I, V, X, L, C, D, M) and handles
    subtractive notation (IV, IX, XL, XC, CD, CM).

    Also handles the user's convention of VIV for 9 (V + IV) which
    sorts alphabetically after VIII.
    """
    if not roman:
        return None

    roman = roman.upper().strip()
    if not roman:
        return None

    # Check if all characters are valid Roman numeral characters
    if not all(c in ROMAN_NUMERALS for c in roman):
        return None

    total = 0
    prev_value = 0

    for char in reversed(roman):
        value = ROMAN_NUMERALS[char]
        if value < prev_value:
            total -= value
        else:
            total += value
        prev_value = value

    # Validate the result is positive
    if total <= 0:
        return None

    return total


def extract_roman_prefix(text: str) -> Optional[tuple[str, int]]:
    """
    Extract a Roman numeral prefix from a directory or file name.

    Returns a tuple of (roman_numeral_string, integer_value) if found,
    or None if no Roman numeral prefix exists.

    Examples:
        "III. Quantum Mechanics" -> ("III", 3)
        "VIV. Cosmology" -> ("VIV", 9)
        "1. Introduction" -> None
    """
    # Match Roman numeral at start, followed by . or space
    match = re.match(r"^([IVXLCDM]+)\.?\s", text, re.IGNORECASE)
    if match:
        roman_str = match.group(1).upper()
        value = roman_to_int(roman_str)
        if value is not None:
            return (roman_str, value)
    return None


class MarkdownFile(BaseModel):
    """Represents a discovered markdown file with its metadata."""

    path: Path
    relative_path: Path
    name: str
    parent_dir: str
    content: Optional[str] = None
    chapter_title: Optional[str] = None  # Full chapter title (e.g., "III. Quantum Mechanics")
    is_first_in_chapter: bool = False  # True if this is the first file in a Roman numeral chapter

    model_config = {"arbitrary_types_allowed": True}

    @field_validator("path", "relative_path")
    @classmethod
    def resolve_paths(cls, v: Path) -> Path:
        """Ensure paths are resolved."""
        return v.resolve() if hasattr(v, "resolve") else Path(v).resolve()

    @computed_field
    @property
    def stem(self) -> str:
        """Get the file stem (name without extension)."""
        return self.path.stem

    @computed_field
    @property
    def suffix(self) -> str:
        """Get the file extension."""
        return self.path.suffix

    def load_content(self) -> str:
        """Load the file content if not already loaded."""
        if self.content is None:
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.content = f.read()
            except UnicodeDecodeError:
                # Try with latin-1 as fallback
                with open(self.path, "r", encoding="latin-1") as f:
                    self.content = f.read()
            except Exception as e:
                raise RuntimeError(f"Error reading {self.path}: {e}") from e
        return self.content


class DocumentStructure(BaseModel):
    """Represents the hierarchical structure of the document."""

    files: List[MarkdownFile] = Field(default_factory=list)
    directories: Dict[str, List[MarkdownFile]] = Field(default_factory=dict)
    total_files: int = 0
    project_path: Path

    model_config = {"arbitrary_types_allowed": True}

    @field_validator("project_path")
    @classmethod
    def resolve_project_path(cls, v: Path) -> Path:
        """Ensure project path is resolved."""
        return v.resolve() if hasattr(v, "resolve") else Path(v).resolve()

    def get_ordered_files(self) -> List[MarkdownFile]:
        """Get all files in their natural sorted order."""
        return self.files

    def get_files_by_directory(self, directory: str) -> List[MarkdownFile]:
        """Get files for a specific directory."""
        return self.directories.get(directory, [])

    def get_directory_names(self) -> List[str]:
        """Get sorted list of directory names."""
        return sorted(self.directories.keys(), key=self._natural_sort_key)

    def _natural_sort_key(self, text: str) -> List:
        """Generate a natural sorting key for alphanumeric sorting."""
        parts = re.split(r"(\d+)", text.lower())
        result = []
        for part in parts:
            if part.isdigit():
                result.append(int(part))
            else:
                result.append(part)
        return result


class DocIgnoreHandler:
    """Handles .docignore file parsing and pattern matching."""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.patterns: List[str] = []
        self._load_docignore()

    def _load_docignore(self) -> None:
        """Load patterns from .docignore file if it exists."""
        docignore_path = self.project_path / ".docignore"
        if docignore_path.exists():
            try:
                with open(docignore_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                for line in lines:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith("#"):
                        self.patterns.append(line)
            except Exception as e:
                raise RuntimeError(f"Error reading .docignore: {e}") from e

    def should_ignore(self, path: Path, project_path: Path) -> bool:
        """Check if a path should be ignored based on patterns."""
        # Always ignore underscore-prefixed files/directories
        if path.name.startswith("_"):
            return True

        # Get relative path for pattern matching
        try:
            rel_path = path.relative_to(project_path)
        except ValueError:
            # Path is not relative to project, ignore it
            return True

        rel_path_str = str(rel_path)

        # Check against .docignore patterns
        for pattern in self.patterns:
            if self._match_pattern(pattern, rel_path_str, path.is_dir()):
                return True

        return False

    def _match_pattern(self, pattern: str, path_str: str, is_dir: bool) -> bool:
        """Match a gitignore-style pattern against a path."""
        # Handle directory-only patterns (ending with /)
        if pattern.endswith("/"):
            if not is_dir:
                return False
            pattern = pattern[:-1]

        # Escape regex special characters first (except * and ?)
        regex_pattern = pattern
        for char in ".+^${}[]|()":
            regex_pattern = regex_pattern.replace(char, f"\\{char}")

        # Handle ** for recursive matching
        regex_pattern = regex_pattern.replace("**/", "(?:.*/)?")
        regex_pattern = regex_pattern.replace("**", ".*")

        # Handle * for single-level wildcard
        regex_pattern = regex_pattern.replace("*", "[^/]*")

        # Handle ? for single character
        regex_pattern = regex_pattern.replace("?", "[^/]")

        # Check if pattern matches from start or anywhere
        if pattern.startswith("/"):
            regex_pattern = "^" + regex_pattern[1:] + "$"
        else:
            regex_pattern = "(?:^|/)" + regex_pattern + "$"

        try:
            return bool(re.search(regex_pattern, path_str))
        except re.error:
            # If regex is invalid, fall back to simple string matching
            return pattern in path_str


class FileDiscovery:
    """Main file discovery class following Unix philosophy principles."""

    def __init__(self, project_path: Path):
        self.project_path = project_path.resolve()
        self.docignore = DocIgnoreHandler(self.project_path)

        if not self.project_path.exists():
            raise FileNotFoundError(f"Project path does not exist: {self.project_path}")

        if not self.project_path.is_dir():
            raise NotADirectoryError(f"Project path is not a directory: {self.project_path}")

    def discover_files(self) -> DocumentStructure:
        """
        Discover all markdown files in the project.

        Returns:
            DocumentStructure: Complete project file structure

        Raises:
            RuntimeError: If file discovery fails
        """
        try:
            markdown_files: List[MarkdownFile] = []
            directories: Dict[str, List[MarkdownFile]] = {}

            # Walk through directory tree
            for path in self._walk_directory(self.project_path):
                if self._is_markdown_file(path):
                    if not self.docignore.should_ignore(path, self.project_path):
                        md_file = self._create_markdown_file(path)
                        markdown_files.append(md_file)

                        # Add to directory mapping
                        dir_name = md_file.parent_dir
                        if dir_name not in directories:
                            directories[dir_name] = []
                        directories[dir_name].append(md_file)

            # Sort files using academic document structure rules
            markdown_files.sort(key=self._academic_sort_key)

            # Sort files within each directory
            for dir_files in directories.values():
                dir_files.sort(key=lambda f: self._natural_sort_key(f.name))

            # Mark chapter information for Roman numeral directories
            self._mark_chapter_info(markdown_files)

            return DocumentStructure(
                files=markdown_files,
                directories=directories,
                total_files=len(markdown_files),
                project_path=self.project_path,
            )

        except Exception as e:
            raise RuntimeError(f"File discovery failed for {self.project_path}: {e}") from e

    def _walk_directory(self, directory: Path) -> List[Path]:
        """Recursively walk directory tree, respecting ignore patterns."""
        paths: List[Path] = []

        try:
            for item in directory.iterdir():
                if self.docignore.should_ignore(item, self.project_path):
                    continue

                if item.is_dir():
                    # Recursively walk subdirectories
                    paths.extend(self._walk_directory(item))
                else:
                    paths.append(item)
        except PermissionError:
            # Skip directories we can't read
            pass

        return paths

    def _is_markdown_file(self, path: Path) -> bool:
        """Check if a file is a markdown file."""
        markdown_extensions = {".md", ".markdown", ".mdown", ".mkd"}
        return path.suffix.lower() in markdown_extensions

    def _create_markdown_file(self, path: Path) -> MarkdownFile:
        """Create a MarkdownFile object from a path."""
        try:
            relative_path = path.relative_to(self.project_path)
        except ValueError as e:
            raise ValueError(f"Path {path} is not relative to project {self.project_path}") from e

        parent_dir = str(relative_path.parent) if relative_path.parent != Path(".") else ""

        return MarkdownFile(path=path, relative_path=relative_path, name=path.name, parent_dir=parent_dir)

    def _natural_sort_key(self, text: str) -> List:
        """Generate a natural sorting key for alphanumeric sorting."""
        # Split text into numeric and non-numeric parts
        parts = re.split(r"(\d+)", text.lower())

        # Convert numeric parts to integers for proper sorting
        result = []
        for part in parts:
            if part.isdigit():
                result.append(int(part))
            else:
                result.append(part)

        return result

    def _academic_sort_key(self, markdown_file) -> tuple:
        """
        Generate sorting key based on academic document structure rules:

        For Roman numeral chapter directories (I., II., III., etc.):
        - Sort chapters alphabetically by Roman numeral
        - Within each chapter: front matter first, then main content, then appendices

        For other directories:
        - Front matter first (lowercase roman numerals in filenames: i., ii., iii...)
        - Main chapters in order (1., 2., 3...)
        - Appendices last (A., B., C... or "Appendices" directory)

        Roman numeral directories are sorted alphabetically, which works correctly
        for sequences like I, II, III, IV, V, VI, VII, VIII, VIV (user's convention for IX), X.
        """
        import re

        path = str(markdown_file.relative_path)
        directory = markdown_file.parent_dir
        filename = markdown_file.name

        # Get the top-level directory (first part of the path)
        top_level_dir = directory.split("/")[0] if "/" in directory else directory

        # Check if this is a Roman numeral chapter directory
        roman_prefix = extract_roman_prefix(top_level_dir)
        is_roman_chapter = roman_prefix is not None

        # File category within a directory: 0=front_matter, 1=main_content, 2=appendices
        file_category = 1  # default to main content

        # Check if it's front matter (lowercase roman numerals in filenames or "Front Matter" directory)
        if re.search(r"[/\\][Ff]ront[^/\\]*[Mm]atter", path) or re.match(
            r"^(i{1,3}v?|iv|v|vi{0,3}|ix|x)\.?\s", filename.lower()
        ):
            file_category = 0

        # Check if it's appendix (latin letters or "Appendix/Appendices" directory)
        elif re.search(r"[/\\][Aa]ppendix|[Aa]ppendices", path) or re.match(r"^[a-z]\.?\s", filename.lower()):
            file_category = 2

        # Determine directory sorting key
        if is_roman_chapter:
            # Roman numeral chapters: sort alphabetically by Roman numeral
            # Top-level category is 1 (main content) so Roman chapters come after root front matter
            directory_sort_key = (1, 0, roman_prefix[0])  # (top_category, type=roman, alphabetic)
        else:
            # Check for Arabic numeral directory
            dir_match = re.match(r"^(\d+)\.", top_level_dir)
            if dir_match:
                directory_sort_key = (1, 1, dir_match.group(1).zfill(10))  # (top_category, type=arabic, number)
            elif top_level_dir == "" or re.search(r"[Ff]ront[^/]*[Mm]atter", top_level_dir):
                # Root files or Front Matter directory → front matter
                directory_sort_key = (0, 0, "")  # (top_category=front_matter, type, key)
            elif re.search(r"[Aa]ppendix|[Aa]ppendices", top_level_dir):
                # Appendix directory
                directory_sort_key = (2, 0, top_level_dir.lower())  # (top_category=appendix, type, key)
            else:
                directory_sort_key = (1, 2, top_level_dir.lower())  # (top_category=main, type=other, alphabetic)

        # Handle subdirectory sorting (for nested structure like "I. Mathematics/1. Linear Algebra")
        subdirectory_sort_key = ""
        if "/" in directory:
            subdirectory = "/".join(directory.split("/")[1:])
            sub_match = re.match(r"^(\d+)\.", subdirectory)
            if sub_match:
                subdirectory_sort_key = sub_match.group(1).zfill(10)
            else:
                subdirectory_sort_key = subdirectory.lower()

        # Extract file number for sorting within directories
        file_number = "999"  # default for non-numbered files
        file_match = re.match(r"^(\d+)\.", filename)
        if file_match:
            file_number = file_match.group(1).zfill(10)
        # Also handle lowercase roman numeral files (i., ii., etc.)
        elif re.match(r"^(i{1,3}v?|iv|v|vi{0,3}|ix|x)\.?\s", filename.lower()):
            # Sort by the roman numeral alphabetically (comes before "999")
            file_number = "000" + filename.lower()[:filename.find('.')]

        # Return tuple for sorting:
        # (top_dir_category, dir_type, dir_key, subdirectory_key, file_category, file_number, filename)
        return (directory_sort_key[0], directory_sort_key[1], directory_sort_key[2],
                subdirectory_sort_key, file_category, file_number, filename.lower())

    def _mark_chapter_info(self, markdown_files: List[MarkdownFile]) -> None:
        """
        Mark chapter information for files in Roman numeral directories.

        Sets chapter_title and is_first_in_chapter for files that belong
        to Roman numeral chapters (e.g., "I. Mathematics", "III. Quantum Mechanics").
        """
        seen_chapters: set = set()

        for md_file in markdown_files:
            # Get the top-level directory
            directory = md_file.parent_dir
            top_level_dir = directory.split("/")[0] if "/" in directory else directory

            if not top_level_dir:
                continue

            # Check if this is a Roman numeral chapter
            roman_prefix = extract_roman_prefix(top_level_dir)
            if roman_prefix is not None:
                # Set the chapter title (the full directory name)
                md_file.chapter_title = top_level_dir

                # Mark if this is the first file in this chapter
                if top_level_dir not in seen_chapters:
                    md_file.is_first_in_chapter = True
                    seen_chapters.add(top_level_dir)


def discover_project_files(project_path: Path) -> DocumentStructure:
    """
    Discover all markdown files in a project directory.

    Args:
        project_path: Path to the project directory

    Returns:
        DocumentStructure: Organized file structure

    Raises:
        FileNotFoundError: If project path doesn't exist
        NotADirectoryError: If project path is not a directory
        RuntimeError: If file discovery fails
    """
    discovery = FileDiscovery(project_path)
    return discovery.discover_files()


def validate_project_structure(project_path: Path) -> DocumentStructure:
    """
    Validate and discover project structure with error handling.

    Args:
        project_path: Path to the project directory

    Returns:
        DocumentStructure: Validated file structure

    Raises:
        FileNotFoundError: If project path doesn't exist
        NotADirectoryError: If project path is not a directory
        ValueError: If no markdown files found
        RuntimeError: If file discovery fails
    """
    structure = discover_project_files(project_path)

    if structure.total_files == 0:
        raise ValueError(f"No markdown files found in {project_path}")

    return structure


def print_structure_summary(structure: DocumentStructure) -> None:
    """
    Print a human-readable summary of the discovered file structure.

    Args:
        structure: The document structure to summarize
    """
    print(f"Project: {structure.project_path.name}")
    print(f"Total markdown files: {structure.total_files}")
    print(f"Directories: {len(structure.directories)}")
    print()

    for directory in structure.get_directory_names():
        files = structure.get_files_by_directory(directory)
        dir_display = directory if directory else "(root)"
        print(f"{dir_display}/ ({len(files)} files)")

        for file in files:
            print(f"  {file.name}")

    print()


def get_structure_stats(structure: DocumentStructure) -> Dict[str, int]:
    """
    Get statistics about the document structure.

    Args:
        structure: The document structure to analyze

    Returns:
        Dictionary with structure statistics
    """
    stats = {
        "total_files": structure.total_files,
        "total_directories": len(structure.directories),
        "files_in_root": len(structure.get_files_by_directory("")),
        "deepest_nesting": 0,
        "largest_directory": 0,
    }

    # Calculate nesting depth and largest directory
    for directory, files in structure.directories.items():
        if directory:  # Skip root directory
            nesting_depth = len(Path(directory).parts)
            stats["deepest_nesting"] = max(stats["deepest_nesting"], nesting_depth)

        stats["largest_directory"] = max(stats["largest_directory"], len(files))

    return stats


def find_files_by_pattern(structure: DocumentStructure, pattern: str) -> List[MarkdownFile]:
    """
    Find files matching a specific pattern in their name or path.

    Args:
        structure: The document structure to search
        pattern: Regular expression pattern to match

    Returns:
        List of matching MarkdownFile objects
    """
    matching_files = []
    compiled_pattern = re.compile(pattern, re.IGNORECASE)

    for file in structure.files:
        if compiled_pattern.search(file.name) or compiled_pattern.search(str(file.relative_path)):
            matching_files.append(file)

    return matching_files


def get_file_extensions(structure: DocumentStructure) -> Dict[str, int]:
    """
    Get count of files by extension.

    Args:
        structure: The document structure to analyze

    Returns:
        Dictionary mapping extensions to counts
    """
    extensions = {}

    for file in structure.files:
        ext = file.suffix.lower()
        extensions[ext] = extensions.get(ext, 0) + 1

    return extensions
