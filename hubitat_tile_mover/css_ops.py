from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

import re

_TILE_ID_PATTERNS = [
    re.compile(r"#tile-(\d+)\b"),
    re.compile(r"\.tile-(\d+)\b"),
    re.compile(r"['\"]tile-(\d+)['\"]"),
]

# More permissive patterns for standalone comment processing.
_COMMENT_TILE_ID_PATTERNS = [
    re.compile(r"#tile-(\d+)\b"),
    re.compile(r"\.tile-(\d+)\b"),
    re.compile(r"['\"]tile-(\d+)['\"]"),
    re.compile(r"\btile-(\d+)\b"),
]


def _split_selector_list(prelude: str) -> List[str]:
    """Split a selector list into items.

    Splits on commas that are *not* inside:
      - strings (single/double quotes)
      - parentheses (), brackets [], or braces {}
      - block comments /* ... */

    This is intentionally lightweight (not a full CSS grammar), but it avoids
    corrupting selector items that contain commas inside :not(...), attribute
    selectors, etc.
    """
    s = prelude
    out: List[str] = []
    buf: List[str] = []
    i = 0
    n = len(s)
    in_str: Optional[str] = None
    depth_paren = 0
    depth_brack = 0
    depth_brace = 0

    while i < n:
        ch = s[i]

        # comment
        if in_str is None and ch == "/" and (i + 1) < n and s[i + 1] == "*":
            endc = s.find("*/", i + 2)
            if endc == -1:
                buf.append(s[i:])
                i = n
                break
            buf.append(s[i : endc + 2])
            i = endc + 2
            continue

        # strings
        if in_str is not None:
            buf.append(ch)
            if ch == "\\" and (i + 1) < n:
                buf.append(s[i + 1])
                i += 2
                continue
            if ch == in_str:
                in_str = None
            i += 1
            continue
        if ch in ("'", '"'):
            in_str = ch
            buf.append(ch)
            i += 1
            continue

        # nesting
        if ch == "(":
            depth_paren += 1
        elif ch == ")":
            depth_paren = max(0, depth_paren - 1)
        elif ch == "[":
            depth_brack += 1
        elif ch == "]":
            depth_brack = max(0, depth_brack - 1)
        elif ch == "{":
            depth_brace += 1
        elif ch == "}":
            depth_brace = max(0, depth_brace - 1)

        # top-level selector separator
        if ch == "," and depth_paren == 0 and depth_brack == 0 and depth_brace == 0:
            item = "".join(buf).strip()
            if item:
                out.append(item)
            buf = []
            i += 1
            continue

        buf.append(ch)
        i += 1

    tail = "".join(buf).strip()
    if tail:
        out.append(tail)
    return out

def _selector_tile_ids(selector: str) -> Set[int]:
    ids: Set[int] = set()
    # Ignore commented-out selector text (e.g. `#tile-1, /* #tile-2 */ #tile-3`).
    selector = _strip_block_comments_outside_strings(selector)
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
    # Also handle bare tile-123 tokens (commonly found inside selector comments).
    selector = re.sub(rf"(tile-){old}\b", rf"\g<1>{new}", selector)
    return selector


def _replace_tile_id_in_body(body: str, old: int, new: int) -> str:
    """Rewrite tile-id references inside a declaration body.

    Used when duplicating a selector rule for a specific tile id. If the rule
    is selector-tied to OLD, then occurrences of "tile-OLD" inside the body
    (including inside strings, url(...), and comments) are safe to rewrite to
    "tile-NEW".

    Notes:
      - Orphan detection ignores comments globally; this rewrite only affects
        the duplicated rule's body.
      - This is intentionally conservative: only tile-OLD is rewritten.
    """
    if not body:
        return body
    return re.sub(rf"\btile-{old}\b", f"tile-{new}", body)


def _tile_ids_in_text(text: str) -> Set[int]:
    ids: Set[int] = set()
    if not text:
        return ids
    for rx in _TILE_ID_PATTERNS:
        for m in rx.finditer(text):
            try:
                ids.add(int(m.group(1)))
            except ValueError:
                pass
    return ids


