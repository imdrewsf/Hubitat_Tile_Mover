from __future__ import annotations

from typing import Any, Dict, List

from .tiles import as_int, set_int_like
from .util import die, dlog


def trim_tiles(
    tiles: List[Dict[str, Any]],
    *,
    do_left: bool,
    do_top: bool,
    debug: bool,
) -> None:
    if not tiles:
        return

    shift_left = 0
    shift_up = 0

    if do_left:
        min_col = min(as_int(t, "col") for t in tiles)
        if min_col < 1:
            die(f"Invalid tile col value (<1) encountered: min col={min_col}")
        shift_left = min_col - 1

    if do_top:
        min_row = min(as_int(t, "row") for t in tiles)
        if min_row < 1:
            die(f"Invalid tile row value (<1) encountered: min row={min_row}")
        shift_up = min_row - 1

    dlog(debug, f"[trim] computed shift_left={shift_left}, shift_up={shift_up}")

    if shift_left == 0 and shift_up == 0:
        return

    for t in tiles:
        tid = as_int(t, "id")

        if shift_left:
            c0 = as_int(t, "col")
            c1 = c0 - shift_left
            if c1 < 1:
                die(f"trim_left would move tile id={tid} to invalid col {c1}")
            set_int_like(t, "col", c1)
            dlog(debug, f"[trim] id={tid}: col {c0} -> {c1}")

        if shift_up:
            r0 = as_int(t, "row")
            r1 = r0 - shift_up
            if r1 < 1:
                die(f"trim_top would move tile id={tid} to invalid row {r1}")
            set_int_like(t, "row", r1)
            dlog(debug, f"[trim] id={tid}: row {r0} -> {r1}")
