from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

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
from .ops_crop import crop_to_cols, crop_to_range, crop_to_rows, prune_except_devices, prune_except_ids
from .ops_insert import insert_cols, insert_rows
from .ops_merge import merge_cols, merge_range, merge_rows
from .ops_move import move_cols, move_range, move_rows
from .ops_trim import trim_tiles
from .sort_tiles import complete_sort_spec, sort_tiles
from .tiles import verify_tiles_minimum, as_int
from .css_ops import (
    cleanup_css_for_tile_ids,
    generate_css_for_id_map,
    get_custom_css,
    orphan_tile_ids_in_css,
    set_custom_css,
    tile_ids_in_css,
)
from .util import die, vlog, ok, wlog, prompt_yes_no


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
    """Backup filename derived from host + dashboard id (stored in CWD)."""
    import re
    import urllib.parse
    u = urllib.parse.urlparse(dashboard_url)
    host = (u.hostname or "hub").replace(":", "_")
    m = re.search(r"/dashboard/(\d+)", u.path)
    dash = m.group(1) if m else "dashboard"
    return f"hubitat_tile_mover_backup_{host}_{dash}.json"

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


def _state_path() -> str:
    return "hubitat_tile_mover_last_run.json"

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

    if argv is None:
        argv = _sys.argv[1:]

    argv = normalize_argv(argv)

    # Guard singletons (track legacy tokens too)
    assert_singleton_flags(argv, ["--import"])
    assert_singleton_flags(argv, ["--output_format", "--output-format", "--output_shape", "--output-shape"])

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.indent < 0:
        die("--indent must be >= 0.")

    import_kind, import_path = parse_import_spec(args.import_spec)
    outputs = parse_output_to_specs(args.output_to)

    # --undo_last is a standalone restore action.
    # It restores the previous backup and writes it to the last output destinations unless --output/--output_to is provided.
    if args.undo_last:
        forbidden = [
            args.insert_rows, args.insert_cols, args.move_cols, args.move_rows, args.move_range,
            args.delete_rows, args.delete_cols, args.clear_rows, args.clear_cols, args.clear_range,
            args.crop_to_rows, args.crop_to_cols, args.crop_to_range,
            args.prune_except_ids, args.prune_except_devices,
            args.copy_cols, args.copy_rows, args.copy_range,
            args.merge_cols, args.merge_rows, args.merge_range,
            args.trim, args.sort, args.scrub_css,
        ]
        if any(x for x in forbidden if x):
            die("--undo_last cannot be combined with other actions. Use -h for help.")

        if not os.path.exists(_state_path()):
            die("No last-run state found; nothing to undo.")
        st = _read_state()

        backup_path = st.get("backup_path")
        if not backup_path or not os.path.exists(backup_path):
            die("Backup file not found; nothing to undo.")

        obj = _read_backup(backup_path)
        kind, full_container, tiles_any = extract_tiles_container(obj, verbose=args.verbose, debug=args.debug)
        from .jsonio import normalize_tiles_list as _ntl
        tiles = _ntl(tiles_any, verbose=args.verbose, debug=args.debug)

        # Default outputs to last outputs, unless user provided outputs this run
        outputs = parse_output_to_specs(args.output_to) if args.output_to else st.get("last_outputs", [("clipboard", None)])
        url = args.url or st.get("last_url")
        using_hub_output = any((k == "hub") for (k, _) in outputs)
        if using_hub_output and not url:
            die("Undo restore requires --url (or a prior hub run with stored URL) when outputting to hub.")

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
        write_outputs(non_hub, args.newline, out_text)
        if using_hub_output:
            hub_ctx, _tmp = hub_import_layout(url, verbose=args.verbose, debug=args.debug)
            hub_post_layout_with_refresh(url, hub_ctx.layout_url, out_obj, verbose=args.verbose, debug=args.debug)

        dests = ", ".join([(k if k != "file" else f"file:{p}") for (k, p) in outputs])
        from .util import ok as _ok
        import sys as _sys
        print(f"{_ok('OK:')} undo applied. Output written to {dests}.", file=_sys.stderr)
        return


    using_hub_import = (import_kind == "hub")
    using_hub_output = any(k == "hub" for (k, _p) in outputs)

    # Determine if any operation was requested
    do_left, do_top = _parse_trim_modes(args.trim, getattr(args, "trim_left", False), getattr(args, "trim_top", False))
    has_trim = bool(do_left or do_top)

    deleted_ids: list[int] = []
    cleared_ids: list[int] = []
    created_id_map: dict[int, int] = {}
    merge_css_source_path: str = ""
    merge_source_path: str = args.merge_source or ""
    if (args.merge_cols or args.merge_rows or args.merge_range) and args.merge_url:
        _, mobj = hub_import_layout(args.merge_url, verbose=args.verbose, debug=args.debug)
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
    )
    if not (has_movement or has_trim or args.scrub_css or (args.sort is not None or args.order is not None)):
        die("No operation specified. Use one movement/edit option and/or trim and/or --sort and/or --scrub_css. Use -h for help.")

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

    # Validate merge usage
    if (args.merge_cols or args.merge_rows or args.merge_range):
        if bool(args.merge_source) == bool(args.merge_url):
            die("For merge operations, specify exactly one of --merge_source <filename> or --merge_url <dashboard_url>.")
    col_range = _parse_inclusive_range("--col_range", args.col_range)
    row_range = _parse_inclusive_range("--row_range", args.row_range)

    if args.verbose:
        outs_desc = []
        for k, v in outputs:
            outs_desc.append(f"{k}({v})" if v else k)

        vlog(True, "=== tile_sorter.py planned actions ===")
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
        if args.merge_source:
            vlog(True, f"Merge source: {args.merge_source}")
        if getattr(args, 'merge_url', None):
            vlog(True, f"Merge URL: {args.merge_url}")
        vlog(True, f"Debug per-tile: {bool(args.debug)}")
        vlog(True, "====================================")
    backup_path = None
    backup_obj = None
    backup_tmp_path = None
    # Backup is required for hub output and for --confirm_keep (and for hub import, as a restore point).
    if args.url and (using_hub_import or using_hub_output or args.confirm_keep) and (not args.undo_last):
        backup_path = _backup_path_for_url(args.url)
        if args.lock_backup and os.path.exists(backup_path):
            # Use existing backup as the restore point and do not overwrite it.
            backup_obj = _read_backup(backup_path)
        else:
            # Write to a temporary file; only commit if the run completes successfully.
            import tempfile
            fd, backup_tmp_path = tempfile.mkstemp(prefix="hubitat_tile_mover_backup_", suffix=".json")
            os.close(fd)
            _write_backup(backup_tmp_path, obj)
            backup_obj = obj
    kind, full_container, tiles_any = extract_tiles_container(obj, verbose=args.verbose, debug=args.debug)
    if using_hub_output and kind != "full_object":
        die("--output:hub requires FULL layout JSON input (cannot use minimal/bare).")
    if using_hub_output:
        if kind != "full_object":
            die("--output:hub requires FULL dashboard JSON input.")
        if args.output_format in ("minimal", "bare", "container", "list"):
            die("--output:hub cannot be used with --output_format:minimal or --output_format:bare.")
    verify_tiles_minimum(tiles_any)
    tiles: List[Dict] = tiles_any  # type: ignore[assignment]

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
        )

    elif args.prune_except_devices:
        deleted_ids = prune_except_devices(
            tiles,
            devices_csv=args.prune_except_devices,
            force=args.force,
            verbose=args.verbose,
        )
    # Post-op CSS handling
    css_key, css_text = get_custom_css(obj)

    if args.cleanup_css and css_key is not None and css_text and (deleted_ids or cleared_ids):
        from .util import format_id_sample, prompt_yes_no_or_die

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

    # CSS orphan detection / scrub (performed last, after sorting).
    if css_key is not None:
        _, css_text2 = get_custom_css(obj)
        css_text2 = css_text2 or ""
        existing_ids = {as_int(t, "id") for t in final_tiles}
        orphans = orphan_tile_ids_in_css(css_text2, existing_ids) if css_text2 else set()
        if orphans and args.scrub_css:
            from .util import format_id_sample, prompt_yes_no_or_die

            prompt_yes_no_or_die(
                args.force,
                f"--scrub_css will remove CSS rules referencing {len(orphans)} missing tile(s). IDs: {format_id_sample(list(orphans))}. Proceed?",
                what="CSS rules",
            )
            css_text2 = cleanup_css_for_tile_ids(css_text2, list(orphans))
            set_custom_css(obj, css_key, css_text2)
        elif orphans and not args.quiet:
            from .util import wlog, format_id_sample

            wlog(
                f"Found {len(orphans)} orphan CSS tile id(s) in customCSS (no matching tile). "
                f"Use --scrub_css to remove. IDs: {format_id_sample(list(orphans))}"
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
        if hub_ctx is None:
            hub_ctx, _tmp = hub_import_layout(args.url, verbose=False, debug=False)
        post_url_used = hub_post_layout_with_refresh(args.url, hub_ctx.layout_url, output_obj, verbose=args.verbose, debug=args.debug)
        posted = True

    # confirm/undo (if user chooses undo, also re-post to hub if requested)
    did_undo = False
    if args.confirm_keep and (backup_obj is not None) and (not args.undo_last):
        keep = prompt_yes_no(args.force, 'Keep these changes?', default_yes=True)
        if not keep:
            did_undo = True
            output_obj = backup_obj

            # Re-output the original (backup) JSON, not the modified tiles.
            b_kind, b_full_container, b_tiles_any = extract_tiles_container(backup_obj, verbose=args.verbose, debug=args.debug)
            verify_tiles_minimum(b_tiles_any)
            b_tiles = b_tiles_any  # type: ignore[assignment]
            undo_obj = build_output_object(b_kind, b_full_container, b_tiles, args.output_format)
            output_obj = undo_obj
            out_text2 = dump_json(undo_obj, indent=args.indent, minify=args.minify)
            if not out_text2.endswith("\n"):
                out_text2 += "\n"

            write_outputs(non_hub_outputs, args.newline, out_text2)
            if using_hub_output:
                if hub_ctx is None:
                    hub_ctx, _tmp = hub_import_layout(args.url, verbose=False, debug=False)
                post_url_used = hub_post_layout_with_refresh(args.url, hub_ctx.layout_url, output_obj, verbose=args.verbose, debug=args.debug)
                posted = True


    if not args.quiet:
        from .util import ok
        import sys

        dests =  ", ".join([f"{k}" if k != "file" else f"file:{p}" for k, p in outputs])
        sort_msg = f"sorted ({args.sort})" if args.sort is not None else "original order"
        status_bits = []
        if args.undo_last:
            status_bits.append('undo applied')
        if posted:
            status_bits.append('saved to hub')
        if did_undo:
            status_bits.append('then undone')
        status = '; '.join(status_bits) if status_bits else 'completed'
        # Commit backup (atomic) and persist last-run state for --undo_last defaults.
        try:
            # If we created a new backup this run, commit it only after all outputs (and hub POST) succeeded.
            if backup_tmp_path and backup_path and (not (args.lock_backup and os.path.exists(backup_path))):
                os.replace(backup_tmp_path, backup_path)
            _write_state({
                "backup_path": backup_path,
                "last_outputs": outputs,
                "last_url": args.url,
                "last_output_format": args.output_format,
            })
        except Exception:
            pass

        print(f"{ok('OK:')} {status}. {len(final_tiles)} tile(s) written to {dests} ({sort_msg}).", file=sys.stderr)