def _strip_block_comments_outside_strings(text: str) -> str:
    """Remove /* ... */ comments unless inside quotes.

    This is intentionally lightweight; it is sufficient for safely stripping
    comments from selector preludes and standalone statements.
    """
    if not text:
        return ""
    out: List[str] = []
    i = 0
    n = len(text)
    in_str: Optional[str] = None
    while i < n:
        ch = text[i]
        if in_str is not None:
            out.append(ch)
            if ch == "\\" and (i + 1) < n:
                out.append(text[i + 1])
                i += 2
                continue
            if ch == in_str:
                in_str = None
            i += 1
            continue
        if ch in ("'", '"'):
            in_str = ch
            out.append(ch)
            i += 1
            continue
        if ch == "/" and (i + 1) < n and text[i + 1] == "*":
            endc = text.find("*/", i + 2)
            if endc == -1:
                # Unterminated comment: drop the remainder.
                break
            i = endc + 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _tile_ids_in_css_stylesheet(css: str) -> Set[int]:
    """Collect tile ids from a CSS stylesheet.

    This is used for orphan detection and id-reservation for new ids.

    Comment handling:
      - ALL block comments are ignored (top-level, inside @media, and inside
        declaration bodies).
    """
    ids: Set[int] = set()
    nodes = _parse_css_nodes(css)
    for node in nodes:
        if isinstance(node, CssStmt):
            ids |= _tile_ids_in_text(_strip_block_comments_outside_strings(node.text))
            continue

        pre = _strip_block_comments_outside_strings(node.prelude or "")
        ids |= _tile_ids_in_text(pre)
        if (node.prelude or "").strip().startswith("@"):
            ids |= _tile_ids_in_css_stylesheet(node.body)
        else:
            ids |= _tile_ids_in_text(_strip_block_comments_outside_strings(node.body))
    return ids
def tile_ids_in_css(css: str) -> Set[int]:
    """Return tile ids referenced in CSS.

    Comment handling:
      - Ignores ALL block comments (/* ... */).
    """
    if not css:
        return set()
    return _tile_ids_in_css_stylesheet(css)


def _tile_ids_in_comment_text(comment_text: str) -> Set[int]:
    ids: Set[int] = set()
    if not comment_text:
        return ids
    for rx in _COMMENT_TILE_ID_PATTERNS:
        for m in rx.finditer(comment_text):
            try:
                ids.add(int(m.group(1)))
            except Exception:
                pass
    return ids


def _duplicate_standalone_comment(comment_text: str, old_id: int, new_id: int) -> str:
    """Duplicate a standalone comment for a copied/merged tile id."""
    text = comment_text.strip()
    if text.startswith("/*") and text.endswith("*/"):
        inner = text[2:-2].strip()
    else:
        inner = text

    # Replace common tile-id forms, including bare tile-123.
    inner2 = re.sub(rf"(#tile-){old_id}\b", rf"\g<1>{new_id}", inner)
    inner2 = re.sub(rf"(\.tile-){old_id}\b", rf"\g<1>{new_id}", inner2)
    inner2 = re.sub(rf"(['\"]tile-){old_id}(['\"])", rf"\g<1>{new_id}\2", inner2)
    inner2 = re.sub(rf"\btile-{old_id}\b", f"tile-{new_id}", inner2)

    note = f"[hubitat_tile_mover] duplicated from tile-{old_id} to tile-{new_id}."
    return f"/* {note} {inner2} */"


def _comment_inner_text(comment_text: str) -> str:
    """Return the inner text of a /* ... */ comment, best-effort."""
    txt = (comment_text or "").strip()
    if txt.startswith("/*") and txt.endswith("*/"):
        return txt[2:-2]
    if txt.startswith("/*"):
        return txt[2:]
    return txt


def _wrap_as_block_comment(inner: str) -> str:
    """Wrap text as a block comment, preserving multi-line content."""
    inner0 = (inner or "").rstrip()
    if "\n" in inner0:
        return f"/*\n{inner0}\n*/"
    return f"/* {inner0} */"


def _looks_like_css_rules(text: str) -> bool:
    """Heuristic: does the text look like it contains CSS blocks?"""
    t = (text or "")
    if "{" not in t or "}" not in t:
        return False
    # Quick parse check: do we get at least one CssBlock?
    try:
        for n in _parse_css_nodes(t):
            if isinstance(n, CssBlock):
                return True
    except Exception:
        return False
    return False


