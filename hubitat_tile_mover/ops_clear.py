from __future__ import annotations

from typing import Any, Dict, List

from .selectors import (
    select_tiles_by_col_range,
    select_tiles_by_rect_range,
    select_tiles_by_row_range,
)
from .tiles import as_int, rect
from .map_view import render_tile_map
from .util import format_id_sample, prompt_yes_no_or_die, vlog


def _maybe_show_remove_map(tiles: List[Dict[str, Any]], selected: List[Dict[str, Any]], *, show_map: bool, map_focus: str) -> None:
    if not show_map or not selected:
        return
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


def clear_rows(
    tiles: List[Dict[str, Any]],
    *,
    start_row: int,
    end_row: int,
    include_overlap: bool,
    force: bool,
    verbose: bool,
    debug: bool,
    show_map: bool = False,
    map_focus: str = "full",
) -> List[int]:
    if start_row > end_row:
        start_row, end_row = end_row, start_row

    selected = select_tiles_by_row_range(tiles, start_row, end_row, include_overlap=include_overlap)
    selected_ids = [as_int(t, "id") for t in selected]

    if selected:
        _maybe_show_remove_map(tiles, selected, show_map=show_map, map_focus=map_focus)
        prompt_yes_no_or_die(
            force,
            f"There are {len(selected)} tiles in rows {start_row}–{end_row}. Are you sure you want to remove them?",
            what="tiles",
            details=f"WARNING: --clear_rows {start_row}..{end_row} will remove {len(selected)} tile(s). IDs: {format_id_sample(selected_ids)}",
            show_details=(verbose or debug),
        )

    sel_obj_ids = {id(t) for t in selected}
    before = len(tiles)
    tiles[:] = [t for t in tiles if id(t) not in sel_obj_ids]
    vlog(verbose, f"[clear_rows] removed {before - len(tiles)} tile(s)")
    return selected_ids


def clear_cols(
    tiles: List[Dict[str, Any]],
    *,
    start_col: int,
    end_col: int,
    include_overlap: bool,
    force: bool,
    verbose: bool,
    debug: bool,
    show_map: bool = False,
    map_focus: str = "full",
) -> List[int]:
    if start_col > end_col:
        start_col, end_col = end_col, start_col

    selected = select_tiles_by_col_range(tiles, start_col, end_col, include_overlap=include_overlap)
    selected_ids = [as_int(t, "id") for t in selected]

    if selected:
        _maybe_show_remove_map(tiles, selected, show_map=show_map, map_focus=map_focus)
        prompt_yes_no_or_die(
            force,
            f"There are {len(selected)} tiles in columns {start_col}–{end_col}. Are you sure you want to remove them?",
            what="tiles",
            details=f"WARNING: --clear_cols {start_col}..{end_col} will remove {len(selected)} tile(s). IDs: {format_id_sample(selected_ids)}",
            show_details=(verbose or debug),
        )

    sel_obj_ids = {id(t) for t in selected}
    before = len(tiles)
    tiles[:] = [t for t in tiles if id(t) not in sel_obj_ids]
    vlog(verbose, f"[clear_cols] removed {before - len(tiles)} tile(s)")
    return selected_ids


def clear_range(
    tiles: List[Dict[str, Any]],
    *,
    top_row: int,
    left_col: int,
    bottom_row: int,
    right_col: int,
    include_overlap: bool,
    force: bool,
    verbose: bool,
    debug: bool,
    show_map: bool = False,
    map_focus: str = "full",
) -> List[int]:
    tr, br = (top_row, bottom_row) if top_row <= bottom_row else (bottom_row, top_row)
    lc, rc = (left_col, right_col) if left_col <= right_col else (right_col, left_col)

    selected = select_tiles_by_rect_range(tiles, tr, lc, br, rc, include_overlap=include_overlap)
    selected_ids = [as_int(t, "id") for t in selected]

    if selected:
        _maybe_show_remove_map(tiles, selected, show_map=show_map, map_focus=map_focus)
        prompt_yes_no_or_die(
            force,
            f"There are {len(selected)} tiles in range ({tr},{lc})–({br},{rc}). Are you sure you want to remove them?",
            what="tiles",
            details=f"WARNING: --clear_range {tr},{lc}..{br},{rc} will remove {len(selected)} tile(s). IDs: {format_id_sample(selected_ids)}",
            show_details=(verbose or debug),
        )

    sel_obj_ids = {id(t) for t in selected}
    before = len(tiles)
    tiles[:] = [t for t in tiles if id(t) not in sel_obj_ids]
    vlog(verbose, f"[clear_range] removed {before - len(tiles)} tile(s)")
    return selected_ids
