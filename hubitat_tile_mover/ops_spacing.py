from __future__ import annotations

from typing import Any, Dict, List, Tuple, DefaultDict
from collections import defaultdict

from .tiles import as_int, set_int_like

Rect = Tuple[int, int, int, int]  # inclusive (top,bottom,left,right)


def _tile_rect(t: Dict[str, Any]) -> Rect:
    r0 = as_int(t, "row")
    c0 = as_int(t, "col")
    rs = int(t.get("rowSpan", 1) or 1)
    cs = int(t.get("colSpan", 1) or 1)
    return (r0, r0 + rs - 1, c0, c0 + cs - 1)


def _rects_overlap(a: Rect, b: Rect) -> bool:
    return not (a[1] < b[0] or b[1] < a[0] or a[3] < b[2] or b[3] < a[2])


def _group_same_origin(tiles: List[Dict[str, Any]]) -> List[List[int]]:
    groups: DefaultDict[Tuple[int, int], List[int]] = defaultdict(list)
    for i, t in enumerate(tiles):
        groups[(as_int(t, "row"), as_int(t, "col"))].append(i)
    return list(groups.values())


def _group_overlaps(tiles: List[Dict[str, Any]]) -> List[List[int]]:
    rects = [_tile_rect(t) for t in tiles]
    n = len(rects)
    seen = [False] * n
    out: List[List[int]] = []
    for i in range(n):
        if seen[i]:
            continue
        stack = [i]
        seen[i] = True
        comp: List[int] = []
        while stack:
            k = stack.pop()
            comp.append(k)
            rk = rects[k]
            for j in range(n):
                if seen[j]:
                    continue
                if _rects_overlap(rk, rects[j]):
                    seen[j] = True
                    stack.append(j)
        out.append(sorted(comp))
    return out


def _unit_rect(tiles: List[Dict[str, Any]], idxs: List[int]) -> Rect:
    rects = [_tile_rect(tiles[i]) for i in idxs]
    return (min(r[0] for r in rects), max(r[1] for r in rects), min(r[2] for r in rects), max(r[3] for r in rects))


def _components_1d(intervals: List[Tuple[int, int]]) -> List[List[int]]:
    """Connected components of overlapping inclusive intervals. Returns lists of indices."""
    order = sorted(range(len(intervals)), key=lambda i: (intervals[i][0], intervals[i][1], i))
    comps: List[List[int]] = []
    cur: List[int] = []
    cur_end = None
    for i in order:
        a, b = intervals[i]
        if cur_end is None:
            cur = [i]
            cur_end = b
            continue
        if a <= cur_end:
            cur.append(i)
            cur_end = max(cur_end, b)
        else:
            comps.append(cur)
            cur = [i]
            cur_end = b
    if cur_end is not None:
        comps.append(cur)
    return comps


def _axis_map_from_intervals(starts: List[int], end_by_start: Dict[int, int], cells: int) -> Dict[int, int]:
    """Map old_start -> new_start using overlap-components of [start..end_by_start[start]].

    For each component:
      - component base = min start
      - component end = max end_by_start[s] within component
      - preserve relative offsets among start lines in the component

    Components are placed in order using:
        old_gap = next_base - prev_end - 1
        new_gap = max(0, old_gap + cells)
        next_new_base = prev_new_end + 1 + new_gap
    """
    if not starts:
        return {}
    if len(starts) == 1:
        return {starts[0]: starts[0]}

    intervals = [(s, end_by_start[s]) for s in starts]
    comps = _components_1d(intervals)
    comp_starts = [[starts[i] for i in comp] for comp in comps]

    comp_info = []
    for ss in comp_starts:
        base = min(ss)
        offsets = {s: s - base for s in ss}
        end = max(end_by_start[s] for s in ss)
        comp_info.append((base, end, ss, offsets))
    comp_info.sort(key=lambda x: x[0])

    base_map: Dict[int, int] = {}
    base0, end0, _, _ = comp_info[0]
    base_map[base0] = base0
    prev_old_end = end0
    prev_new_end = end0

    for base, end, ss, offsets in comp_info[1:]:
        old_gap = base - prev_old_end - 1
        new_gap = max(0, old_gap + cells)
        new_base = prev_new_end + 1 + new_gap
        base_map[base] = new_base

        span = end - base
        prev_old_end = end
        prev_new_end = new_base + span

    out: Dict[int, int] = {}
    for base, end, ss, offsets in comp_info:
        nb = base_map[base]
        for s in ss:
            out[s] = nb + offsets[s]
    return out




