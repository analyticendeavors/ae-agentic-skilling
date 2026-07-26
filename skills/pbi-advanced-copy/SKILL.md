---
name: pbi-advanced-copy
description: Duplicate Power BI report pages along with their bookmarks and visual actions, within the same report or across two PBIP reports. Use when the user says "copy this page with its bookmarks", "duplicate a page across reports", "move a page to another PBIP", "copy pages between reports", or wants a page (and everything wired to it) replicated. Backed by the signed ae-pbi CLI (Windows). Modifies the destination PBIP.
---

# PBI Advanced Copy

Copies whole pages and carries each page's associated bookmarks and visual
actions with it. Two destinations: same report (duplicate) or a different PBIP
(cross-report).

## Locate the binary

Use `ae-pbi` if on PATH, else `"$HOME/.ae-pbi/bin/ae-pbi.exe"`. If missing, point
the user to this skill's README (`scripts/install-ae-pbi.ps1`). Windows only.

## Workflow

1. **Analyze first** to list pages and which carry bookmarks:
   ```bash
   ae-pbi copy analyze "<source>.pbip"
   ```
   Output JSON: `pages_with_bookmarks` / `pages_without_bookmarks` (each has a
   `name` id and `display_name`), plus `analysis_summary`.

2. **Confirm the page selection** with the user using the `name` ids from analyze.

3. **Apply:**
   ```bash
   # duplicate within the same report
   ae-pbi copy apply "<source>.pbip" --pages name1,name2

   # copy into another report (cross-PBIP)
   ae-pbi copy apply "<source>.pbip" --pages name1 --target "<target>.pbip"
   ```
   `--pages` takes the `name` ids (not display names) from analyze, comma-separated.

4. Report `success` and the pages copied; tell the user to reopen the destination
   report in Power BI Desktop.

## Notes

- Full-page copy automatically brings each page's bookmarks and visual actions;
  that is the point of this tool.
- With `--target`, the destination PBIP is modified; back it up first if it matters.
- Use the `name` field from `copy analyze`, not the human display name.

## Verification

Re-run `copy analyze` on the destination and confirm the new page name(s) appear
and that bookmark counts increased as expected; open the report to spot-check.
