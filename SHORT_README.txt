Hubitat Tile Mover: Short Readme / Usage Quick Reference

Import (input) (only one; default is clipboard):
  --import:clipboard
  --import:file <filename>
  --import:hub <dashboard_url>

Output destinations (repeatable; default is clipboard if none specified):
  --output:terminal
  --output:clipboard
  --output:file <filename>
  --output:hub [dashboard_url] (URL optional if importing from hub)

Undo Actions (from output saved directly to hub)
  --undo_last (restores changes saved to hub by previous run)
  --confirm_keep (prompts to keep changes saved directly to hub)
  --lock_backup (keep existing undo file as current restore point)
  Note: undo files are maintained per dashboard.


LAYOUT ACTIONS (mutually exclusive; choose at most ONE per run)

  MOVE EXISTING TILES

    Insert empty rows / columns:
      --insert:rows COUNT AT_ROW
      --insert:cols COUNT AT_COL
      Modifiers: --include_overlap, --col_range/--row_range

    Move tiles:
      --move:cols START_COL END_COL DEST_START_COL
      --move:rows START_ROW END_ROW DEST_START_ROW
      --move:range SRC_TOP_ROW SRC_LEFT_COL SRC_BOTTOM_ROW SRC_RIGHT_COL DEST_TOP_ROW DEST_LEFT_COL
      Modifiers: --include_overlap, --allow_overlap, --skip_overlap

  ADD TILES

    Copy / duplicate existing tiles (within the input layout):
      --copy:cols START_COL END_COL DEST_START_COL
      --copy:rows START_ROW END_ROW DEST_START_ROW
      --copy:range SRC_TOP_ROW SRC_LEFT_COL SRC_BOTTOM_ROW SRC_RIGHT_COL DEST_TOP_ROW DEST_LEFT_COL
      Modifiers: --include_overlap, --allow_overlap, --skip_overlap, --ignore_css

    Merge / import tiles from another layout:
      --merge_source:file <filename>
      --merge_source:hub <dashboard_url>
      --merge:cols START_COL END_COL DEST_START_COL
      --merge:rows START_ROW END_ROW DEST_START_ROW
      --merge:range SRC_TOP_ROW SRC_LEFT_COL SRC_BOTTOM_ROW SRC_RIGHT_COL DEST_TOP_ROW DEST_LEFT_COL
      Modifiers: --include_overlap, --allow_overlap, --skip_overlap, --ignore_css

  REMOVE TILES

    Delete rows / columns (removes tiles AND shifts following tiles up/left):
      --delete:rows START_ROW END_ROW
      --delete:cols START_COL END_COL
      Modifiers: --include_overlap, --row_range/--col_range, --cleanup_css, --force

    Clear tiles (removes tiles but does NOT shift anything):
      --clear:rows START_ROW END_ROW
      --clear:cols START_COL END_COL
      --clear:range TOP_ROW LEFT_COL BOTTOM_ROW RIGHT_COL
      Modifiers: --include_overlap, --cleanup_css, --force

    Crop (remove everything OUTSIDE the kept range):
      --crop:rows START_ROW END_ROW
      --crop:cols START_COL END_COL
      --crop:range TOP_ROW LEFT_COL BOTTOM_ROW RIGHT_COL
      Modifiers: --include_overlap, --cleanup_css, --force
      Notes: the kept range must contain at least one tile; at least one tile must remain.

    Prune:
      Keep-only mode (remove everything EXCEPT matching tiles):
        --prune_except:ids <SPEC>
        --prune_except:devices <SPEC>
      Remove-matches mode (remove only matching tiles):
        --prune:ids <SPEC>
        --prune:devices <SPEC>
      Modifiers: --cleanup_css, --force
      SPEC supports: comma lists (1,5,8), ranges (5-10), comparisons (<5, >=7). For devices, numeric specs match device strings "0","1",...
      Notes: at least one tile must match; at least one tile must remain.


ADDITIONAL ACTIONS (can be used alone or combined with the single layout action)

  Trim (performed after the layout action, before sorting):
    --trim                 (same as --trim:top,left)
    --trim:top
    --trim:left
    --trim:top,left        (default)
    --trim:left,top        (also accepted)

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



  Tile CSS actions (modify customCSS; can run alone):
    Copy CSS from one existing tile id to another existing tile id:
      --copy_css:merge FROM_TILE TO_TILE
      --copy_css:overwrite FROM_TILE TO_TILE
      --copy_css:replace FROM_TILE TO_TILE
      --copy_css:add FROM_TILE TO_TILE
      Notes:
        :merge prompts per conflicting rule (keep/overwrite/abort). With --force, conflicts are skipped.
        :overwrite overwrites conflicting destination rules automatically.
        :replace removes destination tile rules first, then copies all source tile rules.
        :add copies all rules regardless of conflicts (may create duplicates).
      Rule duplication uses the same remap behavior as tile copy/merge (selector remap and body rewrite of tile-OLD→tile-NEW).

    Clear CSS for an existing tile id (tile remains):
      --clear_css TILE_ID


  Compact CSS (performed last; can run alone):
    --compact_css
      Rewrites customCSS as one selector rule per line (selector { body }), splits selector lists, and sorts lines.
      Sorting: non-tile class selectors (start with '.' but not .tile-N) first, then tile selectors (#tile-N/.tile-N) by N, then everything else.
  Layout Maps: (Show in terminal before and after layouts, movement conflicts)
    --show_map                 (same as --show_map:full)
    --show_map:full            (print BEFORE / OUTCOME maps; default)
    --show_map:conflicts       (focus maps on affected/conflicting region)
    --show_map:no_scale        (no scaling; 1 row/col = 1 character)
    Note: Show map can be used without an action to display the current layout of the import dashboard.

MODIFIERS

  Selection / overlap:
    --include_overlap
      Default selection: tiles are selected when their top-left (row,col) is inside the source/range.
      With --include_overlap: tiles are also selected when their span intersects the source/range
      (span uses rowSpan/colSpan; missing span defaults to 1x1).

  Insert/Delete range filters (limit which tiles are affected):
    --col_range <start_col> <end_col>     (only with --insert:rows and --delete:rows)
    --row_range <start_row> <end_row>     (only with --insert:cols and --delete:cols)
      example: --insert:rows 5 10 --col_range 2 7 ==> insert 5 rows at row 10 only in columns 2-7


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
  --version                Print build version and exit.


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



