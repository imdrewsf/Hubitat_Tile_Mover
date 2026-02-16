from __future__ import annotations

import sys as _sys

from typing import Any, Callable, Dict, List, Tuple

from .geometry import rects_overlap
from .selectors import select_tiles_by_col_range, select_tiles_by_row_range, select_tiles_by_rect_range
from .tiles import as_int, rect, set_int_like
from .util import die, dlog, vlog
from .map_view import render_tile_map, conflict_rects_from_details


def scan_move_conflicts(
    moving_tiles: List[Dict[str, Any]],
    stationary_tiles: List[Dict[str, Any]],
    moved_rect_fn: Callable[[Dict[str, Any]], Tuple[int, int, int, int]],
) -> Tuple[Dict[int, List[Tuple[int, Tuple[int, int, int, int]]]], int]:
    stationary_rects: List[Tuple[Dict[str, Any], Tuple[int, int, int, int]]] = [(t, rect(t)) for t in stationary_tiles]

    # conflicts[moving_id] -> list of (stationary_id, overlap_rect)
    conflicts: Dict[int, List[Tuple[int, Tuple[int, int, int, int]]]] = {}
    total_pairs = 0

    for mt in moving_tiles:
        mid = as_int(mt, "id")
        mrect = moved_rect_fn(mt)

        for st, srect in stationary_rects:
            if rects_overlap(mrect, srect):
                sid = as_int(st, "id")
                # overlap rect (inclusive)
                or1 = max(mrect[0], srect[0])
                or2 = min(mrect[1], srect[1])
                oc1 = max(mrect[2], srect[2])
                oc2 = min(mrect[3], srect[3])
                orect = (or1, or2, oc1, oc2)
                conflicts.setdefault(mid, []).append((sid, orect))
                total_pairs += 1

    return conflicts, total_pairs

def move_cols(
    tiles: List[Dict[str, Any]],
    *,
    start_col: int,
    end_col: int,
    dest_start_col: int,
    include_overlap: bool,
    allow_overlap: bool,
    skip_overlap: bool,
    show_map: bool,
    map_focus: str = 'full',
    verbose: bool,
    debug: bool,
) -> None:
    if start_col <= 0 or end_col <= 0 or dest_start_col <= 0:
        die("--move_cols values must be positive (1-based).")
    if start_col > end_col:
        start_col, end_col = end_col, start_col

    delta = dest_start_col - start_col
    vlog(verbose, f"[move_cols] normalized source={start_col}-{end_col}, dest_start={dest_start_col}, delta={delta}")

    moving = select_tiles_by_col_range(tiles, start_col, end_col, include_overlap=include_overlap)
    moving_ids = {id(t) for t in moving}
    stationary = [t for t in tiles if id(t) not in moving_ids]

    vlog(verbose, f"[move_cols] tiles selected to move: {len(moving)} (include_overlap={include_overlap})")

    def moved_rect(t: Dict[str, Any]) -> Tuple[int, int, int, int]:
        r1, r2, c1, c2 = rect(t)
        return (r1, r2, c1 + delta, c2 + delta)

    conflicts_by_mid, total_pairs = scan_move_conflicts(moving, stationary, moved_rect)

    if conflicts_by_mid:
        vlog(verbose, f"[move_cols] conflicts detected: {len(conflicts_by_mid)} moving tiles, {total_pairs} overlap pair(s)")

    if conflicts_by_mid and not allow_overlap and not skip_overlap:
        sample = list(conflicts_by_mid.items())[:10]
        details = '; '.join([f"move id={mid} conflicts at r{entries[0][1][0]}..{entries[0][1][1]},c{entries[0][1][2]}..{entries[0][1][3]} with {[sid for sid,_ in entries]}" for mid, entries in sample])
        more = "" if len(conflicts_by_mid) <= 10 else f" (and {len(conflicts_by_mid) - 10} more)"
        if show_map:
            try:
                # Conflict map (pre-flight): gray=stationary, green=moved destination footprints, red=overlap region
                focus = conflict_rects_from_details(conflicts_by_mid)
                moved_rects = [moved_rect(t) for t in moving]
                bounds_rects = None
                if map_focus == 'full':
                    bounds_rects = [rect(t) for t in stationary] + moved_rects
                elif map_focus == 'conflict':
                    bounds_rects = focus
                print(render_tile_map(stationary, title='CONFLICT MAP', focus_rects=focus, bounds_rects=bounds_rects, highlight_rects=moved_rects), end='', file=_sys.stderr)
            except Exception:
                pass
        die(f"Destination conflicts detected. Re-run with --allow_overlap or --skip_overlap. {details}{more}")

    for t in moving:
        tid = as_int(t, "id")

        if conflicts_by_mid.get(tid) and skip_overlap and not allow_overlap:
            dlog(debug, f"[move_cols] id={tid}: SKIP (conflicts with {conflicts_by_mid[tid]})")
            continue

        c0 = as_int(t, "col")
        c1 = c0 + delta
        if c1 < 1:
            die(f"move_cols would move tile id={tid} to invalid col {c1}")
        set_int_like(t, "col", c1)
        dlog(debug, f"[move_cols] id={tid}: col {c0} -> {c1}" + ("" if not conflicts_by_mid.get(tid) else " (conflict allowed)"))


