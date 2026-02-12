from __future__ import annotations

import argparse
import sys

SHORT_HELP = r"""hubitat_tile_mover: adjust a Hubitat Dashboard "tiles" layout JSON (row/col only), preserving everything else.

Input:
  --import:clipboard (default) | --import:file <filename>

Output (repeatable; default: clipboard):
  --output_to:clipboard | --output_to:terminal | --output_to:file <filename>

Output format (defaults to input level; cannot exceed input):
  --output_format:full | --output_format:minimal | --output_format:bare

Actions (choose at most ONE):
  Insert:  --insert_rows COUNT AT_ROW | --insert_cols COUNT AT_COL
  Move:    --move_cols ... | --move_rows ... | --move_range ...
  Copy:    --copy_cols ... | --copy_rows ... | --copy_range ...
  Merge:   --merge_source <file> + --merge_cols/rows/range ...
  Remove:  --delete_rows/cols | --clear_rows/cols/range
  Crop:    --crop_to_rows/cols/range
  Prune:   --prune_except_ids ... | --prune_except_devices ...

Optional post-actions (can be used alone or with an action):
  --trim[:top|left|top,left]
  --sort[:SPEC]
  --scrub_css

Common modifiers:
  --include_overlap    select by span intersection (not just top-left)
  --allow_overlap | --skip_overlap   (move/copy/merge destination conflicts)
  --force              skip confirmations

More details:
  --help_full
"""

FULL_HELP = r"""hubitat_tile_mover — adjust a Hubitat Dashboard layout by operating on the "tiles" list (row/col only), preserving everything else unchanged.

Accepted input JSON shapes (3 levels):
  A) Full:    { ..., "tiles": [ {...}, ... ], ... }
  B) Minimal: { "tiles": [ {...}, ... ] }
  C) Bare:    [ {...}, ... ]

Import (input) (only one; default is clipboard):
  --import:clipboard
  --import:file <filename>

Output destinations (repeatable; default is clipboard if none specified):
  --output_to:terminal
  --output_to:clipboard
  --output_to:file <filename>

Output format (single choice; default matches the input level; cannot exceed input):
  --output_format:full       (Full dashboard JSON)
  --output_format:minimal    ({"tiles":[...]})
  --output_format:bare       ([...])

  Compatibility aliases (accepted):
    --output_format:container  == minimal
    --output_format:list       == bare


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


MODIFIERS

  Selection / overlap:
    --include_overlap
      Default selection: tiles are selected when their top-left (row,col) is inside the source/range.
      With --include_overlap: tiles are also selected when their span intersects the source/range
      (span uses rowSpan/colSpan; missing span defaults to 1x1).

  Insert/Delete range filters (limit which tiles are affected):
    --col_range <start_col> <end_col>     (only with --insert_rows and --delete_rows)
    --row_range <start_row> <end_row>     (only with --insert_cols and --delete_cols)

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

  Tile id assignment when copying/merging:
      New tile ids are assigned sequentially starting at:
        1 + max(highest existing tile id, highest tile id referenced in customCSS)
      This prevents newly created tiles from accidentally reusing ids that still have orphan CSS rules.


FORMATTING

  --indent N               Pretty JSON indent spaces per nesting level (N can be 0; default: 2)
  --minify                 Compact one-line JSON (overrides --indent)
  --newline keep|lf|crlf   Normalize output newlines


DIAGNOSTICS

  --quiet                  Suppress the final one-line summary
  --verbose                Planned actions summary to STDERR
  --debug                  Per-tile action logs to STDERR

"""


class TileSorterArgumentParser(argparse.ArgumentParser):
    def format_help(self) -> str:
        # Default help is slim; use --help_full for the expanded help text.
        return SHORT_HELP + "\n"

    def error(self, message: str) -> None:
        # Keep argparse-style errors, but add a hint.
        self.print_usage(sys.stderr)
        self.exit(2, f"ERROR: {message}\nUse -h for help.\n")



class HelpFullAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        print(FULL_HELP)
        raise SystemExit(0)

