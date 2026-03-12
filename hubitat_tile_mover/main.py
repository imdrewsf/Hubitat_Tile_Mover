from __future__ import annotations

import os
import sys
from typing import Dict, List, Optional, Tuple

from .util import die, ilog, prompt_yes_no, prompt_yes_no_or_die, format_id_sample, ok, warn, wlog, layout_fingerprint
from .list_views import render_list_tiles

def vlog(enabled: bool, msg: str) -> None:
    """Verbose logger."""
    if enabled:
        ilog(msg)

from .cli import build_parser
from .hubio import hub_import_layout, hub_post_layout_with_refresh
from .io_helpers import (
    assert_singleton_flags,
    normalize_argv,
    parse_import_spec,
    parse_output_to_specs,
    read_input_text,
    write_outputs,
)
from .jsonio import build_output_object, dump_json, extract_tiles_container, load_json_from_text
from .ops_clear import clear_cols, clear_range, clear_rows
from .ops_copy import copy_cols, copy_rows, copy_range
from .ops_delete import delete_cols, delete_rows
from .ops_crop import (
    crop_to_cols,
    crop_to_range,
    crop_to_rows,
    prune_devices,
    prune_except_devices,
    prune_except_ids,
    prune_ids,
    parse_prune_device_spec,
    parse_prune_id_spec,
)
from .ops_insert import insert_cols, insert_rows
from .ops_merge import merge_cols, merge_range, merge_rows
from .ops_move import move_cols, move_range, move_rows
from .ops_trim import trim_tiles
from .ops_spacing import adjust_tile_spacing, set_tile_spacing
from .map_view import render_tile_map
from .sort_tiles import complete_sort_spec, sort_tiles
from .geometry import ranges_overlap, rects_overlap
from .selectors import (
    select_tiles_by_col_range,
    select_tiles_by_rect_range,
    select_tiles_by_row_range,
    tile_matches_col_range,
    tile_matches_row_range,
)
from .tiles import verify_tiles_minimum, as_int, tile_row_extent, tile_col_extent, rect as tile_rect
from .css_ops import (
    cleanup_css_for_tile_ids,
    collect_selector_item_bodies,
    drop_selector_items_by_keys,
    filter_css_fragment_duplicates,
    find_standalone_comment_tile_refs,
    generate_css_for_id_map,
    get_custom_css,
    normalize_css_body,
    orphan_tile_ids_in_css,
    process_standalone_comments_for_css_cleared_tiles,
    remove_selector_items_by_keys,
    set_custom_css,
    tile_has_selector_rules,
    tile_ids_in_css,
)
# # # from .util import die, ilog, vlog, ok, wlog, prompt_yes_no, prompt_yes_no_or_die, layout_fingerprint  # removed: avoid local binding  # removed: avoid local binding  # removed: avoid local binding


# If a significant amount of time has passed since the last run, require confirmation
# before --undo_last overwrites a dashboard layout.
UNDO_STALE_SECONDS = 60 * 60  # 1 hour


def _parse_inclusive_range(name: str, pair: Optional[List[int]]) -> Optional[Tuple[int, int]]:
    if pair is None:
        return None
    if len(pair) != 2:
        die(f"{name} requires exactly two integers.")
    a, b = pair[0], pair[1]
    if a <= 0 or b <= 0:
        die(f"{name} values must be positive (1-based). Got {a} {b}.")
    if a > b:
        a, b = b, a
    return (a, b)


def _compute_before_map_mark_rects(
    args,
    tiles: List[Dict],
    *,
    col_range: Optional[Tuple[int, int]],
    row_range: Optional[Tuple[int, int]],
    has_trim: bool,
) -> List[Tuple[int, int, int, int]]:
    """Return rects (r1,r2,c1,c2) to mark in the BEFORE map as affected by the requested action(s)."""

    include_overlap = bool(getattr(args, "include_overlap", False))

    marked_ids: set[int] = set()
    marked_tiles: List[Dict] = []

    def add(ts: List[Dict]) -> None:
        for t in ts:
            tid = as_int(t, "id")
            if tid in marked_ids:
                continue
            marked_ids.add(tid)
            marked_tiles.append(t)

    # Trim affects all tiles.
    if has_trim and tiles:
        add(list(tiles))

    # Insert shifts tiles at/after the insertion point (and straddlers when include_overlap).
    if getattr(args, "insert_rows", None):
        _count, at_row = args.insert_rows
        for t in tiles:
            if not tile_matches_col_range(t, col_range, include_overlap):
                continue
            r0 = as_int(t, "row")
            if r0 >= at_row:
                add([t])
            elif include_overlap:
                r1, r2 = tile_row_extent(t)
                if r1 < at_row <= r2:
                    add([t])

    if getattr(args, "insert_cols", None):
        _count, at_col = args.insert_cols
        for t in tiles:
            if not tile_matches_row_range(t, row_range, include_overlap):
                continue
            c0 = as_int(t, "col")
            if c0 >= at_col:
                add([t])
            elif include_overlap:
                c1, c2 = tile_col_extent(t)
                if c1 < at_col <= c2:
                    add([t])

    # Move / Copy: mark the selected source tiles.
    if getattr(args, "move_cols", None):
        s, e, _d = args.move_cols
        if s > e:
            s, e = e, s
        add(select_tiles_by_col_range(tiles, s, e, include_overlap=include_overlap))

    if getattr(args, "move_rows", None):
        s, e, _d = args.move_rows
        if s > e:
            s, e = e, s
        add(select_tiles_by_row_range(tiles, s, e, include_overlap=include_overlap))

    if getattr(args, "move_range", None):
        r1, c1, r2, c2, _dr, _dc = args.move_range
        tr, br = (r1, r2) if r1 <= r2 else (r2, r1)
        lc, rc = (c1, c2) if c1 <= c2 else (c2, c1)
        add(select_tiles_by_rect_range(tiles, tr, lc, br, rc, include_overlap=include_overlap))

    if getattr(args, "copy_cols", None):
        s, e, _d = args.copy_cols
        if s > e:
            s, e = e, s
        add(select_tiles_by_col_range(tiles, s, e, include_overlap=include_overlap))

    if getattr(args, "copy_rows", None):
        s, e, _d = args.copy_rows
        if s > e:
            s, e = e, s
        add(select_tiles_by_row_range(tiles, s, e, include_overlap=include_overlap))

    if getattr(args, "copy_range", None):
        r1, c1, r2, c2, _dr, _dc = args.copy_range
        tr, br = (r1, r2) if r1 <= r2 else (r2, r1)
        lc, rc = (c1, c2) if c1 <= c2 else (c2, c1)
        add(select_tiles_by_rect_range(tiles, tr, lc, br, rc, include_overlap=include_overlap))

    # Delete / Clear: mark tiles selected for removal (not the shifted tiles).
    if getattr(args, "delete_rows", None):
        s, e = args.delete_rows
        if s > e:
            s, e = e, s
        selected = [
            t
            for t in select_tiles_by_row_range(tiles, s, e, include_overlap=include_overlap)
            if tile_matches_col_range(t, col_range, include_overlap)
        ]
        add(selected)

    if getattr(args, "delete_cols", None):
        s, e = args.delete_cols
        if s > e:
            s, e = e, s
        selected = [
            t
            for t in select_tiles_by_col_range(tiles, s, e, include_overlap=include_overlap)
            if tile_matches_row_range(t, row_range, include_overlap)
        ]
        add(selected)

    if getattr(args, "clear_rows", None):
        s, e = args.clear_rows
        if s > e:
            s, e = e, s
        add(select_tiles_by_row_range(tiles, s, e, include_overlap=include_overlap))

    if getattr(args, "clear_cols", None):
        s, e = args.clear_cols
        if s > e:
            s, e = e, s
        add(select_tiles_by_col_range(tiles, s, e, include_overlap=include_overlap))

    if getattr(args, "clear_range", None):
        r1, c1, r2, c2 = args.clear_range
        tr, br = (r1, r2) if r1 <= r2 else (r2, r1)
        lc, rc = (c1, c2) if c1 <= c2 else (c2, c1)
        add(select_tiles_by_rect_range(tiles, tr, lc, br, rc, include_overlap=include_overlap))

    # Crop: mark tiles that will be removed.
    if getattr(args, "crop_to_rows", None):
        s, e = args.crop_to_rows
        if s > e:
            s, e = e, s
        removed: List[Dict] = []
        for t in tiles:
            if include_overlap:
                r1, r2 = tile_row_extent(t)
                ok = ranges_overlap(r1, r2, s, e)
            else:
                r0 = as_int(t, "row")
                ok = (s <= r0 <= e)
            if not ok:
                removed.append(t)
        add(removed)

    if getattr(args, "crop_to_cols", None):
        s, e = args.crop_to_cols
        if s > e:
            s, e = e, s
        removed: List[Dict] = []
        for t in tiles:
            if include_overlap:
                c1, c2 = tile_col_extent(t)
                ok = ranges_overlap(c1, c2, s, e)
            else:
                c0 = as_int(t, "col")
                ok = (s <= c0 <= e)
            if not ok:
                removed.append(t)
        add(removed)

    if getattr(args, "crop_to_range", None):
        r1, c1, r2, c2 = args.crop_to_range
        tr, br = (r1, r2) if r1 <= r2 else (r2, r1)
        lc, rc = (c1, c2) if c1 <= c2 else (c2, c1)
        sel_rect = (tr, br, lc, rc)
        removed: List[Dict] = []
        for t in tiles:
            if include_overlap:
                ok = rects_overlap(tile_rect(t), sel_rect)
            else:
                rr = as_int(t, "row")
                cc = as_int(t, "col")
                ok = (tr <= rr <= br) and (lc <= cc <= rc)
            if not ok:
                removed.append(t)
        add(removed)

    # Prune: mark tiles that will be removed.
    if getattr(args, "prune_except_ids", None):
        spec = str(args.prune_except_ids or "")
        keep_ids = parse_prune_id_spec(spec, tiles, op_label="--prune_except_ids")
        removed = [t for t in tiles if as_int(t, "id") not in keep_ids]
        add(removed)

    if getattr(args, "prune_except_devices", None):
        spec = str(args.prune_except_devices or "")
        keep_nums, keep_literals = parse_prune_device_spec(spec, tiles, op_label="--prune_except_devices")
        removed: List[Dict] = []
        for t in tiles:
            dev = t.get("device", None)
            dev_s = "" if dev is None else str(dev).strip()
            if dev_s in keep_literals:
                continue
            if dev_s.lstrip("+-").isdigit():
                try:
                    if int(dev_s) in keep_nums:
                        continue
                except Exception:
                    pass
            removed.append(t)
        add(removed)

    if getattr(args, "prune_ids", None):
        spec = str(args.prune_ids or "")
        remove_ids = parse_prune_id_spec(spec, tiles, op_label="--prune_ids")
        removed = [t for t in tiles if as_int(t, "id") in remove_ids]
        add(removed)

    if getattr(args, "prune_devices", None):
        spec = str(args.prune_devices or "")
        rem_nums, rem_literals = parse_prune_device_spec(spec, tiles, op_label="--prune_devices")
        removed: List[Dict] = []
        for t in tiles:
            dev = t.get("device", None)
            dev_s = "" if dev is None else str(dev).strip()
            if dev_s in rem_literals:
                removed.append(t)
                continue
            if dev_s.lstrip("+-").isdigit():
                try:
                    if int(dev_s) in rem_nums:
                        removed.append(t)
                        continue
                except Exception:
                    pass
        add(removed)

    # CSS-only actions: mark the involved tile(s).
    copy_pair = None
    for _k in (
        "copy_tile_css_merge",
        "copy_tile_css_overwrite",
        "copy_tile_css_replace",
        "copy_tile_css_add",
    ):
        v = getattr(args, _k, None)
        if v:
            copy_pair = v
            break
    if copy_pair:
        from_id, to_id = copy_pair
        add([t for t in tiles if as_int(t, "id") in {int(from_id), int(to_id)}])

    if getattr(args, "clear_tile_css", None) is not None:
        # --clear_css now accepts the same SPEC syntax as --prune:ids.
        spec = str(getattr(args, "clear_tile_css"))
        try:
