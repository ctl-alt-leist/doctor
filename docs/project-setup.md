# Setting Up and Migrating a Doctor Project

This guide describes how a doctor project is structured, how to set one up from
scratch, and — step by step — how to migrate an existing project onto the
current conventions. The migration section is written so it can be followed
mechanically, one project at a time.

## The project model

A **project** is a directory that contains a `.doctor/` directory. Running `doc`
on any file or subdirectory walks *up* to the nearest `.doctor/` and treats that
directory as the project root — the anchor for configuration, build scratch, and
saved versions.

```
MyProject/
  .doctor/
    book.toml          # a compilation profile (the "how")
    article.toml       # another profile; may `extends` book.toml
    build/             # build scratch (regenerated; safe to delete)
    versions/          # saved snapshots (.tar.gz)
  +document.toml       # document information (the "what")
  +figures/            # assets used by the document
  +references.toml     # bibliography (optional; may point elsewhere)
  i. Preface.md        # front matter
  I. Foundations/      # a Part
    1. Introduction/   # a chapter
      1. First Section.md
  A. Appendices/       # an appendix
```

Two ideas do the work:

- **Profiles carry the *how*** — style, layout, typography, bibliography, output.
  They live in `.doctor/<name>.toml`. Select one at compile time with
  `doc <target> --as <name>`. The default profile is the `type` field in
  `+document.toml`, falling back to `book`.
- **`+document.toml` carries the *what*** — `title`, `authors`, `keywords`, and
  `type`. It sits visibly beside the writing, separate from the profiles.

`type` is an open string: it *names a profile*. `book`, `article`, `audiobook`,
or any name a project defines are all valid.

### Structure comes from the file tree

The document outline is derived from directory names; nothing structural is
declared in config. A file authored with plain `#`/`##` headings renders at the
depth implied by where it sits in the tree.

| Directory name | Role |
| --- | --- |
| `I.`, `II.` (uppercase Roman) | Part — full-page divider |
| `1.`, `2.` (arabic) | Chapter — title page |
| `1.`, `2.` nested inside a chapter | Sub-chapter — inline heading, +1 heading level |
| `i.`, `ii.` (lowercase Roman) | front matter |
| `A.`, `B.` (single letter) | appendix — title page, lettered |

Parts do **not** add a heading level; chapters and sub-chapters do. A single
Roman letter beside a multi-letter Roman Part (e.g. `I.` next to `II.`) is a
Part; otherwise a single letter is an appendix.

### The `+` and `_` prefixes

Two prefixes govern an open, user-chosen set of files and directories:

- **`+name`** — *auxiliary*: excluded from the main document's content, but
  available to the build (`+figures/`, `+references.toml`) and compilable on its
  own (`+audio/`, `+papers/`). **Kept in saved versions.**
- **`_name`** — *scratch*: ignored entirely. Not compiled, not resolved as an
  asset, **not preserved in versions**. Use it for drafts, archives, and
  reference copies of old work.

`README.md` and any dot-path (`.doctor`, `.git`, `.obsidian`, `.claude`) are
never treated as content.

## Setting up a new project

1. Create `.doctor/` at the project root.
2. Add a profile, e.g. `.doctor/book.toml`:

   ```toml
   # extends is optional; use it to inherit a shared vault-level config.
   extends = "../../doctor.toml"

   [bibliography]
   references_file = "+references.toml"
   ```

3. Add `+document.toml`:

   ```toml
   [document]
   type = "book"
   title = "My Title"
   authors = ["Author Name"]
   ```

4. Author content using the naming conventions above. Put assets in `+figures/`
   and reference them as `+figures/name.svg`.
5. Compile: `doc <project> --format pdf` (or `--as article`, `--title "…"`).

## Migrating an existing project

This is the procedure applied to a project that still uses a root `doctor.toml`,
`_figures`, `_audio`, `.doctor-build`, and so on. **Back up first** (a zip of the
project directory is enough — the vault is live and synced). Do one project at a
time, and compile after each stage to catch problems early.

Throughout, run `doc` from a checkout of the doctor repo (`uv run doc "<abs
path>"`) so the current code is what compiles, and refer to the project by its
absolute path — a `cd` does not persist across steps.

### Step 1 — Config: `doctor.toml` → `.doctor/` + `+document.toml`

Read the existing root `doctor.toml`. Split it:

- Create `.doctor/<profile>.toml` (name it after the document — `book`,
  `article`, `audiobook`). Move the compilation sections into it: `extends`,
  `[bibliography]`, and anything style/layout/output.
- Create `+document.toml` with the `[document]` block: `type` (= the profile
  name), `title`, `subtitle`, `authors`, `keywords`.
