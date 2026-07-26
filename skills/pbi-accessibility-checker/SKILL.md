---
name: pbi-accessibility-checker
description: Audit a Power BI report (PBIP/PBIX) for WCAG 2.1 accessibility issues: tab order, alt text, color contrast, page/visual titles, data labels, bookmark names, hidden pages. Use when the user says "check report accessibility", "is this report accessible", "run a WCAG audit", "find accessibility issues", "check color contrast", or "check tab order". Backed by the signed ae-pbi CLI (Windows). Read-only.
---

# PBI Accessibility Checker

Read-only WCAG 2.1 audit of a report. Reports issues by check type and severity.
Never modifies the report.

## Locate the binary

Use `ae-pbi` if on PATH, else `"$HOME/.ae-pbi/bin/ae-pbi.exe"`. If missing, point
the user to this skill's README (`scripts/install-ae-pbi.ps1`). Windows only.

## Workflow

1. **Run the audit:**
   ```bash
   ae-pbi accessibility "<path>.pbip"
   ```
   Output JSON: `summary` (`total`/`errors`/`warnings`/`info`) and `issues` (each
   with `check_type`, `severity`, `page_name`, `visual_name`, `issue_description`,
   `recommendation`, `wcag_reference`).

2. **Focus the user** on `error` severity first, then `warning`. Group by
   `check_type` and give the `recommendation` for each.

3. Optional filters:
   - `--checks tab_order,alt_text,color_contrast,page_title,visual_title,data_labels,bookmark_name,hidden_page`
   - `--min-severity error` (or `warning` / `info`)
   - `--format text` for a compact one-line-per-issue listing.

## Notes

- Purely diagnostic; there is no `apply`. The user fixes issues in Power BI Desktop.
- Works on `.pbip` and `.pbix`.
- Large reports can produce many `warning`/`info` items; lead with `--min-severity error`.

## Verification

Re-run after the user's fixes and confirm the `errors` count drops; compare
`summary` before/after.
