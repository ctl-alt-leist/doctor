"""
Structural roles from naming conventions.

The file tree *is* the document outline. A directory's name prefix assigns it a
structural role, and every downstream concern — ordering, chapter title pages,
Part dividers, heading-level bumps, and the table of contents — is derived from
that single assignment rather than re-detected with its own regex.

Conventions:

- ``I.``, ``II.`` … (uppercase Roman)      → Part
- ``1.``, ``2.`` … (arabic, outermost)     → Chapter
- ``1.``, ``2.`` … (arabic, nested)        → Sub-chapter
- ``i.``, ``ii.`` … (lowercase Roman)      → front matter
- ``0.`` or a name containing "front matter" → front matter
- ``A.``, ``B.`` / ``a.``, ``b.`` … (single latin letter) → appendix
- anything else                            → plain (transparent grouping)

Front matter and appendices both use single letters, so they collide on the few
letters that are also small roman numerals. Front matter is the lowercase roman
sequence (``i.``, ``ii.``, …); the single lowercase letters that read as front
matter are just ``i.``, ``v.``, ``x.``. Every other single letter — ``a.``,
``b.``, … and the large-value roman letters ``c.``/``d.``/``l.``/``m.`` — is an
appendix label. Appendices sort *after* the main body at every level.

The Chapter/Sub-chapter distinction is contextual: an arabic directory is a
Sub-chapter when some ancestor directory is itself a chapter or sub-chapter,
and a Chapter otherwise. The single-letter/Roman collision (``C.`` could be
Roman 100 or appendix C) is resolved by sibling context: a single Roman letter
is a Part only when a multi-letter Roman Part sits beside it; otherwise it is an
appendix.
"""

import re
from enum import Enum
from pathlib import PurePosixPath
from typing import Dict, List, Optional


class Role(str, Enum):
    PART = "part"
    CHAPTER = "chapter"
    SUBCHAPTER = "subchapter"
    FRONT_MATTER = "front_matter"
    APPENDIX = "appendix"
    PLAIN = "plain"


_ROMAN_CHARS = set("IVXLCDM")

# The lowercase roman numerals a front-matter sequence realistically reaches as a
# *single* letter: i (1), v (5), x (10). Every other single lowercase letter is
# read as an appendix label — including c./d./l./m., whose only roman value
# (100/500/50/1000) never numbers front matter.
_FRONT_MATTER_ROMAN = {"i", "v", "x"}

_LOWER_ROMAN = re.compile(r"^[ivxlcdm]+\.(\s|$)")
_UPPER_ROMAN = re.compile(r"^([IVXLCDM]+)\.(\s|$)")
_SINGLE_UPPER = re.compile(r"^([A-Z])\.(\s|$)")
_SINGLE_LOWER = re.compile(r"^([a-z])\.(\s|$)")
_SINGLE_LETTER = re.compile(r"^([A-Za-z])\.(\s|$)")
_ARABIC = re.compile(r"^([1-9]\d*)\.")
_ZERO = re.compile(r"^0\.")
_PREFIX = re.compile(r"^([0-9A-Za-z]+)\.")


# ============================================================================
# Per-name classification
# ============================================================================


def clean_title(name: str) -> str:
    """Strip a leading numeral/letter prefix from a directory or file name."""
    cleaned = re.sub(r"^[0-9A-Za-z]+\.\s*", "", name.strip())

    return cleaned if cleaned else name.strip()


def _base_kind(name: str) -> str:
    """
    Classify a directory name by prefix, without sibling or ancestor context.

    Returns one of: front_matter, lower_roman, appendix, part_multi,
    upper_single, arabic, plain. The contextual roles (chapter vs sub-chapter,
    single Roman letter as Part vs appendix) are resolved later.
    """
    stripped = name.strip()

    if _ZERO.match(stripped) or "front matter" in stripped.lower():
        return "front_matter"

    if "appendi" in stripped.lower():
        return "appendix"

    # A single lowercase letter: front matter only for the small romans i./v./x.,
    # an appendix label for every other letter (a., b., … and c./d./l./m.).
    single_lower = _SINGLE_LOWER.match(stripped)
    if single_lower:
        return "front_matter" if single_lower.group(1) in _FRONT_MATTER_ROMAN else "appendix"

    # Multi-letter lowercase roman (ii., iii., iv., …) is front matter.
    if _LOWER_ROMAN.match(stripped):
        return "lower_roman"

    roman = _UPPER_ROMAN.match(stripped)
    if roman and len(roman.group(1)) >= 2:
        return "part_multi"

    if _SINGLE_UPPER.match(stripped):
        return "upper_single"

    if _ARABIC.match(stripped):
        return "arabic"

    return "plain"


