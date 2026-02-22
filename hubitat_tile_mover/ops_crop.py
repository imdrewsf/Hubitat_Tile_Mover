from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple
import re

from .geometry import ranges_overlap, rects_overlap
from .tiles import as_int, rect, tile_col_extent, tile_row_extent
from .util import format_id_sample, prompt_yes_no_or_die, vlog, ilog
from .util import die as _die
from .map_view import render_tile_map


def _warn_and_prompt(
    force: bool,
    op_name: str,
    removed_tiles: list,
    removed_ids: list,
    *,
    extra_warning: str = "",
    verbose: bool,
    debug: bool,
    show_map: bool = False,
    map_focus: str = 'full',
    all_tiles: Optional[list] = None,
) -> None:
    if not removed_ids:
        return

    details_lines = [
        f"WARNING: {op_name} will remove {len(removed_ids)} tile(s). IDs: {format_id_sample(removed_ids)}"
    ]
    friendly = f"There are {len(removed_ids)} tiles that will be removed by {op_name}."
    if extra_warning:
        details_lines.append(extra_warning)
        if not (verbose or debug):
            # Keep this readable for normal users.
            friendly += " Note: some tiles overlap the kept range but do not start inside it (because --include_overlap is not set)."
    friendly += " Are you sure you want to continue?"

    if show_map and removed_tiles and all_tiles is not None:
        import sys as _sys
        mark_rects = [rect(t) for t in removed_tiles]
        bounds_rects = mark_rects if map_focus == 'conflict' else None
        print(
            render_tile_map(
                all_tiles,
                title='BEFORE MAP (TO BE REMOVED)',
                mark_rects=mark_rects,
                bounds_rects=bounds_rects,
                no_scale=(map_focus == 'no_scale'),
            ),
            end='',
            file=_sys.stderr,
        )

    prompt_yes_no_or_die(
        force,
        friendly,
        what="tiles",
        details="\n".join(details_lines),
        show_details=(verbose or debug),
    )


def crop_to_rows(
    tiles: List[Dict[str, Any]],
    *,
    start_row: int,
    end_row: int,
    include_overlap: bool,
    force: bool,
    verbose: bool,
    debug: bool,
    show_map: bool = False,
    map_focus: str = 'full',
) -> List[int]:
    if start_row <= 0 or end_row <= 0:
        _die("--crop_to_rows values must be positive (1-based).")
    if start_row > end_row:
        start_row, end_row = end_row, start_row

    keep: List[Dict[str, Any]] = []
    removed: List[Dict[str, Any]] = []

    # For warnings when include_overlap is not set: tiles that overlap but do not start inside
    straddlers: List[Dict[str, Any]] = []

    for t in tiles:
        if include_overlap:
            r1, r2 = tile_row_extent(t)
            ok = ranges_overlap(r1, r2, start_row, end_row)
        else:
            r0 = as_int(t, "row")
            ok = (start_row <= r0 <= end_row)

            # straddler warning
            r1, r2 = tile_row_extent(t)
            if ranges_overlap(r1, r2, start_row, end_row) and not ok:
                straddlers.append(t)

        (keep if ok else removed).append(t)

    if not keep:
        _die("At least one tile must remain. The crop range contains no tiles under the current selection rules.")
    removed_ids = [as_int(t, "id") for t in removed]
    extra = ""
    if (not include_overlap) and straddlers:
        sids = [as_int(t, "id") for t in straddlers]
        extra = (
            f"WARNING: {len(straddlers)} tile(s) overlap the kept rows but do not start inside them "
            f"(removed because --include_overlap not set). IDs: {format_id_sample(sids)}"
        )

    _warn_and_prompt(force, f"crop_to_rows {start_row}..{end_row}", removed, removed_ids, extra_warning=extra, verbose=verbose, debug=debug, show_map=show_map, map_focus=map_focus, all_tiles=tiles)
    tiles[:] = keep
    vlog(verbose, f"[crop_to_rows] kept {len(keep)} tile(s), removed {len(removed)} tile(s)")
    return removed_ids