#             from .ops_crop import parse_prune_id_spec  # removed: avoid local binding of parse_prune_id_spec
            ids = parse_prune_id_spec(spec, tiles, op_label="--clear_css")
        except Exception:
            # Back-compat: allow a single integer id.
            ids = set()
            s = spec.strip()
            if s.lstrip("+-").isdigit():
                try:
                    ids = {int(s)}
                except Exception:
                    ids = set()
        if ids:
            add([t for t in tiles if as_int(t, "id") in ids])

    return [tile_rect(t) for t in marked_tiles]

def _parse_trim_modes(trim_value: Optional[str], legacy_left: bool, legacy_top: bool) -> Tuple[bool, bool]:
    """
    Returns (do_left, do_top).

    trim_value:
      None            -> no trim unless legacy flags set
      "both" or ""    -> left+top
      "left"          -> left only
      "top"           -> top only
      "top,left"      -> union (comma-separated)

    Legacy flags:
      --trim_left / --trim_top (deprecated) are OR'd in.
    """
    do_left = bool(legacy_left)
    do_top = bool(legacy_top)

    if trim_value is None:
        return (do_left, do_top)

    v = (trim_value or "").strip().lower()
    if v == "" or v == "both":
        return (True, True)

    parts = [p.strip() for p in v.split(",") if p.strip()]
    allowed = {"left", "top", "both"}
    for p in parts:
        if p not in allowed:
            die(f"Invalid --trim mode '{trim_value}'. Use 'top', 'left', 'both', or 'top,left'.")
        if p == "both":
            do_left = True
            do_top = True
        elif p == "left":
            do_left = True
        elif p == "top":
            do_top = True

    return (do_left, do_top)



def _backup_path_for_url(dashboard_url: str) -> str:
    """Backup filename derived from host + dashboard id (stored in app data dir)."""
    import re
    import urllib.parse
    u = urllib.parse.urlparse(dashboard_url)
    host = (u.hostname or "hub").replace(":", "_")
    m = re.search(r"/dashboard/(\d+)", u.path)
    dash = m.group(1) if m else "dashboard"
    return os.path.join(_app_data_dir(), f"hubitat_tile_mover_backup_{host}_{dash}.json")

def _write_backup(path: str, obj: object) -> None:
    import json
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

def _read_backup(path: str) -> object:
    import json
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_temp_merge_source(obj: object) -> str:
    """Write a temporary JSON file for merge_url imports; returns filename."""
    import json
    import tempfile
    fd, path = tempfile.mkstemp(prefix="hubitat_tile_mover_merge_", suffix=".json")
    # mkstemp returns an OS-level fd; wrap it in a file object
    with open(fd, "w", encoding="utf-8") as f:  # type: ignore[arg-type]
        json.dump(obj, f, indent=2, ensure_ascii=False)
    return path


def _app_data_dir() -> str:
    """Return a per-user writable directory for state/backup files."""
    base = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA")
    if not base:
        base = os.path.expanduser("~")
        # Prefer XDG on Unix-like systems
        xdg = os.getenv("XDG_STATE_HOME") or os.getenv("XDG_DATA_HOME")
        if xdg:
            base = xdg
    path = os.path.join(base, "hubitat_tile_mover")
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        # Fall back to CWD if the directory can't be created for some reason
        return os.getcwd()
    return path


def _state_path() -> str:
    return os.path.join(_app_data_dir(), "hubitat_tile_mover_last_run.json")

