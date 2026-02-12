from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .geometry import ranges_overlap, rects_overlap
from .tiles import as_int, rect, tile_col_extent, tile_row_extent


def tile_matches_row_range(tile: Dict[str, Any], row_range: Optional[Tuple[int, int]], include_overlap: bool) -> bool:
    if row_range is None:
        return True
    r1, r2 = row_range
    if include_overlap:
        tr1, tr2 = tile_row_extent(tile)
        return ranges_overlap(tr1, tr2, r1, r2)
    return r1 <= as_int(tile, "row") <= r2


def tile_matches_col_range(tile: Dict[str, Any], col_range: Optional[Tuple[int, int]], include_overlap: bool) -> bool:
    if col_range is None:
        return True
    c1, c2 = col_range
    if include_overlap:
        tc1, tc2 = tile_col_extent(tile)
        return ranges_overlap(tc1, tc2, c1, c2)
    return c1 <= as_int(tile, "col") <= c2


def select_tiles_by_row_range(
    tiles: List[Dict[str, Any]],
    start_row: int,
    end_row: int,
    include_overlap: bool,
) -> List[Dict[str, Any]]:
    selected: List[Dict[str, Any]] = []
    for t in tiles:
        if include_overlap:
            r1, r2 = tile_row_extent(t)
            if ranges_overlap(r1, r2, start_row, end_row):
                selected.append(t)
        else:
            r0 = as_int(t, "row")
            if start_row <= r0 <= end_row:
                selected.append(t)
    return selected


def select_tiles_by_col_range(
    tiles: List[Dict[str, Any]],
    start_col: int,
    end_col: int,
    include_overlap: bool,
) -> List[Dict[str, Any]]:
    selected: List[Dict[str, Any]] = []
    for t in tiles:
        if include_overlap:
            c1, c2 = tile_col_extent(t)
            if ranges_overlap(c1, c2, start_col, end_col):
                selected.append(t)
        else:
            c0 = as_int(t, "col")
            if start_col <= c0 <= end_col:
                selected.append(t)
    return selected


def select_tiles_by_rect_range(
    tiles: List[Dict[str, Any]],
    top_row: int,
    left_col: int,
    bottom_row: int,
    right_col: int,
    include_overlap: bool,
) -> List[Dict[str, Any]]:
    src_rect = (top_row, bottom_row, left_col, right_col)
    selected: List[Dict[str, Any]] = []
    for t in tiles:
        if include_overlap:
            if rects_overlap(rect(t), src_rect):
                selected.append(t)
        else:
            r0 = as_int(t, "row")
            c0 = as_int(t, "col")
            if top_row <= r0 <= bottom_row and left_col <= c0 <= right_col:
                selected.append(t)
    return selected


def find_straddlers_rows(tiles: List[Dict[str, Any]], start_row: int, end_row: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for t in tiles:
        r0 = as_int(t, "row")
        r1, r2 = tile_row_extent(t)
        if ranges_overlap(r1, r2, start_row, end_row) and not (start_row <= r0 <= end_row):
            out.append(t)
    return out


def find_straddlers_cols(tiles: List[Dict[str, Any]], start_col: int, end_col: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for t in tiles:
        c0 = as_int(t, "col")
        c1, c2 = tile_col_extent(t)
        if ranges_overlap(c1, c2, start_col, end_col) and not (start_col <= c0 <= end_col):
            out.append(t)
    return out
