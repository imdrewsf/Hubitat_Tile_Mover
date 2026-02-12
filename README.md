<<<<<<< HEAD
# hubitat tile mover
=======
Hubitat Tile Mover � adjust a Hubitat Dashboard layout by operating on the "tiles" list (row/col only), preserving everything else unchanged.
>>>>>>> b202d7e (update readme.md)

Command-line tool to bulk-edit Hubitat Dashboard layout JSON by operating on the `tiles` list (row/col only) while preserving all other JSON fields unchanged.

It is designed for **moving/copying/merging whole groups of tiles** (ranges/rows/columns) and for cleanup operations like trimming blank space, cropping to a region, and pruning to selected tiles.

## Features

### Layout actions (choose at most one per run)
- **Insert**: `--insert_rows`, `--insert_cols`
- **Move**: `--move_cols`, `--move_rows`, `--move_range`
- **Copy** (duplicate from the same layout): `--copy_cols`, `--copy_rows`, `--copy_range`
- **Merge** (import tiles from another layout file): `--merge_source` + `--merge_cols/rows/range`
- **Remove**:
  - Delete + shift: `--delete_rows`, `--delete_cols`
  - Clear only: `--clear_rows`, `--clear_cols`, `--clear_range`
- **Crop** (remove everything outside a kept range): `--crop_to_rows/cols/range`
- **Prune** (keep only selected): `--prune_except_ids <comma separated list of tile ids>`, `--prune_except_devices <comma separated list of devices>` 

### Additional actions (can be combined with the single layout action)
- **Trim**: `--trim[:top|left|top,left]` (removes empty rows or columns at the top or left of the dashboard runs after the layout action)
- **Sort**: `--sort` or `--sort:<SPEC>` (this only affects the order tiles appear in the JSON but has no effect on the actual layout)
- **Scrub orphan CSS**: `--scrub_css`

### Modifiers
- `--include_overlap`  
  Select tiles by span intersection (using `rowSpan`/`colSpan`) rather than only the tile’s top-left.
- Range filters:
  - `--col_range <start_col> <end_col>` (insert/delete rows only)
  - `--row_range <start_row> <end_row>` (insert/delete cols only)
- Destination conflict policy for move/copy/merge:
  - `--allow_overlap` (force even if destination conflicts exist)
  - `--skip_overlap` (skip only conflicting tiles)
  - default: abort before changing anything if conflicts exist
- Confirmation suppression:
  - `--force` (skip prompts when tiles/CSS would be removed)

### CSS options
- `--cleanup_css`  
  When tiles are removed, attempt to remove tile-specific CSS rules for removed tile ids.
- `--ignore_css`  
  When copying/merging tiles, do not create/merge tile-specific CSS rules for new tile ids.
- `--scrub_css`  
  Remove orphan tile-specific CSS rules (CSS references tile ids that do not exist as tiles).

Tile IDs created during copy/merge are always assigned above the maximum of:
- the highest existing tile id, and
- the highest tile id referenced in `customCSS`

This prevents newly created tiles from accidentally reusing ids that still have orphan CSS rules.

## Input and Output

### Accepted input JSON shapes
- **Full**: `{ ..., "tiles": [ ... ], ... }`
- **Minimal**: `{ "tiles": [ ... ] }`
- **Bare**: `[ ... ]`

### Import (default: clipboard)
- `--import:clipboard`
- `--import:file <filename>`

### Output destinations (repeatable; default: clipboard)
- `--output_to:clipboard`
- `--output_to:terminal`
- `--output_to:file <filename>`

### Output format (default: same level as input; cannot exceed input)
- `--output_format:full`
- `--output_format:minimal`
- `--output_format:bare`

(Compatibility aliases: `container == minimal`, `list == bare`.)


## How to use: 
1. Select All and copy your dashboard's layout CSS to the clipboard.
2. Run the desired action.  The changes will be saved back to the clipboard
3. Paste the changed layout back into your dashboard or run additional actions.
   Additional actions will be made on the layout currently in the clipboard allowing
   you to chain a series of changes.


## Quick examples

### Insert 12 columns at column 15 
```bash
python hubitat_tile_mover.py --insert_cols 12 15
```

### Move a block of columns to a new location
```bash
python hubitat_tile_mover.py --move_cols 1 30 65 --output_to:clipboard
```

### Copy a range of tiles (duplicate) and allow destination overlap
```bash
python hubitat_tile_mover.py --copy_range 1 1 20 40 1 50 --allow_overlap
```

### Merge tiles from another exported layout file
```bash
python hubitat_tile_mover.py --merge_source other.json --merge_cols 1 30 85
```

### Delete columns and also cleanup matching CSS rules (prompts unless --force)
```bash
python hubitat_tile_mover.py --delete_cols 85 100 --cleanup_css --force
```

### Crop to a range (keep only that region)
```bash
python hubitat_tile_mover.py --crop_to_range 1 1 30 60
```

<<<<<<< HEAD
### Remove orphaned tile CSS rules
```bash
python hubitat_tile_mover.py --scrub_css
```
=======
  Selection / overlap:
    --include_overlap
      Default selection: tiles are selected when their top-left (row,col) is inside the source/range.
      With --include_overlap: tiles are also selected when their span intersects the source/range
      (span uses rowSpan/colSpan; missing span defaults to 1x1).

  Insert/Delete range filters (limit which tiles are affected):
    --col_range <start_col> <end_col>     (only with --insert_rows and --delete_rows)
    --row_range <start_row> <end_row>     (only with --insert_cols and --delete_cols)

  Destination conflict policy (move/copy/merge only):
    --allow_overlap
      Proceed even if destination conflicts exist.
    --skip_overlap
      Skip only the tiles that would conflict in the destination.
    default (neither set):
      Abort before changing anything if any destination conflicts exist.

  Confirmation suppression:
    --force
      Skip interactive confirmations when tiles or CSS rules would be removed.


CSS OPTIONS

  --ignore_css
      When copying/merging tiles, do not create/merge tile-specific CSS rules for new tile ids.

  --cleanup_css
      When tiles are removed (delete/clear/crop/prune), attempt to remove tile-specific CSS rules for those tile ids.
      Prompts before removal unless --force is specified.

  Tile id assignment when copying/merging:
      New tile ids are assigned sequentially starting at:
        1 + max(highest existing tile id, highest tile id referenced in customCSS)
      This prevents newly created tiles from accidentally reusing ids that still have orphan CSS rules.


FORMATTING

  --indent N               Pretty JSON indent spaces per nesting level (N can be 0; default: 2)
  --minify                 Compact one-line JSON (overrides --indent)
  --newline keep|lf|crlf   Normalize output newlines


DIAGNOSTICS

  --quiet                  Suppress the final one-line summary
  --verbose                Planned actions summary to STDERR
  --debug                  Per-tile action logs to STDERR

>>>>>>> b202d7e (update readme.md)