def move_rows(
    tiles: List[Dict[str, Any]],
    *,
    start_row: int,
    end_row: int,
    dest_start_row: int,
    include_overlap: bool,
    allow_overlap: bool,
    skip_overlap: bool,
    show_map: bool,
    map_focus: str = 'full',
    verbose: bool,
    debug: bool,
) -> None:
    if start_row <= 0 or end_row <= 0 or dest_start_row <= 0:
        die("--move_rows values must be positive (1-based).")
    if start_row > end_row:
        start_row, end_row = end_row, start_row

    delta = dest_start_row - start_row
    vlog(verbose, f"[move_rows] normalized source={start_row}-{end_row}, dest_start={dest_start_row}, delta={delta}")

    moving = select_tiles_by_row_range(tiles, start_row, end_row, include_overlap=include_overlap)
    moving_ids = {id(t) for t in moving}
    stationary = [t for t in tiles if id(t) not in moving_ids]

    vlog(verbose, f"[move_rows] tiles selected to move: {len(moving)} (include_overlap={include_overlap})")

    def moved_rect(t: Dict[str, Any]) -> Tuple[int, int, int, int]:
        r1, r2, c1, c2 = rect(t)
        return (r1 + delta, r2 + delta, c1, c2)

    conflicts_by_mid, total_pairs = scan_move_conflicts(moving, stationary, moved_rect)

    if conflicts_by_mid:
        vlog(verbose, f"[move_rows] conflicts detected: {len(conflicts_by_mid)} moving tiles, {total_pairs} overlap pair(s)")

    if conflicts_by_mid and not allow_overlap and not skip_overlap:
        sample = list(conflicts_by_mid.items())[:10]
        details = '; '.join([f"move id={mid} conflicts at r{entries[0][1][0]}..{entries[0][1][1]},c{entries[0][1][2]}..{entries[0][1][3]} with {[sid for sid,_ in entries]}" for mid, entries in sample])
        more = "" if len(conflicts_by_mid) <= 10 else f" (and {len(conflicts_by_mid) - 10} more)"
        if show_map:
            try:
                # Conflict map (pre-flight): gray=stationary, green=moved destination footprints, red=overlap region
                focus = conflict_rects_from_details(conflicts_by_mid)
                moved_rects = [moved_rect(t) for t in moving]
                bounds_rects = None
                if map_focus == 'full':
                    bounds_rects = [rect(t) for t in stationary] + moved_rects
                elif map_focus == 'conflict':
                    bounds_rects = focus
                print(render_tile_map(stationary, title='CONFLICT MAP', focus_rects=focus, bounds_rects=bounds_rects, highlight_rects=moved_rects), end='', file=_sys.stderr)
            except Exception:
                pass
        die(f"Destination conflicts detected. Re-run with --allow_overlap or --skip_overlap. {details}{more}")

    for t in moving:
        tid = as_int(t, "id")

        if conflicts_by_mid.get(tid) and skip_overlap and not allow_overlap:
            dlog(debug, f"[move_rows] id={tid}: SKIP (conflicts with {conflicts_by_mid[tid]})")
            continue

        r0 = as_int(t, "row")
        r1 = r0 + delta
        if r1 < 1:
            die(f"move_rows would move tile id={tid} to invalid row {r1}")
        set_int_like(t, "row", r1)
        dlog(debug, f"[move_rows] id={tid}: row {r0} -> {r1}" + ("" if not conflicts_by_mid.get(tid) else " (conflict allowed)"))