def crop_to_cols(
    tiles: List[Dict[str, Any]],
    *,
    start_col: int,
    end_col: int,
    include_overlap: bool,
    force: bool,
    verbose: bool,
    debug: bool,
    show_map: bool = False,
    map_focus: str = 'full',
) -> List[int]:
    if start_col <= 0 or end_col <= 0:
        _die("--crop_to_cols values must be positive (1-based).")
    if start_col > end_col:
        start_col, end_col = end_col, start_col

    keep: List[Dict[str, Any]] = []
    removed: List[Dict[str, Any]] = []
    straddlers: List[Dict[str, Any]] = []

    for t in tiles:
        if include_overlap:
            c1, c2 = tile_col_extent(t)
            ok = ranges_overlap(c1, c2, start_col, end_col)
        else:
            c0 = as_int(t, "col")
            ok = (start_col <= c0 <= end_col)

            c1, c2 = tile_col_extent(t)
            if ranges_overlap(c1, c2, start_col, end_col) and not ok:
                straddlers.append(t)

        (keep if ok else removed).append(t)

    if not keep:
        _die("At least one tile must remain. The crop range contains no tiles under the current selection rules.")
    removed_ids = [as_int(t, "id") for t in removed]
    extra = ""
    if (not include_overlap) and straddlers:
        sids = [as_int(t, "id") for t in straddlers]
        extra = (
            f"WARNING: {len(straddlers)} tile(s) overlap the kept cols but do not start inside them "
            f"(removed because --include_overlap not set). IDs: {format_id_sample(sids)}"
        )

    _warn_and_prompt(force, f"crop_to_cols {start_col}..{end_col}", removed, removed_ids, extra_warning=extra, verbose=verbose, debug=debug, show_map=show_map, map_focus=map_focus, all_tiles=tiles)
    tiles[:] = keep
    vlog(verbose, f"[crop_to_cols] kept {len(keep)} tile(s), removed {len(removed)} tile(s)")
    return removed_ids


def crop_to_range(
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
    map_focus: str = 'full',
) -> List[int]:
    if min(top_row, left_col, bottom_row, right_col) <= 0:
        _die("--crop_to_range values must be positive (1-based).")
    if top_row > bottom_row:
        top_row, bottom_row = bottom_row, top_row
    if left_col > right_col:
        left_col, right_col = right_col, left_col

    sel_rect = (top_row, bottom_row, left_col, right_col)

    keep: List[Dict[str, Any]] = []
    removed: List[Dict[str, Any]] = []
    straddlers: List[Dict[str, Any]] = []

    for t in tiles:
        if include_overlap:
            ok = rects_overlap(rect(t), sel_rect)
        else:
            r0 = as_int(t, "row")
            c0 = as_int(t, "col")
            ok = (top_row <= r0 <= bottom_row) and (left_col <= c0 <= right_col)

            if rects_overlap(rect(t), sel_rect) and not ok:
                straddlers.append(t)

        (keep if ok else removed).append(t)

    if not keep:
        _die("At least one tile must remain. The crop range contains no tiles under the current selection rules.")
    removed_ids = [as_int(t, "id") for t in removed]
    extra = ""
    if (not include_overlap) and straddlers:
        sids = [as_int(t, "id") for t in straddlers]
        extra = (
            f"WARNING: {len(straddlers)} tile(s) overlap the kept range but do not start inside it "
            f"(removed because --include_overlap not set). IDs: {format_id_sample(sids)}"
        )

    _warn_and_prompt(force, f"crop_to_range {top_row},{left_col}..{bottom_row},{right_col}", removed, removed_ids, extra_warning=extra, verbose=verbose, debug=debug, show_map=show_map, map_focus=map_focus, all_tiles=tiles)
    tiles[:] = keep
    vlog(verbose, f"[crop_to_range] kept {len(keep)} tile(s), removed {len(removed)} tile(s)")
    return removed_ids


def _parse_csv_tokens(csv: str) -> List[str]:
    parts = [p.strip() for p in (csv or "").split(",")]
    parts = [p for p in parts if p != ""]
    if not parts:
        _die("Expected a comma-separated list with at least one value.")
    return parts


_RE_INT = re.compile(r"^[+-]?\d+$")
_RE_RANGE = re.compile(r"^\s*([+-]?\d+)\s*-\s*([+-]?\d+)\s*$")
_RE_CMP = re.compile(r"^\s*(<=|>=|<|>)\s*([+-]?\d+)\s*$")


