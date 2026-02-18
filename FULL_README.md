# Hubitat Tile Mover (hubitat_tile_mover)

A command-line utility that edits Hubitat Dashboard layout JSON by **moving, copying, merging, inserting, deleting, clearing, cropping, pruning, trimming, sorting**, and **CSS rule maintenance**, while preserving all other JSON content unchanged (unless you explicitly scrub/cleanup CSS).

Supports **clipboard / file / Hubitat import**, and **clipboard / file / terminal / Hubitat output**.

---

## Core Concepts
 
### Input JSON shapes (three “levels”)

The tool accepts three input shapes. The input “level” determines what can be output.

1) **Full layout JSON**
   A full object containing `"tiles"` plus other fields (e.g., `"customCSS"`):

```json
{ "...": "...", "tiles": [ { ... }, ... ], "...": "..." }
```

2) **Minimal container**
   An object containing only `"tiles"`:

```json
{ "tiles": [ { ... }, ... ] }
```

3) **Bare tiles list**
   The tiles list only:

```json
[ { ... }, ... ]
```

### Output format constraints

- Output can be **equal to or “lower” than** the detected input level.
- Output can **not exceed** the input level.
- When `--output:hub` is used, output must be **full**, so input must be **full**.

### Tile fields the tool edits

Operations modify only:

- `row`
- `col`

All other tile fields are preserved.

Span calculations:

- A tile occupies:
  - rows: `row .. row + rowSpan - 1` (default rowSpan=1)
  - cols: `col .. col + colSpan - 1` (default colSpan=1)

### Sorting behavior

- **No sorting occurs unless `--sort:<spec>` is provided.**
- Default sort priority when sorting is requested is **index, row, col** (`irc`).
- If `--sort` is omitted, tiles preserve **original input order**.

---

## Quick Examples

Sort tiles by ID then row then col:

```bash
python hubitat_tile_mover.py --import:file layout.json --sort:irc --output:file sorted.json
```

Insert 2 columns at col 15 (only affecting rows 4–32):

```bash
python hubitat_tile_mover.py --insert_cols 2 15 --row_range 4 32
```

Move columns 1–14 to start at 85 and save back to hub:

```bash
python hubitat_tile_mover.py --import:hub --url "<dashboard-url>" --move_cols 1 14 85 --output:hub
```

Copy a rectangular range to a new location:

```bash
python hubitat_tile_mover.py --copy_range 1 1 20 20 40 40
```

Crop to a range (delete everything outside), show maps, force, cleanup css:

```bash
python hubitat_tile_mover.py --crop_to_range 1 1 85 85 --show_map --force --cleanup_css
```

Remove orphan CSS rules only (no tile edits):

```bash
python hubitat_tile_mover.py --scrub_css --force
```

Undo last run (restore last input to last outputs unless overridden):

```bash
python hubitat_tile_mover.py --undo_last
```

---

## Command Line Reference (Detailed)

### Help

- `-h`, `--help` — Short help
- `--help_full` — Full detailed help

---

## Import (input source)

Exactly one import method is used. If not specified, clipboard is the default.

- `--import:clipboard` — Read JSON text from clipboard.
- `--import:file <filename>` — Read JSON text from file.
- `--import:hub` — Fetch the full layout JSON from Hubitat using `--url`.

### Hub import required option

- `--url "<dashboard-url>"`

Dashboard URL format (typical):

```
http://<hub-ip>/apps/api/<appId>/dashboard/<dashId>?access_token=<token>&local=true
```

Hub import flow:

1) GET dashboard URL
2) Extract `javascriptRequestToken`
3) Build layout URL (port `:8080`, insert `/layout`, add `requestToken`)
4) GET layout JSON

---

## Output destinations

Destinations are repeatable. If none specified, clipboard is the default.

- `--output:terminal` — Print output to terminal.
- `--output:clipboard` — Write to clipboard.
- `--output:file <filename>` — Write to file.
- `--output:hub` — POST full layout JSON back to Hubitat using `--url`.

Compatibility:

- Some builds also accept `--output_to:<dest>` as a silent alias.

### Hub output safeguards

`--output:hub` is allowed when:

- output JSON is **full**
- `--url` is provided
- requestToken validation succeeds

If input is not full or output is down-leveled, hub output is blocked.

---

## Output format (level)

Allows down-level output (full→minimal/bare). If omitted, output defaults to match input.

- `--output_format:full`
- `--output_format:minimal`
- `--output_format:bare`

