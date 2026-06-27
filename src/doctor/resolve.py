"""
Target resolution for the `doc` command.

Turns a single positional argument into a concrete file or directory to compile.
The argument may be:

- A path (relative or absolute) to a directory or file — used directly.
- A bare name of a directory or file — located by searching downward from the
  current directory, matching the academic naming conventions (roman numeral,
  title, or both, e.g. "X.II", "III", "Galaxies").

This is the Python port of the original `doc.fish` find logic, so the same
behavior is available in every shell from one PATH binary.
"""

from fnmatch import fnmatch
from pathlib import Path
from typing import List


class TargetResolutionError(Exception):
    """Raised when a query cannot be resolved to a single target."""


# Glob patterns tried in order; the first pattern that yields any match wins.
# Mirrors the pattern set from the original doc.fish resolver.
_NAME_PATTERNS = ("{q}", "{q} *", "{q}.*", "* {q}", "* {q} *", "* {q}.*")


def resolve_target(query: str, depth: int = 3, search_root: Path | None = None) -> Path:
    """
    Resolve a query string to a single file or directory path.

    Args:
        query: A path or a bare directory/file name to locate.
        depth: Maximum search depth below the search root for name matching.
        search_root: Directory to search from (defaults to the current directory).

    Returns:
        The resolved target path.

    Raises:
        TargetResolutionError: If no target matches, or the name is ambiguous.
    """
    root = (search_root or Path.cwd()).resolve()

    # An existing path (file or directory) is used directly. The path is part of
    # the argument itself, so "path/to/thing" needs no separate flag.
    direct = Path(query).expanduser()
    if direct.exists():
        return direct.resolve()

    matches = _find_by_name(query, root, depth)

    if not matches:
        raise TargetResolutionError(f"No file or directory found matching: {query}")

    if len(matches) > 1:
        listing = "\n".join(f"  {m}" for m in matches)
        raise TargetResolutionError(f"Multiple matches for '{query}':\n{listing}")

    return matches[0]


def _find_by_name(query: str, root: Path, depth: int) -> List[Path]:
    """Search downward from root for files or directories matching the query."""
    candidates = _walk_with_depth(root, depth)

    for template in _NAME_PATTERNS:
        pattern = template.format(q=query).lower()
        matches = sorted(path for path in candidates if fnmatch(path.name.lower(), pattern))
        if matches:
            return matches

    return []


def _walk_with_depth(root: Path, depth: int) -> List[Path]:
    """Collect files and directories up to `depth` levels below root."""
    collected: List[Path] = []

    def descend(directory: Path, remaining: int) -> None:
        try:
            entries = sorted(directory.iterdir())
        except (PermissionError, OSError):
            return

        for entry in entries:
            # Skip underscore-prefixed and hidden entries, matching discovery rules.
            if entry.name.startswith("_") or entry.name.startswith("."):
                continue

            collected.append(entry)
            if entry.is_dir() and remaining > 1:
                descend(entry, remaining - 1)

    descend(root, depth)

    return collected
