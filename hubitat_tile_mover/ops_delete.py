from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .geometry import ranges_overlap
from .selectors import (
    find_straddlers_cols,
    find_straddlers_rows,
    tile_matches_col_range,
    tile_matches_row_range,
)
from .tiles import as_int, set_int_like, tile_col_extent, tile_row_extent, rect
from .map_view import render_tile_map
from .util import dlog, format_id_sample, prompt_yes_no_or_die, vlog
from .util import die as _die


def delete_rows(
    tiles: List[Dict[str, Any]],
    *,
    start_row: int,
    end_row: int,
    include_overlap: bool,
    col_range: Optional[Tuple[int, int]],
    force: bool,
    verbose: bool,
    debug: bool,
    show_map: bool = False,
    map_focus: str = 'full',
) -> List[int]:
    if start_row <= 0 or end_row <= 0:
        _die("--delete_rows values must be positive (1-based).")
    if start_row > end_row:
        start_row, end_row = end_row, start_row

    delete_count = end_row - start_row + 1

    selected: List[Dict[str, Any]] = []
    for t in tiles:
        if not tile_matches_col_range(t, col_range, include_overlap):
            continue

        if include_overlap:
            r1, r2 = tile_row_extent(t)
            if ranges_overlap(r1, r2, start_row, end_row):
                selected.append(t)
        else:
            r0 = as_int(t, "row")
            if start_row <= r0 <= end_row:
                selected.append(t)

    selected_ids = [as_int(t, "id") for t in selected]
    if selected:
        details_lines = [
            f"WARNING: --delete_rows {start_row}..{end_row} will delete {len(selected)} tile(s).",
            f"IDs: {format_id_sample(selected_ids)}",
        ]
        friendly = f"There are {len(selected)} tiles in rows {start_row}–{end_row}."
        friendly += " Are you sure you want to delete these tiles?"

        if show_map:
            import sys as _sys
            mark_rects = [rect(t) for t in selected]
            bounds_rects = mark_rects if map_focus == "conflict" else None
            print(
                render_tile_map(
                    tiles,
                    title="BEFORE MAP (TO BE REMOVED)",
                    mark_rects=mark_rects,
                    bounds_rects=bounds_rects,
                    no_scale=(map_focus == 'no_scale'),
                ),
                end="",
                file=_sys.stderr,
            )

        prompt_yes_no_or_die(
            force,
            friendly,
            what="tiles",
            details="\n".join(details_lines),
            show_details=(verbose or debug),
        )

    selected_obj_ids = {id(t) for t in selected}
    before = len(tiles)
    tiles[:] = [t for t in tiles if id(t) not in selected_obj_ids]
    after = len(tiles)
    vlog(verbose, f"[delete_rows] deleted {before - after} tile(s); shifting remaining tiles")

    for t in tiles:
        if not tile_matches_col_range(t, col_range, include_overlap):
            continue

        tid = as_int(t, "id")
        r0 = as_int(t, "row")
        if r0 > end_row:
            r1 = r0 - delete_count
            if r1 < 1:
                _die(f"delete_rows shift would move tile id={tid} to invalid row {r1}")
            set_int_like(t, "row", r1)
            dlog(debug, f"[delete_rows] id={tid}: row {r0} -> {r1}")

    return selected_ids

def delete_cols(
    tiles: List[Dict[str, Any]],
    *,
    start_col: int,
    end_col: int,
    include_overlap: bool,
    row_range: Optional[Tuple[int, int]],
    force: bool,
    verbose: bool,
    debug: bool,
    show_map: bool = False,
    map_focus: str = 'full',
) -> List[int]:
    if start_col <= 0 or end_col <= 0:
        _die("--delete_cols values must be positive (1-based).")
    if start_col > end_col:
        start_col, end_col = end_col, start_col

    delete_count = end_col - start_col + 1

    selected: List[Dict[str, Any]] = []
    for t in tiles:
        if not tile_matches_row_range(t, row_range, include_overlap):
            continue

        if include_overlap:
            c1, c2 = tile_col_extent(t)
            if ranges_overlap(c1, c2, start_col, end_col):
                selected.append(t)
        else:
            c0 = as_int(t, "col")
            if start_col <= c0 <= end_col:
                selected.append(t)

    selected_ids = [as_int(t, "id") for t in selected]
    if selected:
        details_lines = [
            f"WARNING: --delete_cols {start_col}..{end_col} will delete {len(selected)} tile(s).",
            f"IDs: {format_id_sample(selected_ids)}",
        ]
        friendly = f"There are {len(selected)} tiles in columns {start_col}–{end_col}."
        friendly += " Are you sure you want to delete these tiles?"

        if show_map:
            import sys as _sys
            mark_rects = [rect(t) for t in selected]
            bounds_rects = mark_rects if map_focus == "conflict" else None
            print(
                render_tile_map(
                    tiles,
                    title="BEFORE MAP (TO BE REMOVED)",
                    mark_rects=mark_rects,
                    bounds_rects=bounds_rects,
                    no_scale=(map_focus == 'no_scale'),
                ),
                end="",
                file=_sys.stderr,
            )

        prompt_yes_no_or_die(
            force,
            friendly,
            what="tiles",
            details="\n".join(details_lines),
            show_details=(verbose or debug),
        )

    selected_obj_ids = {id(t) for t in selected}
    before = len(tiles)
    tiles[:] = [t for t in tiles if id(t) not in selected_obj_ids]
    after = len(tiles)
    vlog(verbose, f"[delete_cols] deleted {before - after} tile(s); shifting remaining tiles")

    for t in tiles:
        if not tile_matches_row_range(t, row_range, include_overlap):
            continue

        tid = as_int(t, "id")
        c0 = as_int(t, "col")
        if c0 > end_col:
            c1 = c0 - delete_count
            if c1 < 1:
                _die(f"delete_cols shift would move tile id={tid} to invalid col {c1}")
            set_int_like(t, "col", c1)
            dlog(debug, f"[delete_cols] id={tid}: col {c0} -> {c1}")

    return selected_ids

