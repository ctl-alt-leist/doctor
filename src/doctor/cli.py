"""
Doctor CLI module
Command line interface for academic document generation
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from doctor.configs import load_configs, resolve_config_path
from doctor.discovery import (
    MARKDOWN_EXTENSIONS,
    discover_project_files,
    discover_single_file,
    get_structure_stats,
    print_structure_summary,
)
from doctor.generators import HTMLGenerator, PDFGenerator
from doctor.ingest import (
    BibliographyProcessing,
    ContentIngestion,
    CrossReferenceTracking,
    DocumentAssembly,
    IngestionReport,
    StructureAnalysis,
)
from doctor.resolve import TargetResolutionError, resolve_target
from doctor.tools import ReforgCommand


def _version_id(value: str) -> int:
    """
    Parse a version identifier from the CLI. Versions are named ``v1``, ``v2``,
    … everywhere doctor shows them (``--versions``, the archives, the restore
    dirs), so that is the form accepted here. The leading ``v`` is required.
    """
    text = value.strip()
    if not (text[:1].lower() == "v" and text[1:].isdigit()):
        raise argparse.ArgumentTypeError(f"invalid version id: {value!r} (expected e.g. 'v1')")

    return int(text[1:])


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for Doctor CLI."""
    parser = argparse.ArgumentParser(
        prog="doc",
        description="Generate professional academic documents from Obsidian-style markdown",
        epilog="For more information, see: https://github.com/doctor/doctor",
    )

    # Positional argument: a path to a markdown file or a project directory
    parser.add_argument(
        "target",
        help="Path to the markdown file or project directory to compile "
        "(relative or absolute; a leading '~' is expanded).",
    )

    # Configuration files
    parser.add_argument(
        "-c",
        "--config",
        dest="config_paths",
        type=Path,
        nargs="*",
        help="Path to config file(s) or directory containing TOML configs. "
        "If not specified, uses defaults with project-level doctor.toml if present.",
    )

    # Compilation profile (the "how": style/layout/typography), from .doctor/<name>.toml
    parser.add_argument(
        "--as",
        dest="profile",
        metavar="PROFILE",
        help="Compilation profile to compile as (e.g. book, article, audiobook). "
        "Loads .doctor/<PROFILE>.toml. Defaults to the type in +document.toml, else 'book'.",
    )

    # Document title override (highest priority in title resolution)
    parser.add_argument(
        "--title",
        dest="title",
        help="Document title. Overrides +document.toml and the filename/dirname fallback.",
    )

    # Output file
    parser.add_argument(
        "-o",
        "--output",
        dest="output_path",
        type=Path,
        help="Output file path. Default: <project-name>.pdf in project directory",
    )

    # Build directory
    parser.add_argument(
        "-b",
        "--build-dir",
        dest="build_dir",
        type=Path,
        help="Build directory for intermediate files. Default: .doctor-build/ in project",
    )

    # Output formats
    parser.add_argument(
        "-f",
        "--format",
        dest="formats",
        choices=["html", "pdf", "docx"],
        nargs="+",
        default=["pdf"],
        help="Output format(s). Default: pdf",
    )

    # Slides mode: compile the target markdown as a presentation instead of a document
    parser.add_argument(
        "--slides",
        action="store_true",
        help="Compile the target markdown file as a 16:9 slide deck (slides separated by '---')",
    )

    # Verbosity
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (-v, -vv, -vvv)",
    )

    # Quiet mode
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress all output except errors",
    )

    # Watch mode (future feature)
    parser.add_argument(
        "-w",
        "--watch",
        action="store_true",
        help="Watch for file changes and rebuild automatically",
    )

    # Clean build directory
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean build directory before processing",
    )

    # Development options
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually processing",
    )

    parser.add_argument(
        "--list-configs",
        action="store_true",
        help="List all configuration files that would be loaded",
    )

    parser.add_argument(
        "--list-files",
        action="store_true",
        help="List all markdown files that would be processed",
    )

    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate project structure without processing",
    )

    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate ingestion pipeline report showing parsed content, references, and citations",
    )

    # Versioning: snapshot / list / restore / build a saved version
    parser.add_argument(
        "--save-version",
        dest="save_version",
        nargs="?",
        const="",
        default=None,
        metavar="NAME",
        help="Save a snapshot of the project to .doctor/versions/ (optional name)",
    )

    parser.add_argument(
        "--versions",
        action="store_true",
        help="List saved versions",
    )

    parser.add_argument(
        "--restore",
        dest="restore",
        type=_version_id,
        metavar="vN",
        help="Unpack a saved version (e.g. v1) alongside its archive in .doctor/versions/ (never swaps HEAD)",
    )

    parser.add_argument(
        "--build-version",
        dest="build_version",
        type=_version_id,
        metavar="vN",
        help="Compile a saved version (e.g. v1) and write its PDF with a version tag",
    )

    parser.add_argument(
        "--keep-pdf",
        dest="keep_pdf",
        action="store_true",
        help="(with --save-version) also store the compiled PDF in the snapshot — not available yet",
    )

    # Reference organizer special flag
    parser.add_argument(
        "--reforg",
        metavar="REFS_FILE",
        type=Path,
        help="Reorganize references.toml file instead of generating documents",
    )

    parser.add_argument(
        "--reforg-sort-by",
        choices=["year", "author", "journal", "type", "title"],
        default="year",
        help="How to organize references when using --reforg (default: year)",
    )

    parser.add_argument(
        "--reforg-reverse",
        action="store_true",
        help="Reverse the sort order when using --reforg",
    )

    parser.add_argument(
        "--reforg-output",
        type=Path,
        help="Output file path for reforg (if not specified, prints to stdout and asks for confirmation)",
    )

    parser.add_argument(
        "--reforg-verbose",
        action="store_true",
        help="Show detailed information about the reorganization when using --reforg",
    )

    return parser


