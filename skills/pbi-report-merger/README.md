# pbi-report-merger

Merge two Power BI reports (PBIP) into one: pages, bookmarks, and measures, with
explicit theme-conflict handling. The two inputs are never modified; a new merged
PBIP is written.

Part of the **AE PBI Tools** skill group (shared `ae-pbi` CLI, Windows, compiled
binary; source not public).

## Platform

**Windows only.** Edits/writes PBIP JSON on disk; no Power BI install required.

## Install the CLI (one time)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-ae-pbi.ps1
```

## Usage

```bash
# 1) Counts and conflicts (read-only)
ae-pbi merge analyze "C:\reports\First.pbip" "C:\reports\Second.pbip"

# 2) Merge, keeping report A's theme
ae-pbi merge apply "C:\reports\First.pbip" "C:\reports\Second.pbip" --out "C:\reports\Merged.pbip" --theme a
```

`--theme`: `a` (keep A's theme), `b` (keep B's), or `same` (themes already match).
Omit `--out` to auto-name `Combined_A_B.pbip` beside the inputs.

## Limitations

- Duplicate measure names across the two models are reported under
  `measures.conflicts` by `analyze`; review them before merging.
- Open the merged report in Power BI Desktop to confirm both reports' pages landed.