- Delete the root `doctor.toml` and the old `.doctor-build/`.

**Two path rules, easy to get wrong:**

- **`extends` shifts down one level.** It is resolved relative to the config
  file, which is now inside `.doctor/`. A root `extends = "../../doctor.toml"`
  becomes `extends = "../../../doctor.toml"`.
- **`references_file` does *not* shift.** It resolves against the project root,
  not the profile's folder. Leave a path like `"../references-gg.toml"`
  unchanged (including symlinked or vault-external bibliographies).

Compile and confirm the PDF matches the pre-migration output, and that the title
comes from `+document.toml`.

### Step 2 — Assets: `_figures/` → `+figures/`

Figures used by the compiled document should be auxiliary (preserved in
versions), so rename their directories from `_figures/` to `+figures/`. These
directories may sit at the project root or be co-located with chapters/parts.

Then **update the embeds**: any `src="_figures/…"` in the content must become
`src="+figures/…"`. Find them with a grep over the *content* directories (not the
`_`-prefixed reference material), rename the dirs, and rewrite the `src`s.

Leave a root `_figures/` alone if it only serves `_`-prefixed reference content
(e.g. an old `_holding/`) — that content is not compiled or versioned, so its
figures need not be preserved.

Recompile and eyeball the figures.

### Step 3 — Sub-documents: `_audio/`, `_papers/` → `+audio/`, `+papers/`

Rename these to `+`. Then decide how each sub-document is configured. A
sub-document that keeps only a bare `doctor.toml` will **not** compile correctly,
because walk-up discovery finds the *parent's* `.doctor/` and uses the parent's
profile and title.

**Make each sub-document self-contained:** give it its own `.doctor/<profile>.toml`
and its own `+document.toml`. Walk-up then stops at the sub-document.

- The sub-document's `references_file` resolves against *its own* root, so a path
  like `"../../../references-egg.toml"` is unchanged by the move into `.doctor/`.
- Its `extends`, if any, shifts down one level (as in Step 1).
- Delete the sub-document's old `doctor.toml` and `.doctor-build/`.

Compile one sub-document and confirm it self-titles correctly.

### Step 4 — Leave scratch as scratch

Do **not** rename reference or archive material. A v1 copy kept for reference
while rewriting, old drafts, working notes, and hand-rolled version archives
should stay `_`-prefixed:

- `_holding/`, `_archive/`, `_notes/`, `_rewrite-notes.md`, `_versions/` — keep
  as `_`. They are correctly invisible to the compile and excluded from
  snapshots, which is exactly what reference cruft should be.

Going forward, `doc … --save-version` writes real snapshots to
`.doctor/versions/`; the old `_versions/` can stay as history. A snapshot is
self-contained: it also captures the resolved bibliography (following symlinks)
into `.doctor/_versioned-refs/`, so `doc … --build-version v1` reproduces the
document's citations even when the bibliography lives outside the project root
or the shared references store later changes. `.DS_Store` and other dot-files
are never captured.

### Step 5 — Cleanup

- Remove stray build artifacts: `..pdf`, `.DS_Store`, leftover `.doctor-build/`
  directories, and any `.doctor/build/` created by test compiles.
- Keep genuine deliverables (e.g. an audiobook's compiled `.pdf` beside its
  source), your call.

## Verification checklist

For each migrated project, from a doctor repo checkout:

1. **No scratch leaks into the document:**

   ```bash
   uv run doc "<project>" --list-files | grep -cE '_holding|_archive|_notes|_audio'   # expect 0
   ```

2. **Profiles resolve as expected:**

   ```bash
   uv run doc "<project>" --list-configs        # should list .doctor/<profile>.toml + +document.toml
   uv run doc "<project>" --as <other-profile> --list-configs
   ```

3. **It compiles, with the right title and figures:**

   ```bash
   uv run doc "<project>" --format pdf --output /tmp/check.pdf
   ```

   Confirm the title page shows the `+document.toml` title and that embedded
   figures render.

4. **Each sub-document compiles on its own** with its own title:

   ```bash
   uv run doc "<project>/+audio/<deck>" --format pdf --output /tmp/deck.pdf
   ```

## Reference: path-shift rules at a glance

| Path | When the config moves into `.doctor/` |
| --- | --- |
| `extends` | shift **down one level** (`../../x` → `../../../x`) — relative to the config file |
| `references_file` | **unchanged** — relative to the project root |

| Prefix | Compiled? | In versions? |
| --- | --- | --- |
| (none) | yes | yes |
| `+name` | no (auxiliary/asset/sub-doc) | yes |
| `_name` | no | no |
| `README.md`, dot-paths | no | (infrastructure) |
