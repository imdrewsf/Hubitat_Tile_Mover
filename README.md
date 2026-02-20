# Hubitat Tile Mover

A command-line utility to make mass changes to tile layout in Hubitat Dashboard layout JSON:

#### Features:

* **MOVE** tiles: columns, rows, range
* **COPY** tiles: columns, rows, range
* **MERGE** tiles (copy from another dashboard): columns, rows, range
* **INSERT** full or partial columns, rows (push tiles over/down at column/row)
* **DELETE** full or partial columns, rows (remove tiles and pull tiles left or up)
* **CLEAR** tiles (remove but keep layout): columns rows, range
* **CROP** layout (remove all tiles not in): columns, rows, range
* **PRUNE** layout (remove all tiles except listed): tile id's, device ids
* **TRIM** layout (remove blank rows, cols): top, left
  <br>
* **Preserve Custom CSS**: CSS rules can be optionally duplicated when copying/merging tiles and optionally removed when tiles are deleted/cleared.
  <br>
* **Import/Load** dashboard layout JSON from: clipboard (default) • files • directly from Hubitat dashboard
  <br>
* **Output/Save** dashboard layout JSON to: clipboard (default) • files • directly to Hubitat dashboard • terminal
  <br>
* **Visual Maps**: Before and after views, easily see layout conflicts.
  ![multimap](https://github.com/user-attachments/assets/547d6dc4-8ab6-4d50-817c-17b7efb767cb)

---

## Quick Examples

Insert 2 columns at col 15 (only in rows 4–32):

```bash
python hubitat_tile_mover.py --insert_cols 2 15 --row_range 4 32
```

Move columns 1–14 to start at 85 and save back to hub.  Show the layout before and after maps:

```bash
python hubitat_tile_mover.py --import:hub --url "<dashboard_local_url>" --move_cols 1 14 85 --output:hub --show_map
```

Copy tiles in the rectangular range 1,1 to 2,20 to a new location at 40,40:

```bash
python hubitat_tile_mover.py --copy_range 1 1 20 20 40 40
```

Crop to a range (delete everything outside), show maps, force, cleanup css, save to a file:

```bash
python hubitat_tile_mover.py --crop_to_range 1 1 85 85 --show_map --force --cleanup_css --output:file "<filename.json>"
```

Remove orphan CSS rules only (no tile edits) without confirmation prompt:

```bash
python hubitat_tile_mover.py --scrub_css --force
```

Undo last run (restore last input to last outputs unless overridden):

```bash
python hubitat_tile_mover.py --undo_last
```

Insert 5 columns in a dashboard at column 10, then merge (copy) tiles from another dashboard into the inserted space.

```bash
python hubitat_tile_mover.py --import:hub --url "<dashboard_local_url>" --output:clipboard --insert_cols 5 10

python hubitat_tile_mover.py --import:clipboard --url "<dashboard_local_url>" --output:hub --merge_url: "<other_dashboard_url>" --merge_cols 15 20 10
```

---

## Command Line Reference

### Help

- `-h`, `--help` — Short help
- `--help_full` — Full detailed help

---

## Import (input source)

Exactly one import method is used. If not specified, clipboard is the default.

- `--import:clipboard` — Read JSON text from clipboard.
- `--import:file <filename>` — Read JSON text from file.
- `--import:hub` — Fetch the full layout JSON from Hubitat using`--url`.

### Hub import required option

- `--url "<dashboard_local_url>"`

Dashboard URL format (typical):

```
http://<hub-ip>/apps/api/<appId>/dashboard/<dashId>?access_token=<token>&local=true
```

---

## Output destinations

Destinations are repeatable. If none specified, clipboard is the default.

- `--output:terminal` — Print output to terminal.
- `--output:clipboard` — Write to clipboard.
- `--output:file <filename>` — Write to file.
- `--output:hub` — POST full layout JSON back to Hubitat using`--url`.

### Hub output safeguards

`--output:hub` is allowed when:

- import and output JSON is **full**
- `--url` is provided
- requestToken validation succeeds

If input is not full or output is down-leveled, hub output is blocked.

---

## Output format (level)

Allows down-level output (full→minimal/bare). If omitted, output defaults to match input.

- `--output_format:full`
- `--output_format:minimal`
- `--output_format:bare`

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

- Actions:
  
  - `--insert_rows <count> <at_row>`
    Increase `row` by COUNT for tiles at/after AT_ROW, and optionally straddlers.
    
    Selection Modifiers:
    
    - `--include_overlap`
    - `--col_range <start_col> <end_col>` (insert_rows only)
      <br>
  - `--insert_cols <count> <at_col>`
    Increase `col` by COUNT for tiles at/after AT_COL, and optionally straddlers.
    
    Selection Modifiers:
    
    - `--include_overlap`
    - `--row_range <start_row> <end row>` (insert_cols only)
      <br>
- Notes
  
  - `--include_overlap` includes tiles which begin (top-left corner) outside of the range, but extend into it.

---

## Move

Moves tiles to a new location.  

- Actions:
  
  - `--move_cols <start_col> <end_col> <dest_start_col>`
  - `--move_rows <start_row> <end_row> <dest_start_row>`
  - `--move_range <src_top_row> <src_left_col> <src_bottom_row> <src_right_col> <dest_top_row> <dest_left_col>`
   <br>
- Selection Modifiers:
  
  - `--include_overlap`
    <br>
- Conflict policy (move/copy/merge):
  
  - `--allow_overlap` — ignore conflicts and allow moved tiles to overlap existing tiles at the destination.
  - `--skip_overlap` — skip tiles that would conflict, move all others.
    <br>
- Notes:
  
  - Conflict detection is evaluated **once, \*before\*** moving/copying, against **existing destination tiles only**.  Any tiles that are being copied/moved can be overlapped and will not be considered in conflict.
  - Default behavior: if any conflicts exist, abort before moving anything.


---

## Copy

Same as Move, but originals remain.  Copies are created with new IDs. Existing tile specific CSS rules in customCSS can be optionally copied with the new IDs

- Actions:
  
  - `--copy_cols <start_col> <end_col> <dest_start_col>`
  - `--copy_rows <start_row> <end_row> <dest_start_row>`
  - `--copy_range <src_top_row> <src_left_col> <src_bottom_row> <src_right_col> <dest_top_row> <dest_left_col>`
    <br>
- Selection Modifiers:
  
  - `--include_overlap`
- Conflict policy (move/copy/merge):
  
  - `--allow_overlap` — ignore conflicts and allow moved tiles to overlap existing tiles at the destination.
  - `--skip_overlap` — skip tiles that would conflict, move all others.
    <br>
- Custom Tile CSS Rule Handling:
  
  - `--ignore_css` — disables creating/copying CSS for new IDs.
    <br>
- Notes:
  
  - ID allocation for new tiles:  New IDs are created sequentially beginning starting with 1 + max(highest existing tile ID, highest referenced tile ID in customCSS).  This prevents any orphaned CSS rules from being applied to new tiles.
  - By default, customCSS is checked for any tile specific CSS rules for copied tiles.  Any rules found are duplicated for the new tile id
  - Conflict detection is evaluated **once, \*before\*** moving/copying, against **existing destination tiles only**.  Any tiles that are being copied/moved can be overlapped and will not be considered in conflict.
  - Default behavior: if any conflicts exist, abort before moving anything.

---

## Merge

Copy tiles from another dashboard layout into this layout.

- Actions:
  
  - `--merge_cols <start_col> <end_col> <dest_start_col>`
  - `--merge_rows <start_row> <end_row> <dest_start_row>`
  - `--merge_range <src_top_row> <src_left_col> <src_bottom_row> <src_right_col> <dest_top_row> <dest_left_col>`
- Required: source selection:
  
  - `--merge_source <filename>` — load source JSON from file
  - `--merge_url "<other_dashboard_local_url>"` — fetch source JSON from hub

- Selection Modifiers:
  
  - `--include_overlap`
- Conflict policy (move/copy/merge):
  
  - `--allow_overlap` — ignore conflicts and allow moved tiles to overlap existing tiles at the destination.
  - `--skip_overlap` — skip tiles that would conflict, move all others.
    <br>
- Custom Tile CSS Rule Handling:
  
  - `--ignore_css` — disables creating/copying CSS for new IDs.
    <br>
- Notes:
    
  - ID allocation for new tiles:  New IDs are created sequentially beginning starting with 1 + max(highest existing tile ID, highest referenced tile ID in customCSS).  This prevents any orphaned CSS rules from being applied to new tiles.
  - By default, customCSS is checked for any tile specific CSS rules for copied tiles.  Any rules found are duplicated for the new tile id
  - Conflict detection is evaluated **once, \*before\*** moving/copying, against **existing destination tiles only**.  Any tiles that are being copied/moved can be overlapped and will not be considered in conflict.
  - Default behavior: if any conflicts exist, abort before moving anything.

---

## Delete (remove + shift)

- `--delete_rows <start_row> <end_row>`
- `--delete_cols <start_col> <end_col>`

Deletes selected tiles then shifts remaining tiles to close the gap.

Modifiers:

- `--include_overlap`
- `--force` (skip confirmation)
- `--cleanup_css` (remove tile-specific CSS for deleted tiles)

---

## Clear (remove without shifting)

- `--clear_rows <start_row> <end_row>`
- `--clear_cols <start_col> <end_col>`
- `--clear_range <top_row> <left_col> <bottom_row> <right_col>`

Modifiers:

- `--include_overlap`
- `--force`
- `--cleanup_css`

---

## Crop (keep only tiles inside)

- `--crop_to_rows <start_row> <end_row>`
- `--crop_to_cols <start_col> <end_col>`
- `--crop_to_range <top_row> <left_col> <bottom_row> <right_col>`

Rules:

- range must contain at least one tile
- at least one tile must remain
- confirm unless`--force`

Modifiers:

- `--include_overlap`
- `--force`
- `--cleanup_css`

---

## Prune (keep only matching listed tile ids or devices)

- `--prune_except_ids "<comma-separated tile ids>"`
- `--prune_except_devices "<comma-separated device ids>"`

Rules:

- at least one tile must match
- at least one tile must remain
- confirm unless`--force`

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

## Sort (Tile order in JSON Only)

- `--sort:<spec>`

Keys:

- `i` = id
- `r` = row
- `c` = col

Rules:

- missing keys appended to make sort total
- default sort when sorting requested:`irc`(index, row, col)
- No effect on the actual tile layout.
- CSS rules are not sorted

If `--sort` omitted, original order is preserved.

---

## CSS Maintenance

- `--cleanup_css`
  Remove tile-specific CSS rules when tiles are deleted/cleared/cropped/pruned.
- `--ignore_css`
  When copying/merging tiles to new IDs, do not create/copy CSS for the new IDs.
- default: create/copy CSS
- `--scrub_css`
  Remove orphan CSS rules referencing missing tile IDs. Prompts unless`--force`.
  Performed at end of run.

Note: Program will warn if orphans are found after an action completes.

---

## Maps (terminal preview)

- `--show_map`
  Show a BEFORE map (and an OUTCOME map when an operation is performed).
- `--map_focus:full`
  Always show full layout (scaled)
  `--map_focus:conflict`
  Show zoomed in view of tiles layout conflicts, otherwise show default full view.
  `--map_focus:no_scale`
  Don't scale layout maps.  A character is rendered for every row / column.

Map semantics (intent):

- empty cells: dot
- unaffected tiles: gray
- changed tiles: green
- overlap conflict: red
- if allow_overlap: overlap shown as yellow

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

<br>

# Notes:

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

Hub import flow:

1) GET dashboard URL
2) Extract `javascriptRequestToken`
3) Build layout URL (port `:8080`, insert `/layout`, add `requestToken`)
4) GET layout JSON
   <br>---

Copyright 2026 Andrew Peck

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

```
http://www.apache.org/licenses/LICENSE-2.0
```

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

