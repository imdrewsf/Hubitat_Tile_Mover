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
    show_ids: bool = False,
    show_axes: str = 'none',
) -> str:
    """
    Render a small ASCII minimap of tiles to stderr-friendly text.
    """
    changed_ids = changed_ids or set()

    tile_rects: List[Rect] = [rect(t) for t in tiles]
    if not tile_rects:
        return f"{title}\n(no tiles)\n"

    bounds = _bounds_from_rects(list(bounds_rects)) if bounds_rects is not None else _bounds_from_rects(tile_rects)
    if bounds is None:
        bounds = _bounds_from_rects(tile_rects)
    assert bounds is not None
    bounds = _expand_bounds(bounds, pad=0 if no_scale else 1)

    br1, br2, bc1, bc2 = bounds
    rows = max(1, br2 - br1 + 1)
    cols = max(1, bc2 - bc1 + 1)

    if no_scale:
        h = rows
        w = cols
    else:
        w = max(10, width - 2)
        h = max(5, height - 2)

    def to_xy(r: int, c: int) -> Tuple[int, int]:
        if no_scale:
            return (r - br1, c - bc1)
        y = round((r - br1) * (h - 1) / max(1, rows - 1))
        x = round((c - bc1) * (w - 1) / max(1, cols - 1))
        return (y, x)

    grid: List[List[int]] = [[0 for _ in range(w)] for _ in range(h)]

    for t in tiles:
        tid = None
        try:
            tid = as_int(t, 'id')
        except Exception:
            tid = None
        r1, r2, c1, c2 = rect(t)
        r1, r2 = max(r1, br1), min(r2, br2)
        c1, c2 = max(c1, bc1), min(c2, bc2)
        if r2 < r1 or c2 < c1:
            continue
        y1, x1 = to_xy(r1, c1)
        y2, x2 = to_xy(r2, c2)
        val = 2 if (tid is not None and tid in changed_ids) else 1
        for y in range(min(y1, y2), max(y1, y2) + 1):
            for x in range(min(x1, x2), max(x1, x2) + 1):
                if 0 <= y < h and 0 <= x < w:
                    if val > grid[y][x]:
                        grid[y][x] = val

    if highlight_rects:
        for rr in highlight_rects:
            r1, r2, c1, c2 = rr
            r1, r2 = max(r1, br1), min(r2, br2)
            c1, c2 = max(c1, bc1), min(c2, bc2)
            if r2 < r1 or c2 < c1:
                continue
            y1, x1 = to_xy(r1, c1)
            y2, x2 = to_xy(r2, c2)
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for x in range(min(x1, x2), max(x1, x2) + 1):
                    if 0 <= y < h and 0 <= x < w:
                        grid[y][x] = max(grid[y][x], 2)

    if focus_rects:
        for rr in focus_rects:
            r1, r2, c1, c2 = rr
            r1, r2 = max(r1, br1), min(r2, br2)
            c1, c2 = max(c1, bc1), min(c2, bc2)
            if r2 < r1 or c2 < c1:
                continue
            y1, x1 = to_xy(r1, c1)
            y2, x2 = to_xy(r2, c2)
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for x in range(min(x1, x2), max(x1, x2) + 1):
                    if 0 <= y < h and 0 <= x < w:
                        grid[y][x] = 3

    if mark_rects:
        for rr in mark_rects:
            r1, r2, c1, c2 = rr
            r1, r2 = max(r1, br1), min(r2, br2)
            c1, c2 = max(c1, bc1), min(c2, bc2)
            if r2 < r1 or c2 < c1:
                continue
            y1, x1 = to_xy(r1, c1)
            y2, x2 = to_xy(r2, c2)
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for x in range(min(x1, x2), max(x1, x2) + 1):
                    if 0 <= y < h and 0 <= x < w:
                        grid[y][x] = 4

    top = "┌" + ("─" * w) + "┐"
    bot = "└" + ("─" * w) + "┘"

    def cell_char(v: int) -> str:
        if v == 0:
            return "·"
        if v == 1:
            return _c("90", "█")
        if v == 2:
            return _c("32;1", "█")
        if v == 4:
            return _c("38;5;208;1", "█") if mark_color == 'orange' else _c("33;1", "█")
        return _c("33;1", "█") if focus_color == 'yellow' else _c("31;1", "█")

    def _group_name(idx: int) -> str:
        idx += 1
        parts: List[str] = []
        while idx > 0:
            idx, rem = divmod(idx - 1, 26)
            parts.append(chr(ord('A') + rem))
        return ''.join(reversed(parts))

    header = (
        f"{title}\n"
        f"Bounds: rows {br1}..{br2}, cols {bc1}..{bc2} | tiles: {len(tiles)}\n"
        f"Legend: {_c('90','█')} tile  {_c('32;1','█')} changed  "
        f"{(_c('38;5;208;1','█') + ' affected  ') if mark_rects else ''}"
        f"{(_c('33;1','█') if focus_color=='yellow' else _c('31;1','█'))} conflict  · empty"
        f"{'  ids shown' if show_ids else ''}"
        f"{'  axis=' + show_axes if show_axes != 'none' else ''}\n"
    )

    overlays_by_row: Dict[int, List[Dict[str, Any]]] = {}
    group_lines: List[str] = []
    if show_ids:
        placements: List[Dict[str, Any]] = []
        for t in tiles:
            tid = t.get('id')
            if tid is None:
                continue
            r1, r2, c1, c2 = rect(t)
            r1 = max(r1, br1)
            r2 = min(r2, br2)
            c1 = max(c1, bc1)
            c2 = min(c2, bc2)
            if r2 < r1 or c2 < c1:
                continue
            y1, x1 = to_xy(r1, c1)
            y2, x2 = to_xy(r2, c2)
            ymin, ymax = min(y1, y2), max(y1, y2)
            xmin, xmax = min(x1, x2), max(x1, x2)
            label = str(tid)
            row = (ymin + ymax) // 2
            center_x = (xmin + xmax) // 2
            start = center_x - (len(label) // 2)
            start = max(0, min(start, max(0, w - len(label))))
            placements.append({'tile_id': int(tid), 'label': label, 'row': row, 'start': start, 'end': start + len(label) - 1, 'center_x': center_x})

        parents = list(range(len(placements)))

        def find(i: int) -> int:
            while parents[i] != i:
                parents[i] = parents[parents[i]]
                i = parents[i]
            return i

        def union(a: int, b: int) -> None:
            ra = find(a)
            rb = find(b)
            if ra != rb:
                parents[rb] = ra

        for i in range(len(placements)):
            pi = placements[i]
            for j in range(i + 1, len(placements)):
                pj = placements[j]
                if pi['row'] != pj['row']:
                    continue
                if pi['end'] < pj['start'] or pj['end'] < pi['start']:
                    continue
                union(i, j)

        clusters: Dict[int, List[int]] = {}
        for i in range(len(placements)):
            clusters.setdefault(find(i), []).append(i)

        group_counter = 0
        for _, members in sorted(clusters.items(), key=lambda kv: min(placements[i]['row'] for i in kv[1])):
            if len(members) == 1:
                p0 = placements[members[0]]
                overlays_by_row.setdefault(p0['row'], []).append({'start': p0['start'], 'text': p0['label'], 'bold': False})
                continue
            tag = _group_name(group_counter)
            group_counter += 1
            member_tiles = sorted(placements[i]['tile_id'] for i in members)
            center_x = sum(placements[i]['center_x'] for i in members) // len(members)
            start = center_x - (len(tag) // 2)
            start = max(0, min(start, max(0, w - len(tag))))
            row = min(placements[i]['row'] for i in members)
            overlays_by_row.setdefault(row, []).append({'start': start, 'text': tag, 'bold': True})
            group_lines.append(f"  {tag}: " + ", ".join(f"tile-{tid}" for tid in member_tiles))
        for row_items in overlays_by_row.values():
            row_items.sort(key=lambda item: (item['start'], len(item['text'])))

    def axis_col_value(x: int) -> int:
        if no_scale:
            return bc1 + x
        return bc1 + int(round(x * max(1, cols - 1) / max(1, w - 1)))

    def axis_row_value(y: int) -> int:
        if no_scale:
            return br1 + y
        return br1 + int(round(y * max(1, rows - 1) / max(1, h - 1)))

    show_row_axes = show_axes in ('row', 'all')
    show_col_axes = show_axes in ('col', 'all')
    row_label_width = max(len(str(br1)), len(str(br2))) if show_row_axes else 0

    body_lines: List[str] = []
    if show_col_axes:
        prefix = (' ' * row_label_width + ' ') if show_row_axes else ''
        axis = [' ' for _ in range(w)]
        step = 1 if no_scale else max(1, cols // 8)
        last_end = -999
        for x in range(w):
            value = axis_col_value(x)
            if x not in (0, w - 1) and ((value - bc1) % step != 0):
                continue
            txt = str(value)
            start = max(0, min(x - (len(txt) // 2), w - len(txt)))
            if start <= last_end and x not in (0, w - 1):
                continue
            for i, ch in enumerate(txt):
                axis[start + i] = ch
            last_end = start + len(txt) - 1
        body_lines.append(prefix + ' ' + ''.join(axis))

    top_line = top
    if show_row_axes:
        top_line = (' ' * row_label_width) + ' ' + top_line
    body_lines.append(top_line)
    for y, row in enumerate(grid):
        cells = [cell_char(v) for v in row]
        if show_ids:
            occupied = [False] * w
            for item in overlays_by_row.get(y, []):
                text = item['text']
                bold = bool(item.get('bold', False))
                start = int(item['start'])
                if start < 0:
                    text = text[-start:]
                    start = 0
                if start >= w or not text:
                    continue
                if start + len(text) > w:
                    text = text[: w - start]
                for idx, ch in enumerate(text):
                    pos = start + idx
                    if occupied[pos]:
                        continue
                    cells[pos] = _c('1', ch) if bold else ch
                    occupied[pos] = True
        line = '│' + ''.join(cells) + '│'
        if show_row_axes:
            line = str(axis_row_value(y)).rjust(row_label_width) + ' ' + line
        body_lines.append(line)
    bot_line = bot
    if show_row_axes:
        bot_line = (' ' * row_label_width) + ' ' + bot_line
    body_lines.append(bot_line)
    if group_lines:
        body_lines.append('Groups:')
        body_lines.extend(group_lines)
    return header + '\n'.join(body_lines) + '\n'


def conflict_rects_from_details(conflicts: Dict[int, List[Tuple[int, Rect]]]) -> List[Rect]:
    rects: List[Rect] = []
    for _, entries in conflicts.items():
        for _, orect in entries:
            rects.append(orect)
    return rects