Compatibility:

- `--output_format:container` ≈ `minimal`
- `--output_format:list` ≈ `bare`

---

## Actions (operations)

### Action classes

1) **Primary edit operation** (at most one per run):
   insert, move, copy, merge, delete, clear, crop, prune
2) **Add-on actions** (can run alone or after a primary operation):

- maps: `--show_map`
- trim: `--trim` / `--trim:top` / `--trim:left`
- sort: `--sort:<spec>`
- scrub CSS: `--scrub_css`

`--undo_last` is standalone and supersedes all other actions.

---

## Insert

- `--insert_rows COUNT AT_ROW`
  Increase `row` by COUNT for tiles at/after AT_ROW, and optionally straddlers.
  
  Modifiers:
  
  - `--include_overlap`
  - `--col_range <start_col> <end_col>` (insert_rows only)
- `--insert_cols COUNT AT_COL`
  Increase `col` by COUNT for tiles at/after AT_COL, and optionally straddlers.
  
  Modifiers:
  
  - `--include_overlap`
  - `--row_range <start_row> <end_row>` (insert_cols only)

Range filters:

- Without `--include_overlap`: match by starting row/col.
- With `--include_overlap`: match by span overlap.

---

## Move

- `--move_cols START_COL END_COL DEST_START_COL`
- `--move_rows START_ROW END_ROW DEST_START_ROW`
- `--move_range SRC_TOP_ROW SRC_LEFT_COL SRC_BOTTOM_ROW SRC_RIGHT_COL DEST_TOP_ROW DEST_LEFT_COL`

Modifiers:

- `--include_overlap`

Conflict policy (move/copy/merge):

- `--allow_overlap` — proceed even if destination overlaps exist.
- `--skip_overlap` — skip tiles that would conflict.
- default: if any conflicts exist, abort before moving anything.

Conflict detection is evaluated **once before** moving/copying, against **stationary destination tiles only**.
Overlaps among the moving/copying tiles themselves are allowed.

---

## Copy

Same as Move, but originals remain and copies are appended with new IDs.

- `--copy_cols START_COL END_COL DEST_START_COL`
- `--copy_rows START_ROW END_ROW DEST_START_ROW`
- `--copy_range SRC_TOP_ROW SRC_LEFT_COL SRC_BOTTOM_ROW SRC_RIGHT_COL DEST_TOP_ROW DEST_LEFT_COL`

ID allocation for new tiles:

```
max(max_tile_id_in_tiles, max_tile_id_referenced_in_customCSS) + 1
```

Increment for each new tile.

---

## Merge

Merge copies tiles from another layout into this layout.

Source selection:

- `--merge_source <filename>` — load source JSON from file
- `--merge_url "<dashboard-url>"` — fetch source JSON from hub

Then one of:

- `--merge_cols ...`
- `--merge_rows ...`
- `--merge_range ...`

Same overlap/conflict and ID rules as Copy.

CSS behavior:

- By default, tile-specific CSS is duplicated/remapped for new IDs.
- `--ignore_css` disables creating/copying CSS for new IDs.

---

## Delete (remove + shift)

- `--delete_rows START_ROW END_ROW`
- `--delete_cols START_COL END_COL`

Deletes selected tiles then shifts remaining tiles to close the gap.

Modifiers:

- `--include_overlap`
- `--force` (skip confirmation)
- `--cleanup_css` (remove tile-specific CSS for deleted tiles)

---

## Clear (remove without shifting)

- `--clear_rows START_ROW END_ROW`
- `--clear_cols START_COL END_COL`
- `--clear_range TOP_ROW LEFT_COL BOTTOM_ROW RIGHT_COL`

Modifiers:

- `--include_overlap`
- `--force`
- `--cleanup_css`

---

## Crop (keep only tiles inside)

- `--crop_to_rows START_ROW END_ROW`
- `--crop_to_cols START_COL END_COL`
- `--crop_to_range TOP_ROW LEFT_COL BOTTOM_ROW RIGHT_COL`

Rules:

- range must contain at least one tile
- at least one tile must remain
- confirm unless `--force`

Modifiers:

- `--include_overlap`
- `--force`
- `--cleanup_css`

---

## Prune (keep only matching tiles)

- `--prune_except_ids <comma-separated tile ids>`
- `--prune_except_devices <comma-separated device ids>`

Rules:

- at least one tile must match
- at least one tile must remain
- confirm unless `--force`

Modifiers:

