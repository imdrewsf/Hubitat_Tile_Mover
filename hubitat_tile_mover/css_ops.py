from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

import re

_TILE_ID_PATTERNS = [
    re.compile(r"#tile-(\d+)\b"),
    re.compile(r"\.tile-(\d+)\b"),
    re.compile(r"['\"]tile-(\d+)['\"]"),
]

def _selector_tile_ids(selector: str) -> Set[int]:
    ids: Set[int] = set()
    for rx in _TILE_ID_PATTERNS:
        for m in rx.finditer(selector):
            try:
                ids.add(int(m.group(1)))
            except ValueError:
                pass
    return ids

def _replace_tile_id_in_selector(selector: str, old: int, new: int) -> str:
    # Common forms: #tile-123, .tile-123, 'tile-123', "tile-123"
    selector = re.sub(rf"(#tile-){old}\b", rf"\g<1>{new}", selector)
    selector = re.sub(rf"(\.tile-){old}\b", rf"\g<1>{new}", selector)
    selector = re.sub(rf"(['\"]tile-){old}(['\"])", rf"\g<1>{new}\2", selector)
    return selector
def tile_ids_in_css(css: str) -> Set[int]:
    """Return all tile ids referenced anywhere in the CSS text (e.g. #tile-123, .tile-123, 'tile-123')."""
    ids: Set[int] = set()
    if not css:
        return ids
    for rx in _TILE_ID_PATTERNS:
        for m in rx.finditer(css):
            try:
                ids.add(int(m.group(1)))
            except ValueError:
                pass
    return ids

def max_tile_id_in_css(css: str) -> int:
    ids = tile_ids_in_css(css)
    return max(ids) if ids else 0


def orphan_tile_ids_in_css(css: str, existing_tile_ids: Set[int]) -> Set[int]:
    """Return tile IDs referenced in CSS that are not present in the layout tiles."""
    if not css:
        return set()
    return {i for i in tile_ids_in_css(css) if i not in existing_tile_ids}


@dataclass
class CssStmt:
    text: str  # includes trailing ; or comments/whitespace as captured

@dataclass
class CssBlock:
    prelude: str  # selector list or at-rule prelude
    body: str     # contents inside braces

CssNode = CssStmt | CssBlock

def _parse_css_nodes(css: str) -> List[CssNode]:
    """
    Very lightweight CSS parser:
      - Preserves raw statements ending with ';' at top level.
      - Preserves comment blocks as statements.
      - Parses brace blocks with correct nesting and returns (prelude, body).
    Designed to be resilient for Hubitat customCSS; not a full CSS grammar.
    """
    nodes: List[CssNode] = []
    i = 0
    n = len(css)

    def skip_ws(j: int) -> int:
        while j < n and css[j].isspace():
            j += 1
        return j

    while i < n:
        i = skip_ws(i)
        if i >= n:
            break

        # comment
        if css.startswith("/*", i):
            j = css.find("*/", i + 2)
            if j == -1:
                nodes.append(CssStmt(css[i:]))
                break
            nodes.append(CssStmt(css[i : j + 2]))
            i = j + 2
            continue

        # find next top-level '{' or ';'
        j = i
        in_str: Optional[str] = None
        while j < n:
            ch = css[j]
            if in_str:
                if ch == "\\":
                    j += 2
                    continue
                if ch == in_str:
                    in_str = None
                j += 1
                continue
            if ch in ("'", '"'):
                in_str = ch
                j += 1
                continue
            if ch == "{":
                break
            if ch == ";":
                break
            if ch == "/" and j + 1 < n and css[j + 1] == "*":
                break
            j += 1

        if j >= n:
            nodes.append(CssStmt(css[i:]))
            break

        if css[j] == ";":
            nodes.append(CssStmt(css[i : j + 1]))
            i = j + 1
            continue

        if css[j] == "{":
            prelude = css[i:j].strip()
            # find matching brace
            depth = 1
            k = j + 1
            in_str = None
            while k < n and depth > 0:
                ch = css[k]
                if in_str:
                    if ch == "\\":
                        k += 2
                        continue
                    if ch == in_str:
                        in_str = None
                    k += 1
                    continue
                if ch in ("'", '"'):
                    in_str = ch
                    k += 1
                    continue
                if css.startswith("/*", k):
                    endc = css.find("*/", k + 2)
                    if endc == -1:
                        k = n
                        break
                    k = endc + 2
                    continue
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                k += 1
            body = css[j + 1 : k - 1] if depth == 0 else css[j + 1 :]
            nodes.append(CssBlock(prelude=prelude, body=body))
            i = k
            continue

        nodes.append(CssStmt(css[i:]))
        break

    return nodes

