"""
Tests for snapshot versioning: what a version contains, the auto-incrementing
ids, restore-alongside-never-swap, and version-tagged PDF naming.
"""

import tarfile
from pathlib import Path

from doctor.versioning import VersionStore, version_tagged_output


def _make_project(root: Path) -> None:
    """A minimal project: content, a "+" auxiliary, "_" scratch, .doctor profile, a stray PDF."""
    (root / ".doctor").mkdir()
    (root / ".doctor" / "book.toml").write_text('[typography]\nbase_size = "12px"\n')
    (root / ".doctor" / "build").mkdir()
    (root / ".doctor" / "build" / "junk.html").write_text("<html></html>")
    (root / "1. Introduction").mkdir()
    (root / "1. Introduction" / "1. Intro.md").write_text("# Intro\n")
    (root / "+figures").mkdir()
    (root / "+figures" / "plot.svg").write_text("<svg/>")
    (root / "+references.toml").write_text("")
    (root / "_scratch").mkdir()
    (root / "_scratch" / "draft.md").write_text("# scratch\n")
    (root / "project.pdf").write_bytes(b"%PDF-1.4 fake")


class TestSnapshotContents:
    def test_includes_content_plus_and_profiles_but_not_scratch_build_or_pdf(self, tmp_path):
        _make_project(tmp_path)
        store = VersionStore(tmp_path)

        version = store.save(name="first", timestamp="2026-01-01T00:00:00")
        archive = store.versions_dir / version.archive

        with tarfile.open(archive, "r:gz") as tar:
            names = {n.split("/", 1)[1] for n in tar.getnames() if "/" in n}

        # Kept: content, "+" auxiliaries, .doctor profile.
        assert "1. Introduction/1. Intro.md" in names
        assert "+figures/plot.svg" in names
        assert "+references.toml" in names
        assert ".doctor/book.toml" in names

        # Dropped: "_" scratch, the build dir, the versions dir, and the PDF.
        assert not any(n.startswith("_scratch") for n in names)
        assert not any(".doctor/build" in n for n in names)
        assert not any(".doctor/versions" in n for n in names)
        assert not any(n.endswith(".pdf") for n in names)


class TestVersionRegistry:
    def test_ids_auto_increment_and_list_is_ordered(self, tmp_path):
        _make_project(tmp_path)
        store = VersionStore(tmp_path)

        v1 = store.save(name="one", timestamp="2026-01-01T00:00:00")
        v2 = store.save(timestamp="2026-01-02T00:00:00")

        assert (v1.id, v2.id) == (1, 2)
        listed = store.list_versions()
        assert [v.id for v in listed] == [1, 2]
        assert listed[0].name == "one"
        assert listed[1].name == ""


class TestRestore:
    def test_restore_unpacks_alongside_and_never_swaps_head(self, tmp_path):
        _make_project(tmp_path)
        store = VersionStore(tmp_path)
        store.save(timestamp="2026-01-01T00:00:00")

        # Mutate HEAD after the snapshot.
        (tmp_path / "1. Introduction" / "1. Intro.md").write_text("# Changed\n")

        destination = store.restore(1)

        # The restored copy sits under .doctor/versions/, and HEAD is untouched.
        assert destination == tmp_path / ".doctor" / "versions" / "v1"
        assert (destination / "1. Introduction" / "1. Intro.md").read_text() == "# Intro\n"
        assert (tmp_path / "1. Introduction" / "1. Intro.md").read_text() == "# Changed\n"


class TestTaggedOutput:
    def test_hyphen_when_no_space(self):
        tagged = version_tagged_output(Path("/x/test-project.pdf"), 3)
        assert tagged.name == "test-project-v3.pdf"

    def test_spaced_when_name_has_space(self):
        tagged = version_tagged_output(Path("/x/Real Gauge Geometry.pdf"), 3)
        assert tagged.name == "Real Gauge Geometry - v3.pdf"
