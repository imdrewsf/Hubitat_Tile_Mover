from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .selectors import tile_matches_col_range, tile_matches_row_range
from .tiles import as_int, set_int_like, tile_col_extent, tile_row_extent
from .util import die, dlog


def insert_rows(
    tiles: List[Dict[str, Any]],
    *,
    count: int,
    at_row: int,
    include_overlap: bool,
    col_range: Optional[Tuple[int, int]],
    debug: bool,
) -> None:
    if count <= 0:
        die(f"--insert_rows COUNT must be > 0, got {count}")
    if at_row <= 0:
        die(f"--insert_rows AT_ROW must be > 0, got {at_row}")

    for t in tiles:
        tid = as_int(t, "id")

        if not tile_matches_col_range(t, col_range, include_overlap):
            dlog(debug, f"[insert_rows] id={tid}: skip (col_range)")
            continue

        row0 = as_int(t, "row")

        reason = None
        if row0 >= at_row:
            reason = "start>=AT"
        elif include_overlap:
            r1, r2 = tile_row_extent(t)
            if r1 < at_row <= r2:
                reason = f"overlap ({r1}-{r2} crosses AT)"

        if reason is None:
            dlog(debug, f"[insert_rows] id={tid}: no shift (row={row0})")
            continue

        row1 = row0 + count
        if row1 < 1:
            die(f"insert_rows would move tile id={tid} to invalid row {row1}")
        set_int_like(t, "row", row1)
        dlog(debug, f"[insert_rows] id={tid}: row {row0} -> {row1} ({reason})")


def insert_cols(
    tiles: List[Dict[str, Any]],
    *,
    count: int,
    at_col: int,
    include_overlap: bool,
    row_range: Optional[Tuple[int, int]],
    debug: bool,
) -> None:
    if count <= 0:
        die(f"--insert_cols COUNT must be > 0, got {count}")
    if at_col <= 0:
        die(f"--insert_cols AT_COL must be > 0, got {at_col}")

    for t in tiles:
        tid = as_int(t, "id")

        if not tile_matches_row_range(t, row_range, include_overlap):
            dlog(debug, f"[insert_cols] id={tid}: skip (row_range)")
            continue

        col0 = as_int(t, "col")

        reason = None
        if col0 >= at_col:
            reason = "start>=AT"
        elif include_overlap:
            c1, c2 = tile_col_extent(t)
            if c1 < at_col <= c2:
                reason = f"overlap ({c1}-{c2} crosses AT)"

        if reason is None:
            dlog(debug, f"[insert_cols] id={tid}: no shift (col={col0})")
            continue

        col1 = col0 + count
        if col1 < 1:
            die(f"insert_cols would move tile id={tid} to invalid col {col1}")
        set_int_like(t, "col", col1)
        dlog(debug, f"[insert_cols] id={tid}: col {col0} -> {col1} ({reason})")