def _axis_map_set_from_intervals(starts: List[int], end_by_start: Dict[int, int], gap: int) -> Dict[int, int]:
    """Map old_start -> new_start like _axis_map_from_intervals, but set spacing to a fixed gap.

    Components are defined the same way (overlap-components of [start..end_by_start[start]]).
    Between consecutive components:
        new_gap = gap
        next_new_base = prev_new_end + 1 + new_gap

    gap must be >= 0.
    """
    if gap < 0:
        raise ValueError(f"gap must be >= 0, got: {gap}")
    if not starts:
        return {}
    if len(starts) == 1:
        return {starts[0]: starts[0]}

    intervals = [(s, end_by_start[s]) for s in starts]
    comps = _components_1d(intervals)
    comp_starts = [[starts[i] for i in comp] for comp in comps]

    comp_info = []
    for ss in comp_starts:
        base = min(ss)
        offsets = {s: s - base for s in ss}
        end = max(end_by_start[s] for s in ss)
        comp_info.append((base, end, ss, offsets))
    comp_info.sort(key=lambda x: x[0])

    base_map: Dict[int, int] = {}
    base0, end0, _, _ = comp_info[0]
    base_map[base0] = base0
    prev_new_end = end0

    for base, end, ss, offsets in comp_info[1:]:
        new_base = prev_new_end + 1 + gap
        base_map[base] = new_base
        span = end - base
        prev_new_end = new_base + span

    out: Dict[int, int] = {}
    for base, end, ss, offsets in comp_info:
        nb = base_map[base]
        for s in ss:
            out[s] = nb + offsets[s]
    return out

def _components_by_x(urects: List[Rect]) -> List[List[int]]:
    """Components of units by 1D overlap of X intervals."""
    x_ints = [(r[2], r[3]) for r in urects]
    return _components_1d(x_ints)


def _components_by_y(urects: List[Rect]) -> List[List[int]]:
    """Components of units by 1D overlap of Y intervals."""
    y_ints = [(r[0], r[1]) for r in urects]
    return _components_1d(y_ints)


