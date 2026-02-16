from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Set, Tuple

from .jsonio import extract_tiles_container, load_json_from_text
from .ops_move import scan_move_conflicts
from .selectors import select_tiles_by_col_range, select_tiles_by_rect_range, select_tiles_by_row_range
from .tiles import as_int, rect, set_int_like, verify_tiles_minimum
from .util import die, dlog, vlog
from .map_view import render_tile_map, conflict_rects_from_details


def _load_merge_tiles_from_file(path: str) -> List[Dict[str, Any]]:
    if not path:
        die("--merge_source requires a filename.")
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        die(f"Merge source file not found: {path}")
    except OSError as e:
        die(f"Unable to read merge source file: {e}")

    obj = load_json_from_text(raw)
    _, _, tiles_any = extract_tiles_container(obj)
    verify_tiles_minimum(tiles_any)
    return tiles_any  # type: ignore[return-value]


def _next_id_state(dest_tiles: List[Dict[str, Any]], *, reserved_ids: Optional[Set[int]] = None) -> Tuple[Set[int], int]:
    used: Set[int] = {as_int(t, "id") for t in dest_tiles}
    if reserved_ids:
        used |= {int(x) for x in reserved_ids}
    next_id = (max(used) + 1) if used else 1
    return used, next_id


def _ensure_unique_id(tile: Dict[str, Any], used: Set[int], next_id: int, debug: bool, label: str) -> int:
    src_id = as_int(tile, "id")
    if src_id not in used:
        used.add(src_id)
        return next_id

    new_id = next_id
    set_int_like(tile, "id", new_id)
    used.add(new_id)
    dlog(debug, f"[{label}] id conflict/reserved: source id={src_id} -> reassigned id={new_id}")
    return next_id + 1


def _conflict_scan_and_append(
    dest_tiles: List[Dict[str, Any]],
    *,
    copies: List[Dict[str, Any]],
    allow_overlap: bool,
    skip_overlap: bool,
    show_map: bool,
    map_focus: str = 'full',
    verbose: bool,
    debug: bool,
    label: str,
) -> Set[int]:
    stationary = dest_tiles  # tiles present before merge

    def moved_rect(t: Dict[str, Any]):
        return rect(t)

    conflicts_by_mid, total_pairs = scan_move_conflicts(copies, stationary, moved_rect)
    if conflicts_by_mid:
        vlog(verbose, f"[{label}] conflicts detected: {len(conflicts_by_mid)} merged tile(s), {total_pairs} overlap pair(s)")

    if conflicts_by_mid and not allow_overlap and not skip_overlap:
        sample = list(conflicts_by_mid.items())[:10]
        details = "; ".join([f"merge id={mid} conflicts at r{entries[0][1][0]}..{entries[0][1][1]},c{entries[0][1][2]}..{entries[0][1][3]} with {[sid for sid,_ in entries]}" for mid, entries in sample])
        more = "" if len(conflicts_by_mid) <= 10 else f" (and {len(conflicts_by_mid) - 10} more)"
        if show_map:
            focus = conflict_rects_from_details(conflicts_by_mid)
            try:
                focus_arg = focus if map_focus == 'conflict' else None
                tiles_for_map = dest_tiles if map_focus == 'full' else (stationary + copies)
                # Conflict map: gray=stationary, green=moving/copied (non-conflict), red=conflict
                tiles_for_map = stationary
                hi_rects = [rect(t) for t in copies]
                bounds_rects = [rect(t) for t in dest_tiles] if map_focus == 'full' else (focus if map_focus == 'conflict' else None)
                print(render_tile_map(tiles_for_map, title='CONFLICT MAP', focus_rects=focus, bounds_rects=bounds_rects, highlight_rects=hi_rects), end='')
            except Exception:
                pass
        die(f"Destination conflicts detected. Re-run with --allow_overlap or --skip_overlap. {details}{more}")

    appended_ids: Set[int] = set()
    added = 0
    for ct in copies:
        tid = as_int(ct, "id")
        if conflicts_by_mid.get(tid) and skip_overlap and not allow_overlap:
            dlog(debug, f"[{label}] id={tid}: SKIP MERGE (conflicts with {conflicts_by_mid[tid]})")
            continue
        dest_tiles.append(ct)
        appended_ids.add(tid)
        added += 1

    vlog(verbose, f"[{label}] appended {added} merged tile(s)")
    return appended_ids


def merge_cols(
    dest_tiles: List[Dict[str, Any]],
    *,
    merge_source_path: str,
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
    reserved_ids: Optional[Set[int]] = None,
) -> Dict[int, int]:
    if start_col <= 0 or end_col <= 0 or dest_start_col <= 0:
        die("--merge_cols values must be positive (1-based).")
    if start_col > end_col:
        start_col, end_col = end_col, start_col

    delta = dest_start_col - start_col
    src_tiles = _load_merge_tiles_from_file(merge_source_path)

    selected = select_tiles_by_col_range(src_tiles, start_col, end_col, include_overlap=include_overlap)
    vlog(verbose, f"[merge_cols] selected {len(selected)} tile(s) from merge_source (include_overlap={include_overlap})")

    used_ids, next_id = _next_id_state(dest_tiles, reserved_ids=reserved_ids)

    id_map: Dict[int, int] = {}
    moving: List[Dict[str, Any]] = []

    for t in selected:
        src_id = as_int(t, "id")
        ct = copy.deepcopy(t)
        next_id = _ensure_unique_id(ct, used_ids, next_id, debug, "merge")
        tid = as_int(ct, "id")
        id_map[src_id] = tid

        c0 = as_int(ct, "col")
        c1 = c0 + delta
        if c1 < 1:
            die(f"merge_cols would move copied tile id={tid} to invalid col {c1}")
        set_int_like(ct, "col", c1)
        moving.append(ct)
        dlog(debug, f"[merge_cols] copy id={tid}: col {c0} -> {c1}")

    appended_ids = _conflict_scan_and_append(
        dest_tiles,
        copies=moving,
        allow_overlap=allow_overlap,
        skip_overlap=skip_overlap,
        verbose=verbose,
        debug=debug,
        label="merge_cols",
        show_map=show_map,
        map_focus=map_focus,
    )

    return {k: v for k, v in id_map.items() if v in appended_ids}


