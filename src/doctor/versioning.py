"""
Snapshot versioning for a doctor project.

A version is a point-in-time snapshot of everything needed to reproduce a
document's PDF: the content files, the ``+`` auxiliaries, and the ``.doctor/``
profiles. It deliberately drops ``_`` scratch, the build directory, saved
versions themselves, other infrastructure dot-directories, and (for now) the
compiled PDF.

Snapshots live in ``.doctor/versions/`` as ``.tar.gz`` archives so they restore
with standard tools (``tar xzf``, or a double-click in Finder) with no
dependence on doctor. Restoring unpacks *alongside* the archive; it never swaps
or overwrites the working tree.
"""

import tarfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import toml


# Directories never included in a snapshot, even though they live under .doctor/
# or look like content.
_EXCLUDED_DIR_NAMES = {".git", ".obsidian", "node_modules", "__pycache__"}
_DOCTOR_TRANSIENT = {"build", "versions"}


@dataclass
class Version:
    """Metadata for one saved snapshot."""

    id: int
    name: str
    created: str
    archive: str  # filename within .doctor/versions/

    @property
    def label(self) -> str:
        return self.name or f"v{self.id}"


class VersionStore:
    """Manages the snapshots under ``<doctor_root>/.doctor/versions/``."""

    def __init__(self, doctor_root: Path):
        self.doctor_root = doctor_root.resolve()
        self.versions_dir = self.doctor_root / ".doctor" / "versions"
        self.index_path = self.versions_dir / "index.toml"

    # -- reading -------------------------------------------------------------

    def list_versions(self) -> List[Version]:
        """All saved versions, oldest first."""
        if not self.index_path.exists():
            return []

        with open(self.index_path, "r", encoding="utf-8") as handle:
            data = toml.load(handle)

        versions = [
            Version(id=entry["id"], name=entry.get("name", ""), created=entry["created"], archive=entry["archive"])
            for entry in data.get("version", [])
        ]

        return sorted(versions, key=lambda v: v.id)

    def get(self, version_id: int) -> Optional[Version]:
        return next((v for v in self.list_versions() if v.id == version_id), None)

    def _next_id(self) -> int:
        existing = self.list_versions()

        return (max((v.id for v in existing), default=0)) + 1

    # -- writing -------------------------------------------------------------

    def save(self, name: str = "", timestamp: Optional[str] = None) -> Version:
        """Write a snapshot of the project to a new ``.tar.gz`` and record it."""
        self.versions_dir.mkdir(parents=True, exist_ok=True)

        version_id = self._next_id()
        created = timestamp or datetime.now().isoformat(timespec="seconds")
        archive_name = f"v{version_id}.tar.gz"
        archive_path = self.versions_dir / archive_name

        root_label = f"v{version_id}"
        with tarfile.open(archive_path, "w:gz") as tar:
            for path in self._snapshot_files():
                arcname = f"{root_label}/{path.relative_to(self.doctor_root).as_posix()}"
                tar.add(path, arcname=arcname)

        version = Version(id=version_id, name=name, created=created, archive=archive_name)
        self._append_to_index(version)

        return version

    def _append_to_index(self, version: Version) -> None:
        versions = self.list_versions()
        versions.append(version)
        data = {"version": [{"id": v.id, "name": v.name, "created": v.created, "archive": v.archive} for v in versions]}
        with open(self.index_path, "w", encoding="utf-8") as handle:
            toml.dump(data, handle)

    def _snapshot_files(self) -> List[Path]:
        """Every file that belongs in a snapshot, walked from the project root."""
        collected: List[Path] = []
        self._walk(self.doctor_root, collected)

        return collected

    def _walk(self, directory: Path, collected: List[Path]) -> None:
        for item in sorted(directory.iterdir()):
            if item.is_dir():
                if not self._include_dir(item):
                    continue
                self._walk(item, collected)
            elif item.is_file():
                if self._include_file(item):
                    collected.append(item)

    def _include_dir(self, path: Path) -> bool:
        name = path.name
        if name.startswith("_") or name in _EXCLUDED_DIR_NAMES:
            return False

        # Keep .doctor itself (profiles, css) but never its transient subdirs.
        if name == ".doctor":
            return True
        rel = path.relative_to(self.doctor_root).parts
        if rel and rel[0] == ".doctor" and len(rel) >= 2 and rel[1] in _DOCTOR_TRANSIENT:
            return False

        # Other dot-directories are infrastructure and excluded.
        if name.startswith(".") and name != ".doctor":
            return False

        return True

    def _include_file(self, path: Path) -> bool:
        # Scratch is never snapshotted; a "+" auxiliary is always kept.
        if any(part.startswith("_") for part in path.relative_to(self.doctor_root).parts):
            return False

        # The compiled PDF is not stored (yet); see the --keep-pdf stub.
        if path.suffix.lower() == ".pdf":
            return False

        return True

    # -- restoring -----------------------------------------------------------

    def restore(self, version_id: int) -> Path:
        """
        Unpack a version *alongside* its archive, into
        ``.doctor/versions/v<id>/``. Never touches the working tree.
        """
        version = self.get(version_id)
        if version is None:
            raise ValueError(f"No such version: v{version_id}")

        archive_path = self.versions_dir / version.archive
        if not archive_path.exists():
            raise FileNotFoundError(f"Version archive missing: {archive_path}")

        destination = self.versions_dir / f"v{version_id}"
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(self.versions_dir, filter="data")

        return destination


def version_tagged_output(output_path: Path, version_id: int) -> Path:
    """
    Insert a version tag before ``.pdf``. The separator matches the base name's
    style: a space if the base name already contains one, else a hyphen.

    ``Real Gauge Geometry.pdf`` -> ``Real Gauge Geometry - v3.pdf``
    ``test-project.pdf``        -> ``test-project-v3.pdf``
    """
    stem = output_path.stem
    separator = f" - v{version_id}" if " " in stem else f"-v{version_id}"

    return output_path.with_name(f"{stem}{separator}{output_path.suffix}")
