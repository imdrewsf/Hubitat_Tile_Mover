from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple, Set

from .tiles import rect, as_int
from .util import _use_color

Rect = Tuple[int, int, int, int]  # (r1, r2, c1, c2) inclusive


def _bounds_from_rects(rects: Sequence[Rect]) -> Optional[Rect]:
    if not rects:
        return None
    r1 = min(r[0] for r in rects)
    r2 = max(r[1] for r in rects)
    c1 = min(r[2] for r in rects)
    c2 = max(r[3] for r in rects)
    return (r1, r2, c1, c2)


def _expand_bounds(b: Rect, pad: int = 1) -> Rect:
    r1, r2, c1, c2 = b
    r1 = max(1, r1 - pad)
    c1 = max(1, c1 - pad)
    return (r1, r2 + pad, c1, c2 + pad)


def _c(code: str, s: str) -> str:
    if not _use_color():
        return s
    return f"\x1b[{code}m{s}\x1b[0m"


def render_tile_map(
    tiles: List[Dict[str, Any]],
    *,
    title: str,
    width: int = 80,
    height: int = 25,
    changed_ids: Optional[Set[int]] = None,
    focus_rects: Optional[List[Rect]] = None,
    bounds_rects: Optional[Sequence[Rect]] = None,
    highlight_rects: Optional[Sequence[Rect]] = None,
    mark_rects: Optional[Sequence[Rect]] = None,
    mark_color: str = 'orange',
    focus_color: str = 'red',
    no_scale: bool = False,
) -> str:
    """
    Render a small ASCII minimap of tiles to stderr-friendly text.

    Symbols:
      - empty: '·'
      - tile fill: '█'
    Colors:
      - unchanged tiles: gray
      - changed tiles:   green
      - conflict focus:  red (overlays)
    """
    changed_ids = changed_ids or set()

    tile_rects: List[Rect] = [rect(t) for t in tiles]
    if not tile_rects:
        return f"{title}\n(no tiles)\n"

    bounds = _bounds_from_rects(list(bounds_rects)) if bounds_rects is not None else _bounds_from_rects(tile_rects)
    if bounds is None:
        bounds = _bounds_from_rects(tile_rects)
    assert bounds is not None
    # In the default scaled minimap, add a small pad for readability.
    # In no-scale mode, the map is intended to match layout dimensions
    # (1 character per dashboard row/col), so do not pad.
    bounds = _expand_bounds(bounds, pad=0 if no_scale else 1)

    br1, br2, bc1, bc2 = bounds
    rows = max(1, br2 - br1 + 1)
    cols = max(1, bc2 - bc1 + 1)

    if no_scale:
        # 1 row/col == 1 character (not counting the border)
        w = max(1, cols)
        h = max(1, rows)
    else:
        w = max(20, width)
        h = max(8, height)

    # 0 empty, 1 unchanged, 2 green (changed/highlight), 3 conflict overlay, 4 mark overlay (e.g., to-be-deleted)
    grid = [[0 for _ in range(w)] for _ in range(h)]

    def to_xy(r: int, c: int) -> Tuple[int, int]:
        if no_scale:
            # Direct grid coordinates (1:1)
            return (r - br1, c - bc1)
        x = int((c - bc1) * (w - 1) / max(1, cols - 1))
        y = int((r - br1) * (h - 1) / max(1, rows - 1))
        return (y, x)

    # Draw tiles
    for t in tiles:
        tid = as_int(t, "id")
        r1, r2, c1, c2 = rect(t)
        r1 = max(r1, br1); r2 = min(r2, br2)
        c1 = max(c1, bc1); c2 = min(c2, bc2)
        if r2 < r1 or c2 < c1:
            continue
        y1, x1 = to_xy(r1, c1)
        y2, x2 = to_xy(r2, c2)
        state = 2 if tid in changed_ids else 1
        for y in range(min(y1, y2), max(y1, y2) + 1):
            for x in range(min(x1, x2), max(x1, x2) + 1):
                # If we already have a tile of different state in the same cell, keep "changed" as higher priority.
                if grid[y][x] == 0:
                    grid[y][x] = state
                elif grid[y][x] == 1 and state == 2:
                    grid[y][x] = 2

    # Overlay highlight rects in green (e.g., moved/copied tiles in outcome/conflict maps)
    if highlight_rects:
        for hr in highlight_rects:
            r1, r2, c1, c2 = hr
            r1 = max(r1, br1); r2 = min(r2, br2)
            c1 = max(c1, bc1); c2 = min(c2, bc2)
            if r2 < r1 or c2 < c1:
                continue
            y1, x1 = to_xy(r1, c1)
            y2, x2 = to_xy(r2, c2)
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for x in range(min(x1, x2), max(x1, x2) + 1):
                    if grid[y][x] != 3:  # don't override conflicts
                        grid[y][x] = 2


    # Overlay mark rects (e.g., tiles to be deleted/cleared) in orange by default
    if mark_rects:
        for mr in mark_rects:
            r1, r2, c1, c2 = mr
            r1 = max(r1, br1); r2 = min(r2, br2)
            c1 = max(c1, bc1); c2 = min(c2, bc2)
            if r2 < r1 or c2 < c1:
                continue
            y1, x1 = to_xy(r1, c1)
            y2, x2 = to_xy(r2, c2)
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for x in range(min(x1, x2), max(x1, x2) + 1):
                    if grid[y][x] != 3:  # don't override conflicts
                        grid[y][x] = 4

    # Overlay focus/conflict rects in red
    if focus_rects:
        for fr in focus_rects:
            r1, r2, c1, c2 = fr
            r1 = max(r1, br1); r2 = min(r2, br2)
            c1 = max(c1, bc1); c2 = min(c2, bc2)
            if r2 < r1 or c2 < c1:
                continue
            y1, x1 = to_xy(r1, c1)
            y2, x2 = to_xy(r2, c2)
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for x in range(min(x1, x2), max(x1, x2) + 1):
                    grid[y][x] = 3

    # Build lines with light box border
    top = "┌" + ("─" * w) + "┐"
    bot = "└" + ("─" * w) + "┘"

    def cell_char(v: int) -> str:
        if v == 0:
            return "·"
        if v == 1:
            return _c("90", "█")  # gray
        if v == 2:
            return _c("32;1", "█")  # green
        if v == 4:
            return _c("38;5;208;1", "█") if mark_color == 'orange' else _c("33;1", "█")
        return _c("33;1", "█") if focus_color == 'yellow' else _c("31;1", "█")  # conflict

    header = (
        f"{title}\n"
        f"Bounds: rows {br1}..{br2}, cols {bc1}..{bc2} | tiles: {len(tiles)}\n"
        f"Legend: {_c('90','█')} tile  {_c('32;1','█')} changed  "
        f"{(_c('38;5;208;1','█') + ' affected  ') if mark_rects else ''}"
        f"{(_c('33;1','█') if focus_color=='yellow' else _c('31;1','█'))} conflict  · empty\n"
    )
    body_lines = [top]
    for row in grid:
        body_lines.append("│" + "".join(cell_char(v) for v in row) + "│")
    body_lines.append(bot)
    return header + "\n".join(body_lines) + "\n"


def conflict_rects_from_details(conflicts: Dict[int, List[Tuple[int, Rect]]]) -> List[Rect]:
    rects: List[Rect] = []
    for _, entries in conflicts.items():
        for _, orect in entries:
            rects.append(orect)
    return rects
