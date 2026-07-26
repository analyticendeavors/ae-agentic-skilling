---
name: pbi-report-merger
description: Merge two Power BI reports (PBIP) into one, combining pages, bookmarks, and measures, with theme-conflict handling. Use when the user says "merge these two reports", "combine two PBIPs", "consolidate reports into one", "join report A and report B", or hands over two .pbip files to fold together. Backed by the signed ae-pbi CLI (Windows). Writes a new merged PBIP.
---

# PBI Report Merger

Combines report A and report B into a single new PBIP, merging pages, bookmarks,
and measures, and resolving theme conflicts by your choice.

## Locate the binary

Use `ae-pbi` if on PATH, else `"$HOME/.ae-pbi/bin/ae-pbi.exe"`. If missing, point
the user to this skill's README (`scripts/install-ae-pbi.ps1`). Windows only.

## Workflow

1. **Analyze first** to surface counts and conflicts:
   ```bash
   ae-pbi merge analyze "<A>.pbip" "<B>.pbip"
   ```
   Output JSON: per-report `pages`/`bookmarks`/`measures`, a `themes` block with
   `conflict: true|false`, and `measures.conflicts`.

2. **If `themes.conflict` is true**, ask the user which theme to keep. If there is
   no conflict, use `--theme same`.

3. **Apply:**
   ```bash
   ae-pbi merge apply "<A>.pbip" "<B>.pbip" --out "<Merged>.pbip" --theme a
   ```
   `--theme a` keeps report A's theme, `b` keeps B's, `same` when they already match.
   Omit `--out` to auto-name `Combined_A_B.pbip` next to the inputs.

4. Report `success` and `output_path`; tell the user to open the merged report in
   Power BI Desktop.

## Notes

- Inputs are not modified; a brand-new merged PBIP is written.
- Surface `measures.conflicts` to the user before merging; duplicate measure names
  across the two models are worth a heads-up.

## Verification

Run `merge analyze` and check the totals; after `apply`, open `output_path` in
Power BI Desktop and confirm both reports' pages are present.