def build_parser() -> argparse.ArgumentParser:
    p = TileSorterArgumentParser(
        add_help=True,
        allow_abbrev=False,
        # Keep argparse usage line short; help text above provides full documentation.
        usage="hubitat_tile_mover.py [options]",
    )

    p.add_argument("--help_full", action=HelpFullAction, nargs=0, help=argparse.SUPPRESS)

    # Keep argument groups for internal structure (even though custom help is printed).
    io_grp = p.add_argument_group("Import / Output")
    io_grp.add_argument(
        "--import",
        dest="import_spec",
        nargs="+",
        metavar=("KIND", "PATH"),
        default=None,
        help=argparse.SUPPRESS,
    )
    io_grp.add_argument(
        "--output_to",
        "--output-to",
        action="append",
        nargs="+",
        metavar=("DEST", "ARG"),
        default=None,
        help=argparse.SUPPRESS,
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

    fmt_grp = p.add_argument_group("JSON Formatting")
    fmt_grp.add_argument("--indent", type=int, default=2, help=argparse.SUPPRESS)
    fmt_grp.add_argument("--minify", action="store_true", help=argparse.SUPPRESS)
    fmt_grp.add_argument("--newline", choices=["keep", "lf", "crlf"], default="keep", help=argparse.SUPPRESS)

    ops_grp = p.add_argument_group("Operations")
    ops = ops_grp.add_mutually_exclusive_group(required=False)

    ops.add_argument("--insert_rows", "--insert-rows", nargs=2, metavar=("COUNT", "AT_ROW"), type=int, help=argparse.SUPPRESS)
    ops.add_argument("--insert_cols", "--insert-cols", "--insert_columns", "--insert-columns",
                     nargs=2, metavar=("COUNT", "AT_COL"), type=int, help=argparse.SUPPRESS)

    ops.add_argument("--move_cols", "--move-cols", "--move_columns", "--move-columns",
                     nargs=3, metavar=("START_COL", "END_COL", "DEST_START_COL"), type=int, help=argparse.SUPPRESS)
    ops.add_argument("--move_rows", "--move-rows",
                     nargs=3, metavar=("START_ROW", "END_ROW", "DEST_START_ROW"), type=int, help=argparse.SUPPRESS)
    ops.add_argument("--move_range", "--move-range",
                     nargs=6, metavar=("SRC_TOP_ROW", "SRC_LEFT_COL", "SRC_BOTTOM_ROW", "SRC_RIGHT_COL", "DEST_TOP_ROW", "DEST_LEFT_COL"),
                     type=int, help=argparse.SUPPRESS)

    ops.add_argument("--copy_cols", "--copy-cols",
                     nargs=3, metavar=("START_COL", "END_COL", "DEST_START_COL"), type=int, help=argparse.SUPPRESS)
    ops.add_argument("--copy_rows", "--copy-rows",
                     nargs=3, metavar=("START_ROW", "END_ROW", "DEST_START_ROW"), type=int, help=argparse.SUPPRESS)
    ops.add_argument("--copy_range", "--copy-range",
                     nargs=6, metavar=("SRC_TOP_ROW", "SRC_LEFT_COL", "SRC_BOTTOM_ROW", "SRC_RIGHT_COL", "DEST_TOP_ROW", "DEST_LEFT_COL"),
                     type=int, help=argparse.SUPPRESS)

    ops.add_argument("--merge_cols", "--merge-cols",
                     nargs=3, metavar=("START_COL", "END_COL", "DEST_START_COL"), type=int, help=argparse.SUPPRESS)
    ops.add_argument("--merge_rows", "--merge-rows",
                     nargs=3, metavar=("START_ROW", "END_ROW", "DEST_START_ROW"), type=int, help=argparse.SUPPRESS)
    ops.add_argument("--merge_range", "--merge-range",
                     nargs=6, metavar=("SRC_TOP_ROW", "SRC_LEFT_COL", "SRC_BOTTOM_ROW", "SRC_RIGHT_COL", "DEST_TOP_ROW", "DEST_LEFT_COL"),
                     type=int, help=argparse.SUPPRESS)

    ops.add_argument("--delete_rows", "--delete-rows", nargs=2, metavar=("START_ROW", "END_ROW"), type=int, help=argparse.SUPPRESS)
    ops.add_argument("--delete_cols", "--delete-cols", "--delete_columns", "--delete-columns",
                     nargs=2, metavar=("START_COL", "END_COL"), type=int, help=argparse.SUPPRESS)

    ops.add_argument("--clear_rows", "--clear-rows", nargs=2, metavar=("START_ROW", "END_ROW"), type=int, help=argparse.SUPPRESS)
    ops.add_argument("--clear_cols", "--clear-cols", "--clear_columns", "--clear-columns",
                     nargs=2, metavar=("START_COL", "END_COL"), type=int, help=argparse.SUPPRESS)
    ops.add_argument("--clear_range", "--clear-range", nargs=4, metavar=("TOP_ROW", "LEFT_COL", "BOTTOM_ROW", "RIGHT_COL"), type=int, help=argparse.SUPPRESS)

    ops.add_argument("--crop_to_rows", "--crop-to-rows", nargs=2, metavar=("START_ROW", "END_ROW"), type=int, help=argparse.SUPPRESS)
    ops.add_argument("--crop_to_cols", "--crop-to-cols", "--crop_to_columns", "--crop-to-columns",
                     nargs=2, metavar=("START_COL", "END_COL"), type=int, help=argparse.SUPPRESS)
    ops.add_argument("--crop_to_range", "--crop-to-range", nargs=4, metavar=("TOP_ROW", "LEFT_COL", "BOTTOM_ROW", "RIGHT_COL"), type=int, help=argparse.SUPPRESS)

    ops.add_argument("--prune_except_ids", "--prune-except-ids", metavar="ID1,ID2,...", type=str, help=argparse.SUPPRESS)
    ops.add_argument("--prune_except_devices", "--prune-except-devices", metavar="DEV1,DEV2,...", type=str, help=argparse.SUPPRESS)


    ops_grp.add_argument("--merge_source", "--merge-source", default=None, help=argparse.SUPPRESS)

    filters_grp = p.add_argument_group("Filters")
    filters_grp.add_argument("--include_overlap", "--include-overlap", action="store_true", help=argparse.SUPPRESS)
    filters_grp.add_argument("--col_range", "--col-range", nargs=2, metavar=("COL_START", "COL_END"), type=int, help=argparse.SUPPRESS)
    filters_grp.add_argument("--row_range", "--row-range", nargs=2, metavar=("ROW_START", "ROW_END"), type=int, help=argparse.SUPPRESS)

    overlap_grp = p.add_argument_group("Overlap Policy")
    conflict = overlap_grp.add_mutually_exclusive_group(required=False)
    conflict.add_argument("--allow_overlap", "--allow-overlap", action="store_true", help=argparse.SUPPRESS)
    conflict.add_argument("--skip_overlap", "--skip-overlap", action="store_true", help=argparse.SUPPRESS)

    safety_grp = p.add_argument_group("Safety")
    safety_grp.add_argument("--force", action="store_true", help=argparse.SUPPRESS)

    trim_sort_grp = p.add_argument_group("Trim / Sort")
    trim_sort_grp.add_argument("--trim", nargs="?", const="both", default=None, metavar="MODE", help=argparse.SUPPRESS)
    trim_sort_grp.add_argument("--trim_left", "--trim-left", action="store_true", help=argparse.SUPPRESS)
    trim_sort_grp.add_argument("--trim_top", "--trim-top", action="store_true", help=argparse.SUPPRESS)

    # --sort[:SPEC] (single switch). We keep legacy --order hidden.
    trim_sort_grp.add_argument("--sort", nargs="?", const="irc", default=None, metavar="SPEC", help=argparse.SUPPRESS)
    trim_sort_grp.add_argument("--order", default=None, help=argparse.SUPPRESS)

    css_grp = p.add_argument_group("CSS")
    css_grp.add_argument("--cleanup_css", "--cleanup-css", action="store_true", help=argparse.SUPPRESS)
    css_grp.add_argument("--ignore_css", "--create-css", action="store_true", help=argparse.SUPPRESS)
    css_grp.add_argument("--scrub_css", "--scrub-css", action="store_true", help=argparse.SUPPRESS)

    diag_grp = p.add_argument_group("Diagnostics")
    diag_grp.add_argument("--verbose", action="store_true", help=argparse.SUPPRESS)
    diag_grp.add_argument("--debug", action="store_true", help=argparse.SUPPRESS)
    diag_grp.add_argument("--quiet", action="store_true", help=argparse.SUPPRESS)

    return p
