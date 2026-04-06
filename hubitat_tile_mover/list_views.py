from __future__ import annotations

from typing import Any, Dict, List, Tuple, Set

from .sort_tiles import sort_tiles
from .tiles import as_int, rect
from .geometry import rects_overlap, ranges_overlap
from .util import die
from .css_ops import CssStmt, _parse_css_nodes, _selector_tile_ids, _split_selector_list, _strip_block_comments_outside_strings

Rect = Tuple[int, int, int, int]

def _span(t: Dict[str, Any]) -> tuple[int,int,int,int]:
    r1, r2, c1, c2 = rect(t)
    return r1, r2, c1, c2

def _area(t: Dict[str, Any]) -> int:
    r1, r2, c1, c2 = _span(t)
    return (r2-r1+1)*(c2-c1+1)

def _contains(a: Rect, b: Rect) -> bool:
    return a[0] <= b[0] and a[1] >= b[1] and a[2] <= b[2] and a[3] >= b[3]

def _same(a: Rect, b: Rect) -> bool:
    return a == b

def _pair_relation(a: Rect, b: Rect) -> str | None:
    if not rects_overlap(a, b):
        return None
    if _same(a,b):
        return 'same'
    if _contains(a,b):
        return 'contains'
    if _contains(b,a):
        return 'inside'
    return 'overlaps'

def parse_list_tiles_spec(spec: str | None) -> tuple[str, str]:
    raw = (spec or 'plain:rci').strip()
    if not raw:
        raw = 'plain:rci'
    parts = raw.split(':', 1)
    kind = parts[0].strip().lower() or 'plain'
    sort_spec = (parts[1].strip() if len(parts) > 1 and parts[1].strip() else 'rci')
    valid = {'plain','tree','overlap','nested','conflicts'}
    if kind not in valid:
        die(f"Invalid --list_tiles '{spec}'. Use plain, tree, overlap, nested, or conflicts.")
    return kind, sort_spec



def _count_tile_scoped_rules(css: str) -> Dict[int, int]:
    counts: Dict[int, int] = {}
    if not css:
        return counts

    def rec(css_text: str) -> None:
        for node in _parse_css_nodes(css_text):
            if isinstance(node, CssStmt):
                continue
            prelude = (node.prelude or '').strip()
            if prelude.startswith('@'):
                rec(node.body)
                continue
            pre_no_comments = _strip_block_comments_outside_strings(node.prelude or '')
            ids: Set[int] = set()
            for sel in _split_selector_list(pre_no_comments.strip()):
                ids |= _selector_tile_ids(sel)
            for tid in ids:
                counts[tid] = counts.get(tid, 0) + 1

    rec(css)
    return counts


def _placement_map(tiles: List[Dict[str, Any]]) -> Dict[int, str]:
    rects = {as_int(t, 'id'): _span(t) for t in tiles}
    ids = sorted(rects)
    has_parent = {tid: False for tid in ids}
    has_child = {tid: False for tid in ids}
    has_partial = {tid: False for tid in ids}

    for i, aid in enumerate(ids):
        ra = rects[aid]
        for bid in ids[i+1:]:
            rb = rects[bid]
            rel = _pair_relation(ra, rb)
            if rel == 'contains':
                has_child[aid] = True
                has_parent[bid] = True
            elif rel == 'inside':
                has_parent[aid] = True
                has_child[bid] = True
            elif rel in ('overlaps', 'same'):
                has_partial[aid] = True
                has_partial[bid] = True

    placement: Dict[int, str] = {}
    for tid in ids:
        if has_parent[tid]:
            placement[tid] = 'nested'
        elif has_child[tid]:
            placement[tid] = 'container'
        elif has_partial[tid]:
            placement[tid] = 'overlapping'
        else:
            placement[tid] = 'independent'
    return placement


def _tile_rows_for_table(tiles: List[Dict[str, Any]], css_text: str = '') -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    placement = _placement_map(tiles)
    css_counts = _count_tile_scoped_rules(css_text)
    for t in tiles:
        tid = as_int(t, 'id')
        r1, r2, c1, c2 = _span(t)
        rs = r2 - r1 + 1
        cs = c2 - c1 + 1
        tpl = '' if t.get('template') in (None, '') else str(t.get('template'))
        dev = '' if t.get('device') in (None, '') else str(t.get('device'))
        rows.append({
            'tile_id': str(tid),
            'row': str(r1),
            'col': str(c1),
            'height': str(rs),
            'width': str(cs),
            'placement': placement.get(tid, 'independent'),
            'device': dev,
            'template': tpl,
            'css_rules': str(css_counts.get(tid, 0)),
        })
    return rows


