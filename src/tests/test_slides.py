"""
Tests for the slides generator's pure logic — parsing, title extraction, math
protection, and header/body splitting. The Playwright render is not exercised
here (no browser in CI); those pieces are verified manually.
"""

from pathlib import Path

from doctor.generators.slides import SlidesGenerator


def _generator(tmp_path: Path) -> SlidesGenerator:
    return SlidesGenerator(tmp_path / "build", config=None)


class TestParseSlides:
    def test_splits_on_separator_lines(self, tmp_path):
        gen = _generator(tmp_path)
        slides = gen._parse_slides("# One\n\nfirst\n\n---\n\n# Two\n\nsecond")
        assert len(slides) == 2
        assert slides[0].startswith("# One")
        assert slides[1].startswith("# Two")

    def test_separator_inside_code_fence_is_not_a_split(self, tmp_path):
        gen = _generator(tmp_path)
        deck = "# Code\n\n```\n---\n```\n\n---\n\n# Next"
        slides = gen._parse_slides(deck)
        assert len(slides) == 2
        assert "---" in slides[0]  # the fenced --- stayed inside slide one

    def test_final_slide_is_kept(self, tmp_path):
        gen = _generator(tmp_path)
        slides = gen._parse_slides("a\n\n---\n\nb\n\n---\n\nc")
        assert slides == ["a", "b", "c"]


class TestTitle:
    def test_prefers_h1_then_h2_else_default(self, tmp_path):
        gen = _generator(tmp_path)
        assert gen._extract_title("# Real Title\n\nbody") == "Real Title"
        assert gen._extract_title("## Sub Title\n\nbody") == "Sub Title"
        assert gen._extract_title("no heading here") == "Presentation"


class TestMathProtection:
    def test_round_trip_preserves_math(self, tmp_path):
        gen = _generator(tmp_path)
        original = r"Text with $$E = mc^2$$ and inline $a + b$ here."
        protected, blocks = gen._protect_math(original)
        assert "$$" not in protected and "MATH_PLACEHOLDER_0_END" in protected
        assert gen._restore_math(protected, blocks) == original


class TestHeaderBodySplit:
    def test_first_heading_becomes_header(self, tmp_path):
        gen = _generator(tmp_path)
        header, body = gen._extract_header_and_body("<h1>Title</h1>\n<p>body</p>")
        assert "<h1>Title</h1>" in header
        assert "<p>body</p>" in body
        assert "<h1>" not in body

    def test_no_heading_leaves_empty_header(self, tmp_path):
        gen = _generator(tmp_path)
        header, body = gen._extract_header_and_body("<p>just body</p>")
        assert header == ""
        assert body == "<p>just body</p>"