def adjust_tile_spacing(
    tiles: List[Dict[str, Any]],
    cells: int,
    *,
    include_overlap: bool,
    mode: str = "all",
    no_overlap: bool = False,
) -> None:
    """Add/subtract spacing between tiles (or overlap unions) by CELLS.

    This is the additive counterpart to set_tile_spacing():

        desired_gap = max(0, old_gap + cells)

    where old_gap is the current number of blank grid cells between two units along the operated axis.

    Overlap behavior matches spacing_set:
      - Default: overlapping tiles are grouped into overlap unions (units).
      - --overlaps:remove: treat every tile as its own unit (fully un-overlap globally).
      - legacy --include_overlap (without --overlaps:remove): apply adjustment *within* each original overlap union
        (same-origin grouped), then pack the unions relative to each other because union extents change.

    Notes:
      - CELLS may be negative; gaps are clamped at 0 so spacing never becomes negative.
      - mode is rows|cols|all.
    """
    if not tiles or cells == 0:
        return

    mode = (mode or "all").lower()
    if mode not in ("rows", "cols", "all"):
        raise ValueError(f"invalid spacing mode: {mode!r}")

    def pack_units_add(units: List[List[int]]) -> None:
        """Pack using *additive* per-pair gaps derived from current geometry."""

        def urects() -> List[Rect]:
            return [_unit_rect(tiles, idxs) for idxs in units]

        def apply_row_pack() -> bool:
            rs0 = urects()  # baseline for old_gap calculations
            order = sorted(range(len(rs0)), key=lambda i: (rs0[i][0], rs0[i][2], i))
            placed: List[Rect] = [None] * len(rs0)  # type: ignore
            new_top: Dict[int, int] = {}
            moved = False

            for idx in order:
                t, b, l, r = rs0[idx]
                h = b - t
                req_top = None
                for j in order:
                    if j == idx:
                        break
                    pj = placed[j]
                    if pj is None:
                        continue
                    tj, bj, lj, rj = pj
                    # Only constrain if overlapping in X
                    if r < lj or rj < l:
                        continue
                    # old gap from baseline geometry (may be 0+)
                    old_gap = t - rs0[j][1] - 1
                    desired_gap = max(0, old_gap + cells)
                    cand = bj + 1 + desired_gap
                    if req_top is None or cand > req_top:
                        req_top = cand
                nt = t if req_top is None else req_top
                if nt != t:
                    moved = True
                nb = nt + h
                placed[idx] = (nt, nb, l, r)
                new_top[idx] = nt

            if not moved:
                return False

            # Apply shifts as rigid body per unit
            for ui, idxs in enumerate(units):
                t0 = rs0[ui][0]
                nt = new_top.get(ui, t0)
                dr = nt - t0
                if dr:
                    for ti in idxs:
                        set_int_like(tiles[ti], "row", as_int(tiles[ti], "row") + dr)
            return True

        def apply_col_pack() -> bool:
            rs0 = urects()
            order = sorted(range(len(rs0)), key=lambda i: (rs0[i][2], rs0[i][0], i))
            placed: List[Rect] = [None] * len(rs0)  # type: ignore
            new_left: Dict[int, int] = {}
            moved = False

            for idx in order:
                t, b, l, r = rs0[idx]
                w = r - l
                req_left = None
                for j in order:
                    if j == idx:
                        break
                    pj = placed[j]
                    if pj is None:
                        continue
                    tj, bj, lj, rj = pj
                    # Only constrain if overlapping in Y
                    if b < tj or bj < t:
                        continue
                    old_gap = l - rs0[j][3] - 1
                    desired_gap = max(0, old_gap + cells)
                    cand = rj + 1 + desired_gap
                    if req_left is None or cand > req_left:
                        req_left = cand
                nl = l if req_left is None else req_left
                if nl != l:
                    moved = True
                nr = nl + w
                placed[idx] = (t, b, nl, nr)
                new_left[idx] = nl

            if not moved:
                return False

            for ui, idxs in enumerate(units):
                l0 = rs0[ui][2]
                nl = new_left.get(ui, l0)
                dc = nl - l0
                if dc:
                    for ti in idxs:
                        set_int_like(tiles[ti], "col", as_int(tiles[ti], "col") + dc)
            return True

        if mode == "rows":
            apply_row_pack()
            return
        if mode == "cols":
            apply_col_pack()
            return

        # mode == all: iterate to settle interactions between axes
        for _ in range(10):
            changed = False
            if apply_row_pack():
                changed = True
            if apply_col_pack():
                changed = True
            if not changed:
                break

    def atomic_units_for(indices: List[int]) -> List[List[int]]:
        # group same-origin inside subset
        groups: DefaultDict[Tuple[int, int], List[int]] = defaultdict(list)
        for ti in indices:
            t = tiles[ti]
            groups[(as_int(t, "row"), as_int(t, "col"))].append(ti)
        units_local: List[List[int]] = []
        used = set()
        for g in groups.values():
            if len(g) > 1:
                units_local.append(sorted(g))
                used.update(g)
        for ti in indices:
            if ti not in used:
                units_local.append([ti])
        return units_local

    overlap_unions = _group_overlaps(tiles)

    # Case 1: global un-overlap (mutually exclusive with include_overlap via main sanity check)
    if no_overlap:
        pack_units_add([[ti] for ti in range(len(tiles))])
        return

    # Case 2: unions as units
    if not include_overlap:
        pack_units_add(overlap_unions)
        return

    # Case 3: include_overlap=True -> adjust within unions then pack unions
    for union in overlap_unions:
        if len(union) <= 1:
            continue
        pack_units_add(atomic_units_for(union))

    pack_units_add(overlap_unions)
