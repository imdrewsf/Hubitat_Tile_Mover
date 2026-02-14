from __future__ import annotations

import json
from typing import Any, List, Literal, Tuple, Optional

from .util import die

# Import input "shape" / level:
#   full_object      -> { ..., "tiles": [..], ... }   (other fields exist)
#   minimal_container-> { "tiles": [..] }
#   bare_tiles_list  -> [ ... ]
ContainerKind = Literal["full_object", "minimal_container", "bare_tiles_list"]


def load_json_from_text(text: str, *, verbose: bool = False, debug: bool = False) -> Any:
    """Parse JSON with user-friendly errors unless verbose/debug.

    If the text appears to be a Hubitat dashboard layout but is malformed, the JSONDecodeError
    location details are always shown.
    """
    looks_jsonish = text.lstrip().startswith(("{", "["))
    looks_dashboardish = ("\"tiles\"" in text) or ("\"customCSS\"" in text)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        if looks_dashboardish:
            die(f"The input looks like a dashboard layout, but the JSON is malformed: {e}")
        if verbose or debug:
            die(f"Input is not valid JSON: {e}")
        if looks_jsonish:
            die("The clipboard/input file does not appear to contain valid JSON.")
        die("The clipboard/input file does not appear to be JSON.")


def extract_tiles_container(obj: Any, *, verbose: bool = False, debug: bool = False) -> Tuple[ContainerKind, Any, List[Any]]:
    if isinstance(obj, dict):
        if "tiles" not in obj:
            die("JSON object does not contain a top-level 'tiles' field.")
        tiles = obj["tiles"]
        if not isinstance(tiles, list):
            die("'tiles' must be a list.")
        kind: ContainerKind = "minimal_container" if set(obj.keys()) == {"tiles"} else "full_object"
        return (kind, obj, tiles)

    if isinstance(obj, list):
        return ("bare_tiles_list", obj, obj)

    die("Top-level JSON must be an object with 'tiles' OR a bare tiles list.")
    return ("full_object", obj, [])  # unreachable


def normalize_tiles_list(tiles_any: Any, *, verbose: bool = False, debug: bool = False) -> List[dict]:
    """Validate and normalize tiles list. Ensures at least one tile has id/row/col."""
    if not isinstance(tiles_any, list):
        die("'tiles' must be a list.")
    if len(tiles_any) == 0:
        die("'tiles' list is empty.")
    tiles: List[dict] = []
    saw_valid = False
    for i, t in enumerate(tiles_any):
        if not isinstance(t, dict):
            die(f"Tile at index {i} is not an object.")
        tiles.append(t)
        if ("id" in t) and ("row" in t) and ("col" in t):
            saw_valid = True
    if not saw_valid:
        die("No tiles found with required fields 'id', 'row', and 'col'.")
    return tiles

def _level_for_kind(kind: ContainerKind) -> int:
    # Higher means "richer" (can output more)
    if kind == "full_object":
        return 3
    if kind == "minimal_container":
        return 2
    return 1  # bare_tiles_list


def _level_for_output_format(fmt: str) -> int:
    fmt = (fmt or "").lower()
    if fmt == "full":
        return 3
    if fmt in ("minimal", "container"):
        return 2
    if fmt in ("bare", "list"):
        return 1
    die("Invalid output_format. Use: full | minimal | bare (legacy: container | list).")
    return 1

def _default_output_format_for_kind(kind: ContainerKind) -> str:
    if kind == "full_object":
        return "full"
    if kind == "minimal_container":
        return "minimal"
    return "bare"

def build_output_object(
    kind: ContainerKind,
    full_container: Any,
    tiles: Any,
    output_format: Optional[str],
) -> Any:
    # Default output matches input format.
    fmt = output_format if output_format is not None else _default_output_format_for_kind(kind)
    fmt = fmt.lower()

    # Normalize legacy synonyms.
    if fmt == "container":
        fmt = "minimal"
    elif fmt == "list":
        fmt = "bare"

    # Disallow outputs "higher" than what the input provided.
    if _level_for_output_format(fmt) > _level_for_kind(kind):
        die(
            f"Requested --output_format:{fmt} exceeds imported JSON format. "
            f"Input kind is '{kind}'."
        )

    if fmt == "bare":
        return tiles

    if fmt == "minimal":
        return {"tiles": tiles}

    # fmt == "full"
    # Only possible for full_object due to validation above.
    if not isinstance(full_container, dict):
        die("Internal error: full output requires an object container.")
    full_container["tiles"] = tiles
    return full_container


def dump_json(obj: Any, indent: int, minify: bool) -> str:
    if minify:
        return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return json.dumps(obj, ensure_ascii=False, indent=indent)
