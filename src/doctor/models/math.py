"""
Math data models.

These models represent mathematical content extracted from documents:
- LaTeX math blocks (display and inline)
- Equation references and labels
- Future: equation numbering, cross-references, environments
"""

from typing import Optional

from pydantic import BaseModel


# TODO: We should have the following classes:
# - MathBlockType: An enum for "in-line" and "display", and may ultimately have others
# - MathBlock: Essentially what we already have


class MathBlock(BaseModel):
    """LaTeX math block ($$...$$ or $...$)."""

    content: str  # LaTeX source
    display: bool  # True for $$, False for $
    line_start: int
    line_end: int
    block_id: Optional[str] = None  # For referencing ^eq-id
