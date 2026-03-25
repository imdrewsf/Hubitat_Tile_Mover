from __future__ import annotations

import argparse
import sys

from . import __version__

def _safe_stdout_write(text: str) -> None:
    """Write text to stdout without UnicodeEncodeError on Windows redirected output."""
    try:
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")
    except UnicodeEncodeError:
        # Fall back to UTF-8 bytes with replacement.
        data = (text + ("\n" if not text.endswith("\n") else "")).encode("utf-8", errors="replace")
        try:
            sys.stdout.buffer.write(data)
        except Exception:
            # Last resort: strip non-encodable chars
            sys.stdout.write(data.decode("utf-8", errors="replace"))
    sys.stdout.flush()





class _SpacingAddModeAction(argparse.Action):
    """Stores (mode, signed_cells) where mode is rows|cols|all derived from option string."""

    def __call__(self, parser, namespace, values, option_string=None):
        mode = "all"
        if option_string and ":" in option_string:
            mode = option_string.split(":", 1)[1]
        try:
            cells = int(values)
        except ValueError:
            raise argparse.ArgumentTypeError(f"Expected integer, got: {values!r}")
        setattr(namespace, self.dest, (mode, cells))

# Short help formatting notes (0.9.98):
# - Removed user-facing JSON formatting/shape details.
# - Added blank lines between layout action groups for readability.
# - Renamed "Tile CSS" -> "Copy CSS" and kept the header on the same line as the first option.
# - Documented --trim default as top,left (and that left,top is also accepted).

SHORT_HELP = r'''Adjust and/or edit the "tiles" list in a Hubitat Dashboard layout JSON while preserving everything else unchanged.

Import (one; default is clipboard):
  --import:clipboard
  --import:file <filename>
  --import:hub <dashboard_url>

Output destinations (repeatable; default is clipboard if none specified):
  --output:terminal
  --output:clipboard
  --output:file <filename>
  --output:hub [dashboard_url]       (FULL input only; URL optional if importing from hub; not valid with --list_tiles)

Layout actions (at most ONE per run):
  Insert:   --insert:rows COUNT AT_ROW
            --insert:cols COUNT AT_COL
  Spacing:  --spacing_add:rows CELLS  |  --spacing_add:cols CELLS  |  --spacing_add:all CELLS   (CELLS may be negative; gaps clamp at 0)
            --spacing_set:rows GAP    |  --spacing_set:cols GAP    |  --spacing_set:all GAP     (GAP must be >= 0)
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
            --clear_css <spec>

Additional actions (may be combined with the single layout action):
  --trim[:top|left|top,left]        (default: top,left; left,top accepted)
  --sort[:<keys>]                   (runs after trim; default keys are irc)
  --scrub_css                       (runs last; can run alone)
  --compact_css                     (runs last; can run alone)

Modifiers:
  --include_overlap
  --no_overlap                    (spacing_set only; global un-overlap; cannot be combined with --include_overlap)
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
  --show_ids                          (label tile ids on maps; group overlapping labels below map)
  --show_axis:row|col|all             (show real row/col numbers on map edges)

Tile reports:
  --list_tiles:<type>[:<keys>]        (standalone tile report; types: plain, tree, overlap, nested, conflicts)

More help:
  --help:full
  --version
'''