def _duplicate_comment_css_rules(comment_text: str, id_map: Dict[int, int], *, skip_new: Set[int]) -> str:
    """Duplicate commented-out CSS selector rules contained inside a standalone comment.

    Example:
      /* #tile-40 { background: url('tile-40.png'); } */

    When 40->123 is in id_map, this returns a new comment containing duplicated
    rules as if they were active (selector-item splitting + body tile-id
    rewrite), but still commented out.

    If no duplicable rules are found, returns an empty string.
    """
    inner = _comment_inner_text(comment_text)
    if not _looks_like_css_rules(inner):
        return ""

    def dup_blocks_only(css_text: str) -> List[CssNode]:
        out: List[CssNode] = []
        for node in _parse_css_nodes(css_text or ""):
            if isinstance(node, CssStmt):
                # Ignore nested statements inside the commented fragment.
                continue

            pre0 = (node.prelude or "").strip()
            if pre0.startswith("@"):
                inner_nodes = dup_blocks_only(node.body)
                if inner_nodes:
                    out.append(CssBlock(prelude=node.prelude, body=_render_css_nodes(inner_nodes).rstrip()))
                continue

            selectors0 = _split_selector_list(pre0)
            for sel0 in selectors0:
                sel_ids0 = _selector_tile_ids(sel0)
                matched_old = [oid for oid in sel_ids0 if oid in id_map]
                if not matched_old:
                    continue
                for oid in matched_old:
                    nid = id_map[oid]
                    if nid in skip_new:
                        continue
                    new_sel = _replace_tile_id_in_selector(sel0, oid, nid)
                    new_body = _replace_tile_id_in_body(node.body, oid, nid)
                    out.append(CssBlock(prelude=new_sel, body=new_body))
        return out

    dup_nodes = dup_blocks_only(inner)
    if not dup_nodes:
        return ""
    dup_css = _render_css_nodes(dup_nodes).strip()
    return _wrap_as_block_comment(dup_css)


def find_standalone_comment_tile_refs(css: str, target_ids: Set[int]) -> List[Tuple[int, Set[int], str]]:
    """Return list of (index, matched_ids, comment_text) for standalone comments.

    Standalone comments are /* ... */ nodes at statement level (top-level or
    inside @media bodies), not comments inside a declaration body.
    """
    if not css or not target_ids:
        return []
    nodes = _parse_css_nodes(css)
    hits: List[Tuple[int, Set[int], str]] = []
    for idx, node in enumerate(nodes):
        if isinstance(node, CssStmt) and node.text.lstrip().startswith("/*"):
            ids = _tile_ids_in_comment_text(node.text)
            matched = ids & target_ids
            if matched:
                hits.append((idx, matched, node.text))
        elif isinstance(node, CssBlock) and (node.prelude or "").strip().startswith("@"): 
            # Recurse into at-rule blocks.
            inner_hits = find_standalone_comment_tile_refs(node.body, target_ids)
            # Index values aren't meaningful for nested blocks; return -1.
            for _i, mids, txt in inner_hits:
                hits.append((-1, mids, txt))
    return hits


def _neutralize_removed_tile_ids_in_comment(comment_text: str, removed_ids: Set[int]) -> Tuple[str, Set[int]]:
    """If a standalone comment references removed tile ids, rewrite those
    references so they don't look like tile selectors.

    Rewrites tile-123 -> tile_123 (and corresponding #tile-/.tile-/quoted forms).
    Returns (new_comment_text, affected_ids).
    """
    ids_found = _tile_ids_in_comment_text(comment_text)
    affected = ids_found & removed_ids
    if not affected:
        return (comment_text, set())

    def repl(m: re.Match, prefix: str, joiner: str) -> str:
        tid = int(m.group(1))
        if tid in affected:
            return f"{prefix}{joiner}{tid}"
        return m.group(0)

    text = comment_text
    text = re.sub(r"#tile-(\d+)\b", lambda m: repl(m, "#tile", "_"), text)
    text = re.sub(r"\.tile-(\d+)\b", lambda m: repl(m, ".tile", "_"), text)
    text = re.sub(
        r"(['\"])tile-(\d+)(['\"])",
        lambda m: f"{m.group(1)}tile_{m.group(2)}{m.group(3)}" if int(m.group(2)) in affected else m.group(0),
        text,
    )
    text = re.sub(r"\btile-(\d+)\b", lambda m: f"tile_{m.group(1)}" if int(m.group(1)) in affected else m.group(0), text)
    return (text, affected)


def process_standalone_comments_for_removed_tiles(css: str, removed_ids: Iterable[int], *, remove: bool) -> Tuple[str, int, int]:
    """Remove or rewrite standalone comments that reference removed tile ids.

    If remove=True: drop the standalone comments.
    If remove=False: keep the comments but rewrite tile-id references so they
    won't match tile scanners, and annotate that the tile rules were removed.
    """
    ids = {int(x) for x in removed_ids}
    if not css or not ids:
        return (css, 0, 0)

    nodes = _parse_css_nodes(css)
    new_nodes: List[CssNode] = []
    removed_count = 0
    rewritten_count = 0

    for node in nodes:
        if isinstance(node, CssStmt) and node.text.lstrip().startswith("/*"):
            comment_ids = _tile_ids_in_comment_text(node.text)
            matched = comment_ids & ids
            if not matched:
                new_nodes.append(node)
                continue
            if remove:
                removed_count += 1
                continue

            # Keep comment but neutralize removed tile ids and annotate.
            neutralized, affected = _neutralize_removed_tile_ids_in_comment(node.text, ids)
            note = f"[hubitat_tile_mover] tile(s) removed; CSS rules removed for: {', '.join('tile_'+str(i) for i in sorted(affected))}."
            txt = neutralized.strip()
            if txt.startswith("/*") and txt.endswith("*/"):
                inner = txt[2:-2].strip()
                new_txt = f"/* {note} {inner} */"
            else:
                new_txt = f"/* {note} {txt} */"
            new_nodes.append(CssStmt(new_txt))
            rewritten_count += 1
            continue

        if isinstance(node, CssBlock) and (node.prelude or "").strip().startswith("@"): 
            # Recurse into at-rule bodies.
            inner_css, r1, r2 = process_standalone_comments_for_removed_tiles(node.body, ids, remove=remove)
            removed_count += r1
            rewritten_count += r2
            new_nodes.append(CssBlock(prelude=node.prelude, body=inner_css.rstrip()))
            continue

        new_nodes.append(node)

    return (_render_css_nodes(new_nodes), removed_count, rewritten_count)


