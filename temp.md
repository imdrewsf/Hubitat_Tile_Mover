
No file chosen

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
  - [CSS Layout Actions](#css-layout-actions)
- [Supplemental Actions and Options](#supplemental-actions-and-options)
  - [Sort](#sort)
  - [Visual Layout Maps](#visual-layout-maps)
  - [Miscellaneous Options:](#miscellaneous-options)
  - [Help](#help)
- [Custom CSS Handling - Capabilities and Limitations](#custom-css-handling---capabilities-and-limitations)
  - [Compatible CSS Rules Types:](#compatible-css-rules-types)
  - [Incompatible and Problematic CSS Selector Types](#incompatible-and-problematic-css-selector-types)
  - [Incompatible and Problematic CSS Rules Bodies](#incompatible-and-problematic-css-rules-bodies)
- [Usage Examples:](#usage-examples)
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

- Valid Sources:
  - `--import:clipboard` — Read JSON text from clipboard.
  - `--import:file <filename>` — Read JSON text from file.
  - `--import:hub` — Fetch the full layout JSON from Hubitat using `--url`.

<br>

- Required for `--import:hub`:
  
  - `--url "<dashboard_local_url>"`

<br>

- Dashboard URL format (typical):
  
  ```
  http://<hub-ip>/apps/api/<appId>/dashboard/<dashId>?access_token=<token>&local=true
  ```

---

<a id="markdown-output-destinations" name="output-destinations"></a>

### Output destinations

- Valid Destinations:
  
  - `--output:terminal` — Print output to terminal.
  - `--output:clipboard` — Write to clipboard (default)
  - `--output:file <filename>` — Write to file.
  - `--output:hub` — POST full layout JSON back to the hub at `--url`.

<br>

- Required for `--output:hub`:
  
  - `--url "<dashboard_local_url>"`

<br>

- Notes:
  
  - Output default is the clipboard if `--output:<destination>` is not specified or present.
  
  <br>
  
  - `--output:hub` will fail if:
    - Import does not contain the full layout JSON object.
    - `--url` is not a valid or reachable local dashboard url.
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

- A tile's location is determined by by the row and column of its upper left corner.
- A tile's span is the area it tile occupies, calculated as (row + height -1), (column + width -1).
- Tiles whose span extends into, but are located (begin) outside of the target area, are considered to be target area "overlaps."

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

- Actions:
  
  - `--insert_rows <count> <at_row>` — Pushes down (increase tile's 'row' by `<count>`) tiles at/after `<at_row>`, and optionally tiles overlapping the insertion row.
    
    <br>
  - `--insert_cols <count> <at_col>` — Pushes right (increase tile's 'col' by `<count>`) tiles at/after `<at_col>`, and optionally tiles overlapping the insertion column.
    
    <br>
- Selection Modifiers:
  
  - `--col_range <start_col> <end_col>` — Insert rows only in column range. Only valid with `--insert_rows`
  - `--row_range <start_row> <end row>` — Insert columns only in row range. Only valid with `--insert_cols`
    
    <br>
  - `--include_overlap`

<br>

- Options:
  
  - `--confirm_keep` — After writing output, prompts (independently of `--force`) to keep or undo the changes made.

---

<a id="markdown-move" name="move"></a>

### Move

Moves tiles to a new location.

- Actions:
  
  - `--move_cols <start_col> <end_col> <dest_start_col>`
  - `--move_rows <start_row> <end_row> <dest_start_row>`
  - `--move_range <src_top_row> <src_left_col> <src_bottom_row> <src_right_col> <dest_top_row> <dest_left_col>`
    
    <br>
- Selection Modifiers:
  
  - `--include_overlap`
    
    <br>
- Options:
  
  - `--allow_overlap`
    ignore conflicts and allow moved tiles to overlap existing tiles at the destination.
  - `--skip_overlap`
    skip tiles that would conflict, move all others.
    
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

- Actions:
  
  - `--copy_cols <start_col> <end_col> <dest_start_col>`
  - `--copy_rows <start_row> <end_row> <dest_start_row>`
  - `--copy_range <src_top_row> <src_left_col> <src_bottom_row> <src_right_col> <dest_top_row> <dest_left_col>`
    
    <br>
- Selection Modifiers:
  
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

Copy tiles from another dashboard layout into this layout.

- Actions:
  
  - `--merge_cols <start_col> <end_col> <dest_start_col>`
  - `--merge_rows <start_row> <end_row> <dest_start_row>`
  - `--merge_range <src_top_row> <src_left_col> <src_bottom_row> <src_right_col> <dest_top_row> <dest_left_col>`
    <br>
- Required: source selection:
  
  - `--merge_source <filename>` — load source JSON from file
  - `--merge_url "<other_dashboard_local_url>"` — fetch source JSON from hub
    <br>
- Selection Modifiers:
  
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

- Actions:
  
  - `--delete_rows <start_row> <end_row>`
  - `--delete_cols <start_col> <end_col>`
    <br>
- Selection Modifiers:
  
  - `--col_range <start_col> <end_col>` — Deletes rows only in column range. Only valid with `--insert_rows`
  - `--row_range <start_row> <end row>` — Deletes columns only in row range. Only valid with `--insert_cols`
    <br>
  - `--include_overlap`
    <br>
- Options:
  
  - `--force` — skip confirmation prompts -- assume yes.
  - `--confirm_keep` — After writing output, prompts (independently of `--force`) to keep or undo the changes made.
  - `--cleanup_css` — remove tile-specific CSS rules from 'customCSS' for tiles deleted by the current action.
  
  <br>
- Notes:
  
  - Default behavior is to leave tile specific CSS rules for deleted tiles in place unless `--cleanup_css` is present.
  - Use the `--scrub_css` action to remove orphaned CSS rules for other tiles,

---

<a id="markdown-clear" name="clear"></a>

### Clear

Removes tiles in the target rows, columns or range but does change the dashboard layout.

- Actions:
  
  - `--clear_rows <start_row> <end_row>`
  - `--clear_cols <start_col> <end_col>`
  - `--clear_range <top_row> <left_col> <bottom_row> <right_col>`
- Selection Modifiers:
  
  - `--include_overlap`
    
    <br>
- Options:
  
  - `--force` — skip confirmation prompts -- assume yes.
  - `--confirm_keep` — After writing output, prompts (independently of `--force`) to keep or undo the changes made.
  - `--cleanup_css` — remove tile-specific CSS rules from 'customCSS' for tiles deleted by the current action.
  
  <br>
- Notes:
  
  - Default behavior is to leave tile specific CSS rules for cleared tiles in place unless `--cleanup_css` is present.
  - Use the `--scrub_css` action to remove orphaned CSS rules for other tiles,

---

<a id="markdown-crop" name="crop"></a>

### Crop

Clears tiles outside of the target rows, columns or range.  The position of remaining tiles is unchanged.

- Actions:
  
  - `--crop_to_rows <start_row> <end_row>`
  - `--crop_to_cols <start_col> <end_col>`
  - `--crop_to_range <top_row> <left_col> <bottom_row> <right_col>`
    
    <br>
- Selection Modifiers:
  
  - `--include_overlap`
    
    <br>
- Options:
  
  - `--force` — skip confirmation prompts -- assume yes.
  - `--confirm_keep` — After writing output, prompts (independently of `--force`) to keep or undo the changes made.
  - `--cleanup_css` — remove tile-specific CSS rules from 'customCSS' for tiles deleted by the current action.
    
    <br>
- Notes:
  
  - Default behavior is to leave tile specific CSS rules for cleared tiles in place unless `--cleanup_css` is present.
  - Use the `--scrub_css` action to remove orphaned CSS rules for other tiles,
  - At least one tile must exist in the target rows, columns or range as at least one tile must remain after cropping.
  - Use `--trim`, `--trim:top` or `--trim:left` to remove blank rows on the top or columns on the left of the remaining tiles.

---

<a id="markdown-prune" name="prune"></a>

### Prune

Clears all tiles listed, or all tiles ***except*** those listed in a comma separated list of tile ids or device ids.  The position of remaining tiles is unchanged.

- Actions:
  
  - `--prune_ids "<id_list>"`
  - `--prune_devices "<device_list>"`
    <br>
  - `--prune_except_ids "<id_list>"`
  - `--prune_except_devices "<device_list>"`

<br>

- Acceptable List Values:
  - Explicit values: `1,4,6,8,9`
  - Comparisons: `<29`
  - Inclusive ranges: `3-20,40-58`
  - Combination: `<29,43,46,>=100`

<br>

- Options:
  
  - `--force` — skip confirmation prompts -- assume yes.
  - `--confirm_keep` — After writing output, prompts (independently of `--force`) to keep or undo the changes made.
  - `--cleanup_css` — remove tile-specific CSS rules from 'customCSS' for tiles deleted by the current action.
    
    <br>
- Notes:
  
  - Default behavior is to leave tile specific CSS rules for cleared tiles in place unless `--cleanup_css` is present.
  - Use the `--scrub_css` action to remove orphaned CSS rules for other tiles,
  - At least one matching tile id or device id must exist.  At least one tile must remain after pruning.
  - Use `--trim`, `--trim:top` or `--trim:left` to remove blank rows on the top or columns on the left of the remaining tiles.

---

<a id="markdown-trim" name="trim"></a>

### Trim

Removes blank rows above the top-most tile and/or blank columns left of the left-most tile.

- Actions:
  
  - `--trim` (defaults to top+left)
  - `--trim:top`
  - `--trim:left`

<br>

- Options:
  - `--confirm_keep` — After writing output, prompts (independently of `--force`) to keep or undo the changes made.

<br>

- Note:
  
  - The trim action can be used in conjunction with another action or as a standalone action..
  - When combined with another action, trimming will only occur after successful completion of the primary action.

---

<div style="page-break-after: always"></div>

<a id="markdown-css-actions" name="css-actions"></a>

## CSS Actions

<a id="markdown-css-layout-actions" name="css-layout-actions"></a>

### CSS Layout Actions

- Copy CSS Rules
  Copies CSS rules from one tile to another.  Similar to the copy layout action but does not create a new tile.  Copy functions are considered primary laytout actions.  Only one copy action can be used per run.
  
  - `--copy_tile_css:merge <from_tile-id> <to_tile-id>` —  Copies rules checking for conflicts with existing rules.  Conflicts generate user prompts to overwrite or keep the rules in the destination tile.  Default is overwrite.
    <br>
  - `--copy_tile_css:replace <from_tile-id> <to_tile-id>` — Removes all rules for the destination tile and replaces them with the rules being copied.
    <br>
  - `--copy_tile_css:overwrite <from_tile-id> <to_tile-id>` — Copies rules and overwrites any conflicting rules.  This is the same as `--copy_tile_css:merge --force.`
    <br>
  - `--copy_tile_css:add <from_tile-id> <to_tile-id>` — Copies all rules to the target tile, regardless of any potential conflicts.
    <br>
  - `--clear_tile_css <tile-id>` — Removes all CSS rules for the specified tile.
    <br>
- Options:
  
  - `--force` — skip confirmation prompts -- assume yes.

<div style="page-break-after: always"></div>

<a id="markdown-supplemental-actions-and-options" name="supplemental-actions-and-options"></a>

## Supplemental Actions and Options

<a id="markdown-sort" name="sort"></a>

### Sort

Changes the order tiles appear in the dashboard layout JSON only

- Actions:
  
  - `--sort:<spec>`
    
    <br>
- Sort Keys:
  
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
  
  - `--show_map` — Enables generation of dashboard layout maps
    <br>
- Map Options:
  
  - `--map_focus:full` — All maps are zoomed out to show the full dashboard, scaled to fit the terminal.
  - `--map_focus:no_scale` — All maps are zoomed out to show an unscaled view of the full dashboard.  Each row / column is represented by one character space and may not display properly depending on terminal size.
  - `--map_focus:conflict` — Conflict maps are zoomed in to show just the tiles in conflict.  All other maps are zoomed out to show the full dashboard.  All maps are scaled.
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
    
    - Restoring and overwriting a different dashboard than the dashboard layout in the undo_file (a different `--output:hub --url <local dashboard url>` is specified with the `--undo_last` action.)
    - Restoring an older backup than intended. (Undo is older than 5 minutes)
    - Edits made to a dashboard after the backup was created (The current dashboard layout stored on the hub does not match the layout that was uploaded last)
  - A confirmation prompt will be presented if any of the safeguards are triggered.  Use `--force` to suppress prompts.
    
    <br>
- Output / Debug Information Options:
  
  - `--quiet` — suppress end-of-run summary line (errors still shown)
  - `--verbose` — planned actions + concise results
  - `--debug` — per-tile action logs + deep details
    
    <br>
- :
  
  - The undo backup file is only created after an action has completed and was successfully saved to the output destination.
  - The purpose of `--confirm_keep` is to provide an opportunity to review or test the outcome of an action, then if necessary, undo it.  This is useful when tweaking action target ranges or options.  It is the same as running an action without `--confirm_keep`, then using the `--undo_last` action.
    
    <br>

<a id="markdown-help" name="help"></a>

### Help

- `-h`, `--help` — Short help
- `--help_full` — Full detailed help

<div style="page-break-after: always"></div>

<a id="markdown-custom-css-handling---capabilities-and-limitations" name="custom-css-handling---capabilities-and-limitations"></a>

## Custom CSS Handling - Capabilities and Limitations

When tiles are added or removed by actions, custom CSS is parsed and searched for references to the original tile's id, such as "#tile-123" or ".tile-123".  Matches are analyzed to determine if the they are selectors, part of a rule body or a comment.

### Rule Processing Overview

- Rules for tiles are determined by matching rules with tile-ids within the selector, not the rule body.
- In almost all instances, only the rule selector is modified when a rule is duplicated in order to point it to a newly copied or merged tile.  The rule body is almost always duplicated verbatim.
- CSS rule parsing is very basic and is only intended for use with relatively simple rulesets.
- Compound selectors and certain complex rules are beyond the scope of this tool and are not compatible.
- Rules that contain tile references like "#tile-xx" or ".tile-xx", should be avoided if at all possible.
- Comments are generally ignored unless they are contained within rule bodies or are standalone comment blocks directly referencing a single existing tile.
  <br>
- When working with dashboards with containing incompatible or problematic customCSS rules:
  - Disable CSS processing by using the `--ignore_css` option with most actions.
  - Avoid using the `--copy-tile-css`, `--cleanup_css` and `--scrub_css` actions

<a id="markdown-compatible-css-rules-types" name="compatible-css-rules-types"></a>

### Compatible CSS Rules Types:

- ✅ **Simple, single-selector rules:**
  - For new tiles created by copy or merge actions, the source tile's rule body is duplicated verbatim and the selector is changed to the new tile's id.<br>
    `#tile-123 { <rule_body> }` ➡️  `#tile-123 { <rule_body> }`
    `                                #tile-141 { <rule_body> }`
    <br>
  - For removed tiles, the selector of the target tile and it's rule body are removed.
    `#tile-123 { <rule_body> }` ➡️ `<blank>                  `

<br>

- 🆗 **Simple, multi-selector rules:**<br>
  - For new tiles created by copy or merge actions, a new rule is single selector rule is created for the new tile-id and the rule body is copied verbatim. <br>
    `#tile-40, #tile-20, #tile-123 { <rule_body> }` ➡️  `#tile-40, #tile-20, #tile-123 { <rule_body> }`
    `                                                   #tile-141 { <rule_body> }                  `
    <br>
  - For removed tiles, only the selector matching the tile-id is removed.  If no selectors remain, the rule body is removed.<br>
    `#tile-40, #tile-20, #tile-123 { <rule_body> }` ➡️  `#tile-40, #tile-20 { <rule_body> }`<br>

<br>

- ✅ **Simple, single and multi-selector rules inside @media blocks:**
  - For new tiles created by copy or merge actions, a new rule is created inside the media block, with the new tile-id selector and the original rule verbatim. <br>
    `@media (max-width: 600px) { #tile-123 { display: none !important; }  } `
    `⬇️                              ⬇️                                ⬇️ `
    `@media (max-width: 600px) { #tile-123 { display: none !important; }    `
    `                            #tile-141 { display: none !important; }  }`
    <br>
  - For removed tiles, only the selector matching the tile-id is removed from the media block with its rule body.  If no rules remain, the media block remains empty.<br>
    `@media (max-width: 600px) { #tile-123 { display: none !important; }  }`
    `⬇️                              ⬇️                               ⬇️ `
    `@media (max-width: 600px) { <blank>  }                                `

<br>

<a id="markdown-incompatible-and-problematic-css-selector-types" name="incompatible-and-problematic-css-selector-types"></a>

### Incompatible and Problematic CSS Selector Types

- Certain types of selectors can't be simply copied with new tile-ids or removed without creating potential conflicting, overlapping, or otherwise broken CSS.  These selector types are not common in dashboard CSS and should be avoided.
  
  - ❌ Multi / Compound Class Selectors:
    
    `.tile-80.tile-123 { <rule_body> }`   ➡️   `.tile-80.tile-123 { <rule_body> }`
    `                                 `   🚫   `.tile-80.tile-141 { <rule_body> }`
  
  <br>
  
  - ❌ Child Combinators
    
    `.tile-80 > .tile-123 { <rule_body> }`   ➡️   `.tile-80 > .tile-123 { <rule_body> }`
    `                                    `   🚫   `.tile-80 > .tile-141 { <rule_body> }`
  
  <br>
  
  - ❌ Descendent Rules:
    
    `#tile-80 #tile-123 .icon { <rule_body> }`   ➡️   `#tile-80 #tile-123 .icon { <rule_body> }`
    `                                        `   🚫   `#tile-80 #tile-141 .icon { <rule_body> }`
    <br>
  - ❌ Rules without tile-id selectors:
    <br>
    `.some-class::after {content: "`<span style="color: red"><b>tile-123</b></span>"`}`
    `.tile .tile-content { background-image: url("/local/tile-images/`<span style="color: red"><b>tile-123</b></span>.png"`);`
    `:root {`<span style="color: red"><b>--tile-123</b></span>`-accent: #ffcc00 }`
    <br>
  - Although the rule bodies contain references to specific tile-ids, the selector does not point to any specific tiles.  These rules would never be duplicated or removed, even if an action was performed on the tile-id referenced in the rule body.

<a id="markdown-incompatible-and-problematic-css-rules-bodies" name="incompatible-and-problematic-css-rules-bodies"></a>

### Tile-IDs in Rules Bodies

- In most instances, rule bodies are copied verbatim.  If the rule body contains a reference to tile-ids, it will remain unchanged when it is copied to a new selector tile-id.<br>
  `#tile-123 .tile-content { background-image: url("/local/tile-images/`<span style="color: red"><b>tile-999</b></span>`.png");}`
  `⬇️                              ⬇️                               ⬇️ `
  `#tile-141 .tile-content { background-image: url("/local/tile-images/`<span style="color: red"><b>tile-999</b></span>`.png");}`

When rules are copied, only the selector is changed to point to a new tile-id.  Except in a few specific instances, rule bodies are copied verbatim.  "Tile-##" references with rule bodies can create a number of issues when they are duplicated.  Although it is sometimes necessary to refer to a tile within a rule body, it should be avoided where possible.

- CSS variables keyed by id
  
  ✅  `#tile-123 {--accent: #ffcc00;}`
  `#tile-123 .some-element {color: var(--accent);}`
- ❌ CSS Comments
  
  Comments that contain "tile-xx" within comments are unlikely to create rule conflicts.  However, depending on where comments are located, could interfere with new tile ID genertion or generate unresolvable orphan warnings.
  
  - Only comments within rule bodies are duplicated.  However, since only the selector is modified to point to the new tile, the comment within the rule body will still refer to the original tile id.  If "tile-123" were removed, the reference to "tile-123" would still remain in the CSS and lead to unresolvable orphan warnings.<br>
    `#tile-123 {`
    ` /* styles for`<span style="color: red"><b>tile-123</b></span>` */`
    `  font-size: 20px;`
    `}`<br>
    `#tile-141 {`
    ` /* styles for`<span style="color: red"><b>tile-123</b></span>` */`
    `  font-size: 20px;`
    `}`<br>
  
  <br>
  
  - Comments outside of rule blocks such as standalone statements or as selector "preludes" are never copied or removed as they are neither a selector or rule.  However, they could still lead to unresolvable orphan warnings and interfere with new tile id generation.
    
    `/* styles for `<span style="color: red"><b>tile-123</b></span>` */`
    `#tile-123 { font-size: 20px; }`<br>
    or<br>
    `#tile-141 { font-size: 20px; }  /* styles for `<span style="color: red"><b>tile-123</b></span>` */`
  
  <br>

<div style="page-break-after: always"></div>

<a id="markdown-usage-examples" name="usage-examples"></a>

## Usage Examples:

* Insert 2 columns at col 15 (only in rows 4–32):
  
  ```bash
  python hubitat_tile_mover.py --insert_cols 2 15 --row_range 4 32
  ```
* Move columns 1–14 to start at 85 and save back to hub.  Show the layout before and after maps:
  
  ```bash
  python hubitat_tile_mover.py --import:hub --url "<dashboard_local_url>" --move_cols 1 14 85 --output:hub --show_map
  ```
* Copy tiles in the rectangular range 1,1 to 2,20 to a new location at 40,40:
  
  ```bash
  python hubitat_tile_mover.py --copy_range 1 1 20 20 40 40
  ```
* Crop to a range (delete everything outside), show maps, force, cleanup CSS, save to a file:
  
  ```bash
  python hubitat_tile_mover.py --crop_to_range 1 1 85 85 --show_map --force --cleanup_css --output:file "<filename.json>"
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
python hubitat_tile_mover.py --import:hub --url "<dashboard_local_url>" --output:clipboard --insert_cols 5 10

python hubitat_tile_mover.py --import:clipboard --output:clipboard --merge_url: "<other_dashboard_url>" --merge_cols 15 20 10 --lock_backup

python hubitat_tile_mover.py --import:clipboard --url "<dashboard_local_url>" --output:hub --crop_to_range 10 10 40 30 --include_overlaps --force --cleanup_css --trim --lock_backup
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

DesktopTabletMobile/Wechat
Hubitat Tile Mover
Overview:
Import, modify and output Hubitat dashboard layouts:
Layout Actions
Additional Features
Layout Import Sources and Output Destinations:
Import Sources
Output destinations
Layout Actions Overview:
Layout Action types:
Action targets:
Key concepts:
Selecting Tiles:
Primary Edit Actions
Insert
Move
Copy
Merge
Delete
Clear
Crop
Prune
Trim
CSS Actions
CSS Layout Actions
Supplemental Actions and Options
Sort
Visual Layout Maps
Miscellaneous Options:
Help
Custom CSS Handling - Capabilities and Limitations
Compatible CSS Rules Types:
Incompatible and Problematic CSS Selector Types
Incompatible and Problematic CSS Rules Bodies
Usage Examples:
Batch Actions:
Tips for running a batched or consecutive actions:
Example Batch
Batch Overview
Example
Batched Actions in Detail
The First Action (Run)
The second action:
The third action:
Overview:
Import, modify and output Hubitat dashboard layouts:
Import dashboard layouts directly from the hub • JSON files • the clipboard (default)
Output changed layouts directly back to the hub • JSON files • the clipboard (default)
Layout Actions
MOVE columns, rows or a rectangular range of tiles
COPY columns, rows or a rectangular range of tiles
MERGE copy columns, rows or a rectangular range of tiles from another dashboard
INSERT full or partial empty columns or rows (push tiles over/down at column/row)
DELETE full or partial columns or rows of tiles (remove tiles and shift the layout left or up)
CLEAR columns, rows or a rectangular range of tiles but leaves the empty space.
CROP a layout by clearing all tiles not in columns, rows or a rectangular range
PRUNE a layout by tile or devices id. Clear only specific id's or clear all except specific id's
TRIM a layout to remove empty top rows and/or left columns.
Additional Features
Preserve, duplicate or remove custom CSS rules when tiles added (copied) or removed by actions
Prevent actions which would result in tiles be placed over existing tiles
Visual Layout Maps: Easily see proposed changes, potential conflicts and final outcome of actions
multimap

Layout Import Sources and Output Destinations:
Import Sources
Exactly one import method is used. If not specified, clipboard is the default.

Valid Sources:
--import:clipboard — Read JSON text from clipboard.
--import:file <filename> — Read JSON text from file.
--import:hub — Fetch the full layout JSON from Hubitat using --url.

Required for --import:hub:

--url "<dashboard_local_url>"

Dashboard URL format (typical):

http://<hub-ip>/apps/api/<appId>/dashboard/<dashId>?access_token=<token>&local=true
Output destinations
Valid Destinations:

--output:terminal — Print output to terminal.
--output:clipboard — Write to clipboard (default)
--output:file <filename> — Write to file.
--output:hub — POST full layout JSON back to the hub at --url.

Required for --output:hub:

--url "<dashboard_local_url>"

Notes:

Output default is the clipboard if --output:<destination> is not specified or present.

--output:hub will fail if:
Import does not contain the full layout JSON object.
--url is not a valid or reachable local dashboard url.
A valid requestToken could not be obtained.
Layout Actions Overview:
Layout Action types:
Primary edit actions — make modifications to tiles. Primary actions include insert, move, copy, merge, delete, clear, crop and prune. Only one primary edit action can be per run.
Supplemental actions — can be used standalone or with primary actions. These include displaying visual layout maps, JSON sorting, orphaned CSS cleanup and trim functions. Supplemental actions are always performed after primary actions.
Undo /restore action — --undo_last is a standalone action. It supersedes all other actions.
Action targets:
Key concepts:
A tile's location is determined by by the row and column of its upper left corner.
A tile's span is the area it tile occupies, calculated as (row + height -1), (column + width -1).
Tiles whose span extends into, but are located (begin) outside of the target area, are considered to be target area "overlaps."
Selecting Tiles:
By default, actions are applied only to tiles that are located (begin) in the target rows, column, or rectangular range.
To include tiles that overlap the boundaries of the target area, use the --include_overlap switch.
Primary Edit Actions
Insert
Inserts empty whole or partial rows or columns by pushing tiles beyond the insertion point

Actions:

--insert_rows <count> <at_row> — Pushes down (increase tile's 'row' by <count>) tiles at/after <at_row>, and optionally tiles overlapping the insertion row.


--insert_cols <count> <at_col> — Pushes right (increase tile's 'col' by <count>) tiles at/after <at_col>, and optionally tiles overlapping the insertion column.


Selection Modifiers:

--col_range <start_col> <end_col> — Insert rows only in column range. Only valid with --insert_rows

--row_range <start_row> <end row> — Insert columns only in row range. Only valid with --insert_cols


--include_overlap


Options:

--confirm_keep — After writing output, prompts (independently of --force) to keep or undo the changes made.
Move
Moves tiles to a new location.

Actions:

--move_cols <start_col> <end_col> <dest_start_col>

--move_rows <start_row> <end_row> <dest_start_row>

--move_range <src_top_row> <src_left_col> <src_bottom_row> <src_right_col> <dest_top_row> <dest_left_col>


Selection Modifiers:

--include_overlap


Options:

--allow_overlap
ignore conflicts and allow moved tiles to overlap existing tiles at the destination.

--skip_overlap
skip tiles that would conflict, move all others.


--confirm_keep — After writing output, prompts (independently of --force) to keep or undo the changes made.


Notes:

Conflict detection is evaluated once, *before* moving/copying, against existing destination tiles only. Any tiles that are being copied/moved can be overlapped and will not be considered in conflict.
Default behavior: if any conflicts exist, abort before moving anything.
Copy
Same as Move, but originals remain. Copies are created with new IDs. Existing tile specific CSS rules in customCSS can be optionally copied with the new IDs

Actions:

--copy_cols <start_col> <end_col> <dest_start_col>

--copy_rows <start_row> <end_row> <dest_start_row>

--copy_range <src_top_row> <src_left_col> <src_bottom_row> <src_right_col> <dest_top_row> <dest_left_col>


Selection Modifiers:

--include_overlap


Options:

--allow_overlap — ignore conflicts and allow moved tiles to overlap existing tiles at the destination.

--skip_overlap — skip tiles that would conflict, move all others.


--ignore_css — disables creating/copying CSS for new IDs.


--confirm_keep — After writing output, prompts (independently of --force) to keep or undo the changes made.


Notes:

ID allocation for new tiles: New IDs are created sequentially beginning starting with 1 + max(highest existing tile ID, highest referenced tile ID in customCSS). This prevents any orphaned CSS rules from being applied to new tiles.
By default, customCSS is checked for any tile specific CSS rules for copied tiles. Any rules found are duplicated for the new tile id
Conflict detection is evaluated once, *before* moving/copying, against existing destination tiles only.
Tiles that are being copied/moved can be overlapped and will not be considered in conflict.
Actions will be aborted if conflicts are found unless --allow_overlap or --skip_overlap is present.
Merge
Copy tiles from another dashboard layout into this layout.

Actions:

--merge_cols <start_col> <end_col> <dest_start_col>
--merge_rows <start_row> <end_row> <dest_start_row>
--merge_range <src_top_row> <src_left_col> <src_bottom_row> <src_right_col> <dest_top_row> <dest_left_col>

Required: source selection:

--merge_source <filename> — load source JSON from file
--merge_url "<other_dashboard_local_url>" — fetch source JSON from hub

Selection Modifiers:

--include_overlap


Options:

--allow_overlap — ignore conflicts and allow moved tiles to overlap existing tiles at the destination.

--skip_overlap — skip tiles that would conflict, move all others.


--ignore_css — disables creating/copying CSS for new IDs.


--confirm_keep — After writing output, prompts (independently of --force) to keep or undo the changes made.


Notes:

ID allocation for new tiles: New IDs are created sequentially beginning starting with 1 + max(highest existing tile ID, highest referenced tile ID in customCSS). This prevents any orphaned CSS rules from being applied to new tiles.
By default, customCSS is checked for any tile specific CSS rules for copied tiles. Any rules found are duplicated for the new tile id
Conflict detection is evaluated once, *before* moving/copying, against existing destination tiles only.
Tiles that are being copied/moved can be overlapped and will not be considered in conflict.
Actions will be aborted if conflicts are found unless --allow_overlap or --skip_overlap is present.
Delete
Deletes tiles located in the target rows or columns, then shifts remaining tiles to close the gap.

Actions:

--delete_rows <start_row> <end_row>
--delete_cols <start_col> <end_col>

Selection Modifiers:

--col_range <start_col> <end_col> — Deletes rows only in column range. Only valid with --insert_rows
--row_range <start_row> <end row> — Deletes columns only in row range. Only valid with --insert_cols

--include_overlap

Options:

--force — skip confirmation prompts -- assume yes.
--confirm_keep — After writing output, prompts (independently of --force) to keep or undo the changes made.
--cleanup_css — remove tile-specific CSS rules from 'customCSS' for tiles deleted by the current action.

Notes:

Default behavior is to leave tile specific CSS rules for deleted tiles in place unless --cleanup_css is present.
Use the --scrub_css action to remove orphaned CSS rules for other tiles,
Clear
Removes tiles in the target rows, columns or range but does change the dashboard layout.

Actions:

--clear_rows <start_row> <end_row>
--clear_cols <start_col> <end_col>
--clear_range <top_row> <left_col> <bottom_row> <right_col>
Selection Modifiers:

--include_overlap


Options:

--force — skip confirmation prompts -- assume yes.
--confirm_keep — After writing output, prompts (independently of --force) to keep or undo the changes made.
--cleanup_css — remove tile-specific CSS rules from 'customCSS' for tiles deleted by the current action.

Notes:

Default behavior is to leave tile specific CSS rules for cleared tiles in place unless --cleanup_css is present.
Use the --scrub_css action to remove orphaned CSS rules for other tiles,
Crop
Clears tiles outside of the target rows, columns or range. The position of remaining tiles is unchanged.

Actions:

--crop_to_rows <start_row> <end_row>

--crop_to_cols <start_col> <end_col>

--crop_to_range <top_row> <left_col> <bottom_row> <right_col>


Selection Modifiers:

--include_overlap


Options:

--force — skip confirmation prompts -- assume yes.

--confirm_keep — After writing output, prompts (independently of --force) to keep or undo the changes made.

--cleanup_css — remove tile-specific CSS rules from 'customCSS' for tiles deleted by the current action.


Notes:

Default behavior is to leave tile specific CSS rules for cleared tiles in place unless --cleanup_css is present.
Use the --scrub_css action to remove orphaned CSS rules for other tiles,
At least one tile must exist in the target rows, columns or range as at least one tile must remain after cropping.
Use --trim, --trim:top or --trim:left to remove blank rows on the top or columns on the left of the remaining tiles.
Prune
Clears all tiles listed, or all tiles except those listed in a comma separated list of tile ids or device ids. The position of remaining tiles is unchanged.

Actions:

--prune_ids "<id_list>"
--prune_devices "<device_list>"

--prune_except_ids "<id_list>"
--prune_except_devices "<device_list>"

Acceptable List Values:
Explicit values: 1,4,6,8,9
Comparisons: <29
Inclusive ranges: 3-20,40-58
Combination: <29,43,46,>=100

Options:

--force — skip confirmation prompts -- assume yes.

--confirm_keep — After writing output, prompts (independently of --force) to keep or undo the changes made.

--cleanup_css — remove tile-specific CSS rules from 'customCSS' for tiles deleted by the current action.


Notes:

Default behavior is to leave tile specific CSS rules for cleared tiles in place unless --cleanup_css is present.
Use the --scrub_css action to remove orphaned CSS rules for other tiles,
At least one matching tile id or device id must exist. At least one tile must remain after pruning.
Use --trim, --trim:top or --trim:left to remove blank rows on the top or columns on the left of the remaining tiles.
Trim
Removes blank rows above the top-most tile and/or blank columns left of the left-most tile.

Actions:

--trim (defaults to top+left)
--trim:top
--trim:left

Options:
--confirm_keep — After writing output, prompts (independently of --force) to keep or undo the changes made.

Note:

The trim action can be used in conjunction with another action or as a standalone action..
When combined with another action, trimming will only occur after successful completion of the primary action.
CSS Actions
CSS Layout Actions
Copy CSS Rules
Copies CSS rules from one tile to another. Similar to the copy layout action but does not create a new tile. Copy functions are considered primary laytout actions. Only one copy action can be used per run.

--copy_tile_css:merge <from_tile-id> <to_tile-id> — Copies rules checking for conflicts with existing rules. Conflicts generate user prompts to overwrite or keep the rules in the destination tile. Default is overwrite.

--copy_tile_css:replace <from_tile-id> <to_tile-id> — Removes all rules for the destination tile and replaces them with the rules being copied.

--copy_tile_css:overwrite <from_tile-id> <to_tile-id> — Copies rules and overwrites any conflicting rules. This is the same as --copy_tile_css:merge --force.

--copy_tile_css:add <from_tile-id> <to_tile-id> — Copies all rules to the target tile, regardless of any potential conflicts.

--clear_tile_css <tile-id> — Removes all CSS rules for the specified tile.

Options:

--force — skip confirmation prompts -- assume yes.
Supplemental Actions and Options
Sort
Changes the order tiles appear in the dashboard layout JSON only

Actions:

--sort:<spec>


Sort Keys:

[-]i = id
[-]r = row
[-]c = col

Sort order for keys is ascending unless preceded by a "-"

Notes:

Sorting only changes the order tiles are listed in the layout JSON. It has no effect on the order tiles appear on the dashboard.
By default, actions do not change the order tiles are listed in the layout JSON unless --sort is present.
The default sort order is irc(id, row, column) in ascending order.
Ascending or descending order can be specified for each key. Examples: --sort:i-rc or --sort:-ir-c.
Missing sort keys are assumed. For example --sort:r will result in --sort:ric.
No sorting is applied to CSS rules in customCSS.
Visual Layout Maps
Show before, outcome and conflict layout previews in the terminal

Optional Action:

--show_map — Enables generation of dashboard layout maps

Map Options:

--map_focus:full — All maps are zoomed out to show the full dashboard, scaled to fit the terminal.
--map_focus:no_scale — All maps are zoomed out to show an unscaled view of the full dashboard. Each row / column is represented by one character space and may not display properly depending on terminal size.
--map_focus:conflict — Conflict maps are zoomed in to show just the tiles in conflict. All other maps are zoomed out to show the full dashboard. All maps are scaled.

Map Legend:

· (gray dot) - empty spaces
█ (gray) - unaffected tiles
█ (orange) - tiles in the target row, column or range before changes are made
█ (green) - tiles successfully changed by the action or portions not in conflict.
█ (red) - tiles (or portions) in conflict that caused the action to fail.
█ (yellow) - tiles (or portions) conflicts allowed by --allow_overlap

Miscellaneous Options:
Prompts / Confirmation Options:

--force — Suppress confirmation prompts for actions which remove tiles or custom CSS rules.

--confirm_keep — After writing output, prompts (independently of --force) to keep or undo the changes made.


Safety / Undo Options:

--lock_backup — Retains the last undo backup (if found) as the undo backup for the current action.

--undo_last — Load the undo backup (if found) and writes it to the previous actions output destination. --undo_last may be used with --output:<type> to override where the undo will be restored to. However, the restore destination type match the specified output type. For example, if the last output was a file, a new filename can be specified but the new output type be file.

Backup files contain the JSON imported before an action is performed. The backup file is not created however, until after the action completes and the result has been successfully saved to the output destination.

When restoring directly to the hub, there are additional safeguards in place to prevent:

Restoring and overwriting a different dashboard than the dashboard layout in the undo_file (a different --output:hub --url <local dashboard url> is specified with the --undo_last action.)
Restoring an older backup than intended. (Undo is older than 5 minutes)
Edits made to a dashboard after the backup was created (The current dashboard layout stored on the hub does not match the layout that was uploaded last)
A confirmation prompt will be presented if any of the safeguards are triggered. Use --force to suppress prompts.


Output / Debug Information Options:

--quiet — suppress end-of-run summary line (errors still shown)

--verbose — planned actions + concise results

--debug — per-tile action logs + deep details


:

The undo backup file is only created after an action has completed and was successfully saved to the output destination.

The purpose of --confirm_keep is to provide an opportunity to review or test the outcome of an action, then if necessary, undo it. This is useful when tweaking action target ranges or options. It is the same as running an action without --confirm_keep, then using the --undo_last action.


Help
-h, --help — Short help
--help_full — Full detailed help
Custom CSS Handling - Capabilities and Limitations
When tiles are added or removed by actions, custom CSS is parsed and searched for references to the original tile's id, such as "#tile-123" or ".tile-123". Matches are analyzed to determine if the they are selectors, part of a rule body or a comment.

Rule Processing Overview
Rules for tiles are determined by matching rules with tile-ids within the selector, not the rule body.
In almost all instances, only the rule selector is modified when a rule is duplicated in order to point it to a newly copied or merged tile. The rule body is almost always duplicated verbatim.
CSS rule parsing is very basic and is only intended for use with relatively simple rulesets.
Compound selectors and certain complex rules are beyond the scope of this tool and are not compatible.
Rules that contain tile references like "#tile-xx" or ".tile-xx", should be avoided if at all possible.
Comments are generally ignored unless they are contained within rule bodies or are standalone comment blocks directly referencing a single existing tile.

When working with dashboards with containing incompatible or problematic customCSS rules:
Disable CSS processing by using the --ignore_css option with most actions.
Avoid using the --copy-tile-css, --cleanup_css and --scrub_css actions
Compatible CSS Rules Types:
✅ Simple, single-selector rules:
For new tiles created by copy or merge actions, the source tile's rule body is duplicated verbatim and the selector is changed to the new tile's id.

#tile-123 { <rule_body> } ➡️ #tile-123 { <rule_body> }
                                #tile-141 { <rule_body> }

For removed tiles, the selector of the target tile and it's rule body are removed.
#tile-123 { <rule_body> } ➡️ <blank>                  

🆗 Simple, multi-selector rules:
For new tiles created by copy or merge actions, a new rule is single selector rule is created for the new tile-id and the rule body is copied verbatim.

#tile-40, #tile-20, #tile-123 { <rule_body> } ➡️ #tile-40, #tile-20, #tile-123 { <rule_body> }
                                                  #tile-141 { <rule_body> }                 

For removed tiles, only the selector matching the tile-id is removed. If no selectors remain, the rule body is removed.

#tile-40, #tile-20, #tile-123 { <rule_body> } ➡️ #tile-40, #tile-20 { <rule_body> }

✅ Simple, single and multi-selector rules inside @media blocks:
For new tiles created by copy or merge actions, a new rule is created inside the media block, with the new tile-id selector and the original rule verbatim.

@media (max-width: 600px) { #tile-123 { display: none !important; }  } 
⬇️                              ⬇️                                ⬇️ 
@media (max-width: 600px) { #tile-123 { display: none !important; }    
                            #tile-141 { display: none !important; }  }

For removed tiles, only the selector matching the tile-id is removed from the media block with its rule body. If no rules remain, the media block remains empty.

@media (max-width: 600px) { #tile-123 { display: none !important; }  }
⬇️                              ⬇️                               ⬇️ 
@media (max-width: 600px) { <blank>  }                                

Incompatible and Problematic CSS Selector Types
Certain types of selectors can't be simply copied with new tile-ids or removed without creating potential conflicting, overlapping, or otherwise broken CSS. These selector types are not common in dashboard CSS and should be avoided.

❌ Multi / Compound Class Selectors:

.tile-80.tile-123 { <rule_body> } ➡️ .tile-80.tile-123 { <rule_body> }
                                  🚫 .tile-80.tile-141 { <rule_body> }


❌ Child Combinators

.tile-80 > .tile-123 { <rule_body> } ➡️ .tile-80 > .tile-123 { <rule_body> }
                                     🚫 .tile-80 > .tile-141 { <rule_body> }


❌ Descendent Rules:

#tile-80 #tile-123 .icon { <rule_body> } ➡️ #tile-80 #tile-123 .icon { <rule_body> }
                                         🚫 #tile-80 #tile-141 .icon { <rule_body> }


❌ Rules without tile-id selectors:


.some-class::after {content: "tile-123"}
.tile .tile-content { background-image: url("/local/tile-images/tile-123.png");
:root {--tile-123-accent: #ffcc00 }


Although the rule bodies contain references to specific tile-ids, the selector does not point to any specific tiles. These rules would never be duplicated or removed, even if an action was performed on the tile-id referenced in the rule body.

Tile-IDs in Rules Bodies
In most instances, rule bodies are copied verbatim. If the rule body contains a reference to tile-ids, it will remain unchanged when it is copied to a new selector tile-id.

#tile-123 .tile-content { background-image: url("/local/tile-images/tile-999.png");}
⬇️                              ⬇️                               ⬇️ 
#tile-141 .tile-content { background-image: url("/local/tile-images/tile-999.png");}
When rules are copied, only the selector is changed to point to a new tile-id. Except in a few specific instances, rule bodies are copied verbatim. "Tile-##" references with rule bodies can create a number of issues when they are duplicated. Although it is sometimes necessary to refer to a tile within a rule body, it should be avoided where possible.

CSS variables keyed by id

✅ #tile-123 {--accent: #ffcc00;}
#tile-123 .some-element {color: var(--accent);}

❌ CSS Comments

Comments that contain "tile-xx" within comments are unlikely to create rule conflicts. However, depending on where comments are located, could interfere with new tile ID genertion or generate unresolvable orphan warnings.

Only comments within rule bodies are duplicated. However, since only the selector is modified to point to the new tile, the comment within the rule body will still refer to the original tile id. If "tile-123" were removed, the reference to "tile-123" would still remain in the CSS and lead to unresolvable orphan warnings.

#tile-123 {
 /* styles fortile-123 */
  font-size: 20px;
}

#tile-141 {
 /* styles fortile-123 */
  font-size: 20px;
}

Comments outside of rule blocks such as standalone statements or as selector "preludes" are never copied or removed as they are neither a selector or rule. However, they could still lead to unresolvable orphan warnings and interfere with new tile id generation.

/* styles for tile-123 */
#tile-123 { font-size: 20px; }

or

#tile-141 { font-size: 20px; }  /* styles for tile-123 */


Usage Examples:
Insert 2 columns at col 15 (only in rows 4–32):

python hubitat_tile_mover.py --insert_cols 2 15 --row_range 4 32
Move columns 1–14 to start at 85 and save back to hub. Show the layout before and after maps:

python hubitat_tile_mover.py --import:hub --url "<dashboard_local_url>" --move_cols 1 14 85 --output:hub --show_map
Copy tiles in the rectangular range 1,1 to 2,20 to a new location at 40,40:

python hubitat_tile_mover.py --copy_range 1 1 20 20 40 40
Crop to a range (delete everything outside), show maps, force, cleanup CSS, save to a file:

python hubitat_tile_mover.py --crop_to_range 1 1 85 85 --show_map --force --cleanup_css --output:file "<filename.json>"
Remove orphan CSS rules only (no tile edits) without confirmation prompt:

python hubitat_tile_mover.py --scrub_css --force
Undo last run (restore last input to last outputs unless overridden):

python hubitat_tile_mover.py --undo_last
Batch Actions:
Tips for running a batched or consecutive actions:
Use --lock_backup on all actions except the first action. This provides an undo from before any actions in the batch were run.
Reduce risk and increase speed by minimizing using the clipboard to read and write intermediate layouts in batches.

Example Batch
Batch Overview
Get the dashboard layout from the hub and insert 5 empty columns at column 10
Merge (copy) columns 15 - 20 from another dashboard into columns 10 - 15 of this dashboard.
Crop the resulting layout keep only tiles in the rectangular region 10,10 - 40,30
Trim empty rows left behind at the top and left sides
Cleanup orphaned CSS rules and output the final layout back to the hub.
Example
python hubitat_tile_mover.py --import:hub --url "<dashboard_local_url>" --output:clipboard --insert_cols 5 10

python hubitat_tile_mover.py --import:clipboard --output:clipboard --merge_url: "<other_dashboard_url>" --merge_cols 15 20 10 --lock_backup

python hubitat_tile_mover.py --import:clipboard --url "<dashboard_local_url>" --output:hub --crop_to_range 10 10 40 30 --include_overlaps --force --cleanup_css --trim --lock_backup

Batched Actions in Detail
The First Action (Run)
Imports a layout from the hub

Inserts 5 blank columns at column 10 in the layout

Writes the new layout to the clipboard

Saves the original imported layout to the undo backup file. In the event of an error, running undo_last would not be necessary to undo any actions performed by the batch as they have only been saved to the clipboard. The original layout still exists unchanged on the hub.


The second action:
Imports the layout saved by the first action from the clipboard.
Copies tiles in columns 15-20 from another dashboard into the blank columns created by the previous action at column 10
Writes the new layout to the clipboard
Does not change the undo backup created by the first action. In the event of an error, running undo_last would not be necessary to undo any actions performed by the batch as they have only been saved to the clipboard. The original layout still exists unchanged on the hub.

The third action:
Imports the layout saved by the second action from the clipboard.
Removes all dashboard tiles except those located or having some portion inside the rectangular range of (row 10, col 10) to (row 40, col 30).
Does present a confirmation prompt.
Removes any tile specific CSS rules from "customCSS" for the tiles that were removed.
Again, does not present a confirmation prompt.
Trims blank column and rows from the top and left sides to move the layout of the remaining tiles as far to the upper left as possible.
Writes the final new layout to the hub
Does not change the undo backup created by the first action. In the event of an error, running --undo_last would undo all changes made by the batch by restoring the undo backup made in the first action.
Copyright 2026 Andrew Peck

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