def find_doctor_root(start: Path) -> Optional[Path]:
    """
    Walk up from ``start`` to the nearest directory that holds a ``.doctor/``
    directory, and return that directory. Returns None if none is found.

    This is the project anchor: it holds compilation profiles, build scratch,
    and saved versions, and it lets ``doc`` be run from any file or subdirectory.
    """
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".doctor").is_dir():
            return candidate

    return None


def read_document_type(doctor_root: Path) -> Optional[str]:
    """Read the ``type`` field from ``+document.toml`` (the default profile), if present."""
    document_file = doctor_root / "+document.toml"
    if not document_file.exists():
        return None

    import toml

    try:
        with open(document_file, "r", encoding="utf-8") as handle:
            data = toml.load(handle)
    except Exception:
        return None

    document = data.get("document", data)

    return document.get("type")


class CliArgs:
    """Parsed and validated CLI arguments."""

    def __init__(self, args: argparse.Namespace):
        # The target may be a single markdown file or a project directory.
        self.target_path = resolve_target(args.target)
        self.is_single_file = self.target_path.is_file()

        # The content root is what gets swept: a single file's parent, or the project dir.
        self.project_path = self.target_path.parent if self.is_single_file else self.target_path

        # The .doctor/ anchor holds profiles, build scratch, and versions. It may sit
        # above the content root (running doc on a chapter deep inside a project).
        self.doctor_root = find_doctor_root(self.project_path) or self.project_path

        self.profile = getattr(args, "profile", None)
        self.title = getattr(args, "title", None)

        self.config_paths = self._resolve_config_paths(args.config_paths)
        self.output_path = self._resolve_output_path(args.output_path)
        self.build_dir = self._resolve_build_dir(args.build_dir)
        self.formats = args.formats
        self.verbose = args.verbose
        self.quiet = args.quiet
        self.watch = args.watch
        self.clean = args.clean
        self.dry_run = args.dry_run
        self.list_configs = args.list_configs
        self.list_files = args.list_files
        self.validate = args.validate
        self.report = args.report
        self.slides = getattr(args, "slides", False)

        # Versioning attributes
        self.save_version = getattr(args, "save_version", None)
        self.versions = getattr(args, "versions", False)
        self.restore = getattr(args, "restore", None)
        self.build_version = getattr(args, "build_version", None)
        self.keep_pdf = getattr(args, "keep_pdf", False)
        # Set when building a saved version: the bibliography files captured in
        # the snapshot to compile against, overriding config/project resolution.
        self.references_override: Optional[List[Path]] = None

        # Reforg-specific attributes
        self.reforg = args.reforg
        self.reforg_sort_by = args.reforg_sort_by
        self.reforg_reverse = args.reforg_reverse
        self.reforg_output = args.reforg_output
        self.reforg_verbose = args.reforg_verbose

        self._validate()

    def _resolve_config_paths(self, config_paths: Optional[List[Path]]) -> List[Path]:
        """
        Resolve configuration paths.

        With no explicit ``--config``, precedence is:

        1. A ``.doctor/`` anchor: the selected compilation profile
           (``.doctor/<profile>.toml``) followed by the visible ``+document.toml``
           (document information layered on top of the profile).
        2. Legacy: a project-level ``doctor.toml``.
        """
        if not config_paths:
            return self._resolve_project_configs()

        resolved_paths = []
        for path in config_paths:
            resolved_path = path.resolve()

            if resolved_path.is_dir():
                # Directory: find all .toml files
                toml_files = list(resolved_path.glob("*.toml"))
                resolved_paths.extend(toml_files)
            elif resolved_path.is_file():
                # Single file
                resolved_paths.append(resolved_path)
            else:
                raise FileNotFoundError(f"Config path not found: {path}")

        return resolved_paths

    def _resolve_project_configs(self) -> List[Path]:
        """Assemble the profile + document-info config chain for a project."""
        doctor_dir = self.doctor_root / ".doctor"
        paths: List[Path] = []

        if doctor_dir.is_dir():
            # The profile: --as wins, else +document.toml's type, else "book".
            profile_name = self.profile or read_document_type(self.doctor_root) or "book"
            self.profile = profile_name
            profile_path = doctor_dir / f"{profile_name}.toml"
            if profile_path.exists():
                paths.append(profile_path)

            document_path = self.doctor_root / "+document.toml"
            if document_path.exists():
                paths.append(document_path)

            return paths

        # Legacy: a single project-level doctor.toml.
        legacy = self.doctor_root / "doctor.toml"
        if legacy.exists():
            return [legacy]

        return []

    def _resolve_output_path(self, output_path: Optional[Path]) -> Path:
        """Resolve output file path."""
        if output_path:
            return output_path.resolve()

        # Single file: sibling PDF with the same name and path (note.md -> note.pdf).
        if self.is_single_file:
            return self.target_path.with_suffix(".pdf")

        # Directory: <project-name>.pdf in the project directory.
        project_name = self.project_path.name
        return self.project_path / f"{project_name}.pdf"

    def _resolve_build_dir(self, build_dir: Optional[Path]) -> Path:
        """Resolve build directory path."""
        if build_dir:
            return build_dir.resolve()

        # With a .doctor/ anchor, build scratch lives inside it; otherwise fall
        # back to the legacy .doctor-build/ beside the content.
        if (self.doctor_root / ".doctor").is_dir():
            return self.doctor_root / ".doctor" / "build"

        return self.project_path / ".doctor-build"

    def _validate(self):
        """Validate arguments."""
        if not self.target_path.exists():
            raise FileNotFoundError(f"Target not found: {self.target_path}")

        # A single-file target must be a markdown file.
        if self.is_single_file and self.target_path.suffix.lower() not in MARKDOWN_EXTENSIONS:
            raise ValueError(f"Target file is not a markdown file: {self.target_path}")

        # Check for conflicting verbosity options
        if self.quiet and self.verbose > 0:
            raise ValueError("Cannot specify both --quiet and --verbose")

        # Validate output path directory exists
        output_parent = self.output_path.parent
        if not output_parent.exists():
            raise FileNotFoundError(f"Output directory not found: {output_parent}")


