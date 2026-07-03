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

A single file needs no `doctor.toml`: doctor falls back to sensible defaults and titles
the document from its frontmatter, its first `#` heading, or its filename.

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
