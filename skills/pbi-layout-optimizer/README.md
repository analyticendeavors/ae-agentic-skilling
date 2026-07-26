# pbi-layout-optimizer

Auto-arrange the Power BI model relationship diagram with a middle-out layout:
fact tables centered, dimensions radiating outward. Rewrites `diagramLayout.json`
in place.

Part of the **AE PBI Tools** skill group (shared `ae-pbi` CLI, Windows, compiled
binary; source not public).

## Platform

**Windows only.** Edits the PBIP project's `diagramLayout.json` text file; no Power
BI install required to run the tool.

## Install the CLI (one time)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-ae-pbi.ps1
```

## Usage

```bash
# Preview (no write)
ae-pbi layout "C:\reports\Sales" --dry-run

# Apply (rewrites diagramLayout.json)
ae-pbi layout "C:\reports\Sales"

# Pass the .pbip file instead of the folder; target diagram tab 0 and 1
ae-pbi layout "C:\reports\Sales.pbip" --diagram 0 1
```

Accepts the project folder or the `.pbip` file. Options: `--dry-run`,
`--canvas-width`, `--canvas-height`, `--diagram`.

## Limitations

- Changes diagram layout coordinates only; never model data, relationships, or DAX.
- Reopen Model view in Power BI Desktop to see the result.
