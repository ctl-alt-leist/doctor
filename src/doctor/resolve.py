"""
Target resolution for the `doc` command.

Turns the single positional argument into a concrete file or directory to
compile. The argument is a **path** — relative or absolute — to an existing
markdown file or project directory. A bare fuzzy name is not searched for: the
path must be given explicitly, so that what compiles is always unambiguous.
"""

from pathlib import Path


class TargetResolutionError(Exception):
    """Raised when the target path does not exist."""


def resolve_target(query: str) -> Path:
    """
    Resolve the positional argument to an existing file or directory path.

    Args:
        query: A path (relative or absolute) to a markdown file or project
            directory. A leading ``~`` is expanded.

    Returns:
        The resolved absolute target path.

    Raises:
        TargetResolutionError: If the path does not exist.
    """
    target = Path(query).expanduser()
    if not target.exists():
        raise TargetResolutionError(f"No such file or directory: {query}")

    return target.resolve()