def move_range(
    tiles: List[Dict[str, Any]],
    *,
    src_top_row: int,
    src_left_col: int,
    src_bottom_row: int,
    src_right_col: int,
    dest_top_row: int,
    dest_left_col: int,
    include_overlap: bool,
    allow_overlap: bool,
    skip_overlap: bool,
    show_map: bool,
    map_focus: str = 'full',
    verbose: bool,
    debug: bool,
) -> None:
    if min(src_top_row, src_left_col, src_bottom_row, src_right_col, dest_top_row, dest_left_col) <= 0:
        die("--move_range values must be positive (1-based).")

    top_row, bottom_row = (src_top_row, src_bottom_row) if src_top_row <= src_bottom_row else (src_bottom_row, src_top_row)
    left_col, right_col = (src_left_col, src_right_col) if src_left_col <= src_right_col else (src_right_col, src_left_col)

    delta_r = dest_top_row - top_row
    delta_c = dest_left_col - left_col

    vlog(
        verbose,
        f"[move_range] normalized src=({top_row},{left_col})-({bottom_row},{right_col}), "
        f"dest_top_left=({dest_top_row},{dest_left_col}), delta=(r:{delta_r}, c:{delta_c})",
    )

    moving = select_tiles_by_rect_range(
        tiles,
        top_row=top_row,
        left_col=left_col,
        bottom_row=bottom_row,
        right_col=right_col,
        include_overlap=include_overlap,
    )
    moving_ids = {id(t) for t in moving}
    stationary = [t for t in tiles if id(t) not in moving_ids]

    vlog(verbose, f"[move_range] tiles selected to move: {len(moving)} (include_overlap={include_overlap})")

    def moved_rect(t: Dict[str, Any]) -> Tuple[int, int, int, int]:
        r1, r2, c1, c2 = rect(t)
        return (r1 + delta_r, r2 + delta_r, c1 + delta_c, c2 + delta_c)

    conflicts_by_mid, total_pairs = scan_move_conflicts(moving, stationary, moved_rect)

    if conflicts_by_mid:
        vlog(verbose, f"[move_range] conflicts detected: {len(conflicts_by_mid)} moving tiles, {total_pairs} overlap pair(s)")

    if conflicts_by_mid and not allow_overlap and not skip_overlap:
        sample = list(conflicts_by_mid.items())[:10]
        details = '; '.join([f"move id={mid} conflicts at r{entries[0][1][0]}..{entries[0][1][1]},c{entries[0][1][2]}..{entries[0][1][3]} with {[sid for sid,_ in entries]}" for mid, entries in sample])
        more = "" if len(conflicts_by_mid) <= 10 else f" (and {len(conflicts_by_mid) - 10} more)"
        if show_map:
            try:
                # Conflict map (pre-flight): gray=stationary, green=moved destination footprints, red=overlap region
                focus = conflict_rects_from_details(conflicts_by_mid)
                moved_rects = [moved_rect(t) for t in moving]
                bounds_rects = None
                if map_focus == 'full':
                    bounds_rects = [rect(t) for t in stationary] + moved_rects
                elif map_focus == 'conflict':
                    bounds_rects = focus
                print(render_tile_map(stationary, title='CONFLICT MAP', focus_rects=focus, bounds_rects=bounds_rects, highlight_rects=moved_rects), end='', file=_sys.stderr)
            except Exception:
                pass
        die(f"Destination conflicts detected. Re-run with --allow_overlap or --skip_overlap. {details}{more}")

    for t in moving:
        tid = as_int(t, "id")

        if conflicts_by_mid.get(tid) and skip_overlap and not allow_overlap:
            dlog(debug, f"[move_range] id={tid}: SKIP (conflicts with {conflicts_by_mid[tid]})")
            continue

        r0 = as_int(t, "row")
        c0 = as_int(t, "col")
        r1 = r0 + delta_r
        c1 = c0 + delta_c

        if r1 < 1 or c1 < 1:
            die(f"move_range would move tile id={tid} to invalid position row={r1}, col={c1}")

        set_int_like(t, "row", r1)
        set_int_like(t, "col", c1)

        dlog(
            debug,
            f"[move_range] id={tid}: (row,col) ({r0},{c0}) -> ({r1},{c1})"
            + ("" if not conflicts_by_mid.get(tid) else " (conflict allowed)"),
        )