def process_standalone_comments_for_css_cleared_tiles(css: str, tile_ids: Iterable[int], *, remove: bool) -> Tuple[str, int, int]:
    """Remove or rewrite standalone comments that reference tile ids whose CSS rules were cleared.

    This is used by --clear_tile_css.

    If remove=True: drop the standalone comments.
    If remove=False: keep the comments but rewrite tile-id references so they
    won't match tile scanners, and annotate that CSS rules were cleared for
    those tiles.

    Note: comments are ignored for orphan detection, but we still neutralize
    the references to reduce confusion and preserve older behaviors.
    """
    ids = {int(x) for x in tile_ids}
    if not css or not ids:
        return (css, 0, 0)

    nodes = _parse_css_nodes(css)
    new_nodes: List[CssNode] = []
    removed_count = 0
    rewritten_count = 0

    for node in nodes:
        if isinstance(node, CssStmt) and node.text.lstrip().startswith("/*"):
            comment_ids = _tile_ids_in_comment_text(node.text)
            matched = comment_ids & ids
            if not matched:
                new_nodes.append(node)
                continue
            if remove:
                removed_count += 1
                continue

            neutralized, affected = _neutralize_removed_tile_ids_in_comment(node.text, ids)
            note = (
                f"[hubitat_tile_mover] CSS rules cleared for: "
                f"{', '.join('tile_'+str(i) for i in sorted(affected))}."
            )
            txt = neutralized.strip()
            if txt.startswith("/*") and txt.endswith("*/"):
                inner = txt[2:-2].strip()
                new_txt = f"/* {note} {inner} */"
            else:
                new_txt = f"/* {note} {txt} */"
            new_nodes.append(CssStmt(new_txt))
            rewritten_count += 1
            continue

        if isinstance(node, CssBlock) and (node.prelude or "").strip().startswith("@"): 
            inner_css, r1, r2 = process_standalone_comments_for_css_cleared_tiles(node.body, ids, remove=remove)
            removed_count += r1
            rewritten_count += r2
            new_nodes.append(CssBlock(prelude=node.prelude, body=inner_css.rstrip()))
            continue

        new_nodes.append(node)

    return (_render_css_nodes(new_nodes), removed_count, rewritten_count)


def tile_has_selector_rules(css: str, tile_id: int) -> bool:
    """Return True if CSS contains at least one selector prelude referencing tile_id."""
    if not css:
        return False
    return int(tile_id) in selector_tile_ids_in_css(css)