def merge_rows(
    dest_tiles: List[Dict[str, Any]],
    *,
    merge_source_path: str,
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
    reserved_ids: Optional[Set[int]] = None,
) -> Dict[int, int]:
    if start_row <= 0 or end_row <= 0 or dest_start_row <= 0:
        die("--merge_rows values must be positive (1-based).")
    if start_row > end_row:
        start_row, end_row = end_row, start_row

    delta = dest_start_row - start_row
    src_tiles = _load_merge_tiles_from_file(merge_source_path)

    selected = select_tiles_by_row_range(src_tiles, start_row, end_row, include_overlap=include_overlap)
    vlog(verbose, f"[merge_rows] selected {len(selected)} tile(s) from merge_source (include_overlap={include_overlap})")

    used_ids, next_id = _next_id_state(dest_tiles, reserved_ids=reserved_ids)

    id_map: Dict[int, int] = {}
    moving: List[Dict[str, Any]] = []

    for t in selected:
        src_id = as_int(t, "id")
        ct = copy.deepcopy(t)
        next_id = _ensure_unique_id(ct, used_ids, next_id, debug, "merge")
        tid = as_int(ct, "id")
        id_map[src_id] = tid

        r0 = as_int(ct, "row")
        r1 = r0 + delta
        if r1 < 1:
            die(f"merge_rows would move copied tile id={tid} to invalid row {r1}")
        set_int_like(ct, "row", r1)
        moving.append(ct)
        dlog(debug, f"[merge_rows] copy id={tid}: row {r0} -> {r1}")

    appended_ids = _conflict_scan_and_append(
        dest_tiles,
        copies=moving,
        allow_overlap=allow_overlap,
        skip_overlap=skip_overlap,
        verbose=verbose,
        debug=debug,
        label="merge_rows",
        show_map=show_map,
        map_focus=map_focus,
    )

    return {k: v for k, v in id_map.items() if v in appended_ids}


def merge_range(
    dest_tiles: List[Dict[str, Any]],
    *,
    merge_source_path: str,
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
    reserved_ids: Optional[Set[int]] = None,
) -> Dict[int, int]:
    if min(src_top_row, src_left_col, src_bottom_row, src_right_col, dest_top_row, dest_left_col) <= 0:
        die("--merge_range values must be positive (1-based).")

    top_row, bottom_row = (src_top_row, src_bottom_row) if src_top_row <= src_bottom_row else (src_bottom_row, src_top_row)
    left_col, right_col = (src_left_col, src_right_col) if src_left_col <= src_right_col else (src_right_col, src_left_col)

    delta_r = dest_top_row - top_row
    delta_c = dest_left_col - left_col

    src_tiles = _load_merge_tiles_from_file(merge_source_path)

    selected = select_tiles_by_rect_range(
        src_tiles,
        top_row=top_row,
        left_col=left_col,
        bottom_row=bottom_row,
        right_col=right_col,
        include_overlap=include_overlap,
    )
    vlog(verbose, f"[merge_range] selected {len(selected)} tile(s) from merge_source (include_overlap={include_overlap})")

    used_ids, next_id = _next_id_state(dest_tiles, reserved_ids=reserved_ids)

    id_map: Dict[int, int] = {}
    moving: List[Dict[str, Any]] = []

    for t in selected:
        src_id = as_int(t, "id")
        ct = copy.deepcopy(t)
        next_id = _ensure_unique_id(ct, used_ids, next_id, debug, "merge")
        tid = as_int(ct, "id")
        id_map[src_id] = tid

        r0 = as_int(ct, "row")
        c0 = as_int(ct, "col")
        r1 = r0 + delta_r
        c1 = c0 + delta_c
        if r1 < 1 or c1 < 1:
            die(f"merge_range would move copied tile id={tid} to invalid position row={r1}, col={c1}")
        set_int_like(ct, "row", r1)
        set_int_like(ct, "col", c1)
        moving.append(ct)
        dlog(debug, f"[merge_range] copy id={tid}: (row,col) ({r0},{c0}) -> ({r1},{c1})")

    appended_ids = _conflict_scan_and_append(
        dest_tiles,
        copies=moving,
        allow_overlap=allow_overlap,
        skip_overlap=skip_overlap,
        verbose=verbose,
        debug=debug,
        label="merge_range",
        show_map=show_map,
        map_focus=map_focus,
    )

    return {k: v for k, v in id_map.items() if v in appended_ids}