def _expand_int_spec_to_set(
    tokens: List[str],
    *,
    max_value: int,
    op_label: str,
    allow_literals: bool,
) -> Tuple[Set[int], Set[str]]:
    """Parse tokens like: 1, 5-10, <5, >=5.

    Returns (numeric_set, literal_set). If allow_literals is False, any non-numeric token is an error.

    Comparison expansion is bounded to [0..max_value].
    """
    nums: Set[int] = set()
    lits: Set[str] = set()

    def add_range(a: int, b: int, *, swap: bool = True) -> None:
        """Add inclusive integer range [a..b].

        For explicit ranges (e.g., 10-5) we swap endpoints.
        For comparisons (e.g., >100) we must NOT swap, because
        a>b should produce an empty expansion.
        """
        if swap:
            lo, hi = (a, b) if a <= b else (b, a)
        else:
            lo, hi = a, b
        # keep expansions non-negative; tile ids/devices are treated as numeric strings starting at 0
        lo = max(lo, 0)
        hi = min(hi, max_value)
        if hi < lo:
            return
        nums.update(range(lo, hi + 1))

    for raw in tokens:
        tok = raw.strip()
        if tok == "":
            continue

        m = _RE_CMP.match(tok)
        if m:
            op = m.group(1)
            n = int(m.group(2))
            if op == "<":
                add_range(0, n - 1, swap=False)
            elif op == "<=":
                add_range(0, n, swap=False)
            elif op == ">":
                add_range(n + 1, max_value, swap=False)
            elif op == ">=":
                add_range(n, max_value, swap=False)
            continue

        m = _RE_RANGE.match(tok)
        if m:
            a = int(m.group(1))
            b = int(m.group(2))
            add_range(a, b)
            continue

        if _RE_INT.match(tok):
            nums.add(int(tok))
            continue

        if allow_literals:
            lits.add(tok)
            continue

        _die(
            f"{op_label} expects a comma-separated list of numeric ids and/or ranges. Got {tok!r}. "
            f"Accepted forms: 1, 5-10, <5, <=5, >5, >=5"
        )

    return nums, lits


def parse_prune_id_spec(ids_csv: str, tiles: List[Dict[str, Any]], *, op_label: str) -> Set[int]:
    """Parse an id spec (comma-separated values, ranges, comparisons) into a numeric id set.

    Used by prune operations and BEFORE-map highlighting. Comparison expansions are bounded
    to the highest id present in the current tiles list.
    """
    id_tokens = _parse_csv_tokens(ids_csv)
    max_id = max((as_int(t, "id") for t in tiles), default=0)
    keep_ids, _ = _expand_int_spec_to_set(
        id_tokens,
        max_value=max_id,
        op_label=op_label,
        allow_literals=False,
    )
    return keep_ids


def parse_prune_device_spec(devices_csv: str, tiles: List[Dict[str, Any]], *, op_label: str) -> Tuple[Set[int], Set[str]]:
    """Parse a device spec into (numeric_set, literal_set).

    Numeric expressions match device strings that are numeric (e.g., "0", "1", ...).
    Comparison expansions are bounded to the highest numeric device value present.
    """
    dev_tokens = _parse_csv_tokens(devices_csv)
    max_dev = 0
    for t in tiles:
        dev = t.get("device", None)
        dev_s = "" if dev is None else str(dev).strip()
        if dev_s.lstrip("+-").isdigit():
            try:
                max_dev = max(max_dev, int(dev_s))
            except Exception:
                pass
    nums, lits = _expand_int_spec_to_set(
        dev_tokens,
        max_value=max_dev,
        op_label=op_label,
        allow_literals=True,
    )
    return nums, lits


def _device_matches_spec(tile: Dict[str, Any], nums: Set[int], lits: Set[str]) -> bool:
    dev = tile.get("device", None)
    dev_s = "" if dev is None else str(dev).strip()
    if dev_s in lits:
        return True
    if dev_s.lstrip("+-").isdigit():
        try:
            return int(dev_s) in nums
        except Exception:
            return False
    return False



def prune_except_ids(
    tiles: List[Dict[str, Any]],
    *,
    ids_csv: str,
    force: bool,
    verbose: bool,
    debug: bool,
    show_map: bool = False,
    map_focus: str = "full",
) -> List[int]:
    keep_ids = parse_prune_id_spec(ids_csv, tiles, op_label="--prune_except_ids")

    keep: List[Dict[str, Any]] = []
    removed: List[Dict[str, Any]] = []
    for t in tiles:
        tid = as_int(t, "id")
        (keep if tid in keep_ids else removed).append(t)

    if not keep:
        _die("prune_except_ids: no tiles matched the provided id list (at least one tile must remain).")

    removed_ids = [as_int(t, "id") for t in removed]
    _warn_and_prompt(
        force,
        f"prune_except_ids {ids_csv}",
        removed,
        removed_ids,
        verbose=verbose,
        debug=debug,
        show_map=show_map,
        map_focus=map_focus,
        all_tiles=tiles,
    )

    tiles[:] = keep
    vlog(verbose, f"[prune_except_ids] kept {len(keep)} tile(s), removed {len(removed)} tile(s)")
    return removed_ids