FULL_HELP = r"""hubitat_tile_mover � adjust a Hubitat Dashboard layout by operating on the "tiles" list (row/col only), preserving everything else unchanged.

Import (input) (only one; default is clipboard):
  --import:clipboard
  --import:file <filename>
  --import:hub <dashboard_url>

Output destinations (repeatable; default is clipboard if none specified):
  --output:terminal
  --output:clipboard
  --output:file <filename>
  --output:hub [dashboard_url] (URL optional if importing from hub; not valid with --list_tiles)

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

  Spacing (performed after the layout action, before trim/sort):

    Add/subtract spacing between units:
      --spacing_add:rows CELLS
      --spacing_add:cols CELLS
      --spacing_add:all  CELLS
        CELLS may be negative. Example: if a gap is 9 and you run --spacing_add:all -2, it becomes 7.
        Gaps are clamped at 0 (never negative).

    Set spacing to a fixed number of blank cells:
      --spacing_set:rows GAP
      --spacing_set:cols GAP
      --spacing_set:all  GAP
        GAP must be >= 0.

    Overlap behavior for spacing:
      Default: overlapping tiles are grouped into overlap-unions (treated as a single unit).
      --include_overlap (spacing_set only): adjusts spacing within each overlap-union only.
      --no_overlap (spacing_set only): treat EVERY tile as its own unit (global un-overlap).
      NOTE: --include_overlap and --no_overlap are mutually exclusive.


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
      --clear_css <spec>


  Compact CSS (performed last; can run alone):
    --compact_css
      Rewrites customCSS as one selector rule per line (selector { body }), splits selector lists, and sorts lines.
      Sorting: non-tile class selectors (start with '.' but not .tile-N) first, then tile selectors (#tile-N/.tile-N) by N, then everything else.
  Layout Maps: (Show in terminal before and after layouts, movement conflicts)
    --show_map                 (same as --show_map:full)
    --show_map:full            (print BEFORE / OUTCOME maps; default)
    --show_map:conflicts       (focus maps on affected/conflicting region)
    --show_map:no_scale        (no scaling; 1 row/col = 1 character)
    --show_ids                 (label tile ids on maps; overlapping/colliding labels become Grp-A, Grp-B, ... with a list below the map)
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


  --version  Print build version and exit.
"""






class _SpacingSetModeAction(argparse.Action):
    """Stores (mode, gap) where mode is rows|cols|all derived from option string.

    GAP must be a non-negative integer.
    """

    def __call__(self, parser, namespace, values, option_string=None):
        mode = "all"
        if option_string and ":" in option_string:
            mode = option_string.split(":", 1)[1]
        try:
            gap = int(values)
        except ValueError:
            raise argparse.ArgumentTypeError(f"Expected integer, got: {values!r}")
        if gap < 0:
            raise argparse.ArgumentTypeError(f"Expected non-negative integer, got: {values!r}")
        setattr(namespace, self.dest, (mode, gap))

class TileSorterArgumentParser(argparse.ArgumentParser):
    def format_help(self) -> str:
        # Default help is slim; use --help:full for the expanded help text.
        return SHORT_HELP + "\n"

    def error(self, message: str) -> None:
        # Keep argparse-style errors, but add a hint.
        self.print_usage(sys.stderr)
        self.exit(2, f"ERROR: {message}\nUse -h for help.\n")



class HelpFullAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        _safe_stdout_write(FULL_HELP)
        raise SystemExit(0)


class _SetImportSpecAction(argparse.Action):
    """Normalize the visible --import:* flags into the same structure used by --import."""
    def __init__(self, option_strings, dest, kind: str, **kwargs):
        self._kind = kind
        super().__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        if self._kind in ("clipboard", "hub"):
            if self._kind == "clipboard":
                setattr(namespace, self.dest, ["clipboard"])
            else:
                # values is a single URL string
                setattr(namespace, self.dest, ["hub", values])
        elif self._kind == "file":
            setattr(namespace, self.dest, ["file", values])
        else:
            setattr(namespace, self.dest, None)


class _AppendOutputToAction(argparse.Action):
    """Normalize visible --output:* flags into the same structure used by --output_to."""
    def __init__(self, option_strings, dest, kind: str, **kwargs):
        self._kind = kind
        super().__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        cur = getattr(namespace, self.dest, None)
        if cur is None:
            cur = []
        if self._kind in ("terminal", "clipboard"):
            cur.append([self._kind])
        elif self._kind == "file":
            cur.append(["file", values])
        elif self._kind == "hub":
            if values is None:
                cur.append(["hub"])
            else:
                cur.append(["hub", values])
        else:
            cur.append([self._kind])
        setattr(namespace, self.dest, cur)