- `--force`
- `--cleanup_css`

---

## Trim

- `--trim` (defaults to top+left)
- `--trim:top`
- `--trim:left`

Applied after primary operation and before sort/scrub_css.

---

## Sort

- `--sort:<spec>`

Keys:

- `i` = id
- `r` = row
- `c` = col

Rules:

- missing keys appended to make sort total
- default sort when sorting requested: `irc`
- some builds support per-key descending via `-` prefix (e.g., `--sort:i-r-c`)

If `--sort` omitted, original order is preserved.

---

## CSS Maintenance

- `--cleanup_css`
  Remove tile-specific CSS rules when tiles are deleted/cleared/cropped/pruned.
- `--ignore_css`
  When copying/merging tiles to new IDs, do not create/copy CSS for the new IDs.

Compatibility note:
Older builds used `--create_css`. New behavior is reversed:

- default: create/copy CSS
- `--ignore_css`: disable it
- `--scrub_css`
  Remove orphan CSS rules referencing missing tile IDs. Prompts unless `--force`.
  Performed at end of run.

If `--scrub_css` is not used but orphans exist, the program may warn with count/sample IDs.

---

## Maps (terminal preview)

- `--show_map`
  Show a BEFORE map (and an OUTCOME map when an operation is performed).
  Can be used alone to show BEFORE map only.

Map semantics (intent):

- empty cells: dot
- unaffected tiles: gray
- changed tiles: green
- overlap conflict: red
- if allow_overlap: overlap shown as yellow

A focus option may exist in some builds to show full bounds vs conflict bounds.

---

## Safety / Undo

- `--force`
  Suppress confirmation prompts for any tile/css deletions.
- `--confirm_keep`
  After writing output, prompt keep/undo; if undo, restore backup to outputs.
- `--lock_backup`
  Create backup only if one does not already exist.
- `--undo_last`
  Standalone restore: load previous run’s input JSON backup and output it to the previous run’s outputs unless overridden.

---

## Diagnostics

- `--quiet` — suppress end-of-run summary line (errors still shown)
- `--verbose` — planned actions + concise results
- `--debug` — per-tile action logs + deep details

---

## Program Flow (high-level)

1) Parse CLI arguments
2) If `--undo_last`: restore + exit
3) Import JSON from clipboard/file/hub
4) Detect input level (full/minimal/bare)
5) Validate structure (tiles may be empty for some operations like merge/scrub_css)
6) Save last-run backup (unless locked)
7) Optional BEFORE map
8) Run primary operation (if any) with one-time conflict scan + prompts
9) Apply trim (if requested)
10) Apply sort (if requested)
11) Apply scrub_css (if requested) + prompt
12) Optional OUTCOME map
13) Write outputs (clipboard/file/terminal/hub)
14) If confirm_keep: prompt; if no -> restore backup to outputs
15) Print status summary (unless quiet)

---

# Best-effort project changelog (from chat history)

This section is reconstructed from conversation history and filenames. It is a best-effort summary and may omit minor refactors or interim debug-only edits.

## Early: tile_sorter (single-file script)

- Initial requirements: import from clipboard or file; modify only `tiles[*].row` and `tiles[*].col`; rebuild JSON preserving everything else.
- Added validation: ensure `tiles` exists and has at least one tile with `row` and `col`; accept inputs that are just `{ "tiles": [...] }` or bare list.
- Switched to `argparse`.
- Added sorting:
  - `--sort` + `--order` where order is subset of `i,r,c`
  - default order evolved (ultimately replaced with `irc` when sorting requested)
  - allowed missing keys to be appended to default priority order.
- Added movement: insert rows/cols with overlap logic and optional range filters:
  - `--insert_rows` / `--insert_cols`
  - `--include_overlap` (span-aware selection)
  - range filters: `--col_range` (insert_rows), `--row_range` (insert_cols)
- Added trimming:
  - `--trim_left`, `--trim_top`, `--trim` (later consolidated to `--trim[:top|left]`)
- Introduced output shape controls:
  - `full/container/list` (later renamed to `full/minimal/bare`)
- Added output destinations:
  - terminal vs clipboard vs file (eventually multi-destination)
- Fixed formatting controls around `--indent` / minify issues and JSON pretty printing.

## CLI refactor (tile_sorter_refactor v8–v12 series)

- Major CLI structure changes:
  - `--import:clipboard` default / `--import:file <filename>` (single import)
  - repeatable `--output_to:terminal|clipboard|file <filename>`
  - single `--output_format:full|container|list`