def _resolve_references_files(config, project_path: Path, override: Optional[List[Path]] = None) -> List[Path]:
    """
    Resolve all references file paths from config or project directory.

    Priority:
    0. ``override`` — when building a saved version, the bibliography captured
       inside the snapshot. Takes full precedence: those files *are* the
       bibliography, so no config- or project-relative resolution is attempted.
    1. Config bibliography.references_file (resolved relative to config file)
       - Can be a single string or list of strings
       - All specified files are loaded and merged
    2. references.toml in project directory (fallback)

    Returns:
        List of existing reference file paths
    """
    if override:
        return [Path(path).resolve() for path in override if Path(path).exists()]

    resolved_files = []

    # Check config for references_file
    if hasattr(config, "bibliography") and config.bibliography.references_file:
        refs = config.bibliography.references_file
        if isinstance(refs, str):
            refs = [refs]

        # Resolve each reference file path
        for ref_path in refs:
            resolved = resolve_config_path(ref_path)
            if resolved.exists():
                resolved_files.append(resolved)

    # If no files found from config, try fallbacks in the project root.
    # "+references.toml" is the auxiliary-prefixed name; plain "references.toml"
    # is still honored for projects that have not adopted the "+" convention.
    if not resolved_files:
        for name in ("+references.toml", "references.toml"):
            fallback = project_path / name
            if fallback.exists():
                resolved_files.append(fallback)
                break

    return resolved_files


