# hubitat_tile_mover refactor

This ZIP contains a multi-module refactor of `hubitat_tile_mover.py` with additional features:

## Key changes

- Range filters now also apply to deletes:
  - `--col_range` applies to `--insert_rows` and `--delete_rows`
  - `--row_range` applies to `--insert_cols` and `--delete_cols`
- Merge-from-another-file:
  - `--merge_source <file>`
  - `--merge_cols`, `--merge_rows`, `--merge_range`
  - These behave like the corresponding `--move_*` operations, but **copy** tiles from the merge source into the destination JSON.
  - Conflict handling is identical (`--allow_overlap` / `--skip_overlap`).
- Trimming is now composable:
  - `--trim`, `--trim_top`, `--trim_left` can be used alongside one movement/edit operation.
  - Trim is applied **after** the movement/edit operation but **before** `--sort`.

## Run

```bash
python hubitat_tile_mover.py --help
```

- Trim usage: `--trim` (default top+left), `--trim:top`, `--trim:left`, or `--trim:top,left`.

- Copy ops: `--copy_cols/--copy_rows/--copy_range` duplicate tiles from the input JSON into a new location.
  If a copied tile's `id` conflicts with an existing tile, it is reassigned to (max existing id + 1), incrementing as needed.
- Merge ops: copied tiles from `--merge_source` also reassign `id` on conflict using the same rule.

- CSS options:
  - `--cleanup_css`: when clearing/deleting tiles, attempt to remove CSS rules that reference deleted tile IDs.
  - `--create_css`: when copying or merging tiles, attempt to create CSS rules for new tile IDs.


## Sorting

- Use `--sort[:SPEC]` to sort the tiles list.
  - Keys: `i`=id, `r`=row, `c`=col
  - Prefix a key with `-` for descending.
  - Examples: `--sort:rci`, `--sort:-rci`, `--sort:r-c-i`
  - Missing keys are appended in `r,c,i` order (ascending).
