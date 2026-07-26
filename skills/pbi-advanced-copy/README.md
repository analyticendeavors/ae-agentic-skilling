# pbi-advanced-copy

Duplicate Power BI report pages together with their bookmarks and visual actions,
within one report, or across two PBIP reports.

Part of the **AE PBI Tools** skill group (shared `ae-pbi` CLI, Windows, compiled
binary; source not public).

## Platform

**Windows only.** Edits PBIP report JSON on disk; no Power BI install required.

## Install the CLI (one time)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-ae-pbi.ps1
```

## Usage

```bash
# 1) List pages and which carry bookmarks (read-only)
ae-pbi copy analyze "C:\reports\Dashboard.pbip"

# 2a) Duplicate pages within the same report (use the page 'name' ids from analyze)
ae-pbi copy apply "C:\reports\Dashboard.pbip" --pages 9b5cd1c092c1fa4f638e

# 2b) Copy a page into a different report
ae-pbi copy apply "C:\reports\Dashboard.pbip" --pages 9b5cd1c092c1fa4f638e --target "C:\reports\Exec.pbip"
```

`--pages` takes the page `name` ids (not display names) reported by `copy analyze`,
comma-separated. `--target` switches to a cross-report copy.

## Limitations

- Selection is by the internal page `name` id from `analyze`, not the display name.
- A cross-report `apply` modifies the target PBIP; back it up first if needed.
- Reopen the destination report in Power BI Desktop to confirm.