def _resolve_title(config, args) -> None:
    """
    Apply title resolution in place: ``--title`` wins, then the title already in
    the config (from ``+document.toml`` or the profile), then a fallback derived
    from the target — the file stem for a single file, the directory name for a
    project.
    """
    if not (config and getattr(config, "document", None)):
        return

    if args.title:
        config.document.title = args.title
        return

    current = config.document.title
    if current and current != "Untitled Document":
        return

    if args.is_single_file:
        config.document.title = args.target_path.stem
    else:
        config.document.title = args.project_path.name


def _outline_for(path: Path):
    """Build the document outline for a directory or single file (no generation)."""
    resolved = path.resolve()
    if resolved.is_file():
        structure = discover_single_file(resolved)
        project_root = resolved.parent
    else:
        structure = discover_project_files(resolved)
        project_root = resolved

    content_ingestion = ContentIngestion()
    parsed_files = [content_ingestion.ingest_file(f) for f in structure.get_ordered_files()]
    document_structure = StructureAnalysis(project_root=project_root).analyze_files(parsed_files)

    return document_structure.global_outline


def _print_toc_entries(entries, max_depth: int, depth: int = 1) -> None:
    for entry in entries:
        indent = "  " * (depth - 1)
        number = f"{entry.number} " if entry.number else ""
        print(f"{indent}{number}{entry.title}")
        if entry.children and depth < max_depth:
            _print_toc_entries(entry.children, max_depth, depth + 1)


def _run_toc(argv: List[str]) -> int:
    """
    ``doc toc [-L DEPTH] [PATH]`` — list a project as a table of contents,
    like ``tree`` but showing the document's structure. Default depth covers the
    Parts/chapters and their file-level headings; deeper descends into
    sub-headings within files.
    """
    parser = argparse.ArgumentParser(prog="doc toc", description="List a project as a table of contents")
    parser.add_argument("path", nargs="?", default=".", help="Project directory or file (default: current directory)")
    parser.add_argument("-L", "--depth", type=int, default=3, help="Levels of the outline to show (default: 3)")
    toc_args = parser.parse_args(argv)

    target = Path(toc_args.path)
    if not target.exists():
        print(f"Error: path not found: {target}", file=sys.stderr)
        return 1

    outline = _outline_for(target)
    if not outline.entries:
        print("(no structure found)")
        return 0

    _print_toc_entries(outline.entries, max(1, toc_args.depth))

    return 0


def _compile(args) -> list:
    """Load config, discover, run the pipeline, and generate outputs for ``args``."""
    config = load_configs(args.config_paths, project_path=args.project_path, base_path=args.doctor_root)
    _resolve_title(config, args)

    if args.is_single_file:
        structure = discover_single_file(args.target_path)
    else:
        structure = discover_project_files(args.project_path)

    if not args.quiet:
        print(f"📄 Processing {structure.total_files} markdown files")

    assembled_doc = _run_ingestion_pipeline(structure, args, config)
    results = _generate_documents(assembled_doc, args, config)

    for result in results:
        if result.success:
            size_mb = result.file_size / (1024 * 1024)
            print(f"✅ Generated {result.format.upper()}: {result.output_path} ({size_mb:.1f}MB)")
        else:
            print(f"❌ Failed to generate {result.format.upper()}: {result.output_path}", file=sys.stderr)

    return results