def filter_css_fragment_duplicates(dest_css: str, frag_css: str) -> str:
    """Filter frag_css by removing blocks that already exist in dest_css.

    This is a best-effort deduper used when appending duplicated tile CSS.
    Deduping is based on a canonical form of (at-rule stack, selector prelude,
    body text).
    """
    if not frag_css.strip():
        return ""

    def norm_at(prelude: str) -> str:
        return re.sub(r"\s+", " ", prelude.strip())

    def norm_pre(prelude: str) -> str:
        pre0 = _strip_block_comments_outside_strings(prelude or "").strip()
        items = [re.sub(r"\s+", " ", s.strip()) for s in _split_selector_list(pre0)]
        items = [s for s in items if s]
        return ", ".join(sorted(items))

    def norm_body(body: str) -> str:
        # Keep this conservative: normalize newlines and trim.
        b = (body or "").replace("\r\n", "\n").replace("\r", "\n")
        # strip trailing spaces per line
        b = "\n".join([ln.rstrip() for ln in b.split("\n")]).strip()
        return b

    def canonical(stack: Tuple[str, ...], prelude: str, body: str) -> str:
        return "|".join(stack) + "||" + norm_pre(prelude) + "{" + norm_body(body) + "}"

    def collect_existing(css_text: str, stack: Tuple[str, ...] = ()) -> Set[str]:
        out: Set[str] = set()
        for node in _parse_css_nodes(css_text or ""):
            if isinstance(node, CssStmt):
                continue
            pre = (node.prelude or "").strip()
            if pre.startswith("@"): 
                out |= collect_existing(node.body, stack + (norm_at(pre),))
            else:
                out.add(canonical(stack, node.prelude, node.body))
        return out

    existing = collect_existing(dest_css or "")

    def filter_nodes(css_text: str, stack: Tuple[str, ...] = ()) -> List[CssNode]:
        kept: List[CssNode] = []
        for node in _parse_css_nodes(css_text or ""):
            if isinstance(node, CssStmt):
                # Keep statements (including comments). The caller can decide
                # whether to keep duplicates by running the operation once.
                kept.append(node)
                continue
            pre = (node.prelude or "").strip()
            if pre.startswith("@"): 
                inner = filter_nodes(node.body, stack + (norm_at(pre),))
                if inner:
                    kept.append(CssBlock(prelude=node.prelude, body=_render_css_nodes(inner).rstrip()))
                continue
            key = canonical(stack, node.prelude, node.body)
            if key in existing:
                continue
            existing.add(key)
            kept.append(node)
        return kept

    kept_nodes = filter_nodes(frag_css)
    return _render_css_nodes(kept_nodes).strip()


def normalize_css_body(body: str) -> str:
    """Normalize a CSS rule body for equality comparison (best-effort)."""
    b = (body or "").replace("\r\n", "\n").replace("\r", "\n")
    b = "\n".join([ln.rstrip() for ln in b.split("\n")]).strip()
    return b


def _norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def normalize_selector_item(selector_item: str) -> str:
    """Normalize a selector item for conflict detection.

    - strips /* ... */ comments outside strings
    - collapses whitespace
    """
    s = _strip_block_comments_outside_strings(selector_item or "")
    return _norm_ws(s)


def normalize_at_prelude(prelude: str) -> str:
    """Normalize an at-rule prelude for stack matching."""
    return _norm_ws(prelude)


def collect_selector_item_bodies(css: str) -> Dict[Tuple[Tuple[str, ...], str], List[str]]:
    """Collect selector-item -> body mappings from a stylesheet.

    Keys are (at_rule_stack, normalized_selector_item). The stack contains
    normalized at-rule preludes such as "@media (max-width: 600px)".

    Bodies are returned as raw body strings (not normalized).
    """
    out: Dict[Tuple[Tuple[str, ...], str], List[str]] = {}

    def rec(css_text: str, stack: Tuple[str, ...] = ()) -> None:
        for node in _parse_css_nodes(css_text or ""):
            if isinstance(node, CssStmt):
                continue
            pre0 = (node.prelude or "").strip()
            if pre0.startswith("@"):
                rec(node.body, stack + (normalize_at_prelude(pre0),))
                continue

            for item in _split_selector_list(pre0):
                k = normalize_selector_item(item)
                if not k:
                    continue
                key = (stack, k)
                out.setdefault(key, []).append(node.body)

    rec(css)
    return out


def remove_selector_items_by_keys(css: str, keys_to_remove: Set[Tuple[Tuple[str, ...], str]]) -> str:
    """Remove selector items matching keys from a stylesheet.

    This is used for copy-tile-css overwrite/merge to remove conflicting
    destination selector items while preserving any other selector items in a
    comma-separated list.
    """
    if not css or not keys_to_remove:
        return css

    def rec(nodes: List[CssNode], stack: Tuple[str, ...] = ()) -> Tuple[List[CssNode], bool]:
        changed = False
        out_nodes: List[CssNode] = []
        for node in nodes:
            if isinstance(node, CssStmt):
                out_nodes.append(node)
                continue

            pre0 = (node.prelude or "").strip()
            if pre0.startswith("@"):
                inner_nodes = _parse_css_nodes(node.body)
                inner_out, inner_changed = rec(inner_nodes, stack + (normalize_at_prelude(pre0),))
                if inner_out:
                    out_nodes.append(CssBlock(prelude=node.prelude, body=_render_css_nodes(inner_out).rstrip()))
                changed = changed or inner_changed
                continue

            items = _split_selector_list(pre0)
            kept: List[str] = []
            for it in items:
                k = normalize_selector_item(it)
                if (stack, k) in keys_to_remove:
                    changed = True
                    continue
                kept.append(it)

            if not kept:
                changed = True
                continue
            if len(kept) != len(items):
                out_nodes.append(CssBlock(prelude=", ".join([s.strip() for s in kept if s.strip()]), body=node.body))
                changed = True
            else:
                out_nodes.append(node)

        return out_nodes, changed

    nodes0 = _parse_css_nodes(css)
    nodes1, _changed = rec(nodes0)
    return _render_css_nodes(nodes1)