def _plain_sort_value(key: str, row: Dict[str, str]):
    if key in {'tile_id', 'row', 'col', 'height', 'width', 'css_rules'}:
        return int(row[key] or 0)
    val = row[key].strip().lower()
    if key == 'device' and val.isdigit():
        return (0, int(val))
    return (1, val)


def _parse_plain_sort_spec(user_spec: str) -> List[Tuple[str, bool]]:
    spec = (user_spec or '').strip().lower()
    if spec == '':
        spec = 'rci'
    valid = {'i', 'r', 'c', 'h', 'w', 'p', 'd', 't', 's'}
    out: List[Tuple[str, bool]] = []
    seen: set[str] = set()
    desc_next = False
    for ch in spec:
        if ch in (' ', '\t', ',', ';', ':', '_', '/', '\\', '.'):
            continue
        if ch == '-':
            desc_next = True
            continue
        if ch not in valid:
            die(
                f"Invalid --list_tiles plain sort '{user_spec}'. Use keys i,r,c,h,w,p,d,t,s and optional '-' for descending. "
                f"Examples: --list_tiles:plain:rci, --list_tiles:plain:-hwi, --list_tiles:plain:-s-r"
            )
        if ch in seen:
            die(f"Invalid --list_tiles plain sort '{user_spec}'. Keys must not repeat.")
        out.append((ch, desc_next))
        seen.add(ch)
        desc_next = False
    if desc_next:
        die(f"Invalid --list_tiles plain sort '{user_spec}'. Trailing '-' must be followed by a key.")
    for k in ['r', 'c', 'i']:
        if k not in seen:
            out.append((k, False))
    return out


def _sort_plain_rows(rows: List[Dict[str, str]], sort_spec: str) -> List[Dict[str, str]]:
    key_map = {
        'i': 'tile_id',
        'r': 'row',
        'c': 'col',
        'h': 'height',
        'w': 'width',
        'p': 'placement',
        'd': 'device',
        't': 'template',
        's': 'css_rules',
    }
    parsed = list(reversed(_parse_plain_sort_spec(sort_spec)))
    out = list(rows)
    for k, desc in parsed:
        field = key_map[k]
        out.sort(key=lambda row, f=field: _plain_sort_value(f, row), reverse=desc)
    return out


def _render_plain_table(tiles: List[Dict[str, Any]], sort_spec: str, css_text: str = '') -> str:
    rows = _tile_rows_for_table(list(tiles), css_text)
    rows = _sort_plain_rows(rows, sort_spec)
    headers = ['Tile ID', 'Row', 'Col', 'Height', 'Width', 'Placement', 'Device', 'Template', 'CSS Rules']
    keys = ['tile_id', 'row', 'col', 'height', 'width', 'placement', 'device', 'template', 'css_rules']
    numeric_keys = {'tile_id', 'row', 'col', 'height', 'width', 'css_rules'}
    widths: Dict[str, int] = {}
    for h, k in zip(headers, keys):
        widths[k] = max(len(h), max((len(r[k]) for r in rows), default=0))

    def fmt_row(row: Dict[str, str] | None = None, *, header: bool = False) -> str:
        vals = {k: (h if header else (row[k] if row is not None else '')) for h, k in zip(headers, keys)}
        parts: List[str] = []
        for h, k in zip(headers, keys):
            val = vals[k]
            if header:
                parts.append(val.ljust(widths[k]))
            elif k in numeric_keys:
                parts.append(val.rjust(widths[k]))
            else:
                parts.append(val.ljust(widths[k]))
        return '  '.join(parts).rstrip()

    divider = '  '.join(('-' * widths[k]) for k in keys).rstrip()
    out: List[str] = [f"TILE LIST (plain, sort={sort_spec})", fmt_row(header=True), divider]
    for row in rows:
        out.append(fmt_row(row))
    return "\n".join(out) + "\n"