def _handle_slides(args) -> int:
    """Compile the target markdown file as a slide deck."""
    from doctor.generators import SlidesGenerator

    if not args.is_single_file:
        print("Error: --slides expects a single markdown file, not a project directory.", file=sys.stderr)
        return 1

    deck = args.target_path
    output_path = args.output_path.with_suffix(".pdf")
    config = load_configs(args.config_paths, project_path=args.project_path, base_path=args.doctor_root)

    if not args.quiet:
        print(f"🖼  Compiling slides: {deck.name}")

    generator = SlidesGenerator(args.build_dir, config)
    result = generator.generate(deck, output_path)

    if result.success:
        size_mb = result.file_size / (1024 * 1024)
        print(f"✅ Generated slides: {result.output_path} ({size_mb:.1f}MB)")
        return 0

    for error in result.errors:
        print(f"❌ {error}", file=sys.stderr)

    return 1


def _handle_versioning(args) -> int:
    """Dispatch --versions / --save-version / --restore / --build-version."""
    from doctor.versioning import VersionStore, captured_references, version_tagged_output

    store = VersionStore(args.doctor_root)

    if args.versions:
        versions = store.list_versions()
        if not versions:
            print("No saved versions.")
        else:
            print("Saved versions:")
            for version in versions:
                name = f"  {version.name}" if version.name else ""
                print(f"  v{version.id}  {version.created}{name}")
        return 0

    if args.save_version is not None:
        if args.keep_pdf:
            print("Note: storing the compiled PDF inside a version is not available yet; saving without it.")

        # Resolve the bibliography now so it is captured into the snapshot. It
        # commonly lives outside the project root (a shared, symlinked store),
        # so without this a built version loses all of its citations.
        config = load_configs(args.config_paths, project_path=args.project_path, base_path=args.doctor_root)
        references = _resolve_references_files(config, args.project_path)

        version = store.save(name=args.save_version, references=references)
        named = f" '{version.name}'" if version.name else ""
        print(f"✅ Saved version v{version.id}{named} → {store.versions_dir / version.archive}")
        if references:
            print(f"   ↳ captured {len(references)} bibliography file(s) into the snapshot")
        return 0

    if args.restore is not None:
        try:
            destination = store.restore(args.restore)
        except (ValueError, FileNotFoundError) as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        print(f"✅ Restored v{args.restore} alongside its archive → {destination}")
        return 0

    if args.build_version is not None:
        try:
            restored_root = store.restore(args.build_version)
        except (ValueError, FileNotFoundError) as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

        # The PDF lands beside the HEAD output, tagged with the version id.
        tagged_output = version_tagged_output(args.output_path.with_suffix(".pdf"), args.build_version)
        sub_namespace = create_parser().parse_args([
            str(restored_root),
            "--format",
            "pdf",
            "--output",
            str(tagged_output),
        ])
        sub_args = CliArgs(sub_namespace)

        # Compile against the bibliography captured in the snapshot, not the live
        # external one — this is what makes a built version reproduce its citations.
        sub_args.references_override = captured_references(restored_root)

        _compile(sub_args)
        print(f"📎 Built v{args.build_version} → {tagged_output}")
        return 0

    return 0