def drop_selector_items_by_keys(css: str, keys_to_drop: Set[Tuple[Tuple[str, ...], str]]) -> Tuple[str, int]:
    """Drop selector items matching keys from a stylesheet.

    Returns (new_css, kept_selector_block_count). CssStmt statements are
    preserved. At-rule blocks are preserved if their resulting body contains at
    least one selector block or nested at-rule block.
    """
    if not css:
        return ("", 0)

    kept_blocks = 0

    def rec(nodes: List[CssNode], stack: Tuple[str, ...] = ()) -> List[CssNode]:
        nonlocal kept_blocks
        out_nodes: List[CssNode] = []
        for node in nodes:
            if isinstance(node, CssStmt):
                out_nodes.append(node)
                continue

            pre0 = (node.prelude or "").strip()
            if pre0.startswith("@"):
                inner_nodes = _parse_css_nodes(node.body)
                inner_out = rec(inner_nodes, stack + (normalize_at_prelude(pre0),))
                # Keep @-rule blocks only if they contain at least one CssBlock after filtering.
                if any(isinstance(n, CssBlock) for n in inner_out):
                    out_nodes.append(CssBlock(prelude=node.prelude, body=_render_css_nodes(inner_out).rstrip()))
                continue

            items = _split_selector_list(pre0)
            kept: List[str] = []
            for it in items:
                k = normalize_selector_item(it)
                if (stack, k) in keys_to_drop:
                    continue
                kept.append(it)

            if not kept:
                continue
            kept_blocks += 1
            out_nodes.append(CssBlock(prelude=", ".join([s.strip() for s in kept if s.strip()]), body=node.body))

        return out_nodes

    nodes0 = _parse_css_nodes(css)
    nodes1 = rec(nodes0)
    return (_render_css_nodes(nodes1).strip(), kept_blocks)

def max_tile_id_in_css(css: str) -> int:
    ids = tile_ids_in_css(css)
    return max(ids) if ids else 0


def orphan_tile_ids_in_css(css: str, existing_tile_ids: Set[int]) -> Set[int]:
    """Return tile IDs referenced in CSS that are not present in the layout tiles."""
    if not css:
        return set()
    return {i for i in tile_ids_in_css(css) if i not in existing_tile_ids}


def selector_tile_ids_in_css(css: str) -> Set[int]:
    """Return tile ids referenced in selector preludes only.

    Used for "does a selector for #tile-N already exist" checks.
    Standalone comments are ignored.
    """
    if not css:
        return set()

    def collect(css_text: str) -> Set[int]:
        out: Set[int] = set()
        for node in _parse_css_nodes(css_text):
            if isinstance(node, CssStmt):
                continue
            prelude = (node.prelude or "").strip()
            if prelude.startswith("@"):
                out |= collect(node.body)
                continue
            pre_no_comments = _strip_block_comments_outside_strings(node.prelude or "")
            for sel in _split_selector_list(pre_no_comments.strip()):
                out |= _selector_tile_ids(sel)
        return out

    return collect(css)


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

def _collapse_ws_one_line(text: str) -> str:
    """Collapse whitespace to a single line, preserving strings and comment blocks."""
    if not text:
        return ""
    s = text
    out: List[str] = []
    i = 0
    n = len(s)
    in_str: Optional[str] = None
    while i < n:
        ch = s[i]
        # strings
        if in_str is not None:
            out.append(ch)
            if ch == "\\" and (i + 1) < n:
                out.append(s[i + 1])
                i += 2
                continue
            if ch == in_str:
                in_str = None
            i += 1
            continue
        if ch in ("'", '"'):
            in_str = ch
            out.append(ch)
            i += 1
            continue

        # comment
        if ch == "/" and (i + 1) < n and s[i + 1] == "*":
            endc = s.find("*/", i + 2)
            if endc == -1:
                seg = s[i:]
                seg = re.sub(r"\s+", " ", seg)
                out.append(seg)
                break
            seg = s[i : endc + 2]
            seg = re.sub(r"\s+", " ", seg.replace("\r", " ").replace("\n", " "))
            out.append(seg)
            i = endc + 2
            continue

        # whitespace
        if ch.isspace():
            if out and out[-1] != " ":
                out.append(" ")
            i += 1
            continue

        out.append(ch)
        i += 1

    return "".join(out).strip()


