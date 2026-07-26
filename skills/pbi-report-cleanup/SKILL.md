---
name: pbi-report-cleanup
description: Find and remove unused themes, custom visuals, bookmarks, visual-level filters, saved DAX/TMDL scripts, and duplicate/unused images from a Power BI report (PBIP). Use when the user says "clean up my report", "report cleanup", "find unused themes/bookmarks/custom visuals", "remove unused visuals", "what can I delete from this report", "consolidate duplicate images", or hands over a .pbip and asks to slim it down. Backed by the signed ae-pbi CLI (Windows). Read-only "analyze" works on .pbip and .pbix; "apply" modifies .pbip only.
---

# PBI Report Cleanup

Two-phase, mirrors the AE Multi-Tool GUI ("Analyze Reports" -> "Clean Selected"):

1. **analyze** (read-only) lists every cleanup opportunity as JSON.
2. **apply** removes only the categories the user picks. PBIP only; backs up first by default.

## Locate the binary

Use `ae-pbi` if it is on PATH. Otherwise use `"$HOME/.ae-pbi/bin/ae-pbi.exe"`.
If neither exists, tell the user to install it (see this skill's README:
`scripts/install-ae-pbi.ps1`). Windows only.

## Workflow

1. **Analyze first, always.** Never guess what to remove.
   ```bash
   ae-pbi cleanup analyze "<path>.pbip"
   ```
   Output JSON: `summary` (counts per `item_type`) and `opportunities` (each with
   `item_type`, `item_name`, `location`, `reason`, `safety_level`, `size_bytes`).

2. **Present the categories** to the user (themes, custom visuals, bookmarks,
   visual filters, DAX queries, TMDL scripts, duplicate images, unused images)
   with counts and the reasons. Let them choose. Do not auto-remove.

3. **Apply** only the chosen categories:
   ```bash
   ae-pbi cleanup apply "<path>.pbip" --themes --bookmarks --duplicate-images
   ```
   Category flags: `--themes --custom-visuals --bookmarks --filters --dax-queries
   --tmdl-scripts --duplicate-images --unused-images`, or `--all`.
   Narrow within categories by item name: `--only Name1,Name2` / `--except Name3`.
   A timestamped `.bak` of the `.pbip` and `.Report` is written unless `--no-backup`.

4. **Report** the apply summary: `removed`, `failed`, `bytes_freed`, and the
   per-item `results`. Tell the user to reopen the report in Power BI Desktop.

## Notes / gotchas

- `--filters` HIDES visual-level filters (it does not delete data); everything else removes files.
- `.pbix` is supported for `analyze` only. `apply` on a `.pbix` errors by design.
- Exit code is non-zero on failure; the error is JSON on stderr.
- `safety_level` is `safe` | `warning` | `risky`; surface `warning`/`risky` items explicitly before applying.

## Verification

After `apply`, re-run `analyze` and confirm the chosen categories dropped to the
expected counts, then open the report in Power BI Desktop to confirm it loads.
