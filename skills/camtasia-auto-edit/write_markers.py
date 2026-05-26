"""
Stage 2 (minimal): inject detected segments as Camtasia markers into an existing .tscproj.

Camtasia stores markers as keyframes on a timeline-level `toc` (table-of-contents)
parameter. The marker time uses the project's editRate (ticks per second).

Usage:
    python write_markers.py <project.tscproj> --segments segments.json [--out modified.tscproj] [--backup]

The .tscproj path can be either:
  - The folder (e.g. .../Visual Cals in Power BI.tscproj/), in which case the inner
    .tscproj JSON file with the matching name is patched
  - The inner JSON file directly
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

TYPE_LABEL = {
    "filler": "FILLER",
    "silence": "SILENCE",
    "static": "STATIC",
    "mistake": "MISTAKE",
    "retake_start": "RETAKE START",
    "retake_keeper": "RETAKE KEEPER",
}


def mmss(t: float) -> str:
    m = int(t // 60)
    s = int(t % 60)
    return f"{m:02d}:{s:02d}"


def label_for(seg: dict) -> str:
    kind = seg.get("type", "?")
    text = (seg.get("text") or "").strip().strip(".,!?;:")
    prefix = TYPE_LABEL.get(kind, kind.upper())
    if text:
        return f"{prefix}: {text}"
    return prefix


def resolve_project_file(p: Path) -> Path:
    """Accept either the .tscproj folder or the inner JSON file. Return the inner JSON file."""
    if p.is_dir() and p.suffix.lower() == ".tscproj":
        # Camtasia 2023+ stores the JSON as <projectname>.tscproj inside a same-named folder.
        candidate = p / p.name
        if candidate.exists():
            return candidate
        # Fallback: any .tscproj file in the folder
        for child in p.iterdir():
            if child.is_file() and child.suffix.lower() == ".tscproj":
                return child
        raise FileNotFoundError(f"No .tscproj JSON file found inside {p}")
    if p.is_file():
        return p
    raise FileNotFoundError(f"Not a file or .tscproj folder: {p}")


def build_keyframes(segments: list[dict], edit_rate: int, dedupe_window_s: float = 0.05) -> list[dict]:
    """Convert segments to Camtasia toc keyframes. Sorted by time. Dedupes near-coincident markers."""
    keyframes = []
    for seg in segments:
        start_s = float(seg["start"])
        ticks = int(round(start_s * edit_rate))
        keyframes.append({
            "endTime": ticks,
            "time": ticks,
            "value": label_for(seg),
            "duration": 0,
        })
    keyframes.sort(key=lambda k: k["time"])

    deduped: list[dict] = []
    window_ticks = int(dedupe_window_s * edit_rate)
    for kf in keyframes:
        if deduped and (kf["time"] - deduped[-1]["time"]) <= window_ticks:
            # merge values with " | "
            if kf["value"] not in deduped[-1]["value"]:
                deduped[-1]["value"] = f"{deduped[-1]['value']} | {kf['value']}"
            continue
        deduped.append(kf)
    return deduped


def patch_project(project: dict, keyframes: list[dict], replace: bool) -> tuple[int, int]:
    """Insert/merge keyframes into the project's parameters.toc.keyframes.

    Returns (existing_count, total_count_after).
    """
    timeline = project.get("timeline")
    if timeline is None:
        raise KeyError("project has no 'timeline' key")

    parameters = timeline.setdefault("parameters", {})
    toc = parameters.setdefault("toc", {"type": "string", "keyframes": []})
    toc.setdefault("type", "string")
    existing = toc.get("keyframes") or []

    if replace:
        merged = keyframes
    else:
        merged = list(existing) + keyframes
        merged.sort(key=lambda k: k["time"])

    toc["keyframes"] = merged
    return len(existing), len(merged)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("project", type=Path, help=".tscproj folder or inner .tscproj JSON file")
    ap.add_argument("--segments", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=None, help="Output path. Default: overwrite input (after backup).")
    ap.add_argument("--backup", action="store_true", help="Write a .bak alongside the input before overwriting.")
    ap.add_argument("--replace", action="store_true", help="Wipe existing markers before writing new ones.")
    ap.add_argument("--types", nargs="+", default=None, help="Only include these segment types (e.g. --types filler discourse silence).")
    args = ap.parse_args()

    inner = resolve_project_file(args.project)
    print(f"Project JSON: {inner}", file=sys.stderr)

    project = json.loads(inner.read_text(encoding="utf-8"))
    edit_rate = int(project.get("editRate", 705600000))
    print(f"editRate: {edit_rate} (ticks/sec)", file=sys.stderr)

    segments = json.loads(args.segments.read_text(encoding="utf-8"))
    if args.types:
        before = len(segments)
        segments = [s for s in segments if s.get("type") in set(args.types)]
        print(f"Filtered to types {args.types}: {len(segments)}/{before}", file=sys.stderr)

    keyframes = build_keyframes(segments, edit_rate)
    print(f"Built {len(keyframes)} marker keyframes from {len(segments)} segments", file=sys.stderr)

    if keyframes[:3]:
        print("First 3:", file=sys.stderr)
        for kf in keyframes[:3]:
            t_s = kf["time"] / edit_rate
            print(f"  {mmss(t_s):>6}  {kf['value']}", file=sys.stderr)

    existing, total = patch_project(project, keyframes, replace=args.replace)
    print(f"Markers: {existing} existing -> {total} after write", file=sys.stderr)

    out_path = args.out if args.out else inner
    if out_path == inner and args.backup:
        bak = inner.with_suffix(inner.suffix + f".bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(inner, bak)
        print(f"Backup: {bak}", file=sys.stderr)

    out_path.write_text(json.dumps(project, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
