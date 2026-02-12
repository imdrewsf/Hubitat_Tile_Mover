from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

from .geometry import ranges_overlap, rects_overlap
from .tiles import as_int, rect, tile_col_extent, tile_row_extent
from .util import format_id_sample, prompt_yes_no_or_die, vlog
from .util import die as _die


def _warn_and_prompt(
    force: bool,
    op_name: str,
    removed_ids: List[int],
    *,
    extra_warning: str = "",
    verbose: bool,
    debug: bool,
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

    _warn_and_prompt(force, f"crop_to_rows {start_row}..{end_row}", removed_ids, extra_warning=extra, verbose=verbose, debug=False)
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

    _warn_and_prompt(force, f"crop_to_cols {start_col}..{end_col}", removed_ids, extra_warning=extra, verbose=verbose, debug=False)
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

    _warn_and_prompt(force, f"crop_to_range {top_row},{left_col}..{bottom_row},{right_col}", removed_ids, extra_warning=extra)
    tiles[:] = keep
    vlog(verbose, f"[crop_to_range] kept {len(keep)} tile(s), removed {len(removed)} tile(s)")
    return removed_ids


def _parse_csv_tokens(csv: str) -> List[str]:
    parts = [p.strip() for p in (csv or "").split(",")]
    parts = [p for p in parts if p != ""]
    if not parts:
        _die("Expected a comma-separated list with at least one value.")
    return parts


def prune_except_ids(
    tiles: List[Dict[str, Any]],
    *,
    ids_csv: str,
    force: bool,
    verbose: bool,
) -> List[int]:
    id_tokens = _parse_csv_tokens(ids_csv)
    keep_ids: Set[int] = set()
    for tok in id_tokens:
        if not tok.lstrip("+-").isdigit():
            _die(f"--prune_except_ids expects numeric tile ids. Got {tok!r}")
        keep_ids.add(int(tok))

    keep: List[Dict[str, Any]] = []
    removed: List[Dict[str, Any]] = []
    for t in tiles:
        tid = as_int(t, "id")
        (keep if tid in keep_ids else removed).append(t)

    if not keep:
        _die("prune_except_ids: no tiles matched the provided id list (at least one tile must remain).")
    removed_ids = [as_int(t, "id") for t in removed]
    _warn_and_prompt(force, f"prune_except_ids {ids_csv}", removed_ids)
    tiles[:] = keep
    vlog(verbose, f"[prune_except_ids] kept {len(keep)} tile(s), removed {len(removed)} tile(s)")
    return removed_ids


def prune_except_devices(
    tiles: List[Dict[str, Any]],
    *,
    devices_csv: str,
    force: bool,
    verbose: bool,
) -> List[int]:
    dev_tokens = _parse_csv_tokens(devices_csv)
    keep_devs: Set[str] = set(dev_tokens)

    keep: List[Dict[str, Any]] = []
    removed: List[Dict[str, Any]] = []
    for t in tiles:
        dev = t.get("device", None)
        dev_s = "" if dev is None else str(dev).strip()
        if dev_s in keep_devs:
            keep.append(t)
        else:
            removed.append(t)

    if not keep:
        _die("prune_except_devices: no tiles matched the provided device list (at least one tile must remain).")
    removed_ids = [as_int(t, "id") for t in removed]
    _warn_and_prompt(force, f"prune_except_devices {devices_csv}", removed_ids)
    tiles[:] = keep
    vlog(verbose, f"[prune_except_devices] kept {len(keep)} tile(s), removed {len(removed)} tile(s)")
    return removed_ids