def _normalize_selector_pre(prelude: str) -> str:
    pre = (prelude or "").strip()
    if not pre:
        return ""
    if pre.startswith("@"):
        return re.sub(r"\s+", " ", pre).strip()
    items = _split_selector_list(pre)
    return ", ".join([it.strip() for it in items if it.strip()])


def _comment_sort_key(comment_text: str) -> str:
    inner = _comment_inner_text(comment_text)
    if _looks_like_css_rules(inner):
        try:
            for n in _parse_css_nodes(inner):
                if isinstance(n, CssBlock):
                    pre0 = (n.prelude or "").strip()
                    if pre0.startswith("@"): 
                        continue
                    return _normalize_selector_pre(pre0)
        except Exception:
            pass
    # Fallback: first tile id (if any), then raw text.
    ids = sorted(_tile_ids_in_comment_text(comment_text))
    if ids:
        return f"tile-{ids[0]:09d}"
    return _collapse_ws_one_line(comment_text)


def _sort_key_for_comment_line(comment_line: str) -> str:
    """Return a stable sort key for a standalone comment line in compact_css.

    Requirements:
      - Commented-out rules (/* selector { ... } */) should be sorted as if they
        were not commented out.
      - Standalone comments that reference a tile id (e.g. "tile-125") should
        sort alongside the rules for that tile id.

    Implementation notes:
      - If the comment contains CSS rule blocks, derive the key from the first
        non-@ selector found.
      - Otherwise, if the comment mentions a tile id, derive the key from that
        tile selector.
      - Otherwise, treat it as "everything else".
    """
    line = (comment_line or "").strip()
    inner = _comment_inner_text(line)

    # 1) Commented-out CSS rules: sort by the first selector found.
    if _looks_like_css_rules(inner):
        try:
            for n in _parse_css_nodes(inner):
                if isinstance(n, CssBlock):
                    pre0 = (n.prelude or "").strip()
                    if not pre0 or pre0.startswith("@"): 
                        continue
                    sel_items = _split_selector_list(_normalize_selector_pre(pre0))
                    first_sel = (sel_items[0].strip() if sel_items else "")
                    if first_sel:
                        base = _sort_key_for_selector(first_sel)
                        return f"{base} ~comment"
        except Exception:
            pass

    # 2) Plain comments with tile references: pin to the first tile id.
    ids = sorted(_tile_ids_in_comment_text(line))
    if ids:
        base = _sort_key_for_selector(f"#tile-{ids[0]}")
        return f"{base} ~comment"

    # 3) Fallback: treat as "everything else".
    return f"0 {_collapse_ws_one_line(line)}"


def _sort_key_for_selector(selector: str) -> str:
    """Return a stable sort key for a selector line.

    Sort order for compact_css output:
      0) Everything else.
      1) Lines whose selector starts with '.' (class selectors) EXCLUDING
         actual tile selectors like '.tile-N'.
      2) Tile selectors (#tile-N or .tile-N), sorted numerically by N.

    Note:
      This matches the user-facing documentation ordering of categories as
      (3) then (1) then (2).
    """
    s = _strip_block_comments_outside_strings(selector or "").strip()
    m = re.search(r"(?:#tile-|\.tile-)(\d+)\b", s)
    if m:
        try:
            tid = int(m.group(1))
            return f"2 tile-{tid:09d} {s}"
        except Exception:
            pass

    # Non-tile class selectors should appear before tile selectors.
    if s.startswith("."):
        return f"1 {s}"

    return f"0 {s}"

