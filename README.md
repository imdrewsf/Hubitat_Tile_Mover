# Hubitat Tile Mover

<!-- TOC -->

- [Overview:](#overview)
    - [Import, modify and output Hubitat dashboard layouts:](#import-modify-and-output-hubitat-dashboard-layouts)
    - [Layout Actions](#layout-actions)
    - [Additional Features](#additional-features)
- [Layout Import Sources and Output Destinations:](#layout-import-sources-and-output-destinations)
    - [Import Sources](#import-sources)
    - [Output destinations](#output-destinations)
- [Layout Actions Overview:](#layout-actions-overview)
    - [Layout Action types:](#layout-action-types)
    - [Action targets:](#action-targets)
        - [Key concepts:](#key-concepts)
        - [Documentation Syntax:](#documentation-syntax)
        - [Selecting Tiles:](#selecting-tiles)
- [Primary Edit Actions](#primary-edit-actions)
    - [Insert](#insert)
    - [Move](#move)
    - [Copy](#copy)
    - [Merge](#merge)
    - [Delete](#delete)
    - [Clear](#clear)
    - [Crop](#crop)
    - [Prune](#prune)
    - [Trim](#trim)
- [CSS Actions](#css-actions)
    - [Copy CSS](#copy-css)
    - [Clear CSS](#clear-css)
- [Supplemental Actions and Options](#supplemental-actions-and-options)
    - [Sort](#sort)
    - [Visual Layout Maps](#visual-layout-maps)
    - [Miscellaneous Options:](#miscellaneous-options)
    - [Help](#help)
- [Custom CSS Handling — Capabilities & Limits](#custom-css-handling--capabilities--limits)
    - [CSS Overview](#css-overview)
    - [CSS Rule Guidelines](#css-rule-guidelines)
    - [Compatible selector patterns](#compatible-selector-patterns)
        - [✅ Single selector item scoped to one tile](#-single-selector-item-scoped-to-one-tile)
        - [🆗 Selector list (comma-separated) containing tile selectors](#-selector-list-comma-separated-containing-tile-selectors)
        - [✅ Rules inside `@media` blocks](#-rules-inside-media-blocks)
    - [Incompatible and Problematic CSS Rules](#incompatible-and-problematic-css-rules)
        - [❌ Multi-tile selector items:](#-multi-tile-selector-items)
        - [🟡 Tile IDs inside declaration blocks](#🟡-tile-ids-inside-declaration-blocks)
    - [CSS Comments](#css-comments)
        - [Comment Block Duplication -  Copy/Merge Operations:](#comment-block-duplication----copymerge-operations)
        - [Comment Block Removal - Delete/Clear/Crop/Prune/CSS Clean-up/Operations](#comment-block-removal---deleteclearcropprunecss-clean-upoperations)
- [Tool Usage Examples:](#tool-usage-examples)
- [Batch Actions:](#batch-actions)
    - [Tips for running a batched or consecutive actions:](#tips-for-running-a-batched-or-consecutive-actions)
    - [Example Batch](#example-batch)
        - [Batch Overview](#batch-overview)
        - [Example](#example)
        - [Batched Actions in Detail](#batched-actions-in-detail)
            - [The First Action (Run)](#the-first-action-run)
            - [The second action:](#the-second-action)
            - [The third action:](#the-third-action)

<!-- /TOC -->

<div style="page-break-after: always"></div>

<a id="markdown-overview" name="overview"></a>

## Overview:

<a id="markdown-import-modify-and-output-hubitat-dashboard-layouts" name="import-modify-and-output-hubitat-dashboard-layouts"></a>

### Import, modify and output Hubitat dashboard layouts:

* **Import** dashboard layouts directly from the hub • JSON files • the clipboard (default)
* **Output** changed layouts directly back to the hub • JSON files • the clipboard (default)

<a id="markdown-layout-actions" name="layout-actions"></a>

### Layout Actions

* <b>[MOVE](#move)</b> columns, rows or a rectangular range of tiles
* <b>[COPY](#copy)</b> columns, rows or a rectangular range of tiles
* <b>[MERGE](#merge)</b> copy columns, rows or a rectangular range of tiles from another dashboard
* <b>[INSERT](#insert)</b> full or partial empty columns or rows (push tiles over/down at column/row)
* <b>[DELETE](#delete)</b> full or partial columns or rows of tiles (remove tiles and shift the layout left or up)
* <b>[CLEAR](#clear)</b> columns, rows or a rectangular range of tiles but leaves the empty space.
* <b>[CROP](#crop)</b> a layout by clearing all tiles not in columns, rows or a rectangular range
* <b>[PRUNE](#prune)</b> a layout by tile or devices id.  Clear only specific id's or clear all ***except*** specific id's
* <b>[TRIM](#trim)</b> a layout to remove empty top rows and/or left columns.

<a id="markdown-additional-features" name="additional-features"></a>

### Additional Features

* Preserve, duplicate or remove custom CSS rules when tiles added (copied) or removed by actions
* Prevent actions which would result in tiles be placed over existing tiles
* Visual Layout Maps: Easily see proposed changes, potential conflicts and final outcome of actions

![multimap](https://github.com/user-attachments/assets/547d6dc4-8ab6-4d50-817c-17b7efb767cb)

---

<div style="page-break-after: always"></div>

<a id="markdown-layout-import-sources-and-output-destinations" name="layout-import-sources-and-output-destinations"></a>

## Layout Import Sources and Output Destinations:

<a id="markdown-import-sources" name="import-sources"></a>

### Import Sources

Exactly one import method is used. If not specified, clipboard is the default.

- Action Setting:
  
  `--import:`***type***
  <br>
- Import Types: `clipboard | file | hub`
  
  `--import:clipboard` — Read JSON text from clipboard.
  `--import:file "<filename>"` — Read JSON text from file.
  `--import:hub "<url>"` — Fetch the full layout JSON from Hubitat using `url`.
  <br>
- Dashboard URL format (typical):
  
  ```
  http://<hub-ip>/apps/api/<appId>/dashboard/<dashId>?access_token=<token>&local=true
  ```

---

<a id="markdown-output-destinations" name="output-destinations"></a>

### Output destinations

Sets the destination to save dashboard layout JSON after layout actions have completed

- Setting:
  
  `--output:`***type***
  <br>
- Output Types: `terminal | clipboard | file | hub`
  
  `--output:terminal` — Print output to terminal.
  `--output:clipboard` — Write to clipboard (default)
  `--output:file "<filename>"` — Write to file.
  `--output:hub "[url]"` — POST full layout JSON back to the hub at `url`
  <br>
- Notes:
  
  - Output default is the clipboard if not specified.
  - `url` can be omitted if specified with `--import:hub`
    <br>
  - `--output:hub` will fail if:
    
    - `url` is not specified and import is not `--import:hub`
    - `url` is not a valid or reachable local dashboard url.
    - A valid requestToken could not be obtained.

---

<div style="page-break-after: always"></div>

<a id="markdown-layout-actions-overview" name="layout-actions-overview"></a>

## Layout Actions Overview:

<a id="markdown-layout-action-types" name="layout-action-types"></a>

### Layout Action types:

1. **Primary edit actions** — make modifications to tiles.  Primary actions include insert, move, copy, merge, delete, clear, crop and prune.  Only one primary edit action can be per run.
2. **Supplemental actions** — can be used standalone or with primary actions.  These include displaying visual layout maps, JSON sorting, orphaned CSS cleanup and trim functions.  Supplemental actions are always performed after primary actions.
3. **Undo /restore action**  — `--undo_last` is a standalone action.  It supersedes all other actions.

<a id="markdown-action-targets" name="action-targets"></a>

### Action targets:

<a id="markdown-key-concepts" name="key-concepts"></a>

#### Key concepts:

- A tile's location is determined by the row and column of its upper left corner.
- A tile's span is the area it occupies, calculated as (row + height -1), (column + width -1).
- Tiles whose span extends into, but are located (begin) outside of the target area, are considered to be target area "overlaps."

<a id="markdown-documentation-syntax" name="documentation-syntax"></a>

#### Documentation Syntax:

- `< ... >` indicate required parameters.  Do not include the `<` or `>`.
- `[ ... ]` indicate optional parameters.  Do not include the `[` or `]`.

<a id="markdown-selecting-tiles" name="selecting-tiles"></a>

#### Selecting Tiles:

- By default, actions are applied only to tiles that are located (begin) in the target rows, column, or rectangular range.
- To include tiles that overlap the boundaries of the target area, use the `--include_overlap` switch.

---

<div style="page-break-after: always"></div>

<a id="markdown-primary-edit-actions" name="primary-edit-actions"></a>

## Primary Edit Actions

<a id="markdown-insert" name="insert"></a>

### Insert

Inserts empty whole or partial rows or columns by pushing tiles beyond the insertion point

- Action:
  
  `--insert:`***mode***
  <br>
- Modes: `rows | cols`
  
  `--insert:rows <count> <at_row>`
  `--insert:cols <count> <at_col>`
  
  - `rows` —  Pushes down (increase tile's 'row' by `count`) tiles at/after `at_row`, and optionally tiles overlapping the insertion row.
    <br>
  - `cols` — Pushes right (increase tile's 'col' by `count`) tiles at/after `at_col`, and optionally tiles overlapping the insertion column.
    <br>
- Selection Modifiers:
  
  - `--col_range <start_col> <end_col>` — Insert rows only in column range. Only valid with `--insert:rows`
  - `--row_range <start_row> <end_row>` — Insert columns only in row range. Only valid with `--insert:cols`
    <br>
  - `--include_overlap`
    <br>
- Options:
  
  - `--confirm_keep` — After writing output, prompts (independently of `--force`) to keep or undo the changes made.

---

<a id="markdown-move" name="move"></a>

### Move

Moves tiles to a new location.

- Action:
  
  `--move:`***mode***
  <br>
- Modes: `rows | cols | range`
  
  `--move:rows <start_row> <end_row> <dest_start_row>`
  `--move:cols <start_col> <end_col> <dest_start_col>`
  `--move:range <src_top_row> <src_left_col> <src_bottom_row> <src_right_col> <dest_top_row> <dest_left_col>`
  <br>
- Selection Modifier:
  
  - `--include_overlap`
    <br>
- Options:
  
  - `--allow_overlap` — ignore conflicts and allow moved tiles to overlap existing tiles at the destination.
  - `--skip_overlap` — skip tiles that would conflict, move all others.
    <br>
  - `--confirm_keep` — After writing output, prompts (independently of `--force`) to keep or undo the changes made.
    <br>
- Notes:
  
  - Conflict detection is evaluated **once, \*before\*** moving/copying, against **existing destination tiles only**.  Any tiles that are being copied/moved can be overlapped and will not be considered in conflict.
  - Default behavior: if any conflicts exist, abort before moving anything.

---

<a id="markdown-copy" name="copy"></a>

### Copy

Same as Move, but originals remain.  Copies are created with new IDs. Existing tile specific CSS rules in customCSS can be optionally copied with the new IDs

- Action:
  
  `--copy:`***mode***
  <br>
- Modes: `rows | cols | range`
  
  `--copy:rows <start_row> <end_row> <dest_start_row>`
  `--copy:cols <start_col> <end_col> <dest_start_col>`
  `--copy:range <src_top_row> <src_left_col> <src_bottom_row> <src_right_col> <dest_top_row> <dest_left_col>`
  <br>
- Selection Modifier:
  
  - `--include_overlap`
    <br>
- Options:
  
  - `--allow_overlap` — ignore conflicts and allow moved tiles to overlap existing tiles at the destination.
  - `--skip_overlap` — skip tiles that would conflict, move all others.
    <br>
  - `--ignore_css` — disables creating/copying CSS for new IDs.
    <br>
  - `--confirm_keep` — After writing output, prompts (independently of `--force`) to keep or undo the changes made.
    <br>
- Notes:
  
  - ID allocation for new tiles:  New IDs are created sequentially beginning starting with 1 + max(highest existing tile ID, highest referenced tile ID in customCSS).  This prevents any orphaned CSS rules from being applied to new tiles.
  - By default, customCSS is checked for any tile specific CSS rules for copied tiles.  Any rules found are duplicated for the new tile id
  - Conflict detection is evaluated **once, \*before\*** moving/copying, against **existing destination tiles only**.
  - Tiles that are being copied/moved can be overlapped and will not be considered in conflict.
  - Actions will be aborted if conflicts are found unless `--allow_overlap` or `--skip_overlap` is present.

---

<a id="markdown-merge" name="merge"></a>

### Merge

Merge (copy) tiles from another dashboard layout into this layout.

- Action:
  
  `--merge:`***mode*** `--merge_source:`***type***` "<filename | hub>"`
  <br>
- Modes: `rows | cols | range`
  
  `--merge:rows <start_row> <end_row> <dest_start_row>`
  `--merge:cols <start_col> <end_col> <dest_start_col>`
  `--merge:range <src_top_row> <src_left_col> <src_bottom_row> <src_right_col> <dest_top_row> <dest_left_col>`
  <br>
- Source Types (required): `file | hub`
  
  - `--merge_source:file "<filename>"` — load source JSON from file
  - `--merge_source:hub "<other_dashboard_local_url>"` — fetch source JSON from hub
    <br>
- Selection Modifier:
  
  - `--include_overlap`
    <br>
- Options:
  
  - `--allow_overlap` — ignore conflicts and allow moved tiles to overlap existing tiles at the destination.
  - `--skip_overlap` — skip tiles that would conflict, move all others.
    <br>
  - `--ignore_css` — disables creating/copying CSS for new IDs.
    <br>
  - `--confirm_keep` — After writing output, prompts (independently of `--force`) to keep or undo the changes made.
    <br>
- Notes:
  
  - ID allocation for new tiles:  New IDs are created sequentially beginning starting with 1 + max(highest existing tile ID, highest referenced tile ID in customCSS).  This prevents any orphaned CSS rules from being applied to new tiles.
  - By default, customCSS is checked for any tile specific CSS rules for copied tiles.  Any rules found are duplicated for the new tile id
  - Conflict detection is evaluated **once, \*before\*** moving/copying, against **existing destination tiles only**.
  - Tiles that are being copied/moved can be overlapped and will not be considered in conflict.
  - Actions will be aborted if conflicts are found unless `--allow_overlap` or `--skip_overlap` is present.

---

<a id="markdown-delete" name="delete"></a>

### Delete

Deletes tiles located in the target rows or columns, then shifts remaining tiles to close the gap.

- Action:
  
  `--delete:`***mode***
  <br>
- Modes: `rows | cols`
  
  `--delete:rows <start_row> <end_row>`
  `--delete:cols <start_col> <end_col>`
  <br>
- Selection Modifiers:
  
  - `--row_range <start_row> <end_row>` — Deletes columns only in row range. Only valid with `--delete:cols`
  - `--col_range <start_col> <end_col>` — Deletes rows only in column range. Only valid with `--delete:rows`
    <br>
  - `--include_overlap`
    <br>
- Options:
  
  - `--force` — skip confirmation prompts -- assume yes.
  - `--confirm_keep` — After writing output, prompts (independently of `--force`) to keep or undo the changes made.
  - `--cleanup_css` — remove tile-specific CSS rules from 'customCSS' for tiles removed or cleared by the current action.
    <br>
- Notes:
  
  - The default behavior is to leave tile CSS rules for tiles removed or cleared by the current operation in place, unless --cleanup_css` is present.
  - Use `--scrub_css` to remove all orphaned CSS rules, including rules for tiles removed or cleared by the current operation. all orphaned CSS rules, including rules for tiles removed or cleared by the current operation.

---

<a id="markdown-clear" name="clear"></a>

### Clear

Removes tiles in the target rows, columns or range but does not change the dashboard layout.

- Action:
  
  `--clear:`***mode***
  <br>
- Modes: `rows | cols | range`
  
  `--clear:rows <start_row> <end_row> `
  `--clear:cols <start_col> <end_col>`
  `--clear:range <top_row> <left_col> <bottom_row> <right_col>`
  <br>
- Selection Modifier:
  
  - `--include_overlap`
    <br>
- Options:
  
  - `--force` — skip confirmation prompts -- assume yes.
  - `--confirm_keep` — After writing output, prompts (independently of `--force`) to keep or undo the changes made.
  - `--cleanup_css` — remove tile-specific CSS rules from 'customCSS' for tiles removed or cleared by the current action.
    <br>
- Notes:
  
  - The default behavior is to leave tile CSS rules for tiles removed or cleared by the current operation in place, unless --cleanup_css` is present.
  - Use `--scrub_css` to remove all orphaned CSS rules, including rules for tiles removed or cleared by the current operation. all orphaned CSS rules, including rules for tiles removed or cleared by the current operation.

---

<a id="markdown-crop" name="crop"></a>

### Crop

Clears tiles outside of the target rows, columns or range.  The position of remaining tiles is unchanged.

- Action:
  
  `--crop:`***mode***
  <br>
- Modes: `rows | cols | range`
  
  `--crop:rows <start_row> <end_row>`
  `--crop:cols <start_col> <end_col>`
  `--crop:range <top_row> <left_col> <bottom_row> <right_col>`
  <br>
- Selection Modifier:
  
  - `--include_overlap`
    <br>
- Options:
  
  - `--force` — skip confirmation prompts -- assume yes.
  - `--confirm_keep` — After writing output, prompts (independently of `--force`) to keep or undo the changes made.
  - `--cleanup_css` — remove tile-specific CSS rules from 'customCSS' for tiles removed or cleared by the current action.
    <br>
- Notes:
  
  - The default behavior is to leave tile CSS rules for tiles removed or cleared by the current operation in place, unless --cleanup_css` is present.
  - Use `--scrub_css` to remove all orphaned CSS rules, including rules for tiles removed or cleared by the current operation. all orphaned CSS rules, including rules for tiles removed or cleared by the current operation.
  - At least one tile must exist in the target rows, columns or range as at least one tile must remain after cropping.
  - Use `--trim`, `--trim:top` , `--trim:left` or `--trim:top,left` to remove blank rows on the top or columns on the left of the remaining tiles.

---

<a id="markdown-prune" name="prune"></a>

### Prune

Clears all tiles listed, or all tiles ***except*** those listed in a comma separated list of tile ids or device ids.  The position of remaining tiles is unchanged.

- Actions:
  
  `--prune:`***mode***` <list>`
  
  `--prune_except:`***mode***` <list>`
  
  <br>
- Modes: `ids | devices`
  
  `--prune:ids <list>`
  `--prune:devices <list>`
  
  `--prune_except:ids <list>`
  `--prune_except:devices <list>`
  <br>
- Acceptable `list` Values:
  
  - Explicit values: `1,4,6,8,9`
  - Comparisons: `<29`
  - Inclusive ranges: `3-20,40-58`
  - Combination: `<29,43,46,>=100`
    <br>
- Options:
  
  - `--force` — skip confirmation prompts -- assume yes.
  - `--confirm_keep` — After writing output, prompts (independently of `--force`) to keep or undo the changes made.
  - `--cleanup_css` — remove tile-specific CSS rules from 'customCSS' for tiles removed or cleared by the current action.
    <br>
- Notes:
  
  - The default behavior is to leave tile CSS rules for tiles removed or cleared by the current operation in place, unless --cleanup_css` is present.
  - Use `--scrub_css` to remove all orphaned CSS rules, including rules for tiles removed or cleared by the current operation. all orphaned CSS rules, including rules for tiles removed or cleared by the current operation.
  - At least one matching tile id or device id must exist.  At least one tile must remain after pruning.
  - Use `--trim`, `--trim:top` or `--trim:left` to remove blank rows on the top or columns on the left of the remaining tiles.

---

<a id="markdown-trim" name="trim"></a>

### Trim

Removes blank rows above the top-most tile and/or blank columns left of the left-most tile.

- Action:
  
  `--trim:`***mode***
  <br>
- Modes: `top | left | top,left`
  
  `--trim` (defaults to `top,left`)
  `--trim:top`
  `--trim:left`
  `--trim:top,left` (🆗`--trim:left,top`)
  <br>
- Options:
  
  - `--confirm_keep` — After writing output, prompts (independently of `--force`) to keep or undo the changes made.
    <br>
- Note:
  
  - The trim action can be used in conjunction with another action or as a standalone action.
  - When combined with another action, trimming will only occur after successful completion of the primary action.

---

<div style="page-break-after: always"></div>

<a id="markdown-css-actions" name="css-actions"></a>

## CSS Actions

<a id="markdown-copy-css" name="copy-css"></a>

### Copy CSS

Copies CSS rules from one tile to another.

- Action
  
  `--copy_css:`***mode***
  <br>
- Modes: `merge | replace | overwrite | add`
  
  `--copy_css:merge <from_tile-id> <to_tile-id>`
  `--copy_css:replace <from_tile-id> <to_tile-id>`
  `--copy_css:overwrite <from_tile-id> <to_tile-id>`
  `--copy_css:add <from_tile-id> <to_tile-id>`
  <br>
  
  - `merge` —  Copies rules checking for conflicts with existing rules.  Conflicts generate user prompts to overwrite or keep the rules in the destination tile.  Default is overwrite.
    <br>
  - `replace` — Removes all rules from the destination tile and replaces them with the rules being copied.
    <br>
  - `overwrite` — Copies rules and overwrites any conflicting rules.  This is the same as `--copy_css:merge --force.`
    <br>
  - `add` — Copies all rules to the target tile, regardless of any potential conflicts.
    <br>
- Options:
  
  - `--force` — skip confirmation prompts -- assume yes.

---

<a id="markdown-clear-css" name="clear-css"></a>

### Clear CSS

Removes CSS rules for a tile

- Action

`--clear_css <tile-id>` — Removes all CSS rules for the specified tile.
<br>

- Option:
  
  - `--force` — skip confirmation prompts -- assume yes.

<div style="page-break-after: always"></div>

<a id="markdown-supplemental-actions-and-options" name="supplemental-actions-and-options"></a>

## Supplemental Actions and Options

<a id="markdown-sort" name="sort"></a>

### Sort

Changes the order tiles appear in the dashboard layout JSON only

- Actions:
  
  `--sort:<spec>`
  <br>
- Spec Keys: `i | -i | r | -r | c | -c`
  
  - `[-]i` = id
  - `[-]r` = row
  - `[-]c` = col
    <br>
  - Sort order for keys is ascending unless preceded by a "`-`"
  
  <br>
- Notes:
  
  - Sorting only changes the order tiles are listed in the layout JSON.  It has no effect on the order tiles appear on the dashboard.
  - By default, actions do not change the order tiles are listed in the layout JSON unless `--sort` is present.
  - The default sort order is `irc`(id, row, column) in ascending order.
  - Ascending or descending order can be specified for each key.  Examples: `--sort:i-rc` or `--sort:-ir-c`.
  - Missing sort keys are assumed.  For example `--sort:r` will result in `--sort:ric`.
  - No sorting is applied to CSS rules in customCSS.

---

<a id="markdown-visual-layout-maps" name="visual-layout-maps"></a>

### Visual Layout Maps

Show before, outcome and conflict layout previews in the terminal

- Optional Action:
  
  `--show_map:`***mode***
  <br>
- Modes: `full | no_scale | conflicts`
  
  `--show_map:full`
  `--show_map:no_scale`
  `--show_map:conflicts`
  <br>
  
  - `full` — Maps show the full dashboard, scaled to fit the terminal.
    <br>
  - `no_scale` — Map show the full dashboard without scaling.  Each row & column is represented by one character space and may not display properly depending on terminal size.
    <br>
  - `conflicts` — Conflict map is zoomed in to show just the tiles in conflict.  All other maps show the full dashboard.  All maps are scaled.
    <br>
- Map Legend:
  
  <span style="color:lightgray">· </span>(gray dot) - empty spaces
  <span style="color:lightgray">█ </span> (gray) - unaffected tiles
  <span style="color:orange">█  </span> (orange) - tiles in the target row, column or range before changes are made
  <span style="color:lime">█  </span> (green) - tiles successfully changed by the action or portions not in conflict.
  <span style="color:red">█ </span> (red) - tiles (or portions) in conflict that caused the action to fail.
  <span style="color:yellow">█ </span> (yellow) - tiles (or portions) conflicts allowed by `--allow_overlap`

---

<a id="markdown-miscellaneous-options" name="miscellaneous-options"></a>

### Miscellaneous Options:

- Prompts / Confirmation Options:
  
  - `--force` — Suppress confirmation prompts for actions which remove tiles or custom CSS rules.
  - `--confirm_keep` — After writing output, prompts (independently of `--force`) to keep or undo the changes made.
    
    <br>
- Safety / Undo Options:
  
  - `--lock_backup` — Retains the last undo backup (if found) as the undo backup for the current action.
  - `--undo_last` — Load the undo backup (if found) and writes it to the previous actions output destination.  `--undo_last` may be used with `--output:<type>` to override where the undo will be restored to.  However, the restore destination type match the specified output type.  For example, if the last output was a file, a new filename can be specified but the new output type be file.
  - Backup files contain the JSON imported before an action is performed.  The backup file is not created however, until after the action completes and the result has been successfully saved to the output destination.
  - When restoring directly to the hub, there are additional safeguards in place to prevent:
    
    - Restoring and overwriting a different dashboard than the dashboard layout in the undo_file (a different `--output:hub <local dashboard url>` is specified with the `--undo_last` action.)
    - Restoring an older backup than intended. (Undo is older than 5 minutes)
    - Edits made to a dashboard after the backup was created (The current dashboard layout stored on the hub does not match the layout that was uploaded last)
  - A confirmation prompt will be presented if any of the safeguards are triggered.  Use `--force` to suppress prompts.
    
    <br>
- Output / Debug Information Options:
  
  - `--quiet` — suppress end-of-run summary line (errors still shown)
  - `--verbose` — planned actions + concise results
  - `--debug` — per-tile action logs + deep details
    
    <br>
- Notes:
  
  - The undo backup file is only created after an action has completed and was successfully saved to the output destination.
  - The purpose of `--confirm_keep` is to provide an opportunity to review or test the outcome of an action, then if necessary, undo it.  This is useful when tweaking action target ranges or options.  It is the same as running an action without `--confirm_keep`, then using the `--undo_last` action.
    
    <br>

---

<a id="markdown-help" name="help"></a>

### Help

- `-h`, `--help` — Short help
- `--help_full` — Full detailed help

---

<div style="page-break-after: always"></div>

<a id="markdown-custom-css-handling--capabilities--limits" name="custom-css-handling--capabilities--limits"></a>

## Custom CSS Handling — Capabilities & Limits

<a id="markdown-css-overview" name="css-overview"></a>

### CSS Overview

When tiles are **copied/merged** (new tile IDs are created) or **removed** (delete/clear/crop/prune), the tool can optionally update `customCSS` by:

- duplicating ***tile-scoped rules*** for the new tile IDs
- removing ***tile-scoped rules*** for removed tile IDs (`--cleanup_css`)
- scrubbing orphaned ***tile-scoped rules*** (`--scrub_css`)

CSS parsing is limited to typical Hubitat dashboard CSS, not full CSS grammar.  Specifically, the parser can only "see" and process "tile-scoped" rules.

<a id="markdown-css-rule-guidelines" name="css-rule-guidelines"></a>

### CSS Rule Guidelines

- A rule is treated as tile-scoped when its selector* (the part before `{`) contains a tile identifier such as `#tile-123` or `.tile-123`.
- Declarations do not define ownership.  Tile-like text inside the declaration block (`{ property: value; }`) is not enough to associate a rule with a tile unless the selector also scopes the rule to that tile.
- Rules inside `@media { ... }` blocks can be duplicated/removed, but the tool does not attempt to fully normalize complex nested at-rules.
  <br>
- Use `--ignore_css` if your `customCSS` contains advanced selector patterns or complicated blocks you do not want rewritten.
- Avoid using `--copy_css`, `--cleanup_css`, and `--scrub_css` on dashboards with CSS that intentionally cross-references multiple tiles in a single selector item.

<a id="markdown-compatible-selector-patterns" name="compatible-selector-patterns"></a>

### Compatible selector patterns

<a id="markdown--single-selector-item-scoped-to-one-tile" name="-single-selector-item-scoped-to-one-tile"></a>

#### ✅ Single selector item scoped to one tile

- Example:
  
  `#tile-123 { <declarations> }      `
  <br>
- When copying/merging tile `123` ➡️ `141`, the selector is remapped:
  
  `#tile-123 { <declarations> }      ` ➡️ `#tile-141 { <declarations> }      `
  `.tile-123 { <declarations> }      ` ➡️ `.tile-141 { <declarations> }      `
  `#tile-123 .icon { <declarations> }` ➡️ `#tile-141 .icon { <declarations> }`
  <br>
- When removing tile `123`, the corresponding tile-scoped rule is removed:
  
  `#tile-123 { <declarations> }      ` ➡️ `*(removed)*                       `
  <br>

<a id="markdown--selector-list-comma-separated-containing-tile-selectors" name="-selector-list-comma-separated-containing-tile-selectors"></a>

#### 🆗 Selector list (comma-separated) containing tile selectors

- Example:
  
  `#tile-40, #tile-20, #tile-123 { <declarations> }`
  <br>
- Copy/merge behavior (copy `123` ➡️ `141`):
  
  - The original rule remains unchanged
  - A new, single selector rule is created for the new tile
    
    `#tile-40, #tile-20, #tile-123 { <declarations> }`
    `#tile-141 { <declarations> }`
    <br>
- Removal behavior (remove tile `123`):
  
  - Only the selector item matching the removed tile is removed
  - If the selector list becomes empty, the whole rule is removed
    
    `#tile-40, #tile-20, #tile-123 { <declarations> }` ➡️  `#tile-40, #tile-20 { <declarations> }`
    <br>

<a id="markdown--rules-inside-media-blocks" name="-rules-inside-media-blocks"></a>

#### ✅ Rules inside `@media` blocks

- Example:
  
  `@media (max-width: 600px) { `
  `#tile-123 { <declarations> }`
  `}                             `
  <br>
- Copy/merge behavior (copy `123` ➡️ `141`):
  
  `@media (max-width: 600px) { `
  `#tile-123 { <declarations> }`
  `#tile-141 { <declarations> }`
  `}                           `
  <br>
- Removal behavior (remove tile `123`):
  
  - Only the selector item matching the removed tile is removed
  - If the selector list becomes empty, the whole rule is removed
    
    `@media (max-width: 600px) { `
    `#tile-123 { <declarations> }`
    `}                           `

<a id="markdown-incompatible-and-problematic-css-rules" name="incompatible-and-problematic-css-rules"></a>

### Incompatible and Problematic CSS Rules

<a id="markdown--multi-tile-selector-items" name="-multi-tile-selector-items"></a>

#### ❌ Multi-tile selector items:

Avoid selector patterns where one selector item references multiple tiles at once. They are problematic because when copying one tile (e.g., `123` ➡️ `141`), the tool would have to guess what to do with the other tile IDs in the same selector item—often producing hybrid selectors that look meaningful but match nothing.  These should not be confused with sector list.

- Examples:
  
  - 🆗 Selector Lists
    
    `#tile-40, #tile-20, #tile-123 { ... }`
    
    Selector lists are compatible but not bullet proof.  For best results, use separate single selector rules.
    <br>
  - ❌ **Compound Selectors with multiple tile-ids**
    
    `.tile-80.tile-123 { ... }`
    
    Avoid selectors requiring one element to have **both classes** at the same time.  Hubitat tile containers typically represent one tile id, so the duplicate selector is usually “dead CSS.”
    <br>
  - ❌ **Child Combinator with multiple tile ids**
    
    `.tile-80 > .tile-123 { ... }`
    
    Avoid selectors having where one tile is a direct child of another.  Hubitat tiles are normally siblings in the grid, not nested.
  - ❌ **Descendant Combinator with multiple tile-ids**
    
    `#tile-80 #tile-123 .icon { ... }`
    
    Avoid nested selectors, or chains of multiple tile IDs.  Hubitat dashboard tiles are normally siblings in a grid (not nested tiles)
  - ❌ **Rules with no tile-scoping selector**
    
    `.some-class::after { content: "..." }`
    `.tile .tile-content { padding: 0; }`
    
    These rules are not associated with a specific tile ID, so they are not duplicated/removed by tile ID operations.

<a id="markdown-🟡-tile-ids-inside-declaration-blocks" name="🟡-tile-ids-inside-declaration-blocks"></a>

#### 🟡 Tile IDs inside declaration blocks

Tile references within the declaration block, are remapped if the tile references matches the selector's tile.  All other rules are duplicated verbatim.

- Tile reference matches the selector and is remapped in duplicated rule:
  
  ✅ `#tile-123 .tile-content { background-image: url("/local/images/tile-123.png"); }`
  
  Copy `123` ➡️ `141`:
  
  ➡️ `#tile-123 .tile-content { background-image: url("/local/images/tile-123.png"); }`
  ➡️ `#tile-141 .tile-content { background-image: url("/local/images/tile-141.png"); }`
  <br>
- Tile reference does not match the selector and is duplicated verbatim:
  
  🟡 `#tile-123 .tile-content { background-image: url("/local/images/tile-999.png"); }`
  
  Copy `123` ➡️ `141`:
  
  ➡️ `#tile-123 .tile-content { background-image: url("/local/images/tile-999.png"); }`
  ➡️ `#tile-141 .tile-content { background-image: url("/local/images/tile-999.png"); }`

---

<a id="markdown-css-comments" name="css-comments"></a>

### CSS Comments

Comment blocks within CSS can be problematic and complicate parsing and be difficult to manage when rules are added or removed.

<a id="markdown-comment-block-duplication----copymerge-operations" name="comment-block-duplication----copymerge-operations"></a>

#### Comment Block Duplication -  Copy/Merge Operations:

- **Standalone (statement-level) comments**
  
  &nbsp;&nbsp;`/* ... */`
  
  - Appear in their own CSS statement, including:
    
    - top-level in the stylesheet
    - inside an `@media { ... }` block, but **not** inside any rule `{ ... }` declaration body
    - rules which follow top-level rules and are outside of any any rule `{ ... }` declaration body
      <br>
  - A standalone comment is duplicated only if:
    
    - it references a tile id being duplicated (e.g., `tile-123`)
    - the destination tile id will also receive at least one duplicated real selector rule
    - the comment references no more than **one** tile id
    
    If those conditions are met, the comment is duplicated **once per** `OLD ➡️ NEW`, its tile-id text is remapped, and it is annotated:
    
    Copy `123` ➡️ `141`:
    
    ✅ `/* tile-123 note */`
    ➡️ `/* [hubitat_tile_mover] duplicated from tile-123 to tile-141. */`
    <br>
- ✅ **Rule-body comments**
  
  &nbsp;&nbsp;`#tile-123 {                  `
  &nbsp;&nbsp;` /* inside the rule body */`
  &nbsp;&nbsp;`color: red;              `
  &nbsp;&nbsp;`}                            `
  
  - Appear Comments inside a selector block’s declaration body.
  - A rule body comments is copied automatically as part of the duplicated rule (because rule body text is always duplicated).
  
  &nbsp;&nbsp;Copy `123` ➡️ `141`:
  
  &nbsp;&nbsp;➡️ `#tile-141 {                  `
  &nbsp;&nbsp;➡️ ` /* inside the rule body */`
  &nbsp;&nbsp;➡️ `color: red;              `
  &nbsp;&nbsp;➡️ `}                            `

<br>

- 🟡 **Selector-prelude comments**
  
  &nbsp;&nbsp;`#tile-40 /* comment #1 */, /* comment #2 */ #tile-123 /* comment #3 */, #tile-50 { ... }`
  
  -Appear embedded in the selector text itself.
  -Comments are only copied if they are part of the selector being copied.
  
  &nbsp;&nbsp;Copy `123` ➡️ `141`:
  
  &nbsp;&nbsp;➡️`#tile-40 /* comment #1 */, /* comment #2 */ #tile-123 /* comment #3 */, #tile-50 { ... }`
  &nbsp;&nbsp;➡️`/* comment #2 */ #tile-141 /* comment #3 */ { ... }`
  <br>

- 🟡 **Rules inside comment blocks / commented out rules**
  
  &nbsp;&nbsp;`/* #tile-123 { ... } */`
  
  - If target tile-ids are found in a comment block, the block is parsed to determine if the comment contains valid CSS rules with a selector matching the target tile-id.
  - If no valid rules are located, the comment block is treated as a standard standalone comment.
  - If one or more valid rules are found in the comment block with selectors containing the target tile-id:
    - Rules with selectors that contain the target tile-id are extracted.
    - Extracted rules are processed as normal CSS rules.
    - When copying or merging tiles, the duplicated CSS will placed back inside comment delimiters.
    - The duplicated comment block will only contain the individual duplicated rules.   All other content in the original comment block is ignored.
  - If valid rules are located but none have selectors which contain the target tile-id, the comment block will be treated as a standard standalone comment.

---

<a id="markdown-comment-block-removal---deleteclearcropprunecss-clean-upoperations" name="comment-block-removal---deleteclearcropprunecss-clean-upoperations"></a>

#### Comment Block Removal - Delete/Clear/Crop/Prune/CSS Clean-up/Operations

When tiles are removed and `--cleanup_css` is present during delete, clear, crop, and prune actions, or when CSS rules are removed during `--clear_css` or `--scrub_css` operations:

- The tool removes tile-scoped selector rules for the removed tile ids.
- If there are standalone comments referencing removed tile ids, the tool prompts (unless `--force`):
  
  &nbsp;&nbsp;&nbsp;`/* styles for #tile-123 */`
  
  - If comments are kept after rules are removed, the tool:
    
    1) annotates the comment to document that the tile/rules were removed
    2) rewrites tile-id tokens to **neutralized** forms
       &nbsp;
       Example:`#tile-123` ➡️ `#tile_123`
    
    <br>
    
    ➡️ `/* [hubitat_tile_mover] tile(s) removed; CSS rules removed for: tile_123 */`
    
    - The neutralized tokens (`tile_123`, `#tile_123`, `.tile_123`) are intentionally **not valid selectors** for the real tile. They exist to make it obvious the comment is historical and to prevent confusion during later review.

---


<a id="markdown-tool-usage-examples" name="tool-usage-examples"></a>

## Tool Usage Examples:

* Insert 2 columns at col 15 (only in rows 4–32):
  
  ```bash
  python hubitat_tile_mover.py --insert:cols 2 15 --row_range 4 32
  ```
* Move columns 1–14 to start at 85 and save back to hub.  Show the layout before and after maps:
  
  ```bash
  python hubitat_tile_mover.py --import:hub "<dashboard_local_url>" --move:cols 1 14 85 --output:hub --show_map
  ```
* Copy tiles in the rectangular range 1,1 to 2,20 to a new location at 40,40:
  
  ```bash
  python hubitat_tile_mover.py --copy:range 1 1 20 20 40 40
  ```
* Crop to a range (delete everything outside), show maps, force, cleanup CSS, save to a file:
  
  ```bash
  python hubitat_tile_mover.py --crop:range 1 1 85 85 --show_map --force --cleanup_css --output:file "<filename.json>"
  ```
* Remove orphan CSS rules only (no tile edits) without confirmation prompt:
  
  ```bash
  python hubitat_tile_mover.py --scrub_css --force
  ```
* Undo last run (restore last input to last outputs unless overridden):
  
  ```bash
  python hubitat_tile_mover.py --undo_last
  ```

---

<div style="page-break-after: always"></div>

<a id="markdown-batch-actions" name="batch-actions"></a>

## Batch Actions:

<a id="markdown-tips-for-running-a-batched-or-consecutive-actions" name="tips-for-running-a-batched-or-consecutive-actions"></a>

### Tips for running a batched or consecutive actions:

- Use `--lock_backup` on all actions except the first action.  This provides an undo from before any actions in the batch were run.
- Reduce risk and increase speed by minimizing using the clipboard to read and write intermediate layouts in batches.

<br>

<a id="markdown-example-batch" name="example-batch"></a>

### Example Batch

<a id="markdown-batch-overview" name="batch-overview"></a>

#### Batch Overview

- Get the dashboard layout from the hub and insert 5 empty columns at column 10
- Merge (copy) columns 15 - 20 from another dashboard into columns 10 - 15 of this dashboard.
- Crop the resulting layout keep only tiles in the rectangular region 10,10 - 40,30
- Trim empty rows left behind at the top and left sides
- Cleanup orphaned CSS rules and output the final layout back to the hub.

<a id="markdown-example" name="example"></a>

#### Example

```bash
python hubitat_tile_mover.py --import:hub "<dashboard_local_url>" --output:clipboard --insert:cols 5 10

python hubitat_tile_mover.py --import:clipboard --output:clipboard --merge_source:hub "<other_dashboard_url>" --merge:cols 15 20 10 --lock_backup

python hubitat_tile_mover.py --import:clipboard --output:hub "<dashboard_local_url>" --crop:range 10 10 40 30 --include_overlap --force --cleanup_css --trim --lock_backup
```

<br>

<a id="markdown-batched-actions-in-detail" name="batched-actions-in-detail"></a>

#### Batched Actions in Detail

<a id="markdown-the-first-action-run" name="the-first-action-run"></a>

##### The First Action (Run)

1. Imports a layout from the hub
2. Inserts 5 blank columns at column 10 in the layout
3. Writes the new layout to the ***clipboard***
4. Saves the original imported layout to the undo backup file.  In the event of an error, running `undo_last` would not be necessary to undo any actions performed by the batch as they have only been saved to the clipboard.  The original layout still exists unchanged on the hub.
   
   <br>

<a id="markdown-the-second-action" name="the-second-action"></a>

##### The second action:

1. Imports the layout saved by the first action from the clipboard.
2. Copies tiles in columns 15-20 from another dashboard into the blank columns created by the previous action at column 10
3. Writes the new layout to the ***clipboard***
4. Does not change the undo backup created by the first action.  In the event of an error, running `undo_last` would not be necessary to undo any actions performed by the batch as they have only been saved to the clipboard.  The original layout still exists unchanged on the hub.

<br>

<a id="markdown-the-third-action" name="the-third-action"></a>

##### The third action:

1. Imports the layout saved by the second action from the clipboard.
2. Removes all dashboard tiles except those located or having some portion inside the rectangular range of (row 10, col 10) to (row 40, col 30).
3. Does present a confirmation prompt.
4. Removes any tile specific CSS rules from "customCSS" for the tiles that were removed.
5. Again, does not present a confirmation prompt.
6. Trims blank column and rows from the top and left sides to move the layout of the remaining tiles as far to the upper left as possible.
7. Writes the final new layout to the ***hub***
8. Does not change the undo backup created by the first action. In the event of an error, running `--undo_last` would undo all changes made by the batch by restoring the undo backup made in the first action.

---

Copyright 2026 Andrew Peck

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

```
http://www.apache.org/licenses/LICENSE-2.0
```

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