def _tile_line(t: Dict[str, Any], prefix: str = '') -> str:
    r1,r2,c1,c2 = _span(t)
    rs = r2-r1+1
    cs = c2-c1+1
    extra = []
    tpl = t.get('template')
    dev = t.get('device')
    if tpl not in (None, ''):
        extra.append(f"template={tpl}")
    if dev not in (None, ''):
        extra.append(f"device={dev}")
    extra_s = ('  ' + '  '.join(extra)) if extra else ''
    return f"{prefix}tile-{as_int(t,'id')}  r={r1} c={c1}  rs={rs} cs={cs}  span=r{r1}..{r2},c{c1}..{c2}{extra_s}"

def _components(tiles: List[Dict[str, Any]], include_contains: bool=True, conflicts_only: bool=False) -> List[List[Dict[str, Any]]]:
    n = len(tiles)
    adj = {i:set() for i in range(n)}
    rects = [_span(t) for t in tiles]
    for i in range(n):
        for j in range(i+1,n):
            rel = _pair_relation(rects[i], rects[j])
            if rel is None:
                continue
            if conflicts_only and rel in ('contains','inside'):
                continue
            if (not include_contains) and rel in ('contains','inside','same'):
                continue
            adj[i].add(j); adj[j].add(i)
    seen=set(); out=[]
    for i in range(n):
        if i in seen or not adj[i]:
            continue
        stack=[i]; seen.add(i); comp=[]
        while stack:
            cur=stack.pop(); comp.append(tiles[cur])
            for nb in adj[cur]:
                if nb not in seen:
                    seen.add(nb); stack.append(nb)
        out.append(comp)
    return out

def _build_nested_roots(comp: List[Dict[str, Any]], sort_spec: str) -> List[Dict[str, Any]]:
    ordered = sort_tiles(comp, sort_spec)
    ordered = sorted(ordered, key=lambda t: (-_area(t), as_int(t,'row'), as_int(t,'col'), as_int(t,'id')))
    return ordered

def _render_nested_tree(comp: List[Dict[str, Any]], sort_spec: str, include_overlap_notes: bool=True) -> List[str]:
    rects = {id(t): _span(t) for t in comp}
    by_id = {as_int(t,'id'): t for t in comp}
    children: dict[int, list[tuple[Dict[str, Any], str]]] = {as_int(t,'id'): [] for t in comp}
    parent: dict[int, int] = {}
    overlap_notes: dict[int, list[str]] = {as_int(t,'id'): [] for t in comp}

    ordered = sorted(comp, key=lambda t: (_area(t), as_int(t,'row'), as_int(t,'col'), as_int(t,'id')))
    for t in ordered:
        tid = as_int(t,'id')
        tr = rects[id(t)]
        candidates = []
        for p in comp:
            pid = as_int(p,'id')
            if pid == tid:
                continue
            pr = rects[id(p)]
            if _contains(pr, tr) and not _same(pr, tr):
                candidates.append(p)
        if candidates:
            best = min(candidates, key=lambda p: (_area(p), as_int(p,'row'), as_int(p,'col'), as_int(p,'id')))
            pid = as_int(best,'id')
            parent[tid] = pid
            children[pid].append((t, 'inside'))

    if include_overlap_notes:
        ids = [as_int(t,'id') for t in comp]
        for i, aid in enumerate(ids):
            for bid in ids[i+1:]:
                if parent.get(aid) == bid or parent.get(bid) == aid:
                    continue
                rel = _pair_relation(rects[id(by_id[aid])], rects[id(by_id[bid])])
                if rel in ('overlaps', 'same'):
                    overlap_notes[aid].append(f"tile-{bid} [{rel}]")
                    overlap_notes[bid].append(f"tile-{aid} [{rel}]")

    for k in children:
        children[k].sort(key=lambda item: (as_int(item[0],'row'), as_int(item[0],'col'), as_int(item[0],'id'), item[1]))

    roots = [t for t in sorted(comp, key=lambda t: (as_int(t,'row'), as_int(t,'col'), as_int(t,'id'))) if as_int(t,'id') not in parent]
    lines = []
    visited: set[int] = set()

    def walk(t: Dict[str, Any], prefix: str='', is_last: bool=True, note: str | None=None, root: bool=False) -> None:
        tid = as_int(t,'id')
        connector = '' if root else ('└─ ' if is_last else '├─ ')
        suffix_parts = []
        if note:
            suffix_parts.append(note)
        if overlap_notes.get(tid):
            suffix_parts.append('refs: ' + ', '.join(sorted(overlap_notes[tid])))
        suffix = '' if not suffix_parts else '  [' + '; '.join(suffix_parts) + ']'
        if tid in visited:
            lines.append(prefix + connector + _tile_line(t) + '  [ref]')
            return
        visited.add(tid)
        lines.append(prefix + connector + _tile_line(t) + suffix)
        kids = children.get(tid, [])
        child_prefix = prefix + ('' if root else ('   ' if is_last else '│  '))
        for idx, (child, rel) in enumerate(kids):
            walk(child, child_prefix, idx == len(kids)-1, rel, False)

    for idx, t in enumerate(roots):
        walk(t, '', idx == len(roots)-1, None, True)
    return lines