def prune_except_devices(
    tiles: List[Dict[str, Any]],
    *,
    devices_csv: str,
    force: bool,
    verbose: bool,
    debug: bool,
    show_map: bool = False,
    map_focus: str = "full",
) -> List[int]:
    keep_nums, keep_literals = parse_prune_device_spec(devices_csv, tiles, op_label="--prune_except_devices")

    keep: List[Dict[str, Any]] = []
    removed: List[Dict[str, Any]] = []
    for t in tiles:
        if _device_matches_spec(t, keep_nums, keep_literals):
            keep.append(t)
        else:
            removed.append(t)

    if not keep:
        _die("prune_except_devices: no tiles matched the provided device list (at least one tile must remain).")

    removed_ids = [as_int(t, "id") for t in removed]
    _warn_and_prompt(
        force,
        f"prune_except_devices {devices_csv}",
        removed,
        removed_ids,
        verbose=verbose,
        debug=debug,
        show_map=show_map,
        map_focus=map_focus,
        all_tiles=tiles,
    )

    tiles[:] = keep
    vlog(verbose, f"[prune_except_devices] kept {len(keep)} tile(s), removed {len(removed)} tile(s)")
    return removed_ids


def prune_ids(
    tiles: List[Dict[str, Any]],
    *,
    ids_csv: str,
    force: bool,
    verbose: bool,
    debug: bool,
    show_map: bool = False,
    map_focus: str = "full",
) -> List[int]:
    """Remove tiles whose numeric ids match the provided spec."""
    remove_ids = parse_prune_id_spec(ids_csv, tiles, op_label="--prune_ids")

    keep: List[Dict[str, Any]] = []
    removed: List[Dict[str, Any]] = []
    for t in tiles:
        tid = as_int(t, "id")
        (removed if tid in remove_ids else keep).append(t)

    if not removed:
        ilog("prune_ids: no tiles matched the provided spec; no changes.")
        return []
    if not keep:
        _die("prune_ids: this would remove all tiles (at least one tile must remain).")

    removed_ids = [as_int(t, "id") for t in removed]
    _warn_and_prompt(
        force,
        f"prune_ids {ids_csv}",
        removed,
        removed_ids,
        verbose=verbose,
        debug=debug,
        show_map=show_map,
        map_focus=map_focus,
        all_tiles=tiles,
    )

    tiles[:] = keep
    vlog(verbose, f"[prune_ids] kept {len(keep)} tile(s), removed {len(removed)} tile(s)")
    return removed_ids


def prune_devices(
    tiles: List[Dict[str, Any]],
    *,
    devices_csv: str,
    force: bool,
    verbose: bool,
    debug: bool,
    show_map: bool = False,
    map_focus: str = "full",
) -> List[int]:
    """Remove tiles whose device matches the provided spec."""
    rem_nums, rem_literals = parse_prune_device_spec(devices_csv, tiles, op_label="--prune_devices")

    keep: List[Dict[str, Any]] = []
    removed: List[Dict[str, Any]] = []
    for t in tiles:
        if _device_matches_spec(t, rem_nums, rem_literals):
            removed.append(t)
        else:
            keep.append(t)

    if not removed:
        ilog("prune_devices: no tiles matched the provided spec; no changes.")
        return []
    if not keep:
        _die("prune_devices: this would remove all tiles (at least one tile must remain).")

    removed_ids = [as_int(t, "id") for t in removed]
    _warn_and_prompt(
        force,
        f"prune_devices {devices_csv}",
        removed,
        removed_ids,
        verbose=verbose,
        debug=debug,
        show_map=show_map,
        map_focus=map_focus,
        all_tiles=tiles,
    )

    tiles[:] = keep
    vlog(verbose, f"[prune_devices] kept {len(keep)} tile(s), removed {len(removed)} tile(s)")
    return removed_ids

