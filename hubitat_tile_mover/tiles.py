from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .util import die


def as_int(tile: Dict[str, Any], key: str) -> int:
    if key not in tile:
        die(f"Tile missing required key '{key}': {tile}")
    v = tile[key]
    if isinstance(v, bool):
        die(f"Tile key '{key}' must be an int, got bool: {tile}")
    if isinstance(v, int):
        return v
    if isinstance(v, str) and v.strip().lstrip("+-").isdigit():
        return int(v.strip())
    die(f"Tile key '{key}' must be an int, got {type(v).__name__}={v!r}: {tile}")
    return 0  # unreachable


def _pos_int_from_value(tile: Dict[str, Any], key: str, v: Any) -> int:
    if isinstance(v, bool):
        die(f"Tile key '{key}' must be a positive int, got bool: {tile}")
    if isinstance(v, int):
        n = v
    elif isinstance(v, str) and v.strip().lstrip("+-").isdigit():
        n = int(v.strip())
    else:
        die(f"Tile key '{key}' must be a positive int, got {type(v).__name__}={v!r}: {tile}")
    if n < 1:
        die(f"Tile key '{key}' must be >= 1, got {n}: {tile}")
    return n


def get_span(tile: Dict[str, Any], keys: List[str], default: int = 1) -> int:
    found: List[Tuple[str, int]] = []
    for k in keys:
        if k in tile:
            found.append((k, _pos_int_from_value(tile, k, tile[k])))

    if not found:
        return default

    vals = {v for _, v in found}
    if len(vals) > 1:
        die(f"Conflicting span values for {keys}: {found} in tile {tile}")

    return found[0][1]


def tile_row_extent(tile: Dict[str, Any]) -> Tuple[int, int]:
    r = as_int(tile, "row")
    rs = get_span(tile, ["rowSpan", "rowspan"], default=1)
    return (r, r + rs - 1)


def tile_col_extent(tile: Dict[str, Any]) -> Tuple[int, int]:
    c = as_int(tile, "col")
    cs = get_span(tile, ["colSpan", "colspan"], default=1)
    return (c, c + cs - 1)


def rect(tile: Dict[str, Any]) -> Tuple[int, int, int, int]:
    r1, r2 = tile_row_extent(tile)
    c1, c2 = tile_col_extent(tile)
    return (r1, r2, c1, c2)


def set_int_like(tile: Dict[str, Any], key: str, new_value: int) -> None:
    old = tile.get(key, None)
    if old is None:
        die(f"Tile missing required key '{key}' (cannot set): {tile}")
    if isinstance(old, int):
        tile[key] = int(new_value)
    elif isinstance(old, str):
        tile[key] = str(int(new_value))
    else:
        die(f"Tile key '{key}' must be int or str to update, got {type(old).__name__}: {tile}")


def verify_tiles_minimum(tiles: List[Any]) -> None:
    if len(tiles) == 0:
        die("'tiles' list is empty. Expected at least one tile.")
    for t in tiles:
        if not isinstance(t, dict):
            die(f"Each tile must be an object/dict, got: {type(t).__name__}")
        _ = as_int(t, "id")
        _ = as_int(t, "row")
        _ = as_int(t, "col")