def render_list_tiles(tiles: List[Dict[str, Any]], spec: str | None, css_text: str = "") -> str:
    kind, sort_spec = parse_list_tiles_spec(spec)
    lines: List[str] = []
    if kind == 'plain':
        return _render_plain_table(tiles, sort_spec, css_text)
    ordered = sort_tiles(list(tiles), sort_spec)
    comps_all = _components(ordered, include_contains=True, conflicts_only=False)
    comps_nested = []
    for comp in comps_all:
        rects = [_span(t) for t in comp]
        if any((_contains(rects[i], rects[j]) or _contains(rects[j], rects[i])) and not _same(rects[i],rects[j]) for i in range(len(comp)) for j in range(i+1,len(comp)) if rects_overlap(rects[i], rects[j])):
            comps_nested.append(comp)
    comps_conflicts = _components(ordered, include_contains=True, conflicts_only=True)
    if kind == 'overlap':
        lines.append(f"TILE LIST ({kind}, sort={sort_spec})")
        if not comps_all:
            lines.append('(no overlap groups)')
        for idx,comp in enumerate(comps_all):
            lines.append(f"Group {idx+1}")
            for line in _render_nested_tree(comp, sort_spec, include_overlap_notes=True):
                lines.append(line)
        return "\n".join(lines) + "\n"
    if kind == 'nested':
        lines.append(f"TILE LIST ({kind}, sort={sort_spec})")
        if not comps_nested:
            lines.append('(no nested groups)')
        for idx,comp in enumerate(comps_nested):
            lines.append(f"Group {idx+1}")
            for line in _render_nested_tree(comp, sort_spec, include_overlap_notes=False):
                lines.append(line)
        return "\n".join(lines) + "\n"
    if kind == 'conflicts':
        lines.append(f"TILE LIST ({kind}, sort={sort_spec})")
        if not comps_conflicts:
            lines.append('(no conflict groups)')
        for idx,comp in enumerate(comps_conflicts):
            lines.append(f"Group {idx+1}")
            for line in _render_nested_tree(comp, sort_spec, include_overlap_notes=True):
                lines.append(line)
        return "\n".join(lines) + "\n"
    # tree
    lines.append(f"TILE LIST ({kind}, sort={sort_spec})")
    if comps_all:
        involved = {id(t) for comp in comps_all for t in comp}
        roots = [t for t in ordered if id(t) not in involved]
        if roots:
            lines.append('Independent tiles')
            for t in roots:
                lines.append(_tile_line(t))
        for idx,comp in enumerate(comps_all):
            lines.append(f"Group {idx+1}")
            for line in _render_nested_tree(comp, sort_spec, include_overlap_notes=True):
                lines.append(line)
    else:
        for t in ordered:
            lines.append(_tile_line(t))
    return "\n".join(lines) + "\n"


