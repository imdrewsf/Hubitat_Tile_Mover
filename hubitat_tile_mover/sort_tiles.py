from __future__ import annotations

from typing import Any, Callable, Dict, List, Tuple

from .tiles import as_int
from .util import die


def _parse_sort_spec(user_spec: str) -> List[Tuple[str, bool]]:
    """
    Parse a sort spec string into [(key, desc), ...].

    Keys:
      i = id
      r = row
      c = col

    A '-' immediately before a key makes that key descending.

    Examples:
      rci        -> r asc, c asc, i asc
      -rci       -> r desc, c asc, i asc
      r-c-i      -> r asc, c desc, i desc
      -r-c-i     -> r desc, c desc, i desc

    Non-key separators (spaces, commas, underscores, etc.) are ignored.
    """
    spec = (user_spec or "").strip().lower()
    if spec == "":
        spec = "irc"

    out: List[Tuple[str, bool]] = []
    seen: set[str] = set()
    desc_next = False
    valid = {"i", "r", "c"}

    for ch in spec:
        if ch in (" ", "\t", ",", ";", ":", "_", "/", "\\", "."):
            continue
        if ch == "-":
            desc_next = True
            continue
        if ch not in valid:
            die(
                f"Invalid --sort '{user_spec}'. Use keys i,r,c (id,row,col) and optional '-' for descending. "

                f"Examples: --sort:rci, --sort:-rci, --sort:r-c-i"
            )
        if ch in seen:
            die(f"Invalid --sort '{user_spec}'. Keys must not repeat.")
        out.append((ch, desc_next))
        seen.add(ch)
        desc_next = False

    if desc_next:
        die(f"Invalid --sort '{user_spec}'. Trailing '-' must be followed by a key (i,r,c).")

    return out


def complete_sort_spec(user_spec: str) -> List[Tuple[str, bool]]:
    """
    Completes user spec by appending any missing keys in default priority order r,c,i (ascending).

    Example:
      user_spec = "r"    -> r, c, i
      user_spec = "i"    -> i, r, c
      user_spec = "-r"   -> r desc, c asc, i asc
    """
    parsed = _parse_sort_spec(user_spec)
    seen = {k for k, _ in parsed}
    for k in ["r", "c", "i"]:
        if k not in seen:
            parsed.append((k, False))
    return parsed


def make_sort_key(spec: List[Tuple[str, bool]]) -> Callable[[Dict[str, Any]], Tuple[int, ...]]:
    getters: Dict[str, Callable[[Dict[str, Any]], int]] = {
        "r": lambda t: as_int(t, "row"),
        "c": lambda t: as_int(t, "col"),
        "i": lambda t: as_int(t, "id"),
    }

    def key(tile: Dict[str, Any]) -> Tuple[int, ...]:
        parts: List[int] = []
        for k, desc in spec:
            v = getters[k](tile)
            parts.append(-v if desc else v)
        return tuple(parts)

    return key


def sort_tiles(tiles: List[Dict[str, Any]], user_spec: str) -> List[Dict[str, Any]]:
    spec = complete_sort_spec(user_spec)
    key_fn = make_sort_key(spec)
    return sorted(tiles, key=key_fn)
