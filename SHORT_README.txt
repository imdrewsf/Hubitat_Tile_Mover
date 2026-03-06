Hubitat Tile Mover
------------------

Adjust and/or edit the "tiles" list in a Hubitat Dashboard layout JSON while preserving everything else unchanged.

Import (one; default is clipboard):
  --import:clipboard
  --import:file <filename>
  --import:hub <dashboard_url>

Output destinations (repeatable; default is clipboard if none specified):
  --output:terminal
  --output:clipboard
  --output:file <filename>
  --output:hub [dashboard_url] (URL optional if importing from hub)

Layout actions (at most ONE per run):
  Insert:   --insert:rows COUNT AT_ROW
            --insert:cols COUNT AT_COL

  Move:     --move:cols START END DEST
            --move:rows START END DEST
            --move:range SRC_T SRC_L SRC_B SRC_R DEST_T DEST_L

  Copy:     --copy:cols START END DEST
            --copy:rows START END DEST
            --copy:range SRC_T SRC_L SRC_B SRC_R DEST_T DEST_L

  Merge:    --merge:cols START END DEST
            --merge:rows START END DEST
            --merge:range SRC_T SRC_L SRC_B SRC_R DEST_T DEST_L
            --merge_source:file <filename> OR  --merge_source:hub <dashboard_url>

  Delete:   --delete:rows START END
            --delete:cols START END

  Clear:    --clear:rows START END
            --clear:cols START END
            --clear:range TOP LEFT BOTTOM RIGHT

  Crop:     --crop:rows START END
            --crop:cols START END
            --crop:range TOP LEFT BOTTOM RIGHT

  Prune:    --prune:ids <spec>
            --prune:devices <spec>
            --prune_except:ids <spec>
            --prune_except:devices <spec>

  Copy CSS: --copy_css:merge FROM_TILE TO_TILE
            --copy_css:overwrite FROM_TILE TO_TILE
            --copy_css:replace FROM_TILE TO_TILE
            --copy_css:add FROM_TILE TO_TILE
            
Clear CSS:  --clear_css TILE_ID

Additional actions (may be combined with the single layout action):
  --trim[:top|left|top,left]        (default: top,left; left,top accepted)
  --sort[:<keys>]                   (runs after trim; default keys are irc)
  --scrub_css                       (runs last; can run alone)
  --compact_css                     (runs last; can run alone)

Modifiers:
  --include_overlap
  --row_range <start> <end>         (insert_cols only)
  --col_range <start> <end>         (insert_rows only)
  --allow_overlap / --skip_overlap  (move/copy/merge)
  --force                           (skip confirmation prompts)
  --cleanup_css                     (remove tile-specific CSS for removed tiles)
  --ignore_css                      (do not copy/create CSS for copy/merge)

Hubitat direct mode:
  --undo_last
  --confirm_keep
  --lock_backup

Maps:
  --show_map[:full|:conflicts|:no_scale]

More help:
  --help_full
  --version

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