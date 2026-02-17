HUBITAT TILE MOVER (hubitat_tile_mover)

A command-line utility that edits Hubitat Dashboard layout JSON by moving, copying,
merging, inserting, deleting, clearing, cropping, pruning, trimming, sorting, and
CSS rule maintenance — while preserving all non-tile JSON content unchanged
(unless you explicitly scrub/cleanup CSS).

Supports clipboard/file/Hubitat import and clipboard/file/terminal/Hubitat output.


CORE CONCEPTS
=============

INPUT JSON SHAPES (THREE “LEVELS”)
1) Full layout JSON: a full object containing "tiles" plus other fields
2) Minimal container: { "tiles": [ ... ] }
3) Bare tiles list: [ ... ]

OUTPUT FORMAT CONSTRAINTS
- Output can be equal to or “lower” than the detected input level.
- Output cannot exceed the input level.
- --output:hub requires FULL output, therefore input must be FULL.

WHAT IS MODIFIED
Only tile fields row and col are changed. All other fields are preserved.

SPAN / OVERLAP
Tile rectangle:
- rows: row .. row + rowSpan - 1 (default 1)
- cols: col .. col + colSpan - 1 (default 1)

SORTING
- No sorting occurs unless --sort:<spec> is provided.
- Default sort priority when sorting requested: index,row,col (irc).
- If --sort omitted, tiles remain in original input order.


QUICK EXAMPLES
==============
Sort:
  python hubitat_tile_mover.py --import:file layout.json --sort:irc --output:file sorted.json

Insert cols:
  python hubitat_tile_mover.py --insert_cols 2 15 --row_range 4 32

Move to hub:
  python hubitat_tile_mover.py --import:hub --url "<dashboard-url>" --move_cols 1 14 85 --output:hub

Copy range:
  python hubitat_tile_mover.py --copy_range 1 1 20 20 40 40

Crop + maps:
  python hubitat_tile_mover.py --crop_to_range 1 1 85 85 --show_map --force --cleanup_css

Scrub orphans:
  python hubitat_tile_mover.py --scrub_css --force

Undo:
  python hubitat_tile_mover.py --undo_last


HELP
====
-h, --help       Short help
--help_full      Long detailed help


IMPORT (INPUT)
==============
Exactly one import method is used. Default is clipboard.

--import:clipboard
--import:file <filename>
--import:hub

Hub import requires:
--url "<dashboard-url>"
Typical:
  http://<hub-ip>/apps/api/<appId>/dashboard/<dashId>?access_token=<token>&local=true

Hub import flow:
1) GET dashboard URL
2) Extract javascriptRequestToken
3) Build /layout URL (port 8080, insert /layout, add requestToken)
4) GET layout JSON


OUTPUT DESTINATIONS
===================
Repeatable. Default is clipboard.

--output:terminal
--output:clipboard
--output:file <filename>
--output:hub

Compatibility: --output_to:<dest> may be accepted as an alias.

Hub output safeguards:
- must be FULL output
- --url required
- requestToken validation performed


OUTPUT FORMAT (LEVEL)
=====================
Allows down-level output. If omitted, defaults to match input.

--output_format:full
--output_format:minimal
--output_format:bare

Compatibility:
--output_format:container == minimal
--output_format:list == bare


ACTIONS / OPERATIONS
====================
Two action classes:

1) Primary edit operation (at most one per run):
   insert, move, copy, merge, delete, clear, crop, prune

2) Add-on actions (can run alone or after primary op):
   show_map, trim, sort, scrub_css

--undo_last supersedes everything (standalone restore).


INSERT
======
--insert_rows COUNT AT_ROW
  Modifiers:
  --include_overlap
  --col_range <start_col> <end_col>

--insert_cols COUNT AT_COL
  Modifiers:
  --include_overlap
  --row_range <start_row> <end_row>

Range filters:
- without --include_overlap: match by starting row/col
- with --include_overlap: match by span overlap


MOVE
====
--move_cols START_COL END_COL DEST_START_COL
--move_rows START_ROW END_ROW DEST_START_ROW
--move_range SRC_TOP_ROW SRC_LEFT_COL SRC_BOTTOM_ROW SRC_RIGHT_COL DEST_TOP_ROW DEST_LEFT_COL

Modifiers:
--include_overlap

Conflict policy (move/copy/merge):
--allow_overlap
--skip_overlap
default: conflicts abort before moving anything

Conflicts are scanned ONCE against stationary destination tiles only.


COPY
====
Like move, but originals remain and copies are appended with new IDs.

--copy_cols ...
--copy_rows ...
--copy_range ...

ID allocation:
  max(max_tile_id_in_tiles, max_tile_id_referenced_in_customCSS) + 1


MERGE
=====
Copy tiles from another source.

Source:
--merge_source <filename>
--merge_url "<dashboard-url>"

Then:
--merge_cols ...
--merge_rows ...
--merge_range ...

Same overlap/conflict and ID rules as copy.

CSS:
Default copies/remaps CSS rules for new IDs; --ignore_css disables that.


DELETE (REMOVE + SHIFT)
=======================
--delete_rows START_ROW END_ROW
--delete_cols START_COL END_COL

Modifiers:
--include_overlap
--force
--cleanup_css


CLEAR (REMOVE, NO SHIFT)
========================
--clear_rows START_ROW END_ROW
--clear_cols START_COL END_COL
--clear_range TOP_ROW LEFT_COL BOTTOM_ROW RIGHT_COL

Modifiers:
--include_overlap
--force
--cleanup_css