- Added move operations:
  - `--move_cols START END DEST`
  - `--move_rows START END DEST`
  - `--move_range SRC_RECT DEST_TOPLEFT`
- Added conflict policy:
  - pre-scan destination conflicts against stationary tiles
  - `--allow_overlap` and `--skip_overlap` or abort
  - clarified that moving tiles may overlap each other intentionally
- Added delete/clear:
  - `--delete_rows/--delete_cols` (delete and shift)
  - `--clear_rows/--clear_cols/--clear_range` (delete no shift)
  - `--force` to skip prompts
- Renames:
  - `output_shape` → `output_format`
  - `insert_columns/move_columns` → `insert_cols/move_cols`
- Split into modules (multi-file package) due to length.

## Merge/copy and CSS handling (tile_sorter_refactor v8–v12 and beyond)

- Added `--merge_source` with merge operations mirroring move:
  - `--merge_cols/--merge_rows/--merge_range`
  - merge copies tiles from external source into destination
- Added `--copy_cols/--copy_rows/--copy_range`:
  - copy from input JSON into itself at new location
- Added ID conflict handling for merge/copy:
  - generate new IDs when conflicts exist
  - later strengthened to avoid collisions with orphan `customCSS` IDs
- Added CSS maintenance:
  - `--cleanup_css` remove tile-specific CSS rules when tiles removed
  - `--create_css` added rules for new IDs when copying/merging (later inverted)
- Fixed merge crash (`id_map` undefined) and ensured CSS post-processing occurs inside main.

## Rename and feature expansion (hubitat_tile_mover beta series)

- Renamed project to **hubitat_tile_mover**.
- Enforced output format limits based on import format.
- Renamed output formats to **full/minimal/bare** (kept legacy names for compatibility).
- Ensured no sorting unless explicitly requested.
- Added crop and prune:
  - `--crop_to_rows/cols/range` (delete everything outside)
  - `--prune_except_ids` and `--prune_except_devices`
  - ensured at least one tile remains; crop range must contain at least one tile
- Changed CSS copy behavior:
  - default became “copy/create CSS rules”
  - added `--ignore_css` to disable (replacing `--create_css`)
- Added `--scrub_css`:
  - detect/remove orphan CSS rules referencing missing tiles
  - prompt unless `--force`
  - warn if orphans found when not scrubbing
- Improved help structure:
  - grouped arguments
  - long help intended to be generated by program
  - made user-facing errors more conversational unless verbose/debug.

## Hub I/O integration (RC series)

- Added Hubitat import/output:
  - `--import:hub`
  - `--output:hub` (and `--output_to:hub` compatibility)
  - `--url` required for hub actions
  - requestToken extraction from dashboard HTML (`javascriptRequestToken`)
  - build layout URL on port 8080 with `/layout` and `requestToken`
  - GET for import; POST for save
- Added `--merge_url` for merge source from another dashboard.
- Added safety:
  - never POST to hub if errors
  - backup original JSON before modifications
  - `--confirm_keep` prompt to keep/undo after output
  - `--undo_last` restore prior input to prior output destinations
  - `--lock_backup` reuse existing backup (do not overwrite)
- Multiple RC bugfix iterations:
  - argparse missing switches in `-h` / help_full
  - NameErrors due to moved/indented blocks
  - ensure undo runs standalone and exits early
  - ensure hub output allowed when importing from file/clipboard (requires `--url` validation)
  - ensure full-format requirement applies to hub output, not hub import.

## Maps and visualization (late RC series)

- Added `--show_map` to display:
  - BEFORE map (alone or with operation)
  - OUTCOME map when operation occurs
- Map intent:
  - line art / solid tiles
  - unchanged tiles gray, changed green
  - conflicts red; if `--allow_overlap`, overlaps yellow
  - for delete/clear/crop/prune, highlight “to be removed” tiles (orange) before confirm prompt
- Added focus behavior (full bounds vs conflict bounds), iterated due to bugs and CLI mismatch.

## Recent stabilization (RC55–RC62)

- Continued fixes for crop/map plumbing:
  - missing args passed, missing imports, mismatched function signatures
- Addressed end-of-run crashes:
  - `did_undo` referenced before assignment
  - confirm_keep blocks at module scope causing NameError
- Added `__main__.py` entrypoint for `python -m hubitat_tile_mover` style execution (requested).
- Continued aligning help output with actual switches and ensuring legacy aliases behave.