def _render_css_nodes(nodes: Sequence[CssNode]) -> str:
    out_parts: List[str] = []
    for node in nodes:
        if isinstance(node, CssStmt):
            out_parts.append(node.text)
            if not node.text.endswith("\n"):
                out_parts.append("\n")
        else:
            out_parts.append(node.prelude.strip())
            out_parts.append(" {\n")
            out_parts.append(node.body.rstrip())
            out_parts.append("\n}\n")
    return "".join(out_parts).rstrip() + "\n"

def cleanup_css_for_tile_ids(css: str, removed_ids: Iterable[int]) -> str:
    ids = {int(x) for x in removed_ids}
    if not ids:
        return css

    nodes = _parse_css_nodes(css)
    new_nodes: List[CssNode] = []

    for node in nodes:
        if isinstance(node, CssStmt):
            new_nodes.append(node)
            continue

        pre = node.prelude.strip()
        if pre.startswith("@"):
            # Recurse into at-rule bodies (e.g. @media)
            inner_nodes = _parse_css_nodes(node.body)
            inner_clean = cleanup_css_for_tile_ids(_render_css_nodes(inner_nodes), ids)
            new_nodes.append(CssBlock(prelude=node.prelude, body=inner_clean.rstrip()))
            continue

        selectors = [s.strip() for s in pre.split(",") if s.strip()]
        kept: List[str] = []
        for sel in selectors:
            sel_ids = _selector_tile_ids(sel)
            if sel_ids and (sel_ids & ids):
                continue
            kept.append(sel)

        if not kept:
            continue

        new_nodes.append(CssBlock(prelude=", ".join(kept), body=node.body))

    return _render_css_nodes(new_nodes)

def generate_css_for_id_map(source_css: str, id_map: Dict[int, int], *, dest_css: Optional[str] = None) -> str:
    if not id_map:
        return ""

    skip_new: Set[int] = set()
    if dest_css:
        for new_id in set(id_map.values()):
            if re.search(rf"(#tile-{new_id}\b|\.tile-{new_id}\b|['\"]tile-{new_id}['\"])", dest_css):
                skip_new.add(new_id)

    nodes = _parse_css_nodes(source_css)
    out_nodes: List[CssNode] = []

    for node in nodes:
        if isinstance(node, CssStmt):
            continue
        pre = node.prelude.strip()
        if pre.startswith("@"):
            inner = generate_css_for_id_map(node.body, id_map, dest_css=dest_css)
            if inner.strip():
                out_nodes.append(CssBlock(prelude=node.prelude, body=inner.rstrip()))
            continue

        selectors = [s.strip() for s in pre.split(",") if s.strip()]
        new_selectors: List[str] = []

        for sel in selectors:
            sel_ids = _selector_tile_ids(sel)
            matched_old = [oid for oid in sel_ids if oid in id_map]
            if not matched_old:
                continue
            for oid in matched_old:
                nid = id_map[oid]
                if nid in skip_new:
                    continue
                new_sel = _replace_tile_id_in_selector(sel, oid, nid)
                new_selectors.append(new_sel)

        if not new_selectors:
            continue

        out_nodes.append(CssBlock(prelude=", ".join(sorted(set(new_selectors))), body=node.body))

    return _render_css_nodes(out_nodes).strip()

def get_custom_css(obj: object) -> Tuple[Optional[str], str]:
    if not isinstance(obj, dict):
        return (None, "")
    if "customCSS" in obj and isinstance(obj.get("customCSS"), str):
        return ("customCSS", obj.get("customCSS") or "")
    if "customCss" in obj and isinstance(obj.get("customCss"), str):
        return ("customCss", obj.get("customCss") or "")
    return ("customCSS", "")

def set_custom_css(obj: object, key: Optional[str], css: str) -> None:
    if key is None:
        return
    if isinstance(obj, dict):
        obj[key] = css