def set_tile_spacing(
    tiles: List[Dict[str, Any]],
    gap: int,
    *,
    include_overlap: bool,
    mode: str = "all",
    no_overlap: bool = False,
) -> None:
    """Set spacing between tiles (or overlap unions) to a fixed number of blank cells.

    Behavior summary:

    - Default (no --include_overlap):
        Overlapping tiles are grouped into overlap unions; spacing is enforced between unions.

    - With legacy --include_overlap AND --overlaps:remove:
        Legacy behavior (preserved): overlapping tiles are treated as individual tiles (except same-origin
        tiles are grouped) and spacing is enforced between all tiles, effectively "unoverlapping" globally.

    - With legacy --include_overlap (and WITHOUT --overlaps:remove):
        New behavior: spacing is applied *inside* each original overlap union only (except same-origin grouping),
        and the union's bounding box may grow/shrink. Then unions are packed relative to each other so external
        spacing constraints are still respected as unions change size.

    Parameters:
      gap: number of empty grid cells to leave between units (must be >= 0).
      mode: 'rows', 'cols', or 'all'.
    """
    if not tiles:
        return
    if gap < 0:
        raise ValueError(f"gap must be >= 0, got: {gap}")

    mode = (mode or "all").lower()
    if mode not in ("rows", "cols", "all"):
        raise ValueError(f"invalid spacing mode: {mode!r}")

    def pack_units(units: List[List[int]]) -> None:
        """Pack using current tile positions; shifts entire units as rigid bodies."""

        def urects() -> List[Rect]:
            return [_unit_rect(tiles, idxs) for idxs in units]

        def apply_row_pack() -> bool:
            rs = urects()
            order = sorted(range(len(rs)), key=lambda i: (rs[i][0], rs[i][2], i))
            placed: List[Rect] = [None] * len(rs)  # type: ignore
            new_top: Dict[int, int] = {}
            moved = False
            for idx in order:
                t, b, l, r = rs[idx]
                h = b - t
                req_top = None
                for j in order:
                    if j == idx:
                        break
                    pj = placed[j]
                    if pj is None:
                        continue
                    tj, bj, lj, rj = pj
                    if r < lj or rj < l:
                        continue
                    cand = bj + 1 + gap
                    if req_top is None or cand > req_top:
                        req_top = cand
                nt = t if req_top is None else req_top
                if nt != t:
                    moved = True
                nb = nt + h
                placed[idx] = (nt, nb, l, r)
                new_top[idx] = nt
            if not moved:
                return False
            for ui, idxs in enumerate(units):
                t0 = rs[ui][0]
                nt = new_top.get(ui, t0)
                dr = nt - t0
                if dr:
                    for ti in idxs:
                        set_int_like(tiles[ti], "row", as_int(tiles[ti], "row") + dr)
            return True

        def apply_col_pack() -> bool:
            rs = urects()
            order = sorted(range(len(rs)), key=lambda i: (rs[i][2], rs[i][0], i))
            placed: List[Rect] = [None] * len(rs)  # type: ignore
            new_left: Dict[int, int] = {}
            moved = False
            for idx in order:
                t, b, l, r = rs[idx]
                w = r - l
                req_left = None
                for j in order:
                    if j == idx:
                        break
                    pj = placed[j]
                    if pj is None:
                        continue
                    tj, bj, lj, rj = pj
                    if b < tj or bj < t:
                        continue
                    cand = rj + 1 + gap
                    if req_left is None or cand > req_left:
                        req_left = cand
                nl = l if req_left is None else req_left
                if nl != l:
                    moved = True
                nr = nl + w
                placed[idx] = (t, b, nl, nr)
                new_left[idx] = nl
            if not moved:
                return False
            for ui, idxs in enumerate(units):
                l0 = rs[ui][2]
                nl = new_left.get(ui, l0)
                dc = nl - l0
                if dc:
                    for ti in idxs:
                        set_int_like(tiles[ti], "col", as_int(tiles[ti], "col") + dc)
            return True

        if mode == "rows":
            apply_row_pack()
            return
        if mode == "cols":
            apply_col_pack()
            return
        for _ in range(10):
            changed = False
            if apply_row_pack():
                changed = True
            if apply_col_pack():
                changed = True
            if not changed:
                break

    def atomic_units_for(indices: List[int]) -> List[List[int]]:
        """Like include_overlap=True grouping, but restricted to a subset of tile indices."""
        # group same-origin inside subset
        groups: DefaultDict[Tuple[int, int], List[int]] = defaultdict(list)
        for ti in indices:
            t = tiles[ti]
            groups[(as_int(t, "row"), as_int(t, "col"))].append(ti)
        units_local: List[List[int]] = []
        used = set()
        for g in groups.values():
            if len(g) > 1:
                units_local.append(sorted(g))
                used.update(g)
        for ti in indices:
            if ti not in used:
                units_local.append([ti])
        return units_local

    # --- Determine overlap unions from the ORIGINAL geometry (before we modify anything) ---
    # Note: we must preserve these unions even after internal unoverlap, so we compute them once.
    overlap_unions = _group_overlaps(tiles)

    # Case 1: legacy global unoverlap
    if no_overlap:
        # Unoverlap EVERYTHING (including same-origin tiles) and set spacing globally.
        pack_units([[ti] for ti in range(len(tiles))])
        return

    # Case 2: include_overlap=False -> unions as units
    if not include_overlap:
        pack_units(overlap_unions)
        return

    # Case 3: include_overlap=True and no_overlap=False
    # Step A: adjust spacing *within* each original overlap union using atomic units (same-origin preserved).
    for union in overlap_unions:
        if len(union) <= 1:
            continue
        pack_units(atomic_units_for(union))

    # Step B: pack the unions relative to each other (as rigid bodies) using their NEW extents.
    pack_units(overlap_unions)
