"""
Tests for snapshot versioning: what a version contains, the auto-incrementing
ids, restore-alongside-never-swap, and version-tagged PDF naming.
"""

import tarfile
from pathlib import Path

from doctor.versioning import VersionStore, captured_references, version_tagged_output


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
    (root / "+figures" / ".DS_Store").write_bytes(b"\x00\x01macos junk")
    (root / "+references.toml").write_text("")
    (root / "_scratch").mkdir()
    (root / "_scratch" / "draft.md").write_text("# scratch\n")
    (root / ".DS_Store").write_bytes(b"\x00\x01macos junk")
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

        # Dropped everywhere: .DS_Store and other OS/editor dot-files.
        assert not any(n.endswith(".DS_Store") for n in names)


class TestBibliographyCapture:
    def test_external_bibliography_is_captured_and_readable(self, tmp_path):
        # A project whose bibliography lives OUTSIDE its root, reached by symlink
        # — the case that silently dropped every citation from a built version.
        project = tmp_path / "project"
        project.mkdir()
        _make_project(project)

        shared_bib = tmp_path / "shared" / "references.toml"
        shared_bib.parent.mkdir()
        shared_bib.write_text('[einstein-1905]\ntitle = "On the Electrodynamics of Moving Bodies"\n')
        symlinked = project / "linked-references.toml"
        symlinked.symlink_to(shared_bib)

        store = VersionStore(project)
        version = store.save(name="withbib", references=[symlinked], timestamp="2026-01-01T00:00:00")

        # The bibliography content is frozen inside the archive.
        with tarfile.open(store.versions_dir / version.archive, "r:gz") as tar:
            names = {n.split("/", 1)[1] for n in tar.getnames() if "/" in n}
        assert ".doctor/_versioned-refs/references.toml" in names

        # After restore, the capture reader hands the build the frozen copy, and
        # its content survives a later change to the shared source.
        shared_bib.write_text("# gutted after the snapshot\n")
        restored = store.restore(1)
        found = captured_references(restored)
        assert [p.name for p in found] == ["references.toml"]
        assert "einstein-1905" in found[0].read_text()

    def test_no_bibliography_leaves_no_capture_dir(self, tmp_path):
        _make_project(tmp_path)
        store = VersionStore(tmp_path)
        store.save(references=[], timestamp="2026-01-01T00:00:00")

        restored = store.restore(1)
        assert captured_references(restored) == []


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
