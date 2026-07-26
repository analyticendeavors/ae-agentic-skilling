# pbi-report-cleanup

Find and remove dead weight from a Power BI report (PBIP): unused themes, custom
visuals, bookmarks, visual-level filters, saved DAX/TMDL scripts, and
duplicate/unused images.

Part of the **AE PBI Tools** skill group. All of these skills share one signed
CLI, `ae-pbi` (Windows). The tool's logic is distributed as a compiled binary;
the source is not public.

## Platform

**Windows only.** `ae-pbi` is a Windows console executable. It edits PBIP files
on disk (which are just JSON/TMDL text), so no Power BI install is required to run it.

## Install the CLI (one time)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-ae-pbi.ps1
```

This downloads the latest signed `ae-pbi.exe` to `%USERPROFILE%\.ae-pbi\bin` and
adds it to your PATH. The binary checks once a day for a newer release and prints
a one-line notice if you are behind (silence with `AE_PBI_NO_UPDATE_CHECK=1`).

## Usage

```bash
# 1) See what could be removed (read-only; works on .pbip or .pbix)
ae-pbi cleanup analyze "C:\reports\Sales.pbip"

# 2) Remove only what you choose (PBIP only; writes a timestamped .bak first)
ae-pbi cleanup apply "C:\reports\Sales.pbip" --themes --bookmarks --duplicate-images

# Everything, but skip two named bookmarks
ae-pbi cleanup apply "C:\reports\Sales.pbip" --all --except "Old View,Scratch"
```

Category flags: `--themes`, `--custom-visuals`, `--bookmarks`, `--filters`
(hides visual filters), `--dax-queries`, `--tmdl-scripts`, `--duplicate-images`,
`--unused-images`, or `--all`. Scope by item name with `--only` / `--except`.
Disable the backup with `--no-backup` (not recommended).

## Limitations

- `apply` refuses `.pbix` files (analyze-only for PBIX). Convert to PBIP to clean.
- Always reopen the report in Power BI Desktop after an apply to confirm it loads.