def _run_ingestion_pipeline(structure, args, config):
    """Run the complete ingestion pipeline and return assembled document."""
    # Step 1: Content Ingestion (G → L)
    content_ingestion = ContentIngestion()
    parsed_files = []

    for md_file in structure.get_ordered_files():
        try:
            parsed_content = content_ingestion.ingest_file(md_file)
            parsed_files.append(parsed_content)
        except Exception as e:
            if args.verbose > 0:
                print(f"Warning: Failed to parse {md_file.relative_path}: {e}")

    # Step 2: Structure Analysis (H → N)
    structure_analysis = StructureAnalysis(project_root=args.project_path)
    document_structure = structure_analysis.analyze_files(parsed_files)

    # Step 3: Cross-Reference Tracking (I → O)
    reference_tracking = CrossReferenceTracking(args.project_path)
    reference_map = reference_tracking.track_references(document_structure)

    # Step 4: Bibliography Processing (J → P)
    bib_processing = BibliographyProcessing()
    references_files = _resolve_references_files(
        config, args.project_path, override=getattr(args, "references_override", None)
    )
    citation_database = bib_processing.process_bibliography(parsed_files, references_files)

    # Step 5: Document Assembly (K)
    assembler = DocumentAssembly(config)
    assembled_doc = assembler.assemble_document(document_structure, reference_map, citation_database)

    return assembled_doc


def _generate_documents(assembled_doc, args, config):
    """Generate documents in all requested formats."""
    from doctor.generators.base import OutputFormat

    results = []

    for format_str in args.formats:
        OutputFormat(format_str)

        # Generate output filename with correct extension
        if format_str == "html":
            output_path = args.output_path.with_suffix(".html")
            html_mode = (
                getattr(config.output.html, "html_mode", "single")
                if config and hasattr(config, "output") and hasattr(config.output, "html")
                else "single"
            )
            generator = HTMLGenerator(args.build_dir, html_mode, config)
        elif format_str == "pdf":
            output_path = args.output_path.with_suffix(".pdf")
            generator = PDFGenerator(args.build_dir, config)
        elif format_str == "docx":
            output_path = args.output_path.with_suffix(".docx")
            # TODO: Implement DOCX generator
            continue  # Skip DOCX for now
        else:
            continue  # Unknown format

        # Generate document
        result = generator.generate(assembled_doc, output_path)
        results.append(result)

    return results


def parse_args(args: Optional[List[str]] = None) -> CliArgs:
    """Parse command line arguments."""
    parser = create_parser()
    parsed_args = parser.parse_args(args)

    try:
        return CliArgs(parsed_args)
    except (FileNotFoundError, NotADirectoryError, ValueError, TargetResolutionError) as e:
        parser.error(str(e))


