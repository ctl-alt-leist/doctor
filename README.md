# Doctor

Academic document generation from Obsidian notes. Doctor compiles LaTeX-heavy markdown documents into PDFs using a CSS/HTML backend approach.

## Installation

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/ctl-alt-leist/doctor.git
cd doctor
make install-app   # install the `doc` command system-wide
```

`make install-app` installs the `doc` executable into the first writable standard
bin directory already on your PATH (`/opt/homebrew/bin`, `/usr/local/bin`, or
`~/.local/bin`), seeds the default configuration into `~/.config/doctor/defaults`, and
provisions the Chromium build that PDF output needs. Override the location with
`make install-app DOC_BIN_DIR=/some/bin`. Remove it with `make uninstall-app`.

For local development instead, use `make install`, which builds the project venv and
installs pre-commit hooks without touching your system.

## Usage

The `doc` command compiles a markdown file or a project directory. Its single argument
is a path, or a bare name located by searching downward from the current directory:

```bash
doc note.md          # compile one file -> note.pdf beside it (no doctor.toml needed)
doc path/to/Project  # compile a project directory -> Project.pdf
doc "X.II"           # find a directory or file by name and compile it
doc Galaxies -f html # choose the output format
```

A single file needs no configuration: doctor falls back to sensible defaults and titles
the document from its frontmatter, its first `#` heading, or its filename.

## Projects and the `.doctor/` anchor

A project is a directory holding a `.doctor/` directory. Running `doc` on any file or
subdirectory walks up to the nearest `.doctor/` and uses it as the config, build, and
version root.

```
MyBook/
  .doctor/
    book.toml          # a compilation profile (how it compiles)
    article.toml       # another profile; may `extends = "book.toml"`
    build/             # build scratch
    versions/          # saved snapshots
  +document.toml       # document info (title, authors, keywords, type)
  i. Preface.md        # front matter
  I. Foundations/      # a Part
    1. Introduction/   # a chapter
      1. Historical Context.md
  A. Appendices/       # an appendix
```

- **Compilation profiles** live in `.doctor/<name>.toml` and carry the *how* — style,
  layout, typography, bibliography, output. Pick one with `doc <target> --as article`;
  the default is `+document.toml`'s `type`, else `book`.
- **`+document.toml`** carries the *what* — title, authors, keywords — visible beside the
  writing. Title resolution: `--title` > `+document.toml` > directory/file name.

## Structure from the file tree

The document outline is derived from how directories are named — no structural
declarations in config:

| Naming | Role |
| --- | --- |
| `I.`, `II.` (uppercase Roman) | Part (full-page divider) |
| `1.`, `2.` (arabic) | Chapter (title page) |
| `1.`, `2.` nested in a chapter | Sub-chapter (inline heading, +1 heading level) |
| `i.`, `ii.` (lowercase Roman) | front matter |
| `A.`, `B.` (single letter) | appendix |

A file authored with plain `#`/`##` headings renders at the depth implied by its place in
the tree. Config styles these tiers but never defines them.

## Auxiliary and scratch prefixes

Two prefixes govern an open, user-chosen set of files and directories:

- **`+name`** — auxiliary: excluded from the main document but available to the build
  (`+figures/`, `+references.toml`) and compilable on its own (`+papers/`, `+slides/`).
  Kept in saved versions.
- **`_name`** — scratch: ignored entirely, never preserved in versions.

`README.md` and dot-directories are never treated as content.

## Versioning

Snapshot the state needed to reproduce a PDF, stored in `.doctor/versions/` as `.tar.gz`
(restorable with standard tools):

```bash
doc <target> --save-version [name]   # snapshot: content + "+" files + profiles
doc <target> --versions              # list saved versions
doc <target> --restore <id>          # unpack alongside the archive (never swaps HEAD)
doc <target> --build-version <id>    # compile a version -> tagged PDF beside HEAD
```

## Other commands

```bash
doc toc [-L DEPTH] [PATH]     # list a project as a table of contents (like `tree`)
doc <deck>.md --slides        # compile a markdown deck -> 16:9 presentation PDF
```

## Development

This project uses [uv](https://docs.astral.sh/uv/) for Python project management and [ruff](https://docs.astral.sh/ruff/) for linting.

```bash
make setup     # Create venv and sync dependencies
make lint      # Format and lint code
make test      # Run tests
make clean     # Remove generated files
```

---

*Claude Code was used in the development of this project.*
