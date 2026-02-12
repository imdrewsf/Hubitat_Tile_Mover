from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .cli import build_parser
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
from .util import die, vlog


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

    # Determine if any operation was requested
    do_left, do_top = _parse_trim_modes(args.trim, getattr(args, "trim_left", False), getattr(args, "trim_top", False))
    has_trim = bool(do_left or do_top)

    deleted_ids: list[int] = []
    cleared_ids: list[int] = []
    created_id_map: dict[int, int] = {}
    merge_css_source_path: str = ""

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
    if (args.merge_cols or args.merge_rows or args.merge_range) and not args.merge_source:
        die("--merge_source <filename> is required when using --merge_cols/--merge_rows/--merge_range.")

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
        vlog(True, f"Debug per-tile: {bool(args.debug)}")
        vlog(True, "====================================")

    raw = read_input_text(import_kind, import_path)
    obj = load_json_from_text(raw, verbose=args.verbose, debug=args.debug)

    kind, full_container, tiles_any = extract_tiles_container(obj, verbose=args.verbose, debug=args.debug)
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
            merge_source_path=args.merge_source,
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
        merge_css_source_path = args.merge_source


    elif args.merge_rows:
        s, e, d = args.merge_rows
        created_id_map = merge_rows(
            tiles,
            merge_source_path=args.merge_source,
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
        merge_css_source_path = args.merge_source


    elif args.merge_range:
        r1, c1, r2, c2, dr, dc = args.merge_range
        created_id_map = merge_range(
            tiles,
            merge_source_path=args.merge_source,
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
        merge_css_source_path = args.merge_source


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

    write_outputs(outputs, args.newline, out_text)

    if not args.quiet:
        from .util import ok
        import sys

        dests = ", ".join([f"{k}" if k != "file" else f"file:{p}" for k, p in outputs])
        sort_msg = f"sorted ({args.sort})" if args.sort is not None else "original order"
        print(
            f"{ok('OK:')} {len(final_tiles)} tile(s) written to {dests} ({sort_msg}).",
            file=sys.stderr,
        )