def main():
    """Main CLI entry point."""
    # Bound before the try so the catch-all handler can inspect it even when
    # CliArgs construction (e.g. an unresolvable target path) fails early.
    args = None
    try:
        # The `toc` subcommand is handled by its own parser before the main one.
        if len(sys.argv) > 1 and sys.argv[1] == "toc":
            return _run_toc(sys.argv[2:])

        parser = create_parser()
        parsed_args = parser.parse_args()

        # Handle reforg flag
        if parsed_args.reforg:
            reforg_command = ReforgCommand()
            # Convert namespace to arg list for reforg command
            reforg_args = [str(parsed_args.reforg), "--sort-by", parsed_args.reforg_sort_by]
            if parsed_args.reforg_reverse:
                reforg_args.append("--reverse")
            if parsed_args.reforg_output:
                reforg_args.extend(["--output", str(parsed_args.reforg_output)])
            if parsed_args.dry_run:
                reforg_args.append("--dry-run")
            if parsed_args.reforg_verbose:
                reforg_args.append("--verbose")

            return reforg_command.run(reforg_args)

        # Handle document generation (default)
        args = CliArgs(parsed_args)

        # Handle slides mode (compile the target as a presentation)
        if args.slides:
            return _handle_slides(args)

        # Handle versioning commands (snapshot / list / restore / build a version)
        if args.versions or args.save_version is not None or args.restore is not None or args.build_version is not None:
            return _handle_versioning(args)

        # Load configurations. Config-relative paths (e.g. references_file) resolve
        # against the project root, even when profiles live in .doctor/.
        config = load_configs(args.config_paths, project_path=args.project_path, base_path=args.doctor_root)

        # Title resolution: --title > +document.toml/profile title > dir/filename.
        _resolve_title(config, args)

        # Discover files: a single markdown file, or a full project directory
        try:
            if args.is_single_file:
                structure = discover_single_file(args.target_path)
            else:
                structure = discover_project_files(args.project_path)
        except (FileNotFoundError, ValueError) as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        if args.list_configs:
            print("Configuration files:")
            if args.config_paths:
                for config_path in args.config_paths:
                    print(f"  {config_path}")
            else:
                print("  (using defaults)")
            return

        if args.list_files:
            print("Discovered markdown files:")
            for file in structure.get_ordered_files():
                print(f"  {file.relative_path}")
            return

        if args.validate:
            print_structure_summary(structure)
            stats = get_structure_stats(structure)

            # Check for potential issues
            warnings = []
            if stats["files_in_root"] == 0:
                warnings.append("No files in project root")
            if stats["deepest_nesting"] > 3:
                warnings.append(f"Deep nesting detected ({stats['deepest_nesting']} levels)")
            if stats["largest_directory"] > 20:
                warnings.append(f"Large directory detected ({stats['largest_directory']} files)")

            if warnings:
                print("Warnings:")
                for warning in warnings:
                    print(f"  ⚠  {warning}")
            else:
                print("✓ Project structure looks good")
            return

        if args.report:
            # Run full ingestion pipeline and generate report
            if not args.quiet:
                print(f"Generating ingestion report for {structure.total_files} files...")

            # Run ingestion pipeline
            try:
                assembled_doc = _run_ingestion_pipeline(structure, args, config)

                # Generate and display report
                reporter = IngestionReport()
                reporter.print_report(assembled_doc)

                # Optionally save report to file
                report_path = args.build_dir / "ingestion-report.txt"
                args.build_dir.mkdir(parents=True, exist_ok=True)
                reporter.write_report_file(assembled_doc, report_path)

                if not args.quiet:
                    print(f"\nReport saved to: {report_path}")

            except Exception as e:
                print(f"Error generating ingestion report: {e}", file=sys.stderr)
                if args.verbose > 1:
                    import traceback

                    traceback.print_exc()
                sys.exit(1)
            return

        if args.dry_run:
            print(f"Would process: {args.target_path}")
            print(f"Output: {args.output_path}")
            print(f"Build dir: {args.build_dir}")
            print(f"Formats: {', '.join(args.formats)}")
            print(f"Config files: {len(args.config_paths)}")
            print(f"Markdown files: {structure.total_files}")
            print_structure_summary(structure)
            return

        # Process the documents
        if not args.quiet:
            print(f"📁 Target: {args.target_path}")
            print(f"📄 Processing {structure.total_files} markdown files")
            if args.verbose > 0:
                print_structure_summary(structure)

        # Run document generation
        try:
            if not args.quiet:
                print("🔄 Processing content and citations...")
            assembled_doc = _run_ingestion_pipeline(structure, args, config)

            if not args.quiet:
                print("📝 Generating documents...")
            results = _generate_documents(assembled_doc, args, config)

            # Report results
            if not args.quiet:
                print()  # Empty line for spacing
            for result in results:
                if result.success:
                    size_mb = result.file_size / (1024 * 1024)
                    print(f"✅ Generated {result.format.upper()}: {result.output_path} ({size_mb:.1f}MB)")
                    if result.warnings:
                        for warning in result.warnings:
                            print(f"   ⚠️  {warning}")
                else:
                    print(f"❌ Failed to generate {result.format.upper()}: {result.output_path}")
                    for error in result.errors:
                        print(f"   💥 {error}")

            # Summary
            if not args.quiet:
                successful_results = [r for r in results if r.success]
                if successful_results:
                    total_citations = assembled_doc.total_citations
                    missing_citations = len(assembled_doc.missing_citations)
                    print(f"\n📊 Summary: {len(successful_results)} document(s) generated")
                    if total_citations > 0:
                        resolved = total_citations - missing_citations
                        print(f"📚 Citations: {resolved}/{total_citations} resolved")

        except Exception as e:
            print(f"Error during document generation: {e}", file=sys.stderr)
            if args.verbose > 1:
                import traceback

                traceback.print_exc()
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        if hasattr(args, "verbose") and args.verbose > 1:
            import traceback

            traceback.print_exc()
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
