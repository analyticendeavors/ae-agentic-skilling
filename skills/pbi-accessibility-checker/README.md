# pbi-accessibility-checker

Audit a Power BI report (PBIP or PBIX) for WCAG 2.1 accessibility issues: tab
order, alt text, color contrast, page/visual titles, data labels, bookmark names,
and hidden pages. Read-only: it reports, it never edits.

Part of the **AE PBI Tools** skill group (shared `ae-pbi` CLI, Windows, compiled
binary; source not public).

## Platform

**Windows only.** Reads PBIP/PBIX files; no Power BI install required.

## Install the CLI (one time)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-ae-pbi.ps1
```

## Usage

```bash
# Full audit (JSON)
ae-pbi accessibility "C:\reports\Sales.pbip"

# Errors only, compact text
ae-pbi accessibility "C:\reports\Sales.pbip" --min-severity error --format text

# Only contrast and alt-text checks
ae-pbi accessibility "C:\reports\Sales.pbip" --checks color_contrast,alt_text
```

Filters: `--checks` (comma list), `--min-severity error|warning|info`,
`--format json|text`.

## Limitations

- Diagnostic only; fixes are made by hand in Power BI Desktop.
- Big reports surface many `warning`/`info` items; start with `--min-severity error`.
