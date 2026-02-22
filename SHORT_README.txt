hubitat_tile_mover � adjust a Hubitat Dashboard layout by operating on the "tiles" list (row/col only), preserving everything else unchanged.

Accepted input JSON shapes (3 levels):
  A) Full:    { ..., "tiles": [ {...}, ... ], ... }
  B) Minimal: { "tiles": [ {...}, ... ] }
  C) Bare:    [ {...}, ... ]

Import (input) (only one; default is clipboard):
  --import:clipboard
  --import:file <filename>
  --import:hub  (requires --url <dashboard local url)

Output destinations (repeatable; default is clipboard if none specified):
  --output:terminal
  --output:clipboard
  --output:file <filename>
  --output:hub (requires --url <dashboard local url)

Output format (single choice; default matches the input level; cannot exceed input):
  --output_format:full       (Full dashboard JSON)
  --output_format:minimal    ({"tiles":[...]}) (cannot be used with --output:hub)
  --output_format:bare       ([...]) (cannot be used with --output:hub)

Undo Actions (from output saved directly to hub)
  --undo_last (restores changes saved to hub by previous run)
  --confirm_keep (prompts to keep changes saved directly to hub)
  --lock_backup (keep existing undo file as current restore point)
  Note: undo files are maintained per dashboard.


LAYOUT ACTIONS (mutually exclusive; choose at most ONE per run)

  MOVE EXISTING TILES

    Insert empty rows / columns:
      --insert_rows COUNT AT_ROW
      --insert_cols COUNT AT_COL
      Modifiers: --include_overlap, --col_range/--row_range

    Move tiles:
      --move_cols START_COL END_COL DEST_START_COL
      --move_rows START_ROW END_ROW DEST_START_ROW
      --move_range SRC_TOP_ROW SRC_LEFT_COL SRC_BOTTOM_ROW SRC_RIGHT_COL DEST_TOP_ROW DEST_LEFT_COL
      Modifiers: --include_overlap, --allow_overlap, --skip_overlap

  ADD TILES

    Copy / duplicate existing tiles (within the input layout):
      --copy_cols START_COL END_COL DEST_START_COL
      --copy_rows START_ROW END_ROW DEST_START_ROW
      --copy_range SRC_TOP_ROW SRC_LEFT_COL SRC_BOTTOM_ROW SRC_RIGHT_COL DEST_TOP_ROW DEST_LEFT_COL
      Modifiers: --include_overlap, --allow_overlap, --skip_overlap, --ignore_css

    Merge / import tiles from another layout:
      --merge_source <filename>
      --merge_cols START_COL END_COL DEST_START_COL
      --merge_rows START_ROW END_ROW DEST_START_ROW
      --merge_range SRC_TOP_ROW SRC_LEFT_COL SRC_BOTTOM_ROW SRC_RIGHT_COL DEST_TOP_ROW DEST_LEFT_COL
      Modifiers: --include_overlap, --allow_overlap, --skip_overlap, --ignore_css

  REMOVE TILES

    Delete rows / columns (removes tiles AND shifts following tiles up/left):
      --delete_rows START_ROW END_ROW
      --delete_cols START_COL END_COL
      Modifiers: --include_overlap, --row_range/--col_range, --cleanup_css, --force

    Clear tiles (removes tiles but does NOT shift anything):
      --clear_rows START_ROW END_ROW
      --clear_cols START_COL END_COL
      --clear_range TOP_ROW LEFT_COL BOTTOM_ROW RIGHT_COL
      Modifiers: --include_overlap, --cleanup_css, --force

    Crop (remove everything OUTSIDE the kept range):
      --crop_to_rows START_ROW END_ROW
      --crop_to_cols START_COL END_COL
      --crop_to_range TOP_ROW LEFT_COL BOTTOM_ROW RIGHT_COL
      Modifiers: --include_overlap, --cleanup_css, --force
      Notes: the kept range must contain at least one tile; at least one tile must remain.

    Prune (remove everything EXCEPT matching tiles):
      --prune_ids <comma-separated tile ids>
      --prune_devices <comma-separated device ids>
      --prune_except_ids <comma-separated tile ids>
      --prune_except_devices <comma-separated device ids>
      Modifiers: --cleanup_css, --force
      Notes: at least one tile must match the provided ids/devices; at least one tile must remain.


ADDITIONAL ACTIONS (can be used alone or combined with the single layout action)

  Trim (performed after the layout action, before sorting):
    --trim                 (same as --trim:top,left)
    --trim:top
    --trim:left
    --trim:top,left

  Sort (only applied if --sort is present; affects output order only):
    --sort                 (same as --sort:irc)
    --sort:<SPEC>

    Keys: i=id, r=row, c=col
    Default SPEC: irc
    Prefix a key with '-' to sort that key descending (example: --sort:-i r c)
    Missing keys are appended in i,r,c order (ascending)

  Scrub orphan CSS (performed last, after sorting):
    --scrub_css
      Finds tile-specific CSS rules in customCSS that reference tile ids not present as tiles.
      Prompts before removal unless --force is specified.
      If --scrub_css is NOT specified and orphans are detected, the program warns how many were found.

  Layout Maps: (Show in terminal before and after layouts, movement conflicts)
    --show_map                 (print BEFORE / OUTCOME maps)
    --map_focus full|conflict|no_scale  (default: full; conflict maps only)
    Note: Show map can be used without an action to display the current layout of the import dashboard.

MODIFIERS

  Selection / overlap:
    --include_overlap
      Default selection: tiles are selected when their top-left (row,col) is inside the source/range.
      With --include_overlap: tiles are also selected when their span intersects the source/range
      (span uses rowSpan/colSpan; missing span defaults to 1x1).

  Insert/Delete range filters (limit which tiles are affected):
    --col_range <start_col> <end_col>     (only with --insert_rows and --delete_rows)
    --row_range <start_row> <end_row>     (only with --insert_cols and --delete_cols)
      example: --insert_rows 5 10 --col_range 2 7 ==> insert 5 rows at row 10 only in columns 2-7


  Destination conflict policy (move/copy/merge only):
    --allow_overlap
      Proceed even if destination conflicts exist.
    --skip_overlap
      Skip only the tiles that would conflict in the destination.
    default (neither set):
      Abort before changing anything if any destination conflicts exist.

  Confirmation suppression:
    --force
      Skip interactive confirmations when tiles or CSS rules would be removed.


CSS OPTIONS

  --ignore_css
      When copying/merging tiles, do not create/merge tile-specific CSS rules for new tile ids.

  --cleanup_css
      When tiles are removed (delete/clear/crop/prune), attempt to remove tile-specific CSS rules for those tile ids.
      Prompts before removal unless --force is specified.

  Note: Tile id assignment when copying/merging:
        New tile ids are assigned sequentially starting at:
            1 + max(highest existing tile id, highest tile id referenced in customCSS)
        This prevents newly created tiles from accidentally reusing ids that still have orphan CSS rules.


DIAGNOSTICS

  --quiet                  Suppress the final one-line summary
  --verbose                Planned actions summary to STDERR
  --debug                  Per-tile action logs to STDERR



  Copyright 2026 Andrew Peck

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