# The role a name implies on its own, with no sibling or ancestor context. Used
# for files (which are never Parts, and whose single-letter prefix is always an
# appendix label). Directories go through ``assign_roles`` instead, which adds the
# contextual Part/appendix and Chapter/Sub-chapter resolution.
_KIND_ROLE = {
    "front_matter": Role.FRONT_MATTER,
    "lower_roman": Role.FRONT_MATTER,
    "appendix": Role.APPENDIX,
    "upper_single": Role.APPENDIX,
    "part_multi": Role.PART,
    "arabic": Role.PLAIN,
    "plain": Role.PLAIN,
}


def _role_for_name(name: str) -> Role:
    """The structural role implied by a file or directory *name* alone."""
    return _KIND_ROLE.get(_base_kind(name), Role.PLAIN)


# ============================================================================
# Whole-tree role assignment
# ============================================================================


def assign_roles(dir_paths: List[str]) -> Dict[str, Role]:
    """
    Assign a Role to every directory, given their POSIX relative paths.

    Context is needed for two decisions, so this operates on the whole set at
    once rather than name by name.
    """
    # Expand to every ancestor, so sibling/ancestor context is complete even if
    # a caller passes only leaf directories.
    complete: set = set()
    for path in dir_paths:
        parts = PurePosixPath(path).parts
        for depth in range(1, len(parts) + 1):
            complete.add(str(PurePosixPath(*parts[:depth])))
    dir_paths = sorted(complete)

    roles: Dict[str, Role] = {}

    # Group directories by parent scope, to resolve the single-letter collision.
    children: Dict[str, List[str]] = {}
    for path in dir_paths:
        parent = str(PurePosixPath(path).parent)
        parent = "" if parent == "." else parent
        children.setdefault(parent, []).append(path)

    for path in dir_paths:
        name = PurePosixPath(path).name
        kind = _base_kind(name)

        if kind == "front_matter":
            roles[path] = Role.FRONT_MATTER

        elif kind == "lower_roman":
            roles[path] = Role.FRONT_MATTER

        elif kind == "appendix":
            roles[path] = Role.APPENDIX

        elif kind == "part_multi":
            roles[path] = Role.PART

        elif kind == "upper_single":
            roles[path] = _resolve_single_letter(path, name, children)

        elif kind == "arabic":
            roles[path] = Role.SUBCHAPTER if _has_arabic_ancestor(path, dir_paths) else Role.CHAPTER

        else:
            roles[path] = Role.PLAIN

    return roles


def _resolve_single_letter(path: str, name: str, children: Dict[str, List[str]]) -> Role:
    """A single uppercase letter is a Part only if it is Roman and a multi-letter Roman Part sits beside it."""
    letter = name.strip()[0]
    if letter not in _ROMAN_CHARS:
        return Role.APPENDIX

    parent = str(PurePosixPath(path).parent)
    parent = "" if parent == "." else parent
    siblings = children.get(parent, [])
    for sibling in siblings:
        if _base_kind(PurePosixPath(sibling).name) == "part_multi":
            return Role.PART

    return Role.APPENDIX


def _has_arabic_ancestor(path: str, dir_paths: List[str]) -> bool:
    """True if any ancestor directory of ``path`` is arabic-numbered (a chapter or sub-chapter)."""
    parts = PurePosixPath(path).parts
    for depth in range(1, len(parts)):
        ancestor = PurePosixPath(*parts[:depth])
        if _ARABIC.match(ancestor.name):
            return True

    return False


# ============================================================================
# Per-file structural information
# ============================================================================


class FileTiers:
    """The structural placement of a single file, derived from its directory chain."""

    def __init__(self) -> None:
        self.part_title: Optional[str] = None
        self.chapter_title: Optional[str] = None
        self.subchapter_title: Optional[str] = None
        self.is_front_matter: bool = False
        self.is_appendix: bool = False
        self.heading_offset: int = 0
        # Keyed by the directory path that owns each tier, so "first file" can be decided.
        self.part_key: Optional[str] = None
        self.chapter_key: Optional[str] = None
        self.subchapter_key: Optional[str] = None