def compact_css_stylesheet(css: str) -> str:
    """Compact and sort a stylesheet.

    - Selector rules are rendered one per line: <selector> { <body> }
    - Selector lists are split into individual selector rules.
    - Rule bodies are collapsed to a single line.
    - Top-level rules are sorted by selector; @-blocks are sorted by prelude.
    - Rules inside @-blocks are compacted and sorted recursively.

    Notes:
      - Standalone comments are preserved (one line), but may not start with a selector.
      - This is intended as a readability/diffing aid, not a full CSS formatter.
    """
    if not css:
        return ""

    def compact_nodes(nodes: Sequence[CssNode], indent: str = "") -> List[Tuple[str, str]]:
        imports: List[Tuple[str, str]] = []
        items: List[Tuple[str, str]] = []

        for node in nodes:
            if isinstance(node, CssStmt):
                t = (node.text or "").strip()
                if not t:
                    continue
                line = _collapse_ws_one_line(t)
                if line.lower().startswith("@import"):
                    imports.append((line.lower(), indent + line))
                    continue
                if line.startswith("/*"):
                    key = _sort_key_for_comment_line(line)
                else:
                    key = f"4 {line}"
                items.append((key, indent + line))
                continue

            pre0 = _normalize_selector_pre(node.prelude)
            if not pre0:
                continue

            if pre0.startswith("@"): 
                inner_items = compact_nodes(_parse_css_nodes(node.body), indent + "  ")
                # Render the block with inner lines already compacted.
                inner_text = "\n".join([t for _k, t in inner_items])
                block_lines = [f"{indent}{pre0} {{"]
                if inner_text.strip():
                    block_lines.append(inner_text)
                block_lines.append(f"{indent}}}")
                items.append((f"2 {pre0}", "\n".join(block_lines)))
                continue

            body1 = _collapse_ws_one_line(node.body)
            # Split selector lists into one rule per selector.
            for sel in _split_selector_list(pre0):
                sel0 = sel.strip()
                if not sel0:
                    continue
                txt = f"{indent}{sel0} {{ {body1} }}" if body1 else f"{indent}{sel0} {{ }}"
                key = _sort_key_for_selector(sel0)
                items.append((key, txt))

        # Sort imports at top, then everything else.
        imports_sorted = sorted(imports, key=lambda x: x[0])
        items_sorted = sorted(items, key=lambda x: (x[0], x[1]))
        return imports_sorted + items_sorted

    top = compact_nodes(_parse_css_nodes(css), indent="")
    out = "\n".join([t for _k, t in top]).rstrip() + "\n"
    return out

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

        selectors = _split_selector_list(pre)
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
        # Only consider selectors that already exist in dest_css.
        existing_selector_ids = selector_tile_ids_in_css(dest_css)
        for new_id in set(id_map.values()):
            if new_id in existing_selector_ids:
                skip_new.add(new_id)

    # Pre-scan: determine which *new* tile ids will actually receive duplicated
    # selector rules. Standalone comments are only duplicated when a tile also
    # receives real selector rules.
    def predict_new_ids(css_text: str) -> Set[int]:
        predicted: Set[int] = set()
        for n in _parse_css_nodes(css_text):
            if isinstance(n, CssStmt):
                continue
            pre0 = (n.prelude or "").strip()
            if pre0.startswith("@"): 
                predicted |= predict_new_ids(n.body)
                continue
            selectors0 = _split_selector_list(pre0)
            for sel0 in selectors0:
                sel_ids0 = _selector_tile_ids(sel0)
                for oid0 in sel_ids0:
                    if oid0 in id_map:
                        nid0 = id_map[oid0]
                        if nid0 not in skip_new:
                            predicted.add(nid0)
        return predicted

    predicted_new_ids = predict_new_ids(source_css)

    nodes = _parse_css_nodes(source_css)
    out_nodes: List[CssNode] = []
    dup_comment_done: Set[Tuple[int, int]] = set()

    for node in nodes:
        if isinstance(node, CssStmt):
            # Standalone comments are normally not copied.
            #
            # Two exceptions:
            #  (1) Commented-out tile-specific CSS rules: if the comment contains
            #      CSS blocks (e.g. /* #tile-40 { ... } */), duplicate those rules
            #      exactly as normal (selector-item splitting + body tile-id
            #      rewrite), but keep them commented out.
            #  (2) Note-style standalone comments that mention a copied tile id:
            #      duplicate once per (old->new) only if the new tile will receive
            #      other selector rules, and annotate.
            if node.text.lstrip().startswith("/*"):
                dup_rules_comment = _duplicate_comment_css_rules(node.text, id_map, skip_new=skip_new)
                if dup_rules_comment:
                    out_nodes.append(CssStmt(dup_rules_comment))
                else:
                    cids = _tile_ids_in_comment_text(node.text)
                    for oid in sorted(cids):
                        if oid not in id_map:
                            continue
                        nid = id_map[oid]
                        if nid in skip_new:
                            continue
                        if nid not in predicted_new_ids:
                            continue
                        key = (oid, nid)
                        if key in dup_comment_done:
                            continue
                        out_nodes.append(CssStmt(_duplicate_standalone_comment(node.text, oid, nid)))
                        dup_comment_done.add(key)
            continue

        pre = node.prelude.strip()
        if pre.startswith("@"): 
            inner = generate_css_for_id_map(node.body, id_map, dest_css=dest_css)
            if inner.strip():
                out_nodes.append(CssBlock(prelude=node.prelude, body=inner.rstrip()))
            continue

        selectors = _split_selector_list(pre)

        # Emit one duplicated block per (old_id -> new_id) match.
        # This matches the documented behavior and enables safe body rewrites
        # of tile-OLD tokens when the selector is tied to OLD.
        emitted_any = False
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
                new_body = _replace_tile_id_in_body(node.body, oid, nid)
                out_nodes.append(CssBlock(prelude=new_sel, body=new_body))
                emitted_any = True

        if not emitted_any:
            continue

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