def render_abort_conflicts(
    moving_tiles: List[Dict[str, Any]],
    stationary_tiles: List[Dict[str, Any]],
    conflicts_by_mid: Dict[int, List[Tuple[int, Rect]]],
    *,
    action_word: str = 'move',
    sort_spec: str = 'rci',
    detail_level: str = 'summary',
) -> str:
    """Render a preflight conflict report for aborted layout actions."""

    def _fmt_range(a: int, b: int, noun_singular: str, noun_plural: str | None = None) -> str:
        noun_plural = noun_plural or (noun_singular + 's')
        if a == b:
            return f"{noun_singular} {a}"
        return f"{noun_plural} {a}-{b}"

    def _merge_int_ranges(values: List[int]) -> List[Tuple[int, int]]:
        vals = sorted(set(int(v) for v in values))
        if not vals:
            return []
        out: List[Tuple[int, int]] = []
        s = e = vals[0]
        for v in vals[1:]:
            if v == e + 1:
                e = v
            else:
                out.append((s, e))
                s = e = v
        out.append((s, e))
        return out

    def _fmt_row_ranges(ranges: List[Tuple[int, int]]) -> str:
        parts: List[str] = []
        for a, b in ranges:
            if a == b:
                parts.append(str(a))
            else:
                parts.append(f"{a}-{b}")
        if not parts:
            return ''
        if len(parts) == 1:
            return f"row {parts[0]}" if '-' not in parts[0] else f"rows {parts[0]}"
        if len(parts) == 2:
            return f"rows {parts[0]} and {parts[1]}"
        return "rows " + ", ".join(parts[:-1]) + f", and {parts[-1]}"

    def _build_summary_lines() -> List[str]:
        rects: List[Rect] = []
        for entries in conflicts_by_mid.values():
            rects.extend(orect for _, orect in entries)
        if not rects:
            return [f"The {action_word} operation could not complete because of conflicts."]
        by_cols: Dict[Tuple[int, int], Set[int]] = {}
        for r1, r2, c1, c2 in rects:
            rows = by_cols.setdefault((c1, c2), set())
            rows.update(range(r1, r2 + 1))
        groups = sorted(by_cols.items(), key=lambda kv: (kv[0][0], kv[0][1]))
        lines = [f"The {action_word} operation could not complete because of conflicts in:"]
        for idx, ((c1, c2), rows) in enumerate(groups, 1):
            row_ranges = _merge_int_ranges(sorted(rows))
            col_label = _fmt_range(c1, c2, 'column')
            row_label = _fmt_row_ranges(row_ranges)
            lines.append(f"{idx}) {col_label} at {row_label}")
        lines.append('')
        lines.append('Use --allow_overlap to force the action, or --skip_overlap to skip only the blocked tiles.')
        lines.append('Use --show_map:conflicts to view the conflict area.')
        lines.append('Use --verbose for detailed conflict pairs, or --debug for full diagnostic output.')
        return lines

    def _build_legacy_lines() -> List[str]:
        sample = list(conflicts_by_mid.items())[:10]
        details = '; '.join([
            f"{action_word} id={mid} conflicts at r{entries[0][1][0]}..{entries[0][1][1]},c{entries[0][1][2]}..{entries[0][1][3]} with {[sid for sid,_ in entries]}"
            for mid, entries in sample
        ])
        more = '' if len(conflicts_by_mid) <= 10 else f" (and {len(conflicts_by_mid) - 10} more)"
        return [
            f"Destination conflicts detected. Re-run with --allow_overlap or --skip_overlap. {details}{more}"
        ]

    if detail_level == 'summary':
        return '\n'.join(_build_summary_lines()) + '\n'
    if detail_level == 'legacy':
        return '\n'.join(_build_legacy_lines()) + '\n'

    moving_by_id = {as_int(t, 'id'): t for t in moving_tiles}
    stationary_by_id = {as_int(t, 'id'): t for t in stationary_tiles}

    nodes: Set[tuple[str, int]] = set()
    adj: Dict[tuple[str, int], Set[tuple[str, int]]] = {}
    overlap_rects: Dict[frozenset, List[Rect]] = {}

    def add_edge(a: tuple[str, int], b: tuple[str, int], orect: Rect) -> None:
        nodes.add(a); nodes.add(b)
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
        overlap_rects.setdefault(frozenset((a, b)), []).append(orect)

    for mid, entries in conflicts_by_mid.items():
        for sid, orect in entries:
            add_edge(('moving', int(mid)), ('stationary', int(sid)), orect)

    comps: List[List[tuple[str, int]]] = []
    seen: Set[tuple[str, int]] = set()
    for node in sorted(nodes):
        if node in seen:
            continue
        stack = [node]
        seen.add(node)
        comp: List[tuple[str, int]] = []
        while stack:
            cur = stack.pop()
            comp.append(cur)
            for nb in adj.get(cur, set()):
                if nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        comps.append(comp)

    def node_tile(node: tuple[str, int]) -> Dict[str, Any]:
        kind, tid = node
        return moving_by_id[tid] if kind == 'moving' else stationary_by_id[tid]

    def rect_bounds(rects: List[Rect]) -> Rect:
        return (
            min(r[0] for r in rects),
            max(r[1] for r in rects),
            min(r[2] for r in rects),
            max(r[3] for r in rects),
        )

    def classify_group(comp: List[tuple[str, int]]) -> tuple[str, str]:
        same_origin = False
        exact_dup = False
        partial = False
        overlap_count = 0
        for a in comp:
            for b in adj.get(a, set()):
                if a >= b:
                    continue
                ta = node_tile(a); tb = node_tile(b)
                ra = _span(ta); rb = _span(tb)
                overlap_count += 1
                if ra[0] == rb[0] and ra[2] == rb[2]:
                    same_origin = True
                if _same(ra, rb):
                    exact_dup = True
                elif not _contains(ra, rb) and not _contains(rb, ra):
                    partial = True
        if exact_dup:
            return ('exact duplicate footprint', 'high')
        if partial and same_origin:
            return ('same-origin overlap cluster', 'high')
        if same_origin:
            return ('same-origin cluster', 'medium')
        if partial:
            return ('partial overlap cluster', 'high')
        return ('nested/contained conflict cluster', 'medium')

    def tile_summary_line(t: Dict[str, Any], role: str, rel_notes: List[str] | None = None) -> str:
        r1, r2, c1, c2 = _span(t)
        rs = r2 - r1 + 1
        cs = c2 - c1 + 1
        note = ''
        if rel_notes:
            note = '  ' + '; '.join(rel_notes)
        return f"  - tile-{as_int(t,'id'):>4}  {role:<8} row={r1} col={c1} rs={rs} cs={cs}  span=r{r1}..{r2},c{c1}..{c2}{note}"

    lines: List[str] = []
    total_moving = len(conflicts_by_mid)
    total_pairs = sum(len(v) for v in conflicts_by_mid.values())
    lines.append('CONFLICT DETAILS')
    lines.append(f"Action aborted: destination conflicts detected during {action_word}.")
    lines.append(f"Groups: {len(comps)}  {action_word.title()} tile(s) blocked: {total_moving}  Overlap pair(s): {total_pairs}")
    lines.append('')

    for idx, comp in enumerate(comps, 1):
        moving_nodes = sorted([n for n in comp if n[0] == 'moving'], key=lambda n: (as_int(node_tile(n),'row'), as_int(node_tile(n),'col'), n[1]))
        stationary_nodes = sorted([n for n in comp if n[0] == 'stationary'], key=lambda n: (as_int(node_tile(n),'row'), as_int(node_tile(n),'col'), n[1]))
        group_overlap_rects: List[Rect] = []
        all_tile_rects: List[Rect] = []
        for node in comp:
            all_tile_rects.append(_span(node_tile(node)))
            for nb in adj.get(node, set()):
                if node < nb:
                    group_overlap_rects.extend(overlap_rects.get(frozenset((node, nb)), []))
        gb = rect_bounds(all_tile_rects) if all_tile_rects else (0,0,0,0)
        ob = rect_bounds(group_overlap_rects) if group_overlap_rects else gb
        gtype, severity = classify_group(comp)
        lines.append(f"[{idx}] {gtype}  |  severity: {severity}")
        lines.append(f"    Tile bounds:    rows {gb[0]}..{gb[1]}, cols {gb[2]}..{gb[3]}")
        lines.append(f"    Overlap bounds: rows {ob[0]}..{ob[1]}, cols {ob[2]}..{ob[3]}")
        lines.append(f"    {action_word.title()} tile(s): " + (', '.join(f"tile-{n[1]}" for n in moving_nodes) if moving_nodes else '(none)'))
        lines.append(f"    Blocking tile(s): " + (', '.join(f"tile-{n[1]}" for n in stationary_nodes) if stationary_nodes else '(none)'))
        lines.append('    Members:')
        for n in moving_nodes:
            tid = n[1]
            rels = []
            for sid, orect in sorted(conflicts_by_mid.get(tid, []), key=lambda x: x[0]):
                rels.append(f"hits tile-{sid} at r{orect[0]}..{orect[1]},c{orect[2]}..{orect[3]}")
            lines.append(tile_summary_line(node_tile(n), action_word, rels))
        for n in stationary_nodes:
            sid = n[1]
            blockers = []
            for mid, entries in sorted(conflicts_by_mid.items()):
                hits = [orect for sid2, orect in entries if sid2 == sid]
                for orect in hits:
                    blockers.append(f"blocks tile-{mid} at r{orect[0]}..{orect[1]},c{orect[2]}..{orect[3]}")
            lines.append(tile_summary_line(node_tile(n), 'blocking', blockers))
        lines.append('')

    lines.append('Re-run with --allow_overlap to force the action, or --skip_overlap to skip only the blocked tiles.')
    return "\n".join(lines) + "\n"