def _write_state(state: dict) -> None:
    import json
    with open(_state_path(), "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def _read_state() -> dict:
    import json
    with open(_state_path(), "r", encoding="utf-8") as f:
        return json.load(f)

def kind_to_default_output_format(kind: str) -> str:
    if kind == "full_object":
        return "full"
    if kind == "minimal_container":
        return "minimal"
    return "bare"

def main(argv: Optional[List[str]] = None) -> None:
    import sys as _sys
    import copy as _copy

    did_undo = False
    if argv is None:
        argv = _sys.argv[1:]

    argv = normalize_argv(argv)

    # If invoked with no switches/args, show short help instead of attempting to parse input.
    if not argv:
        p = build_parser()
        p.print_help()
        return


    # Guard singletons (track legacy tokens too)
    assert_singleton_flags(argv, ["--import"])
    assert_singleton_flags(argv, ["--output_format", "--output-format", "--output_shape", "--output-shape"])

    parser = build_parser()
    args = parser.parse_args(argv)

    # Option sanity checks
    if getattr(args, "no_overlap", False) and getattr(args, "include_overlap", False):
        die("ERROR: --no_overlap and --include_overlap cannot be used together.")

    # --no_overlap scope: only valid with --spacing_set:*
    if getattr(args, "no_overlap", False) and getattr(args, "spacing_set", None) is None:
        die("ERROR: --no_overlap is only valid with --spacing_set:rows|cols|all.")
    if getattr(args, "no_overlap", False) and getattr(args, "spacing_add", None) is not None:
        die("ERROR: --no_overlap cannot be used with --spacing_add:*. Use --spacing_set:* instead.")

    if args.indent < 0:
        die("--indent must be >= 0.")

    import_kind, import_path = parse_import_spec(args.import_spec)
    outputs = parse_output_to_specs(args.output_to)

    # Standalone tile reports use the normal output destinations, but never hub.
    if getattr(args, 'list_tiles', None) and any(k == 'hub' for (k, _) in outputs):
        die("--output:hub is not valid with --list_tiles. Use --output:terminal, --output:clipboard, or --output:file.")

    # Resolve hub URLs:
    # - import_path is the dashboard URL when import_kind == 'hub'
    # - output entries may include ('hub', None) or ('hub', url)
    #   If omitted, inherit from hub import URL when available.
    if any(k == 'hub' and p is None for (k, p) in outputs):
        if import_kind == 'hub' and import_path:
            outputs = [(k, (import_path if (k == 'hub' and p is None) else p)) for (k, p) in outputs]

    if any(k == 'hub' and p is None for (k, p) in outputs):
        die("--output:hub requires a dashboard URL unless importing from hub with --import:hub <dashboard_url>.")

    # Map printing: prefer new --show_map[:MODE] interface.
    show_map_mode = getattr(args, 'show_map_mode', None)
    legacy_map_focus = getattr(args, 'map_focus', None)
    map_focus = None
    if show_map_mode:
        map_focus = show_map_mode
    elif legacy_map_focus:
        # Back-compat only (undocumented)
        map_focus = legacy_map_focus
    show_map = bool(map_focus)
    if map_focus is None:
        map_focus = 'full'
    no_scale = (map_focus == 'no_scale')
    show_ids = bool(getattr(args, 'show_ids', False))
    show_axes = getattr(args, 'show_axes', None) or 'none'
    if show_ids and not show_map:
        die("--show_ids requires --show_map.")
    if show_axes != 'none' and not show_map:
        die("--show_axis:* requires --show_map. (legacy --show_axes:* also accepted)")
    list_tiles_spec = getattr(args, 'list_tiles', None)

    # --undo_last is a standalone restore action.
    # It restores the previous backup and writes it to the last output destinations unless --output/--output_to is provided.
    if args.undo_last:
        forbidden = [
            args.insert_rows, args.insert_cols, args.move_cols, args.move_rows, args.move_range,
            args.delete_rows, args.delete_cols, args.clear_rows, args.clear_cols, args.clear_range,
            args.crop_to_rows, args.crop_to_cols, args.crop_to_range,
            args.prune_except_ids, args.prune_except_devices, args.prune_ids, args.prune_devices,
            getattr(args, 'copy_tile_css_merge', None),
            getattr(args, 'copy_tile_css_overwrite', None),
            getattr(args, 'copy_tile_css_replace', None),
            getattr(args, 'copy_tile_css_add', None),
            args.clear_tile_css,
            args.copy_cols, args.copy_rows, args.copy_range,
            args.merge_cols, args.merge_rows, args.merge_range,
            args.trim, args.sort, args.scrub_css,
        ]
        if any(x for x in forbidden if x):
            die("--undo_last cannot be combined with other actions. Use -h for help.")

        # Load last-run state (new location). Fall back to legacy CWD file if present.
        st_path = _state_path()
        if not os.path.exists(st_path) and os.path.exists("hubitat_tile_mover_last_run.json"):
            st_path = "hubitat_tile_mover_last_run.json"
        if not os.path.exists(st_path):
            die("No last-run state found; nothing to undo.")
        try:
            import json as _json
            with open(st_path, "r", encoding="utf-8") as f:
                st = _json.load(f)
        except Exception:
            die("Last-run state file exists but could not be read. Try re-running your last command, or delete the state file.")

        # Prefer embedded backup object (global last-run) so undo works for file/clipboard imports.
        obj = st.get("backup_obj")
        if obj is None:
            backup_path = st.get("backup_path")
            # If the user specified a hub output URL this run, try the derived per-dashboard backup path.
            out_url = None
            if args.output_to:
                outs_tmp = parse_output_to_specs(args.output_to)
                for k, p in outs_tmp:
                    if k == 'hub' and p:
                        out_url = p
                        break
            if (not backup_path or not os.path.exists(backup_path)) and out_url:
                cand = _backup_path_for_url(out_url)
                if os.path.exists(cand):
                    backup_path = cand
            if not backup_path or not os.path.exists(backup_path):
                die("Backup file not found; nothing to undo.")
            obj = _read_backup(backup_path)
        kind, full_container, tiles_any = extract_tiles_container(obj, verbose=args.verbose, debug=args.debug)
        from .jsonio import normalize_tiles_list as _ntl
        tiles = _ntl(tiles_any, verbose=args.verbose, debug=args.debug)

        # Default outputs to last outputs, unless user provided outputs this run
        outputs = parse_output_to_specs(args.output_to) if args.output_to else st.get("last_outputs", [("clipboard", None)])
        # Resolve dashboard URL for hub undo: prefer explicit hub output URL, else last_url.
        url = None
        for k, p in outputs:
            if k == 'hub' and p:
                url = p
                break
        if url is None:
            url = st.get("last_url")
        using_hub_output = any((k == "hub") for (k, _) in outputs)
        if using_hub_output and not url:
            die("Undo restore requires a dashboard URL (either --output:hub <dashboard_url> or a prior hub run with stored URL).")

        # Output format: for hub output force FULL; otherwise default to kind unless user explicitly requested.
        output_format = args.output_format or st.get("last_output_format") or kind_to_default_output_format(kind)
        if using_hub_output:
            if kind != "full_object":
                die("Cannot restore to hub because the backup is not FULL dashboard JSON.")
            output_format = "full"

        out_obj = build_output_object(kind, full_container, tiles, output_format)
        out_text = dump_json(out_obj, indent=args.indent, minify=args.minify)
        if not out_text.endswith("\n"):
            out_text += "\n"
        non_hub = [(k, p) for (k, p) in outputs if k != "hub"]

        # Safety confirmation: if the dashboard has likely changed since the last run (or if the
        # backup is "stale"), require explicit confirmation before overwriting via --undo_last.
        hub_ctx_current = None
        if using_hub_output:
            import time as _time
            import datetime as _dt

            last_url = st.get("last_url")
            last_saved_hash = st.get("last_hub_saved_hash")
            st_epoch = st.get("state_written_at_epoch")
            if st_epoch is None:
                try:
                    st_epoch = int(os.path.getmtime(st_path))
                except Exception:
                    st_epoch = None
            now_epoch = int(_time.time())
            age_sec = (now_epoch - int(st_epoch)) if st_epoch is not None else None

            # Always fetch current hub layout once (needed for POST token/layout_url too).
            hub_ctx_current, cur_obj = hub_import_layout(url, verbose=args.verbose, debug=args.debug)
            cur_hash = layout_fingerprint(cur_obj)

            needs_prompt = False
            reason = None

            # If the user is undoing onto a different dashboard URL than last run, always confirm.
            if last_url and url and (last_url != url):
                needs_prompt = True
                reason = f"target URL differs from last run ({last_url})"
            else:
                # If we have a saved fingerprint from the last hub save, confirm when the hub no longer matches.
                if last_saved_hash and last_url and url and (last_url == url) and (cur_hash != last_saved_hash):
                    needs_prompt = True
                    reason = "dashboard layout has changed since your last run"
                # If enough time has passed since the last run, confirm even if the hash matches.
                elif age_sec is not None and age_sec >= UNDO_STALE_SECONDS:
                    needs_prompt = True
                    reason = f"last run was {int(age_sec // 60)} minute(s) ago"
                # If we can't determine age/hash context, be conservative.
                elif (last_saved_hash is None) and (age_sec is None):
                    needs_prompt = True
                    reason = "cannot determine when the backup was created"

            if needs_prompt:
                when_s = st.get("state_written_at")
                if not when_s and st_epoch is not None:
                    try:
                        when_s = _dt.datetime.fromtimestamp(int(st_epoch)).isoformat(sep=" ", timespec="seconds")
                    except Exception:
                        when_s = None
                age_s = "unknown"
                if age_sec is not None:
                    mins = int(age_sec // 60)
                    hrs = int(mins // 60)
                    if hrs:
                        age_s = f"{hrs}h {mins % 60}m"
                    else:
                        age_s = f"{mins}m"

                details = (
                    f"Undo will overwrite the dashboard layout at:\n  {url}\n"
                    f"Backup created: {when_s or 'unknown'} (age {age_s}).\n"
                    f"Reason: {reason}.\n"
                )
                prompt_yes_no_or_die(
                    args.force,
                    "Proceed with overwrite?",
                    what="the dashboard layout",
                    details=details,
                    show_details=True,
                )

        # Proceed with the undo outputs.
        write_outputs(non_hub, args.newline, out_text)
        if using_hub_output:
            assert hub_ctx_current is not None
            hub_post_layout_with_refresh(url, hub_ctx_current.layout_url, out_obj, verbose=args.verbose, debug=args.debug)

        dests = ", ".join([(k if k != "file" else f"file:{p}") for (k, p) in outputs])
#         from .util import ok as _ok  # removed: avoid local binding
        import sys as _sys
        print(f"{ok('OK:')} undo applied. Output written to {dests}.", file=sys.stderr)
        return


    using_hub_import = (import_kind == "hub")
    using_hub_output = any(k == "hub" for (k, _p) in outputs)

    # Load input JSON (file/clipboard/hub)
    hub_ctx = None
    if using_hub_import:
        if not import_path:
            die("--import:hub requires a dashboard URL. Use -h for help.")
        hub_ctx, obj = hub_import_layout(import_path, verbose=args.verbose, debug=args.debug)
    else:
        from .io_helpers import read_input_text
        from .jsonio import load_json_from_text
        input_text = read_input_text(import_kind, import_path)
        obj = load_json_from_text(input_text, verbose=args.verbose, debug=args.debug)

    # Keep an immutable copy of the imported JSON for --undo_last.
    # (The main flow mutates `obj` in-place.)
    original_obj = _copy.deepcopy(obj)

    # Determine if any operation was requested
    do_left, do_top = _parse_trim_modes(args.trim, getattr(args, "trim_left", False), getattr(args, "trim_top", False))
    has_trim = bool(do_left or do_top)

    deleted_ids: list[int] = []
    cleared_ids: list[int] = []
    created_id_map: dict[int, int] = {}
    merge_css_source_path: str = ""
    merge_source_path: str = ""
    from .io_helpers import parse_merge_source_spec
    merge_source_kind, merge_source_arg = parse_merge_source_spec(args.merge_source)
    if merge_source_kind == "file" and merge_source_arg:
        merge_source_path = merge_source_arg
    elif merge_source_kind == "hub" and merge_source_arg:
        # Merge from a Hubitat dashboard URL. Fetch the source layout JSON and
        # write it to a temp file so the merge ops (and optional CSS handling)
        # can reuse the same path-based loading flow.
        _, mobj = hub_import_layout(merge_source_arg, verbose=args.verbose, debug=args.debug)
        merge_source_path = _write_temp_merge_source(mobj)
        merge_css_source_path = merge_source_path


    has_movement = bool(
        args.insert_rows
        or args.insert_cols
        or args.move_cols
        or args.move_rows
        or args.move_range
        or args.copy_cols
        or args.copy_rows
        or args.copy_range
        or args.merge_cols
        or args.merge_rows
        or args.merge_range
        or args.delete_rows
        or args.delete_cols
        or args.clear_rows
        or args.clear_cols
        or args.clear_range
        or args.crop_to_rows
        or args.crop_to_cols
        or args.crop_to_range
        or args.prune_except_ids
        or args.prune_except_devices
        or args.prune_ids
        or args.prune_devices
        or getattr(args, 'copy_tile_css_merge', None)
        or getattr(args, 'copy_tile_css_overwrite', None)
        or getattr(args, 'copy_tile_css_replace', None)
        or getattr(args, 'copy_tile_css_add', None)
        or args.clear_tile_css
    )

    has_sort = bool((args.sort is not None) or (getattr(args, "order", None) is not None))
    # Standalone view modes.
    list_tiles_only = bool(list_tiles_spec) and not (
        bool(show_map) or has_movement or has_trim or getattr(args, 'spacing_add', None) is not None or getattr(args, 'spacing_set', None) is not None or args.scrub_css or args.compact_css or has_sort
    )
    view_only = bool(show_map) and not (
        bool(list_tiles_spec) or has_movement or has_trim or getattr(args, 'spacing_add', None) is not None or getattr(args, 'spacing_set', None) is not None or args.scrub_css or args.compact_css or has_sort
    )

    if bool(list_tiles_spec) and not list_tiles_only:
        die("--list_tiles is a standalone action and cannot be combined with layout actions, --show_map, --sort, --trim, spacing, or CSS operations.")

    if not (has_movement or has_trim or getattr(args, 'spacing_add', None) is not None or getattr(args, 'spacing_set', None) is not None or args.scrub_css or args.compact_css or has_sort or view_only or list_tiles_only):
        die(
            "No operation specified. Use one movement/edit option and/or trim and/or --sort and/or --scrub_css and/or --compact_css, or use standalone --show_map or standalone --list_tiles to view the imported layout. Use -h for help."
        )

    # Validate range filters usage
    if args.col_range and not (args.insert_rows or args.delete_rows):
        die("--col_range is only valid with --insert_rows or --delete_rows.")
    if args.row_range and not (args.insert_cols or args.delete_cols):
        die("--row_range is only valid with --insert_cols or --delete_cols.")

    # Validate conflict policy usage
    if (args.allow_overlap or args.skip_overlap) and not (
        args.move_cols or args.move_rows or args.move_range
        or args.copy_cols or args.copy_rows or args.copy_range
        or args.merge_cols or args.merge_rows or args.merge_range
    ):
        die("--allow_overlap/--skip_overlap are only valid with --move_*, --copy_*, or --merge_* commands.")
    # --force is allowed for any action that would otherwise prompt for confirmation.

    # Copy-tile-css modes are expressed as action switches (mutually exclusive).

    # Validate merge usage
    if (args.merge_cols or args.merge_rows or args.merge_range):
        if not merge_source_kind or not merge_source_arg:
            die("For merge operations, --merge_source is required (use --merge_source:file <filename> or --merge_source:hub <dashboard_url>).")
        # merge_source cannot be the same as the input
        if using_hub_import and merge_source_kind == 'hub' and import_path and (import_path == merge_source_arg):
            die("--merge_source cannot refer to the same dashboard URL as the hub import.")
        if (import_kind == 'file') and merge_source_kind == 'file' and import_path:
            try:
                if os.path.abspath(import_path) == os.path.abspath(merge_source_arg):
                    die("--merge_source cannot refer to the same file as the file import.")
            except Exception:
                pass
    col_range = _parse_inclusive_range("--col_range", args.col_range)
    row_range = _parse_inclusive_range("--row_range", args.row_range)

    if args.verbose:
        outs_desc = []
        for k, v in outputs:
            outs_desc.append(f"{k}({v})" if v else k)

        vlog(True, "=== hubitat_tile_mover planned actions ===")
        vlog(True, f"Import: {import_kind}{' ' + import_path if import_path else ''}")
        vlog(True, f"Outputs: {', '.join(outs_desc)}")
        vlog(True, f"Output format: {args.output_format}")
        vlog(True, f"Formatting: {'minify=true' if args.minify else f'indent={args.indent}'}")
        vlog(True, f"Newlines: {args.newline}")
        vlog(True, f"include_overlap={bool(args.include_overlap)} force={bool(args.force)}")
        vlog(True, f"allow_overlap={bool(args.allow_overlap)} skip_overlap={bool(args.skip_overlap)}")
        vlog(True, f"Trim: {args.trim if args.trim is not None else '(none)'} (do_left={do_left} do_top={do_top})")
        if args.sort is not None or args.order is not None:
            spec = args.sort if args.sort is not None else args.order
            eff = ''.join([('-' if d else '') + k for k, d in complete_sort_spec(spec)])
            vlog(True, f"Sort: enabled spec='{spec}' effective='{eff}'")
        else:
            vlog(True, "Sort: disabled")
        if merge_source_kind and merge_source_arg:
            vlog(True, f"Merge source: {merge_source_kind}:{merge_source_arg}")
        vlog(True, f"Debug per-tile: {bool(args.debug)}")
        vlog(True, "====================================")

    # Determine primary hub URL for backup bookkeeping (hub import URL or first hub output URL)
    hub_url_for_backup = None
    if using_hub_import and import_path:
        hub_url_for_backup = import_path
    else:
        for k, p in outputs:
            if k == 'hub' and p:
                hub_url_for_backup = p
                break

    backup_path = None
    backup_obj = None
    backup_tmp_path = None
    # Backup is required for hub output and for --confirm_keep (and for hub import, as a restore point).
    # In standalone map view mode, do not create/overwrite backups.
    if (not view_only) and hub_url_for_backup and (using_hub_import or using_hub_output or args.confirm_keep) and (not args.undo_last):
        backup_path = _backup_path_for_url(hub_url_for_backup)
        if args.lock_backup and os.path.exists(backup_path):
            # Use existing backup as the restore point and do not overwrite it.
            backup_obj = _read_backup(backup_path)
        else:
            # Write to a temporary file; only commit if the run completes successfully.
            import tempfile
            fd, backup_tmp_path = tempfile.mkstemp(prefix="hubitat_tile_mover_backup_", suffix=".json")
            os.close(fd)
            _write_backup(backup_tmp_path, obj)
            backup_obj = _copy.deepcopy(obj)  # immutable snapshot
    kind, full_container, tiles_any = extract_tiles_container(obj, verbose=args.verbose, debug=args.debug)
    if using_hub_output and kind != "full_object":
        die("--output:hub requires FULL layout JSON input (cannot use minimal/bare).")
    if using_hub_output:
        if kind != "full_object":
            die("--output:hub requires FULL dashboard JSON input.")
        if args.output_format in ("minimal", "bare", "container", "list"):
            die("--output:hub cannot be used with --output_format:minimal or --output_format:bare.")
    # Tile list validation
    # Some actions (merge, scrub_css) can run even when the dashboard has no tiles yet.
    has_tiles = bool(tiles_any)
    merge_like = bool(merge_source_kind) and bool(args.merge_cols or args.merge_rows or args.merge_range)
    scrub_like = bool(args.scrub_css)
    compact_like = bool(args.compact_css)

    def _ga(name):
        return getattr(args, name, None)
    show_map_only = (bool(show_map) or bool(list_tiles_spec)) and not any([
        _ga('sort'), _ga('sort_spec'), _ga('trim'),
        _ga('insert_rows'), _ga('insert_cols'),
        _ga('move_cols'), _ga('move_rows'), _ga('move_range'),
        _ga('copy_cols'), _ga('copy_rows'), _ga('copy_range'),
        _ga('merge_cols'), _ga('merge_rows'), _ga('merge_range'),
        _ga('delete_rows'), _ga('delete_cols'),
        _ga('clear_rows'), _ga('clear_cols'), _ga('clear_range'),
        _ga('crop_to_rows'), _ga('crop_to_cols'), _ga('crop_to_range'),
        _ga('prune_except_ids'), _ga('prune_except_devices'), _ga('prune_ids'), _ga('prune_devices'),
        _ga('copy_tile_css_merge'), _ga('copy_tile_css_overwrite'), _ga('copy_tile_css_replace'), _ga('copy_tile_css_add'),
        _ga('clear_tile_css'),
        _ga('scrub_css'),
        _ga('compact_css'),

    ])
    if has_tiles or (not (merge_like or scrub_like or show_map_only)):
        verify_tiles_minimum(tiles_any)
    tiles: List[Dict] = tiles_any  # type: ignore[assignment]
    tiles_before_map = [dict(t) for t in tiles]
    def _span_len(ext):
        return int(ext[1]) - int(ext[0]) + 1

    before_pos = {
        as_int(t, "id"): (
            as_int(t, "row"),
            as_int(t, "col"),
            _span_len(tile_row_extent(t)),
            _span_len(tile_col_extent(t)),
        )
        for t in tiles
        if t.get("id") is not None
    }
    before_mark_rects = _compute_before_map_mark_rects(args, tiles_before_map, col_range=col_range, row_range=row_range, has_trim=has_trim)
    if show_map:
        bounds_rects = before_mark_rects if (map_focus == 'conflict' and before_mark_rects) else None
        title = 'BEFORE MAP'
        if view_only:
            title = 'LAYOUT MAP'
            bounds_rects = None
        if before_mark_rects:
            # Match earlier UX for destructive operations, while also covering move/copy/insert.
            destructive = any(
                getattr(args, k, None)
                for k in (
                    'delete_rows',
                    'delete_cols',
                    'clear_rows',
                    'clear_cols',
                    'clear_range',
                    'crop_to_rows',
                    'crop_to_cols',
                    'crop_to_range',
                    'prune_except_ids',
                    'prune_except_devices',
                    'prune_ids',
                    'prune_devices',
                )
            )
            if destructive:
                title = 'BEFORE MAP (TO BE REMOVED)'
            elif any(getattr(args, k, None) for k in ('move_cols', 'move_rows', 'move_range')):
                title = 'BEFORE MAP (TO BE MOVED)'
            elif any(getattr(args, k, None) for k in ('copy_cols', 'copy_rows', 'copy_range')):
                title = 'BEFORE MAP (TO BE COPIED)'
            elif any(getattr(args, k, None) for k in ('insert_rows', 'insert_cols')) or has_trim:
                title = 'BEFORE MAP (TO BE SHIFTED)'
            else:
                title = 'BEFORE MAP (AFFECTED)'
        print(
            render_tile_map(
                tiles_before_map,
                title=title,
                mark_rects=before_mark_rects,
                bounds_rects=bounds_rects,
                no_scale=no_scale,
                show_ids=show_ids,
                show_axes=show_axes,
            ),
            end='',
            file=sys.stderr,
        )

    # Standalone map view mode ends here: still check and warn for orphan CSS, but do not write outputs unless explicitly requested.
    if view_only:
        css_key0, css_text0 = get_custom_css(obj)
        if css_key0 is not None:
            css_text0 = css_text0 or ""
            existing_ids0 = {as_int(t, "id") for t in tiles_before_map if t.get("id") is not None}
            orphans0 = orphan_tile_ids_in_css(css_text0, existing_ids0) if css_text0 else set()
            if orphans0 and (not args.quiet):
#                 from .util import wlog, format_id_sample  # removed: avoid local binding

                wlog(
                    f"Found {len(orphans0)} orphan CSS tile id(s) in customCSS (no matching tile). "
                    f"Use --scrub_css to remove. IDs: {format_id_sample(list(orphans0))}"
                )

        # Explicit hub output in view-only mode is disallowed (avoid no-op POSTs).
        if using_hub_output:
            die("--output:hub requires an action; it is not supported with standalone --show_map.")

        # If the user explicitly requested non-hub outputs, write the imported JSON unchanged.
        if args.output_to:
            output_obj0 = build_output_object(kind, full_container, tiles_before_map, args.output_format)
            out_text0 = dump_json(output_obj0, indent=args.indent, minify=args.minify)
            if not out_text0.endswith("\n"):
                out_text0 += "\n"
            non_hub_outputs0 = [(k, p) for (k, p) in outputs if k != 'hub']
            write_outputs(non_hub_outputs0, args.newline, out_text0)
        return

    if list_tiles_only:
        report_outputs = outputs if args.output_to else [('terminal', None)]
        _, css_text0 = get_custom_css(obj)
        tile_report_text = render_list_tiles(tiles_before_map, list_tiles_spec, css_text0 or '')
        write_outputs(report_outputs, args.newline, tile_report_text)
        return

    # Treat tile ids referenced in customCSS as reserved for id assignment (avoids collisions with orphaned CSS).
    css_key_pre, css_text_pre = get_custom_css(obj)
    reserved_css_ids = tile_ids_in_css(css_text_pre or "") if css_key_pre is not None else set()

    vlog(args.verbose, f"Loaded JSON kind={kind}, tiles={len(tiles)}")

    # One movement/edit operation (mutually exclusive)
    if args.insert_rows:
        count, at_row = args.insert_rows
        insert_rows(
            tiles,
            count=count,
            at_row=at_row,
            include_overlap=args.include_overlap,
            col_range=col_range,
            debug=args.debug,
        )

    elif args.insert_cols:
        count, at_col = args.insert_cols
        insert_cols(
            tiles,
            count=count,
            at_col=at_col,
            include_overlap=args.include_overlap,
            row_range=row_range,
            debug=args.debug,
        )



    elif getattr(args, "spacing_add", None) is not None:
        mode, cells = args.spacing_add
        if getattr(args, "verbose", False):
            _before_pos = {t.get("id"): (t.get("row"), t.get("col")) for t in tiles}
        adjust_tile_spacing(
            tiles,
            cells=int(cells),
            include_overlap=bool(args.include_overlap),
            no_overlap=bool(getattr(args, "no_overlap", False)),
            mode=str(mode),
        )
        if getattr(args, "verbose", False):
            _after_pos = {t.get("id"): (t.get("row"), t.get("col")) for t in tiles}
            _changed = sum(1 for k,v in _after_pos.items() if _before_pos.get(k) != v)
            ilog(f"--spacing_add:{mode} {cells}: shifted {_changed} tile(s).")

    elif getattr(args, "spacing_set", None) is not None:
        mode, gap = args.spacing_set
        mode = str(mode)
        gap = int(gap)
        if gap < 0:
            die(f"--spacing_set:{mode}: GAP must be >= 0, got: {gap}")
        _rows_snapshot = None
        _cols_snapshot = None
        if mode == "rows":
            _cols_snapshot = {t.get("id"): t.get("col") for t in tiles}
        elif mode == "cols":
            _rows_snapshot = {t.get("id"): t.get("row") for t in tiles}
        if getattr(args, "verbose", False):
            _before_pos = {t.get("id"): (t.get("row"), t.get("col")) for t in tiles}
        set_tile_spacing(
            tiles,
            gap=gap,
            include_overlap=bool(args.include_overlap),
            no_overlap=bool(getattr(args, 'no_overlap', False)),
            mode=mode,
        )
        # Defensive: ensure axis-only modes do not alter the other axis, regardless of ops implementation.
        if _cols_snapshot is not None:
            for t in tiles:
                tid = t.get("id")
                if tid in _cols_snapshot:
                    t["col"] = _cols_snapshot[tid]
        if _rows_snapshot is not None:
            for t in tiles:
                tid = t.get("id")
                if tid in _rows_snapshot:
                    t["row"] = _rows_snapshot[tid]
        if getattr(args, "verbose", False):
            _after_pos = {t.get("id"): (t.get("row"), t.get("col")) for t in tiles}
            _changed = sum(1 for k, v in _after_pos.items() if _before_pos.get(k) != v)
            ilog(f"--spacing_set:{mode} {gap}: shifted {_changed} tile(s).")

    elif args.move_cols:
        s, e, d = args.move_cols
        move_cols(
            tiles,
            start_col=s,
            end_col=e,
            dest_start_col=d,
            include_overlap=args.include_overlap,
            allow_overlap=args.allow_overlap,
            skip_overlap=args.skip_overlap,
            show_map=show_map,
            map_focus=map_focus,
            show_axes=show_axes,
            show_ids=show_ids,
            verbose=args.verbose,
            debug=args.debug,
        )

    elif args.move_rows:
        s, e, d = args.move_rows
        move_rows(
            tiles,
            start_row=s,
            end_row=e,
            dest_start_row=d,
            include_overlap=args.include_overlap,
            allow_overlap=args.allow_overlap,
            skip_overlap=args.skip_overlap,
            show_map=show_map,
            map_focus=map_focus,
            show_axes=show_axes,
            show_ids=show_ids,
            verbose=args.verbose,
            debug=args.debug,
        )

    elif args.move_range:
        r1, c1, r2, c2, dr, dc = args.move_range
        move_range(
            tiles,
            src_top_row=r1,
            src_left_col=c1,
            src_bottom_row=r2,
            src_right_col=c2,
            dest_top_row=dr,
            dest_left_col=dc,
            include_overlap=args.include_overlap,
            allow_overlap=args.allow_overlap,
            skip_overlap=args.skip_overlap,
            show_map=show_map,
            map_focus=map_focus,
            show_axes=show_axes,
            show_ids=show_ids,
            verbose=args.verbose,
            debug=args.debug,
        )


    elif args.copy_cols:
        s, e, d = args.copy_cols
        created_id_map = copy_cols(
            tiles,
            start_col=s,
            end_col=e,
            dest_start_col=d,
            include_overlap=args.include_overlap,
            allow_overlap=args.allow_overlap,
            skip_overlap=args.skip_overlap,
            show_map=show_map,
            map_focus=map_focus,
            show_axes=show_axes,
            show_ids=show_ids,
            verbose=args.verbose,
            debug=args.debug,
            reserved_ids=reserved_css_ids,
        )

    elif args.copy_rows:
        s, e, d = args.copy_rows
        created_id_map = copy_rows(
            tiles,
            start_row=s,
            end_row=e,
            dest_start_row=d,
            include_overlap=args.include_overlap,
            allow_overlap=args.allow_overlap,
            skip_overlap=args.skip_overlap,
            show_map=show_map,
            map_focus=map_focus,
            show_axes=show_axes,
            show_ids=show_ids,
            verbose=args.verbose,
            debug=args.debug,
            reserved_ids=reserved_css_ids,
        )

    elif args.copy_range:
        r1, c1, r2, c2, dr, dc = args.copy_range
        created_id_map = copy_range(
            tiles,
            src_top_row=r1,
            src_left_col=c1,
            src_bottom_row=r2,
            src_right_col=c2,
            dest_top_row=dr,
            dest_left_col=dc,
            include_overlap=args.include_overlap,
            allow_overlap=args.allow_overlap,
            skip_overlap=args.skip_overlap,
            show_map=show_map,
            map_focus=map_focus,
            show_axes=show_axes,
            show_ids=show_ids,
            verbose=args.verbose,
            debug=args.debug,
            reserved_ids=reserved_css_ids,
        )

    elif args.merge_cols:
        s, e, d = args.merge_cols
        created_id_map = merge_cols(
            tiles,
            merge_source_path=merge_source_path,
            start_col=s,
            end_col=e,
            dest_start_col=d,
            include_overlap=args.include_overlap,
            allow_overlap=args.allow_overlap,
            skip_overlap=args.skip_overlap,
            show_map=show_map,
            map_focus=map_focus,
            show_axes=show_axes,
            show_ids=show_ids,
            verbose=args.verbose,
            debug=args.debug,
            reserved_ids=reserved_css_ids,
        )
        merge_css_source_path = merge_source_path


    elif args.merge_rows:
        s, e, d = args.merge_rows
        created_id_map = merge_rows(
            tiles,
            merge_source_path=merge_source_path,
            start_row=s,
            end_row=e,
            dest_start_row=d,
            include_overlap=args.include_overlap,
            allow_overlap=args.allow_overlap,
            skip_overlap=args.skip_overlap,
            show_map=show_map,
            map_focus=map_focus,
            show_axes=show_axes,
            show_ids=show_ids,
            verbose=args.verbose,
            debug=args.debug,
            reserved_ids=reserved_css_ids,
        )
        merge_css_source_path = merge_source_path


    elif args.merge_range:
        r1, c1, r2, c2, dr, dc = args.merge_range
        created_id_map = merge_range(
            tiles,
            merge_source_path=merge_source_path,
            src_top_row=r1,
            src_left_col=c1,
            src_bottom_row=r2,
            src_right_col=c2,
            dest_top_row=dr,
            dest_left_col=dc,
            include_overlap=args.include_overlap,
            allow_overlap=args.allow_overlap,
            skip_overlap=args.skip_overlap,
            show_map=show_map,
            map_focus=map_focus,
            show_axes=show_axes,
            show_ids=show_ids,
            verbose=args.verbose,
            debug=args.debug,
            reserved_ids=reserved_css_ids,
        )
        merge_css_source_path = merge_source_path


    elif args.delete_rows:
        s, e = args.delete_rows
        deleted_ids = delete_rows(
            tiles,
            start_row=s,
            end_row=e,
            include_overlap=args.include_overlap,
            col_range=col_range,
            force=args.force,
            verbose=args.verbose,
            debug=args.debug,
        )

    elif args.delete_cols:
        s, e = args.delete_cols
        deleted_ids = delete_cols(
            tiles,
            start_col=s,
            end_col=e,
            include_overlap=args.include_overlap,
            row_range=row_range,
            force=args.force,
            verbose=args.verbose,
            debug=args.debug,
        )

    elif args.clear_rows:
        s, e = args.clear_rows
        cleared_ids = clear_rows(
            tiles,
            start_row=s,
            end_row=e,
            include_overlap=args.include_overlap,
            force=args.force,
            verbose=args.verbose,
            debug=args.debug,
        )

    elif args.clear_cols:
        s, e = args.clear_cols
        cleared_ids = clear_cols(
            tiles,
            start_col=s,
            end_col=e,
            include_overlap=args.include_overlap,
            force=args.force,
            verbose=args.verbose,
            debug=args.debug,
        )

    elif args.clear_range:
        tr, lc, br, rc = args.clear_range
        cleared_ids = clear_range(
            tiles,
            top_row=tr,
            left_col=lc,
            bottom_row=br,
            right_col=rc,
            include_overlap=args.include_overlap,
            force=args.force,
            verbose=args.verbose,
            debug=args.debug,
        )

    elif args.crop_to_rows:
        s, e = args.crop_to_rows
        deleted_ids = crop_to_rows(
            tiles,
            start_row=s,
            end_row=e,
            include_overlap=args.include_overlap,
            force=args.force,
            verbose=args.verbose,
            debug=args.debug,
        )

    elif args.crop_to_cols:
        s, e = args.crop_to_cols
        deleted_ids = crop_to_cols(
            tiles,
            start_col=s,
            end_col=e,
            include_overlap=args.include_overlap,
            force=args.force,
            verbose=args.verbose,
            debug=args.debug,
        )

    elif args.crop_to_range:
        tr, lc, br, rc = args.crop_to_range
        deleted_ids = crop_to_range(
            tiles,
            top_row=tr,
            left_col=lc,
            bottom_row=br,
            right_col=rc,
            include_overlap=args.include_overlap,
            force=args.force,
            verbose=args.verbose,
            debug=args.debug,
        )

    elif args.prune_except_ids:
        deleted_ids = prune_except_ids(
            tiles,
            ids_csv=args.prune_except_ids,
            force=args.force,
            verbose=args.verbose,
            debug=args.debug,
        )

    elif args.prune_except_devices:
        deleted_ids = prune_except_devices(
            tiles,
            devices_csv=args.prune_except_devices,
            force=args.force,
            verbose=args.verbose,
            debug=args.debug,
        )

    elif args.prune_ids:
        deleted_ids = prune_ids(
            tiles,
            ids_csv=args.prune_ids,
            force=args.force,
            verbose=args.verbose,
            debug=args.debug,
        )

    elif args.prune_devices:
        deleted_ids = prune_devices(
            tiles,
            devices_csv=args.prune_devices,
            force=args.force,
            verbose=args.verbose,
            debug=args.debug,
        )
    # Post-op CSS handling
    css_key, css_text = get_custom_css(obj)

    # CSS-only actions: copy tile CSS in one of the explicit modes.
    copy_mode = None
    copy_pair = None
    for _attr, _mode in (
        ("copy_tile_css_merge", "merge"),
        ("copy_tile_css_overwrite", "overwrite"),
        ("copy_tile_css_replace", "replace"),
        ("copy_tile_css_add", "add"),
    ):
        v = getattr(args, _attr, None)
        if v:
            copy_mode = _mode
            copy_pair = v
            break

    if copy_mode and copy_pair:
        from_id, to_id = copy_pair
        from_id = int(from_id)
        to_id = int(to_id)
        if from_id == to_id:
            die(f"--copy_css:{copy_mode} requires different FROM_TILE and TO_TILE ids.")

        if css_key is None:
            die(f"--copy_css:{copy_mode} requires a JSON object input that can contain customCSS (full/minimal).")

        existing_ids = {as_int(t, 'id') for t in tiles if t.get('id') is not None}
        if from_id not in existing_ids:
            die(f"--copy_css:{copy_mode}: source tile id {from_id} not found in layout.")
        if to_id not in existing_ids:
            die(f"--copy_css:{copy_mode}: destination tile id {to_id} not found in layout.")

        css_text = css_text or ""

        # Generate CSS fragment by duplicating FROM selectors to TO.
        # This uses the same selector+body rewriting logic as tile copy/merge.
        frag = generate_css_for_id_map(css_text, {from_id: to_id}, dest_css=None)
        if not frag.strip():
            if not args.quiet:
                wlog(f"--copy_css:{copy_mode}: no tile-specific CSS rules found for tile-{from_id}; no changes.")
        else:
            if copy_mode == 'replace':
                css_text2 = cleanup_css_for_tile_ids(css_text, [to_id])
                css_text2 = css_text2.rstrip() + "\n\n" + frag.strip() + "\n"
                css_text = css_text2
                set_custom_css(obj, css_key, css_text)

            elif copy_mode == 'add':
                # Add everything regardless of conflicts.
                css_text2 = css_text.rstrip() + "\n\n" + frag.strip() + "\n"
                css_text = css_text2
                set_custom_css(obj, css_key, css_text)

            else:
                # merge/overwrite: resolve conflicts by selector item + at-rule stack.
                incoming = collect_selector_item_bodies(frag)
                existing = collect_selector_item_bodies(css_text)

                keys_to_drop: set = set()      # do not add these incoming rules
                keys_to_remove: set = set()    # remove these destination selector items before adding

                # Determine conflicts and duplicates.
                for key, inc_bodies in incoming.items():
                    if not inc_bodies:
                        continue
                    inc_norm = normalize_css_body(inc_bodies[0])
                    if key not in existing:
                        continue

                    ex_norms = {normalize_css_body(b) for b in existing.get(key, [])}
                    if ex_norms and (ex_norms == {inc_norm}):
                        # Exact duplicate already exists.
                        keys_to_drop.add(key)
                        continue

                    # Conflict: same selector item exists with different body.
                    if copy_mode == 'overwrite':
                        keys_to_remove.add(key)
                        continue

                    # merge mode
                    if args.force:
                        # With --force, skip conflicting rules.
                        keys_to_drop.add(key)
                        continue

                    if not sys.stdin.isatty():
                        die(
                            "Conflicting CSS rule(s) detected for --copy_css:merge, but no TTY is available. "
                            "Re-run with --force (to skip conflicting rules) or use --copy_css:overwrite / :add / :replace."
                        )

                    stack, sel = key
                    stack_txt = " > ".join(stack) if stack else "(top-level)"
                    ans = input(
                        f"CSS conflict for {stack_txt} selector '{sel}'. Keep existing [k] / overwrite [o] / abort [x]? [k/o/x]: "
                    ).strip().lower()
                    if ans.startswith('o'):
                        keys_to_remove.add(key)
                    elif ans.startswith('x'):
                        raise SystemExit(1)
                    else:
                        # default keep
                        keys_to_drop.add(key)

                frag2, kept_blocks = drop_selector_items_by_keys(frag, keys_to_drop)
                if kept_blocks == 0:
                    if not args.quiet:
                        ilog(f"--copy_css:{copy_mode}: no changes (all rules already present or conflicts skipped).")
                else:
                    css_text2 = css_text
                    if keys_to_remove:
                        css_text2 = remove_selector_items_by_keys(css_text2, keys_to_remove)
                    css_text2 = css_text2.rstrip() + "\n\n" + frag2.strip() + "\n"
                    css_text = css_text2
                    set_custom_css(obj, css_key, css_text)

    if getattr(args, "clear_tile_css", None) is not None:
        spec = str(getattr(args, "clear_tile_css"))

        if css_key is None:
            die("--clear_css requires a JSON object input that can contain customCSS (full/minimal).")

        existing_ids = {as_int(t, "id") for t in tiles if t.get("id") is not None}
        if not existing_ids:
            die("--clear_css: no tile ids found in layout.")

        # Parse using the same syntax as --prune:ids (comma list, ranges, comparisons).
        # Comparisons are bounded to the highest tile id present in the current layout.
        matched = parse_prune_id_spec(spec, tiles, op_label="--clear_css")
        target_ids = sorted(int(i) for i in matched if int(i) in existing_ids)

        if not target_ids:
            die(f"--clear_css: SPEC matched no tile ids in layout: {spec!r}")

        css_text = css_text or ""

        # Fast exit: if none of the targets have selector rules, there is nothing to clear.
        if not any(tile_has_selector_rules(css_text, tid) for tid in target_ids):
            if not args.quiet:
                ilog(f"--clear_css: no selector rules found for {len(target_ids)} tile id(s); no changes.")
        else:
            css_text2 = cleanup_css_for_tile_ids(css_text, target_ids)

            # Optionally remove or rewrite standalone comments referencing these tile id(s).
            hits = find_standalone_comment_tile_refs(css_text2, set(target_ids))
            if hits:
                remove_comments = prompt_yes_no(
                    args.force,
                    f"Also remove {len(hits)} standalone CSS comment(s) referencing the cleared tile id(s)?",
                    default_yes=False,
                )
                css_text3, removed_cnt, rewritten_cnt = process_standalone_comments_for_css_cleared_tiles(
                    css_text2,
                    target_ids,
                    remove=remove_comments,
                )
                if removed_cnt or rewritten_cnt:
                    css_text2 = css_text3
                    if args.verbose or args.debug:
                        ilog(
                            f"CSS comments: removed {removed_cnt} standalone comment(s), "
                            f"rewritten {rewritten_cnt} comment(s)."
                        )

            if css_text2 != css_text:
                css_text = css_text2
                set_custom_css(obj, css_key, css_text)
            else:
                if not args.quiet:
                    ilog("--clear_css: no changes.")



    if args.cleanup_css and css_key is not None and css_text and (deleted_ids or cleared_ids):
# #         from .util import format_id_sample, prompt_yes_no_or_die  # removed: avoid local binding  # removed: avoid local binding
        from .css_ops import process_standalone_comments_for_removed_tiles

        ids_to_clean = deleted_ids + cleared_ids
        details = f"--cleanup_css will remove CSS rules for {len(ids_to_clean)} tile id(s). IDs: {format_id_sample(ids_to_clean)}"
        prompt_yes_no_or_die(
            args.force,
            f"This will remove CSS rules for {len(ids_to_clean)} tile id(s). Are you sure you want to continue?",
            what="CSS rules",
            details=details,
            show_details=(args.verbose or args.debug),
        )
        css_text = cleanup_css_for_tile_ids(css_text, ids_to_clean)
        # Optionally remove or neutralize standalone comments that reference the
        # removed tile ids.
        hits = find_standalone_comment_tile_refs(css_text, set(ids_to_clean))
        if hits:
            remove_comments = prompt_yes_no(
                args.force,
                f"Also remove {len(hits)} standalone CSS comment(s) referencing removed tile ids?",
                default_yes=False,
            )
            css_text2, removed_cnt, rewritten_cnt = process_standalone_comments_for_removed_tiles(
                css_text,
                ids_to_clean,
                remove=remove_comments,
            )
            if removed_cnt or rewritten_cnt:
                css_text = css_text2
                if args.verbose or args.debug:
                    ilog(
                        f"CSS comments: removed {removed_cnt} standalone comment(s), rewritten {rewritten_cnt} comment(s)."
                    )

        set_custom_css(obj, css_key, css_text)

    if (not args.ignore_css) and css_key is not None and created_id_map:
        source_css = css_text
        if merge_css_source_path:
            try:
                import json
                with open(merge_css_source_path, "r", encoding="utf-8") as f:
                    mo = json.load(f)
                _, source_css = get_custom_css(mo)
            except Exception:
                source_css = css_text

        frag = generate_css_for_id_map(source_css or "", created_id_map, dest_css=css_text or "")
        if frag.strip():
            css_text = (css_text or "").rstrip() + "\n\n" + frag.strip() + "\n"
            set_custom_css(obj, css_key, css_text)

    # Trim AFTER movement but BEFORE sort (can be used alone too)
    if has_trim:
        trim_tiles(tiles, do_left=do_left, do_top=do_top, debug=args.debug)

    # Legacy: map --order (hidden) to --sort if needed.
    if args.sort is None and getattr(args, "order", None) is not None:
        args.sort = args.order

    # Sort last (only when --sort is present; otherwise preserve original tile order).
    final_tiles = sort_tiles(tiles, args.sort) if args.sort is not None else tiles

    # Track which tiles changed position (or are new) for maps and strict overlap checks.
    after_pos = {
        as_int(t, "id"): (
            as_int(t, "row"),
            as_int(t, "col"),
            _span_len(tile_row_extent(t)),
            _span_len(tile_col_extent(t)),
        )
        for t in final_tiles
        if t.get("id") is not None
    }
    changed_ids = {tid for tid, apos in after_pos.items() if before_pos.get(tid) != apos}

    # Backstop overlap detector: find the first overlap pair between a changed/new tile
    # and an unchanged tile. Overlaps *within* the moved/copied/merged set are allowed
    # (e.g., already-overlapped source tiles should remain overlapped after move/copy).
    def _first_overlap_changed_vs_unchanged(ts: List[Dict[str, Any]]) -> Tuple[int, int, Tuple[int, int, int, int]] | None:
        rects = [(as_int(t, "id"), tile_rect(t)) for t in ts]
        n = len(rects)
        for i in range(n):
            id1, r1 = rects[i]
            for j in range(i + 1, n):
                id2, r2 = rects[j]
                # Only detect overlaps where exactly one tile is changed/new.
                if (id1 in changed_ids) == (id2 in changed_ids):
                    continue
                if rects_overlap(r1, r2):
                    or1 = max(r1[0], r2[0])
                    or2 = min(r1[1], r2[1])
                    oc1 = max(r1[2], r2[2])
                    oc2 = min(r1[3], r2[3])
                    return id1, id2, (or1, or2, oc1, oc2)
        return None

    if show_map:
        conflict_rects: List[Tuple[int, int, int, int]] = []
        if changed_ids:
            changed_tiles = [t for t in final_tiles if as_int(t, "id") in changed_ids]
            unchanged_tiles = [t for t in final_tiles if as_int(t, "id") not in changed_ids]
            for mt in changed_tiles:
                mrect = tile_rect(mt)
                for st in unchanged_tiles:
                    srect = tile_rect(st)
                    if rects_overlap(mrect, srect):
                        or1 = max(mrect[0], srect[0])
                        or2 = min(mrect[1], srect[1])
                        oc1 = max(mrect[2], srect[2])
                        oc2 = min(mrect[3], srect[3])
                        conflict_rects.append((or1, or2, oc1, oc2))

        focus_color = "yellow" if getattr(args, "allow_overlap", False) else "red"
        outcome_no_scale = no_scale or bool(conflict_rects)
        print(
            render_tile_map(
                final_tiles,
                title="OUTCOME MAP",
                changed_ids=changed_ids,
                focus_rects=conflict_rects,
                focus_color=focus_color,
                no_scale=outcome_no_scale,
                show_ids=show_ids,
                show_axes=show_axes,
            ),
            end="",
            file=sys.stderr,
        )
    # CSS orphan detection / scrub (performed last, after sorting).
    if css_key is not None:
        _, css_text2 = get_custom_css(obj)
        css_text2 = css_text2 or ""
        existing_ids = {as_int(t, "id") for t in final_tiles}
        orphans = orphan_tile_ids_in_css(css_text2, existing_ids) if css_text2 else set()
        if orphans and args.scrub_css:
# #             from .util import format_id_sample, prompt_yes_no_or_die  # removed: avoid local binding  # removed: avoid local binding

            prompt_yes_no_or_die(
                args.force,
                f"--scrub_css will remove CSS rules referencing {len(orphans)} missing tile(s). IDs: {format_id_sample(list(orphans))}. Proceed?",
                what="CSS rules",
            )
            css_text2 = cleanup_css_for_tile_ids(css_text2, list(orphans))
            set_custom_css(obj, css_key, css_text2)
        elif orphans and not args.quiet:
#             from .util import wlog, format_id_sample  # removed: avoid local binding

            wlog(
                f"Found {len(orphans)} orphan CSS tile id(s) in customCSS (no matching tile). "
                f"Use --scrub_css to remove. IDs: {format_id_sample(list(orphans))}"
            )

        if args.compact_css:
            from .css_ops import compact_css_stylesheet

            css_compact = compact_css_stylesheet(css_text2)
            if css_compact != css_text2:
                css_text2 = css_compact
                set_custom_css(obj, css_key, css_text2)

    # Strict overlap guard (extra safety): for move/copy/merge in strict mode, ensure the result has no overlaps
    # involving any changed tile. (Pre-flight checks should normally prevent this; this is a backstop.)
    overlap_ops = bool(
        args.move_cols
        or args.move_rows
        or args.move_range
        or args.copy_cols
        or args.copy_rows
        or args.copy_range
        or args.merge_cols
        or args.merge_rows
        or args.merge_range
    )
    if overlap_ops and (not args.allow_overlap) and (not args.skip_overlap):
        ov = _first_overlap_changed_vs_unchanged(final_tiles)
        if ov is not None:
            id1, id2, orect = ov
            if show_map:
                print(
                    render_tile_map(
                        final_tiles,
                        title="CONFLICT MAP (OUTCOME)",
                        focus_rects=[orect],
                        focus_color="red",
                        no_scale=True,
                        show_ids=show_ids,
                        show_axes=show_axes,
                    ),
                    end="",
                    file=sys.stderr,
                )
            die(
                f"Overlapping tiles detected in result: id={id1} overlaps id={id2} at r{orect[0]}..{orect[1]},c{orect[2]}..{orect[3]}. "
                "Re-run with --allow_overlap or --skip_overlap."
            )

    output_obj = build_output_object(kind, full_container, final_tiles, args.output_format)

    out_text = dump_json(output_obj, indent=args.indent, minify=args.minify)
    if not out_text.endswith("\n"):
        out_text += "\n"

    non_hub_outputs = [(k, p) for (k, p) in outputs if k != 'hub']
    write_outputs(non_hub_outputs, args.newline, out_text)

    posted = False
    post_url_used = ''
    if using_hub_output:
        # Determine hub output URL (required).
        hub_out_url = None
        for k, p in outputs:
            if k == 'hub':
                hub_out_url = p
                break
        if not hub_out_url:
            die("--output:hub requires a dashboard URL (or import from hub with --import:hub <dashboard_url>).")

        # Use the import hub context only if it matches the output URL; otherwise fetch a new context.
        hub_ctx_out = hub_ctx if (hub_ctx is not None and using_hub_import and import_path and import_path == hub_out_url) else None
        if hub_ctx_out is None:
            hub_ctx_out, _tmp = hub_import_layout(hub_out_url, verbose=False, debug=False)

        post_url_used = hub_post_layout_with_refresh(hub_out_url, hub_ctx_out.layout_url, output_obj, verbose=args.verbose, debug=args.debug)
        posted = True

    # Optional: write changes first, then prompt to keep; if not kept, restore the backup to the same outputs.
    if args.confirm_keep and (not args.undo_last):
#         from .util import prompt_yes_no  # removed: avoid local binding

        # --confirm_keep must be independent of --force. Users may use --force to suppress
        # destructive-action prompts while still wanting the final keep/rollback confirmation.
        keep = prompt_yes_no(False, "Keep these changes?", default_yes=True)
        if not keep:
            did_undo = True

            restore_src = backup_obj if backup_obj is not None else original_obj
            restore_obj = _copy.deepcopy(restore_src)
            r_kind, r_container, r_tiles_any = extract_tiles_container(restore_obj, verbose=args.verbose, debug=args.debug)

            r_output_format = args.output_format
            if using_hub_output:
                if r_kind != "full_object":
                    die("Cannot restore to hub because the backup is not FULL dashboard JSON.")
                r_output_format = "full"

            restore_output_obj = build_output_object(r_kind, r_container, r_tiles_any, r_output_format)
            restore_text = dump_json(restore_output_obj, indent=args.indent, minify=args.minify)
            if not restore_text.endswith("\n"):
                restore_text += "\n"

            # Rewrite non-hub outputs.
            write_outputs(non_hub_outputs, args.newline, restore_text)

            # Restore hub output (posts backup layout back to dashboard).
            if using_hub_output:
                hub_out_url = None
                for k, p in outputs:
                    if k == 'hub':
                        hub_out_url = p
                        break
                if not hub_out_url:
                    die("--output:hub requires a dashboard URL (or import from hub with --import:hub <dashboard_url>).")
                hub_ctx_out = hub_ctx if (hub_ctx is not None and using_hub_import and import_path and import_path == hub_out_url) else None
                if hub_ctx_out is None:
                    hub_ctx_out, _tmp = hub_import_layout(hub_out_url, verbose=False, debug=False)
                post_url_used = hub_post_layout_with_refresh(
                    hub_out_url, hub_ctx_out.layout_url, restore_output_obj, verbose=args.verbose, debug=args.debug
                )
                posted = True

            # Update status counters to reflect the final (restored) content.
            output_obj = restore_output_obj
            out_text = restore_text
            final_tiles = r_tiles_any


    # Persist last-run state for --undo_last.
    # Important: CSS-only actions must be undoable too, even when tiles do not change.
    # To avoid losing undo history on no-op runs, only update the last-run state when
    # the layout content (tiles and/or customCSS) actually changed.
    net_changed = False
    try:
        net_changed = (layout_fingerprint(original_obj) != layout_fingerprint(output_obj))
    except Exception:
        # Be conservative: if we can't fingerprint, assume it changed.
        net_changed = True

    try:
        import time as _time
        import datetime as _dt

        if net_changed:
            # If we created a new backup this run, commit it only after all outputs (and hub POST) succeeded.
            if backup_tmp_path and backup_path and (not (args.lock_backup and os.path.exists(backup_path))):
                os.replace(backup_tmp_path, backup_path)

            now_epoch = int(_time.time())
            state = {
                # Global last-run backup (works for file/clipboard/hub imports)
                "backup_obj": original_obj,
                # Optional per-dashboard backup path (only meaningful when a hub URL is in use)
                "backup_path": backup_path,
                "last_outputs": outputs,
                "last_url": hub_url_for_backup,
                "last_output_format": args.output_format,
                "last_import_kind": import_kind,
                "state_written_at_epoch": now_epoch,
                "state_written_at": _dt.datetime.fromtimestamp(now_epoch).isoformat(sep=" ", timespec="seconds"),
            }

            if posted and hub_url_for_backup:
                # Fingerprint the last layout saved to hub so --undo_last can detect external changes.
                try:
                    state["last_hub_saved_hash"] = layout_fingerprint(output_obj)
                    state["last_hub_saved_at_epoch"] = now_epoch
                except Exception:
                    state["last_hub_saved_hash"] = None
            else:
                state["last_hub_saved_hash"] = None

            _write_state(state)
        else:
            # No net change: do not overwrite last-run state or backup. Remove any uncommitted temp backup.
            if backup_tmp_path and os.path.exists(backup_tmp_path):
                try:
                    os.remove(backup_tmp_path)
                except Exception:
                    pass
    except Exception:
        pass

    if not args.quiet:
        dests = ", ".join([f"{k}" if k != "file" else f"file:{p}" for k, p in outputs])
        sort_msg = "original order (restored)" if did_undo else (f"sorted ({args.sort})" if args.sort is not None else "original order")
        status_bits = []
        if posted:
            status_bits.append("saved to hub")
        if did_undo:
            status_bits.append("then undone")
        status = "; ".join(status_bits) if status_bits else "completed"

        print(f"{ok('OK:')} {status}. {len(final_tiles)} tile(s) written to {dests} ({sort_msg}).", file=sys.stderr)