CROP (KEEP ONLY RANGE)
======================
--crop_to_rows START_ROW END_ROW
--crop_to_cols START_COL END_COL
--crop_to_range TOP_ROW LEFT_COL BOTTOM_ROW RIGHT_COL

Rules:
- range must contain at least one tile
- at least one tile must remain
- confirm unless --force

Modifiers:
--include_overlap
--force
--cleanup_css


PRUNE
=====
--prune_except_ids <comma-separated tile ids>
--prune_except_devices <comma-separated device ids>

Rules:
- at least one tile must match
- at least one tile must remain
- confirm unless --force

Modifiers:
--force
--cleanup_css


TRIM
====
--trim (default top+left)
--trim:top
--trim:left

Applied after primary op and before sort/scrub_css.


SORT
====
--sort:<spec>
Keys: i=id, r=row, c=col
Default when requested: irc
If --sort omitted, original order preserved.


CSS MAINTENANCE
===============
--cleanup_css  remove tile-specific CSS when tiles removed
--ignore_css   do not create/copy CSS for new IDs when copying/merging
--scrub_css    remove orphan CSS rules referencing missing tile IDs (prompts unless --force)

If scrub not used but orphans exist, tool may warn with count/sample IDs.


MAPS
====
--show_map
Shows BEFORE map (and OUTCOME map when an operation is performed).
Intended colors:
- empty: dot
- unchanged: gray
- changed: green
- conflict overlap: red
- allow_overlap overlap: yellow
Some builds include a focus option for full vs conflict bounds.


SAFETY / UNDO
=============
--force
--confirm_keep
--lock_backup
--undo_last (standalone restore)


DIAGNOSTICS
===========
--quiet
--verbose
--debug


PROGRAM FLOW (HIGH LEVEL)
=========================
1) Parse args
2) If undo_last: restore + exit
3) Import JSON
4) Detect input level
5) Validate
6) Save last-run backup
7) BEFORE map (optional)
8) Primary op (optional) + conflict scan + prompts
9) Trim (optional)
10) Sort (optional)
11) Scrub CSS (optional)
12) OUTCOME map (optional)
13) Write outputs
14) confirm_keep prompt (optional) + possible restore
15) Status summary


BEST-EFFORT PROJECT CHANGELOG (FROM CHAT HISTORY)
=================================================

This is reconstructed from conversation history and filenames. It may omit minor refactors
or interim debugging edits.

EARLY: tile_sorter (single-file script)
- Import from clipboard or file; modify only tiles[*].row/col; preserve rest.
- Validation of tiles presence; accept full/minimal/bare.
- argparse added.
- Sorting introduced: --sort + --order (subset i,r,c) with default completion.
- Insert rows/cols added with --include_overlap span logic and range filters:
  --col_range (insert_rows), --row_range (insert_cols).
- Trim added: trim_left/trim_top/trim (later consolidated to --trim[:top|left]).
- Output shape controls: full/container/list; output destinations terminal/clipboard/file.
- JSON formatting controls refined.

CLI REFACTOR: tile_sorter_refactor v8–v12
- CLI redesign:
  --import:clipboard default / --import:file <filename> (single import)
  repeatable --output_to:terminal|clipboard|file <filename>
  single --output_format:full|container|list
- Move operations: move_cols/move_rows/move_range
- One-time conflict scan against stationary destination tiles with allow/skip/abort.
- Delete/clear added with --force and shifting behavior.
- Renames: output_shape->output_format; insert_columns/move_columns->insert_cols/move_cols.
- Project split into modules due to length.

MERGE/COPY + CSS
- Added merge_source and merge_cols/rows/range (copy from external JSON).
- Added copy_cols/rows/range (copy within layout).
- ID conflict handling: generate new IDs when conflicts occur.
- Strengthened later to allocate above max tile id AND max id referenced in customCSS.
- CSS features:
  cleanup_css removes tile-specific rules when tiles removed
  create_css duplicated rules for new ids when copying/merging (later inverted)
- Fixed merge crashes and ensured css post-processing runs inside main.

BETA SERIES: hubitat_tile_mover
- Renamed to hubitat_tile_mover.
- Enforced output format limits; renamed formats to full/minimal/bare (legacy kept).
- No sorting unless --sort present; default sort spec when requested became irc.
- Added crop_to_rows/cols/range, prune_except_ids/devices with safety constraints.
- Changed css behavior: default create/copy css; added ignore_css to disable.
- Added scrub_css to remove orphan css rules; warn if orphans exist.
- Help rework: argument grouping; friendlier errors unless verbose/debug.

RC SERIES: Hub I/O + safeguards
- Added import:hub and output:hub with --url token flow:
  GET dashboard, extract javascriptRequestToken, use port 8080 /layout, GET/POST JSON.
- Added merge_url (source dashboard).
- Safety: backup original json; confirm_keep; undo_last; lock_backup.
- Many RC iterations fixing argparse missing switches, NameErrors, and ensuring undo exits early.
- Clarified hub requirements: hub output requires full; hub import always returns full.

MAPS: terminal visualization
- Added show_map BEFORE/OUTCOME maps; highlight conflicts and changed tiles.
- Intended colors: unchanged gray, changed green, conflicts red, allow_overlap yellow.
- For delete/clear/crop/prune: highlight to-be-removed tiles (orange) prior to prompt.
- Added focus behavior full vs conflict bounds (iterated due to bugs).

RECENT STABILIZATION (RC55–RC62)
- Continued crop/map plumbing fixes and signature consistency.
- End-of-run crash fixes (did_undo, args at module scope).
- Added __main__.py entrypoint for python -m hubitat_tile_mover (requested).
- Ongoing alignment of -h/help_full with actual switches and legacy aliases.
