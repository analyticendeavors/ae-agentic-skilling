---
name: pbi-layout-optimizer
description: Auto-arrange the Power BI model relationship diagram using a middle-out layout (facts centered, dimensions radiating out). Use when the user says "organize the relationship diagram", "auto-arrange the model", "tidy the model layout", "fix the diagram view", "run the layout optimizer", or wants the model diagram cleaned up. Backed by the signed ae-pbi CLI (Windows). Modifies diagramLayout.json in place.
---

# PBI Layout Optimizer

Rearranges the model's relationship-diagram coordinates (middle-out: facts in the
center, dimensions around them) by rewriting `diagramLayout.json`.

## Locate the binary

Use `ae-pbi` if on PATH, else `"$HOME/.ae-pbi/bin/ae-pbi.exe"`. If missing, point
the user to this skill's README (`scripts/install-ae-pbi.ps1`). Windows only.

## Workflow

1. **Dry-run first** to preview without writing:
   ```bash
   ae-pbi layout "<pbip project folder or .pbip file>" --dry-run
   ```
   Output JSON includes `success`, `tables_arranged`, `layout_method`, `changes_saved`.

2. **Apply** (writes `diagramLayout.json`):
   ```bash
   ae-pbi layout "<pbip project folder or .pbip file>"
   ```

3. Report `tables_arranged` and tell the user to reopen the model in Power BI
   Desktop (Model view) to see the new arrangement.

## Notes

- Accepts either the PBIP **project folder** (the dir containing the
  `.SemanticModel`) or the `.pbip` file (it resolves to the folder).
- Optional: `--canvas-width N --canvas-height N`, `--diagram I [I ...]` to target
  specific diagram tabs (default: the first).
- This rewrites layout coordinates only; it never changes model data, relationships,
  measures, or columns.

## Verification

Run `--dry-run`, confirm `tables_arranged` matches the model's table count, then
apply and open Model view in Power BI Desktop.
