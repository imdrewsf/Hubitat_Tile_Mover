from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .selectors import tile_matches_col_range, tile_matches_row_range
from .tiles import as_int, set_int_like, tile_col_extent, tile_row_extent, rect
from .ops_move import scan_move_conflicts
from .map_view import render_tile_map
from .util import die, dlog


def insert_rows(
    tiles: List[Dict[str, Any]],
    *,
    count: int,
    at_row: int,
    include_overlap: bool,
    col_range: Optional[Tuple[int, int]],
    allow_overlap: bool = False,
    debug: bool = False,
    show_map: bool = False,
    map_focus: str = 'full',
    show_ids: bool = False,
    show_axes: str = 'none',
) -> None:
    if count <= 0:
        die(f"--insert_rows COUNT must be > 0, got {count}")
    if at_row <= 0:
        die(f"--insert_rows AT_ROW must be > 0, got {at_row}")

    shifting: List[Dict[str, Any]] = []
    stationary: List[Dict[str, Any]] = []

    for t in tiles:
        tid = as_int(t, "id")

        if not tile_matches_col_range(t, col_range, include_overlap):
            stationary.append(t)
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
            stationary.append(t)
            dlog(debug, f"[insert_rows] id={tid}: no shift (row={row0})")
            continue

        shifting.append(t)

    def shifted_rect_rows(t: Dict[str, Any]) -> Tuple[int, int, int, int]:
        r1, r2, c1, c2 = rect(t)
        return (r1 + count, r2 + count, c1, c2)

    conflicts_by_mid, _total_pairs = scan_move_conflicts(shifting, stationary, shifted_rect_rows)
    if conflicts_by_mid and not allow_overlap:
        sample = list(conflicts_by_mid.items())[:10]
        details = '; '.join([f"shift id={mid} conflicts at r{entries[0][1][0]}..{entries[0][1][1]},c{entries[0][1][2]}..{entries[0][1][3]} with {[sid for sid,_ in entries]}" for mid, entries in sample])
        more = "" if len(conflicts_by_mid) <= 10 else f" (and {len(conflicts_by_mid) - 10} more)"
        if show_map:
            import sys as _sys
            focus = []
            for entries in conflicts_by_mid.values():
                for _, orect in entries:
                    focus.append(orect)
            projected = []
            projected_ids = set()
            for st in shifting:
                cp = dict(st)
                r1, r2, c1, c2 = shifted_rect_rows(st)
                cp['row'] = r1
                cp['col'] = c1
                if 'rowSpan' in cp:
                    cp['rowSpan'] = (r2 - r1 + 1)
                if 'colSpan' in cp:
                    cp['colSpan'] = (c2 - c1 + 1)
                projected.append(cp)
                try:
                    projected_ids.add(as_int(cp, 'id'))
                except Exception:
                    pass
            full_like = (map_focus == 'full' or map_focus == 'no_scale')
            bounds_rects = ([rect(t) for t in stationary] + [rect(t) for t in projected]) if full_like else (focus if map_focus == 'conflict' else None)
            print(
                render_tile_map(
                    stationary + projected,
                    title='CONFLICT MAP',
                    focus_rects=focus or None,
                    bounds_rects=bounds_rects,
                    changed_ids=projected_ids,
                    no_scale=True,
                    show_ids=show_ids,
                    show_axes=show_axes,
                ),
                end='',
                file=_sys.stderr,
            )
        die(f"Destination conflicts detected after insert_rows shift. Re-run with --overlaps:allow. {details}{more}")

    for t in shifting:
        tid = as_int(t, "id")
        row0 = as_int(t, "row")
        row1 = row0 + count
        if row1 < 1:
            die(f"insert_rows would move tile id={tid} to invalid row {row1}")
        set_int_like(t, "row", row1)
        dlog(debug, f"[insert_rows] id={tid}: row {row0} -> {row1}")


def insert_cols(
    tiles: List[Dict[str, Any]],
    *,
    count: int,
    at_col: int,
    include_overlap: bool,
    row_range: Optional[Tuple[int, int]],
    allow_overlap: bool = False,
    debug: bool = False,
    show_map: bool = False,
    map_focus: str = 'full',
    show_ids: bool = False,
    show_axes: str = 'none',
) -> None:
    if count <= 0:
        die(f"--insert_cols COUNT must be > 0, got {count}")
    if at_col <= 0:
        die(f"--insert_cols AT_COL must be > 0, got {at_col}")

    shifting: List[Dict[str, Any]] = []
    stationary: List[Dict[str, Any]] = []

    for t in tiles:
        tid = as_int(t, "id")

        if not tile_matches_row_range(t, row_range, include_overlap):
            stationary.append(t)
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
            stationary.append(t)
            dlog(debug, f"[insert_cols] id={tid}: no shift (col={col0})")
            continue

        shifting.append(t)

    def shifted_rect_cols(t: Dict[str, Any]) -> Tuple[int, int, int, int]:
        r1, r2, c1, c2 = rect(t)
        return (r1, r2, c1 + count, c2 + count)

    conflicts_by_mid, _total_pairs = scan_move_conflicts(shifting, stationary, shifted_rect_cols)
    if conflicts_by_mid and not allow_overlap:
        sample = list(conflicts_by_mid.items())[:10]
        details = '; '.join([f"shift id={mid} conflicts at r{entries[0][1][0]}..{entries[0][1][1]},c{entries[0][1][2]}..{entries[0][1][3]} with {[sid for sid,_ in entries]}" for mid, entries in sample])
        more = "" if len(conflicts_by_mid) <= 10 else f" (and {len(conflicts_by_mid) - 10} more)"
        if show_map:
            import sys as _sys
            focus = []
            for entries in conflicts_by_mid.values():
                for _, orect in entries:
                    focus.append(orect)
            projected = []
            projected_ids = set()
            for st in shifting:
                cp = dict(st)
                r1, r2, c1, c2 = shifted_rect_cols(st)
                cp['row'] = r1
                cp['col'] = c1
                if 'rowSpan' in cp:
                    cp['rowSpan'] = (r2 - r1 + 1)
                if 'colSpan' in cp:
                    cp['colSpan'] = (c2 - c1 + 1)
                projected.append(cp)
                try:
                    projected_ids.add(as_int(cp, 'id'))
                except Exception:
                    pass
            full_like = (map_focus == 'full' or map_focus == 'no_scale')
            bounds_rects = ([rect(t) for t in stationary] + [rect(t) for t in projected]) if full_like else (focus if map_focus == 'conflict' else None)
            print(
                render_tile_map(
                    stationary + projected,
                    title='CONFLICT MAP',
                    focus_rects=focus or None,
                    bounds_rects=bounds_rects,
                    changed_ids=projected_ids,
                    no_scale=True,
                    show_ids=show_ids,
                    show_axes=show_axes,
                ),
                end='',
                file=_sys.stderr,
            )
        die(f"Destination conflicts detected after insert_cols shift. Re-run with --overlaps:allow. {details}{more}")

    for t in shifting:
        tid = as_int(t, "id")
        col0 = as_int(t, "col")
        col1 = col0 + count
        if col1 < 1:
            die(f"insert_cols would move tile id={tid} to invalid col {col1}")
        set_int_like(t, "col", col1)
        dlog(debug, f"[insert_cols] id={tid}: col {col0} -> {col1}")