def build_parser() -> argparse.ArgumentParser:
    p = TileSorterArgumentParser(
        add_help=True,
        allow_abbrev=False,
        # Keep argparse usage line short; help text above provides full documentation.
        usage="hubitat_tile_mover.py [options]",
    )

    p.add_argument(
        "--version",
        action="version",
        version=f"hubitat_tile_mover {__version__}",
        help="Print build version and exit.",
    )

    p.add_argument("--help:full", "--help_full", action=HelpFullAction, nargs=0, help="(see --help:full for details)")

    # Keep argument groups for internal structure (even though custom help is printed).
    io_grp = p.add_argument_group("Import / Output")
    # User-facing convenience switches (these appear in -h via SHORT_HELP / FULL_HELP)
    imp_vis = io_grp.add_mutually_exclusive_group(required=False)
    imp_vis.add_argument('--import:clipboard', dest='import_spec', nargs=0, action=_SetImportSpecAction, kind='clipboard', help='Read JSON from clipboard (default).')
    imp_vis.add_argument('--import:file', dest='import_spec', action=_SetImportSpecAction, kind='file', metavar='FILENAME', help='Read JSON from file.')
    imp_vis.add_argument('--import:hub', dest='import_spec', action=_SetImportSpecAction, kind='hub', metavar='DASHBOARD_URL', help='Read layout JSON from Hubitat dashboard URL.')

    out_vis = io_grp.add_argument_group('Output destinations')
    out_vis.add_argument('--output:terminal', dest='output_to', nargs=0, action=_AppendOutputToAction, kind='terminal', help='Write JSON to terminal. Repeatable.')
    out_vis.add_argument('--output:clipboard', dest='output_to', nargs=0, action=_AppendOutputToAction, kind='clipboard', help='Write JSON to clipboard. Repeatable.')
    out_vis.add_argument('--output:file', dest='output_to', action=_AppendOutputToAction, kind='file', metavar='FILENAME', help='Write JSON to file. Repeatable.')
    out_vis.add_argument('--output:hub', dest='output_to', nargs='?', action=_AppendOutputToAction, kind='hub', metavar='DASHBOARD_URL', help='POST resulting FULL layout JSON back to Hubitat dashboard URL (URL optional if importing from hub).')
    io_grp.add_argument("--undo_last", dest="undo_last", action="store_true", help="Restore from the last backup (writes to requested outputs).")
    io_grp.add_argument("--confirm_keep", dest="confirm_keep", action="store_true", help="After writing changed output(s), prompt to keep; if not, restore backup to the same outputs.")
    io_grp.add_argument("--lock_backup", dest="lock_backup", action="store_true", help="Do not overwrite an existing backup; reuse it as the restore point.")

    io_grp.add_argument(
        "--import",
        dest="import_spec",
        nargs="+",
        metavar=("KIND", "PATH"),
        default=None,
        help="(see --help:full for details)",
    )
    io_grp.add_argument(
        "--output_to",
        "--output-to",
        "--output",
        action="append",
        nargs="+",
        metavar=("DEST", "ARG"),
        default=None,
        help="(see --help:full for details)",
    )
    io_grp.add_argument(
        "--output_format",
        "--output-format",
        "--output_shape",
        "--output-shape",
        choices=["full", "minimal", "bare", "container", "list"],
        default=None,
        help=argparse.SUPPRESS,
    )

    # JSON formatting knobs are intentionally supported for power users / internal use, but not documented.
    # User-facing docs assume full Hubitat layout JSON and default formatting.
    p.add_argument("--indent", type=int, default=2, help=argparse.SUPPRESS)
    p.add_argument("--minify", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--newline", choices=["keep", "lf", "crlf"], default="keep", help=argparse.SUPPRESS)

    ops_grp = p.add_argument_group("Operations")
    ops = ops_grp.add_mutually_exclusive_group(required=False)

    # IMPORTANT: argparse derives Namespace attribute names from the *first* option string.
    # For colon-form options (e.g., --insert:rows), that would create attributes like "insert:rows",
    # which then breaks code expecting insert_rows/move_cols/etc. Always set dest=... explicitly.
    ops.add_argument(
        "--insert:rows",
        "--insert_rows",
        "--insert-rows",
        dest="insert_rows",
        nargs=2,
        metavar=("COUNT", "AT_ROW"),
        type=int,
        help="(see --help:full for details)",
    )
    ops.add_argument(
        "--insert:cols",
        "--insert_cols",
        "--insert-cols",
        "--insert_columns",
        "--insert-columns",
        dest="insert_cols",
        nargs=2,
        metavar=("COUNT", "AT_COL"),
        type=int,
        help="(see --help:full for details)",
    )



    ops.add_argument(
        "--spacing_add:rows",
        dest="spacing_add",
        metavar="CELLS",
        action=_SpacingAddModeAction,
        help="(see --help:full for details)",
    )
    ops.add_argument(
        "--spacing_add:cols",
        dest="spacing_add",
        metavar="CELLS",
        action=_SpacingAddModeAction,
        help="(see --help:full for details)",
    )
    ops.add_argument(
        "--spacing_add:all",
        dest="spacing_add",
        metavar="CELLS",
        action=_SpacingAddModeAction,
        help="(see --help:full for details)",
    )


    ops.add_argument(
        "--spacing_set:rows",
        dest="spacing_set",
        metavar="GAP",
        action=_SpacingSetModeAction,
        help="(see --help:full for details)",
    )
    ops.add_argument(
        "--spacing_set:cols",
        dest="spacing_set",
        metavar="GAP",
        action=_SpacingSetModeAction,
        help="(see --help:full for details)",
    )
    ops.add_argument(
        "--spacing_set:all",
        dest="spacing_set",
        metavar="GAP",
        action=_SpacingSetModeAction,
        help="(see --help:full for details)",
    )
    ops.add_argument(
        "--move:cols",
        "--move_cols",
        "--move-cols",
        "--move_columns",
        "--move-columns",
        dest="move_cols",
        nargs=3,
        metavar=("START_COL", "END_COL", "DEST_START_COL"),
        type=int,
        help="(see --help:full for details)",
    )
    ops.add_argument(
        "--move:rows",
        "--move_rows",
        "--move-rows",
        dest="move_rows",
        nargs=3,
        metavar=("START_ROW", "END_ROW", "DEST_START_ROW"),
        type=int,
        help="(see --help:full for details)",
    )
    ops.add_argument(
        "--move:range",
        "--move_range",
        "--move-range",
        dest="move_range",
        nargs=6,
        metavar=("SRC_TOP_ROW", "SRC_LEFT_COL", "SRC_BOTTOM_ROW", "SRC_RIGHT_COL", "DEST_TOP_ROW", "DEST_LEFT_COL"),
        type=int,
        help="(see --help:full for details)",
    )

    ops.add_argument(
        "--copy:cols",
        "--copy_cols",
        "--copy-cols",
        dest="copy_cols",
        nargs=3,
        metavar=("START_COL", "END_COL", "DEST_START_COL"),
        type=int,
        help="(see --help:full for details)",
    )
    ops.add_argument(
        "--copy:rows",
        "--copy_rows",
        "--copy-rows",
        dest="copy_rows",
        nargs=3,
        metavar=("START_ROW", "END_ROW", "DEST_START_ROW"),
        type=int,
        help="(see --help:full for details)",
    )
    ops.add_argument(
        "--copy:range",
        "--copy_range",
        "--copy-range",
        dest="copy_range",
        nargs=6,
        metavar=("SRC_TOP_ROW", "SRC_LEFT_COL", "SRC_BOTTOM_ROW", "SRC_RIGHT_COL", "DEST_TOP_ROW", "DEST_LEFT_COL"),
        type=int,
        help="(see --help:full for details)",
    )

    ops.add_argument(
        "--merge:cols",
        "--merge_cols",
        "--merge-cols",
        dest="merge_cols",
        nargs=3,
        metavar=("START_COL", "END_COL", "DEST_START_COL"),
        type=int,
        help="(see --help:full for details)",
    )
    ops.add_argument(
        "--merge:rows",
        "--merge_rows",
        "--merge-rows",
        dest="merge_rows",
        nargs=3,
        metavar=("START_ROW", "END_ROW", "DEST_START_ROW"),
        type=int,
        help="(see --help:full for details)",
    )
    ops.add_argument(
        "--merge:range",
        "--merge_range",
        "--merge-range",
        dest="merge_range",
        nargs=6,
        metavar=("SRC_TOP_ROW", "SRC_LEFT_COL", "SRC_BOTTOM_ROW", "SRC_RIGHT_COL", "DEST_TOP_ROW", "DEST_LEFT_COL"),
        type=int,
        help="(see --help:full for details)",
    )

    ops.add_argument(
        "--delete:rows",
        "--delete_rows",
        "--delete-rows",
        dest="delete_rows",
        nargs=2,
        metavar=("START_ROW", "END_ROW"),
        type=int,
        help="(see --help:full for details)",
    )
    ops.add_argument(
        "--delete:cols",
        "--delete_cols",
        "--delete-cols",
        "--delete_columns",
        "--delete-columns",
        dest="delete_cols",
        nargs=2,
        metavar=("START_COL", "END_COL"),
        type=int,
        help="(see --help:full for details)",
    )

    ops.add_argument(
        "--clear:rows",
        "--clear_rows",
        "--clear-rows",
        dest="clear_rows",
        nargs=2,
        metavar=("START_ROW", "END_ROW"),
        type=int,
        help="(see --help:full for details)",
    )
    ops.add_argument(
        "--clear:cols",
        "--clear_cols",
        "--clear-cols",
        "--clear_columns",
        "--clear-columns",
        dest="clear_cols",
        nargs=2,
        metavar=("START_COL", "END_COL"),
        type=int,
        help="(see --help:full for details)",
    )
    ops.add_argument(
        "--clear:range",
        "--clear_range",
        "--clear-range",
        dest="clear_range",
        nargs=4,
        metavar=("TOP_ROW", "LEFT_COL", "BOTTOM_ROW", "RIGHT_COL"),
        type=int,
        help="(see --help:full for details)",
    )

    ops.add_argument(
        "--crop:rows",
        "--crop_to_rows",
        "--crop-to-rows",
        dest="crop_to_rows",
        nargs=2,
        metavar=("START_ROW", "END_ROW"),
        type=int,
        help="(see --help:full for details)",
    )
    ops.add_argument(
        "--crop:cols",
        "--crop_to_cols",
        "--crop-to-cols",
        "--crop_to_columns",
        "--crop-to-columns",
        dest="crop_to_cols",
        nargs=2,
        metavar=("START_COL", "END_COL"),
        type=int,
        help="(see --help:full for details)",
    )
    ops.add_argument(
        "--crop:range",
        "--crop_to_range",
        "--crop-to-range",
        dest="crop_to_range",
        nargs=4,
        metavar=("TOP_ROW", "LEFT_COL", "BOTTOM_ROW", "RIGHT_COL"),
        type=int,
        help="(see --help:full for details)",
    )

    # Prune specs (new preferred syntax)
    ops.add_argument("--prune_except:ids", dest="prune_except_ids", metavar="SPEC", type=str, help="(see --help:full for details)")
    ops.add_argument("--prune_except:devices", dest="prune_except_devices", metavar="SPEC", type=str, help="(see --help:full for details)")
    ops.add_argument("--prune:ids", dest="prune_ids", metavar="SPEC", type=str, help="(see --help:full for details)")
    ops.add_argument("--prune:devices", dest="prune_devices", metavar="SPEC", type=str, help="(see --help:full for details)")

    # Legacy aliases (accepted but not documented)
    ops.add_argument("--prune_except_ids", "--prune-except-ids", dest="prune_except_ids", metavar="SPEC", type=str, help=argparse.SUPPRESS)
    ops.add_argument("--prune_except_devices", "--prune-except-devices", dest="prune_except_devices", metavar="SPEC", type=str, help=argparse.SUPPRESS)
    ops.add_argument("--prune_ids", "--prune-ids", dest="prune_ids", metavar="SPEC", type=str, help=argparse.SUPPRESS)
    ops.add_argument("--prune_devices", "--prune-devices", dest="prune_devices", metavar="SPEC", type=str, help=argparse.SUPPRESS)

    # CSS-only actions (operate on customCSS/customCss; tiles are unchanged)
    ops.add_argument(
        "--copy_css:merge",
        "--copy-css:merge",
        dest="copy_tile_css_merge",
        nargs=2,
        metavar=("FROM_TILE", "TO_TILE"),
        type=int,
        help="Copy tile-specific CSS (merge): prompt per conflicting rule; --force skips conflicts",
    )
    ops.add_argument(
        "--copy_css:overwrite",
        "--copy-css:overwrite",
        dest="copy_tile_css_overwrite",
        nargs=2,
        metavar=("FROM_TILE", "TO_TILE"),
        type=int,
        help="Copy tile-specific CSS (overwrite): overwrite conflicting destination rules",
    )
    ops.add_argument(
        "--copy_css:replace",
        "--copy-css:replace",
        dest="copy_tile_css_replace",
        nargs=2,
        metavar=("FROM_TILE", "TO_TILE"),
        type=int,
        help="Copy tile-specific CSS (replace): remove destination tile rules first, then copy source rules",
    )
    ops.add_argument(
        "--copy_css:add",
        "--copy-css:add",
        dest="copy_tile_css_add",
        nargs=2,
        metavar=("FROM_TILE", "TO_TILE"),
        type=int,
        help="Copy tile-specific CSS (add): copy all rules regardless of conflicts (may create duplicates)",
    )
    ops.add_argument(
        "--clear_css",
        "--clear-css",
        dest="clear_tile_css",
        metavar="SPEC",
        type=str,
        help="Remove tile-specific CSS rules for tile id(s) matched by SPEC (does not remove tiles). SPEC matches --prune:ids syntax (comma list, ranges, comparisons).",
    )

    # Legacy CSS action aliases (accepted but not documented)
    ops.add_argument("--copy_tile_css:merge", "--copy-tile-css:merge", dest="copy_tile_css_merge", nargs=2, metavar=("FROM_TILE", "TO_TILE"), type=int, help=argparse.SUPPRESS)
    ops.add_argument("--copy_tile_css:overwrite", "--copy-tile-css:overwrite", dest="copy_tile_css_overwrite", nargs=2, metavar=("FROM_TILE", "TO_TILE"), type=int, help=argparse.SUPPRESS)
    ops.add_argument("--copy_tile_css:replace", "--copy-tile-css:replace", dest="copy_tile_css_replace", nargs=2, metavar=("FROM_TILE", "TO_TILE"), type=int, help=argparse.SUPPRESS)
    ops.add_argument("--copy_tile_css:add", "--copy-tile-css:add", dest="copy_tile_css_add", nargs=2, metavar=("FROM_TILE", "TO_TILE"), type=int, help=argparse.SUPPRESS)
    ops.add_argument("--clear_tile_css", "--clear-tile-css", dest="clear_tile_css", metavar="TILE_ID", type=int, help=argparse.SUPPRESS)


    ops_grp.add_argument("--merge_source", "--merge-source", default=None, nargs='+', help="(see --help:full for details)")

    filters_grp = p.add_argument_group("Filters")
    filters_grp.add_argument("--include_overlap", "--include-overlap", action="store_true", help="(see --help:full for details)")
    filters_grp.add_argument("--no_overlap", "--no-overlap", action="store_true", help="(see --help:full for details)")
    filters_grp.add_argument("--col_range", "--col-range", nargs=2, metavar=("COL_START", "COL_END"), type=int, help="(see --help:full for details)")
    filters_grp.add_argument("--row_range", "--row-range", nargs=2, metavar=("ROW_START", "ROW_END"), type=int, help="(see --help:full for details)")

    overlap_grp = p.add_argument_group("Overlap Policy")
    conflict = overlap_grp.add_mutually_exclusive_group(required=False)
    conflict.add_argument("--allow_overlap", "--allow-overlap", action="store_true", help="(see --help:full for details)")
    conflict.add_argument("--skip_overlap", "--skip-overlap", action="store_true", help="(see --help:full for details)")

    safety_grp = p.add_argument_group("Safety")
    safety_grp.add_argument("--force", action="store_true", help="(see --help:full for details)")

    trim_sort_grp = p.add_argument_group("Trim / Sort")
    trim_sort_grp.add_argument("--trim", nargs="?", const="both", default=None, metavar="MODE", help="(see --help:full for details)")
    trim_sort_grp.add_argument("--trim_left", "--trim-left", action="store_true", help="(see --help:full for details)")
    trim_sort_grp.add_argument("--trim_top", "--trim-top", action="store_true", help="(see --help:full for details)")

    # --sort[:SPEC] (single switch). We keep legacy --order hidden.
    trim_sort_grp.add_argument("--sort", nargs="?", const="irc", default=None, metavar="SPEC", help="(see --help:full for details)")
    trim_sort_grp.add_argument("--order", default=None, help="(see --help:full for details)")

    css_grp = p.add_argument_group("CSS")
    css_grp.add_argument("--cleanup_css", "--cleanup-css", action="store_true", help="Remove tile-specific CSS rules for deleted/cleared tiles (best-effort)")
    css_grp.add_argument("--ignore_css", "--ignore-css", action="store_true", help="Do NOT create/copy tile-specific CSS rules for new ids when copying/merging (default is to create/copy)")
    # NOTE: copy-tile-css modes are expressed as action switches in the Operations group:
    #   --copy_tile_css:merge / :overwrite / :replace / :add
    # Legacy (no-op): historically enabled CSS creation; now creation/copy is the default.
    css_grp.add_argument("--create_css", "--create-css", dest="legacy_create_css", action="store_true", help=argparse.SUPPRESS)
    css_grp.add_argument("--scrub_css", "--scrub-css", action="store_true", help="Remove orphan tile-specific CSS rules (no matching tile id) after actions")
    css_grp.add_argument("--compact_css", "--compact-css", action="store_true", help="Compact/sort customCSS: one rule per line starting with selector (runs last; can run alone)")


    diag_grp = p.add_argument_group("Diagnostics")
    # Map printing. The visible interface is --show_map:MODE with a default of full.
    # Keep a hidden --map_focus for backwards compatibility but do not document it.
    diag_grp.add_argument("--show_map", dest="show_map_mode", action="store_const", const="full", help="Show ASCII layout maps in the terminal (same as --show_map:full)")
    diag_grp.add_argument("--show_map:full", dest="show_map_mode", action="store_const", const="full", help="Show BEFORE/AFTER ASCII layout maps in the terminal")
    diag_grp.add_argument("--show_map:conflicts", dest="show_map_mode", action="store_const", const="conflict", help="Focus maps on affected/conflicting region")
    diag_grp.add_argument("--show_map:no_scale", dest="show_map_mode", action="store_const", const="no_scale", help="Show maps unscaled (1 row/col = 1 character)")
    diag_grp.add_argument("--show_ids", "--show-ids", action="store_true", help="Show tile ids on ASCII maps; colliding labels are grouped below the map")
    diag_grp.add_argument("--show_axis:row", dest="show_axes", action="store_const", const="row", help="Show row numbers on the left edge of ASCII maps")
    diag_grp.add_argument("--show_axis:col", dest="show_axes", action="store_const", const="col", help="Show column numbers along the top edge of ASCII maps")
    diag_grp.add_argument("--show_axis:all", dest="show_axes", action="store_const", const="all", help="Show both row and column numbers on ASCII maps")
    diag_grp.add_argument("--show_axis:both", dest="show_axes", action="store_const", const="all", help=argparse.SUPPRESS)
    diag_grp.add_argument("--show_axes:row", dest="show_axes", action="store_const", const="row", help=argparse.SUPPRESS)
    diag_grp.add_argument("--show_axes:col", dest="show_axes", action="store_const", const="col", help=argparse.SUPPRESS)
    diag_grp.add_argument("--show_axes:all", dest="show_axes", action="store_const", const="all", help=argparse.SUPPRESS)
    diag_grp.add_argument("--show_axes:both", dest="show_axes", action="store_const", const="all", help=argparse.SUPPRESS)
    diag_grp.add_argument("--list_tiles", dest="list_tiles", nargs="?", const="plain:rci", metavar="TYPE[:SPEC]", help="Standalone tile report action: plain, tree, overlap, nested, conflicts")

    diag_grp.add_argument(
        "--map_focus",
        dest="map_focus",
        choices=["full", "conflict", "no_scale"],
        default=None,
        help=argparse.SUPPRESS,
    )
    diag_grp.add_argument("--verbose", action="store_true", help="Verbose output to STDERR")
    diag_grp.add_argument("--debug", action="store_true", help="Debug output (very verbose) to STDERR")
    diag_grp.add_argument("--quiet", action="store_true", help="Suppress final status line")

    return p