def file_tiers(rel_path: str, roles: Dict[str, Role]) -> FileTiers:
    """
    Compute the structural tiers for a file from its ancestor directories' roles.

    ``rel_path`` is the file's POSIX path relative to the project root.
    """
    tiers = FileTiers()
    ancestors = PurePosixPath(rel_path).parent.parts

    offset = 0
    for depth in range(1, len(ancestors) + 1):
        dir_path = str(PurePosixPath(*ancestors[:depth]))
        role = roles.get(dir_path, Role.PLAIN)
        name = ancestors[depth - 1]

        if role == Role.PART:
            tiers.part_title = clean_title(name)
            tiers.part_key = dir_path

        elif role == Role.CHAPTER:
            tiers.chapter_title = clean_title(name)
            tiers.chapter_key = dir_path
            offset += 1

        elif role == Role.SUBCHAPTER:
            tiers.subchapter_title = clean_title(name)
            tiers.subchapter_key = dir_path
            offset += 1

        elif role == Role.APPENDIX:
            # An appendix directory behaves like a chapter: its own title page and heading tier.
            tiers.chapter_title = clean_title(name)
            tiers.chapter_key = dir_path
            tiers.is_appendix = True
            offset += 1

        elif role == Role.FRONT_MATTER:
            tiers.is_front_matter = True
            offset += 1

    # A root-level file carries no directory tier, so classify it from its own
    # name: lowercase-roman front matter ("i. Preface.md") or a single-letter
    # appendix ("a. The Path Integral.md").
    if not ancestors:
        root_role = _role_for_name(PurePosixPath(rel_path).name)
        if root_role == Role.FRONT_MATTER:
            tiers.is_front_matter = True
        elif root_role == Role.APPENDIX:
            tiers.is_appendix = True

    tiers.heading_offset = offset

    return tiers


# ============================================================================
# Ordering
# ============================================================================

# Front matter sorts first, main body next, appendices last.
_TIER_RANK = {
    Role.FRONT_MATTER: 0,
    Role.PART: 1,
    Role.CHAPTER: 1,
    Role.SUBCHAPTER: 1,
    Role.PLAIN: 1,
    Role.APPENDIX: 2,
}


def _component_key(name: str, role: Role) -> tuple:
    """Sort key for one path component: (tier rank, order-within-tier, alphabetic fallback)."""
    rank = _TIER_RANK.get(role, 1)

    # Appendix labels order alphabetically by their letter (a. < b. < c.), never by
    # roman value — c. is the third appendix, not 100.
    if role == Role.APPENDIX:
        single = _SINGLE_LETTER.match(name)
        if single:
            return (rank, ord(single.group(1).upper()), "")
        return (rank, 0, name.lower())

    roman = _UPPER_ROMAN.match(name)
    if roman:
        return (rank, _roman_value(roman.group(1)), "")

    lower_roman = _LOWER_ROMAN.match(name)
    if lower_roman:
        return (rank, _roman_value(name.split(".")[0]), "")

    arabic = _ARABIC.match(name)
    if arabic:
        return (rank, int(arabic.group(1)), "")

    single = _SINGLE_LETTER.match(name)
    if single:
        return (rank, ord(single.group(1).upper()), "")

    return (rank, 0, name.lower())


def _roman_value(roman: str) -> int:
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    prev = 0
    for char in reversed(roman.upper()):
        value = values.get(char, 0)
        total += -value if value < prev else value
        prev = value

    return total


def structural_sort_key(rel_path: str, roles: Dict[str, Role]) -> tuple:
    """
    A path-aware ordering key that respects structural roles at every level.

    Each directory component contributes its (tier, order) key, and the file
    name contributes last. A front-matter file inside a directory sorts ahead
    of that directory's ordinary content because its component rank is lower.
    """
    path = PurePosixPath(rel_path)
    keys: List[tuple] = []

    for depth in range(1, len(path.parts)):
        dir_path = str(PurePosixPath(*path.parts[: depth + 1])) if depth < len(path.parts) else None
        # Component is the directory at this depth.
        component = path.parts[depth - 1]
        role = roles.get(str(PurePosixPath(*path.parts[:depth])), Role.PLAIN)
        keys.append(_component_key(component, role))
        _ = dir_path

    # The file name itself, ranked by the role its own name implies: front-matter
    # files rank ahead of the numbered body, appendix files after it.
    file_name = path.name
    keys.append(_component_key(file_name, _role_for_name(file_name)))

    return tuple(keys)
