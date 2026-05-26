"""
Stage 2 (minimal): inject detected segments as Camtasia markers into an existing .tscproj.

Camtasia supports markers at TWO levels:

  1. Timeline-level: stored at `timeline.parameters.toc.keyframes` with absolute
     timeline times. Drawback: when the user ripple-deletes content, the audio
     shifts left but timeline markers stay put, becoming misaligned.

  2. Clip-level (the default this tool now uses): stored at
     <StitchedMedia>.parameters.toc.keyframes inside a media clip group.
     Crucially, Camtasia auto-adjusts these times when the user trims or
     ripple-deletes content within the clip -- so they stay aligned with the
     audio they were describing.

This tool prefers clip-level. It finds the StitchedMedia whose attributes.ident
matches the project's recording (typically a .trec file referenced in sourceBin)
and writes markers there. If no suitable StitchedMedia is found (e.g. the user
hasn't dragged the recording onto the timeline yet), it falls back to
timeline-level markers with a warning.

The marker time uses the project's editRate (ticks per second), typically
705600000. Same conversion either way: ticks = seconds * editRate.

Usage:
    python write_markers.py <project.tscproj> --segments segments.json [--out modified.tscproj] [--backup]

The .tscproj path can be either:
  - The folder (e.g. .../My Project.tscproj/), in which case the inner
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


def _recording_idents(project: dict) -> set[str]:
    """Return the set of sourceBin idents that look like recordings (.trec).

    Used to identify which StitchedMedia in the timeline corresponds to a
    recording (vs. background music, intro logo, etc.).
    """
    idents: set[str] = set()
    for src in project.get("sourceBin", []) or []:
        src_name = src.get("src", "")
        if src_name.lower().endswith(".trec"):
            # The ident in the timeline matches the file stem, without extension.
            stem = src_name.rsplit(".", 1)[0]
            idents.add(stem)
    return idents


def _iter_stitched_media(node):
    """Yield every StitchedMedia dict found in the project tree.

    Depth-first walk. Yields the dicts themselves so the caller can mutate
    parameters in place.
    """
    if isinstance(node, dict):
        if node.get("_type") == "StitchedMedia":
            yield node
        for v in node.values():
            yield from _iter_stitched_media(v)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_stitched_media(item)


def _find_recording_stitched_media(project: dict) -> dict | None:
    """Find the StitchedMedia clip whose ident matches a recording in sourceBin.

    Returns the StitchedMedia dict, or None if no match found.
    """
    rec_idents = _recording_idents(project)
    if not rec_idents:
        return None
    for sm in _iter_stitched_media(project):
        ident = (sm.get("attributes") or {}).get("ident", "")
        if ident in rec_idents:
            return sm
    return None


def patch_project(project: dict, keyframes: list[dict], replace: bool, force_timeline: bool = False) -> tuple[int, int, str]:
    """Insert/merge keyframes into the right toc parameter.

    Prefers a clip-level toc on the recording's StitchedMedia (markers travel
    with the clip when content is trimmed). Falls back to timeline-level toc
    if no recording StitchedMedia is found, or if force_timeline=True.

    Returns (existing_count, total_count_after, location_description).
    """
    target_toc = None
    location = ""

    if not force_timeline:
        sm = _find_recording_stitched_media(project)
        if sm is not None:
            parameters = sm.setdefault("parameters", {})
            target_toc = parameters.setdefault("toc", {"type": "string", "keyframes": []})
            ident = (sm.get("attributes") or {}).get("ident", "?")
            location = f"clip-level (StitchedMedia ident={ident!r}) -- markers will move with trims"

    if target_toc is None:
        timeline = project.get("timeline")
        if timeline is None:
            if force_timeline:
                raise KeyError("--timeline-markers requested but project has no 'timeline' key")
            raise KeyError("project has no 'timeline' key and no recording StitchedMedia found")
        parameters = timeline.setdefault("parameters", {})
        target_toc = parameters.setdefault("toc", {"type": "string", "keyframes": []})
        if force_timeline:
            location = "timeline-level (forced via --timeline-markers) -- markers will not move on trim"
        else:
            print(
                "WARNING: No recording StitchedMedia found in the project. Falling back to\n"
                "         timeline-level markers, which DO NOT move when the user trims content.\n"
                "         To get clip-anchored markers, drag the recording onto the timeline first,\n"
                "         then re-run this tool.",
                file=sys.stderr,
            )
            location = "timeline-level (FALLBACK -- no recording StitchedMedia found) -- markers will drift on trim"

    target_toc.setdefault("type", "string")
    existing = target_toc.get("keyframes") or []

    if replace:
        merged = keyframes
    else:
        merged = list(existing) + keyframes
        merged.sort(key=lambda k: k["time"])

    target_toc["keyframes"] = merged
    return len(existing), len(merged), location


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("project", type=Path, help=".tscproj folder or inner .tscproj JSON file")
    ap.add_argument("--segments", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=None, help="Output path. Default: overwrite input (after backup).")
    ap.add_argument("--backup", action="store_true", help="Write a .bak alongside the input before overwriting.")
    ap.add_argument("--replace", action="store_true", help="Wipe existing markers before writing new ones.")
    ap.add_argument("--types", nargs="+", default=None, help="Only include these segment types (e.g. --types filler silence).")
    ap.add_argument("--timeline-markers", action="store_true", help="Force timeline-level markers (legacy behavior). Default is clip-level, which moves with trims.")
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

    existing, total, location = patch_project(project, keyframes, replace=args.replace, force_timeline=args.timeline_markers)
    print(f"Markers: {existing} existing -> {total} after write", file=sys.stderr)
    print(f"Written to: {location}", file=sys.stderr)

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
