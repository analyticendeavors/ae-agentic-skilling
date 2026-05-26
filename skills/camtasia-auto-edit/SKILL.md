---
name: camtasia-auto-edit
description: Detect filler words (um/uh), long silences, and retake attempts in a Camtasia recording, then drop visible Camtasia markers on the timeline so the user can scrub-and-cut. Use when the user says "auto-mark this video", "find the ums in this recording", "where are the retakes", "drop markers in this .tscproj", or hands over a `.trec` / `.mp4` / `.tscproj` file and asks for help editing.
---

# Camtasia Auto-Edit

Two-stage pipeline:

1. **Detect** filler words (`um`/`uh`/`er`), long silences (≥ 2s), and re-take attempts (phrase repeats within 15s) in any video or audio file
2. **Write** the detections as native Camtasia markers into a `.tscproj` so the user can `Ctrl+]` / `Ctrl+[` through them in the timeline

The user keeps full control: every detection becomes a marker, nothing is auto-cut. They scrub marker-to-marker and ripple-delete what they want.

## When to invoke

- "Auto-mark this video" / "drop markers in this project"
- "Find the ums" / "where are the retakes" / "find the long silences"
- User hands over a `.trec`, `.mp4`, or `.tscproj` folder and wants editing help

## Workflow

### Always do these in order:

1. **Locate inputs.** Confirm:
   - **Video/audio source** — usually a `.trec` inside a `.tscproj` folder, or an `.mp4`
   - **Target `.tscproj`** — the project to receive markers. Often the same folder.

2. **Camtasia must be closed OR write to a copy.** Default: write to a copy. Use `duplicate_project.ps1` as a Windows template, or `cp -r` on Mac/Linux. The original is never touched.

3. **Run detector** (writes a JSON of detections):
   ```bash
   python detect_fillers.py "<path to .trec or .mp4>" --out segments.json --skip-panns
   ```

   Use `--skip-panns` by default. The PANNs cough/breath classifier is 327 MB, adds ~60s per run, and on typical microphone setups produces zero hits. Enable it only if the user has noisy audio with frequent coughs/breaths.

4. **Write markers** into the target `.tscproj`:
   ```bash
   python write_markers.py "<path to .tscproj folder>" --segments segments.json --replace
   ```

   - `--replace` wipes existing markers before writing. Use this for fresh detection runs.
   - Omit `--replace` to append.
   - The script accepts either the `.tscproj` folder path or the inner JSON file path directly.

5. **Report to user**: total markers, breakdown by type, biggest retake/silence found. Tell them to **reload the project in Camtasia** (close+reopen, or File → Revert).

## Detector behavior

| Type | Detection | Default action |
|---|---|---|
| `filler` | Whisper word-level: `um`, `uh`, `er`, `ah`, `hmm`, `mm`, `umm`, `uhh` | Marker named `FILLER: um` |
| `silence` | ffmpeg `silencedetect` at -30 dB, **≥ 2s** gap | Marker named `SILENCE: 2.34s gap` |
| `retake_start` | Phrase repetition: 4-word ngram appearing 2+ times within 15s, nested events merged | Marker at the **first attempt** |
| `retake_keeper` | Same retake event, last occurrence | Marker at the **keeper take's start**. User cuts from START to KEEPER. |
| `mistake` | Regex: "let me try that again", "sorry let me", "scratch that", etc. | Marker. Rare hit. |
| `static` | ffmpeg `freezedetect` ≥ 3s of no pixel change | Marker. Rare hit. |

**Discourse markers** (sentence-initial "So" / "Now") are intentionally NOT detected — they are speaking style, not errors, and produce too many false positives.

**PANNs (cough/breath classifier)** is implemented but `--skip-panns` is the default. Found 0 hits on clean recordings.

## Marker schema (Camtasia internals)

Camtasia stores markers as keyframes on a `toc` (table-of-contents) parameter. They can live at TWO levels:

**Clip-level (preferred, default).** Inside a `StitchedMedia` group's `parameters.toc.keyframes`. Camtasia auto-adjusts the times when the user trims or ripple-deletes content within the clip, so markers stay aligned with the audio they describe:

```json
{
  "_type": "StitchedMedia",
  "attributes": { "ident": "Rec 5-20-2026-3-27-37-PM" },
  "parameters": {
    "toc": {
      "type": "string",
      "keyframes": [
        { "endTime": <ticks>, "time": <ticks>, "value": "MARKER NAME", "duration": 0 }
      ]
    }
  }
}
```

**Timeline-level (fallback).** At `timeline.parameters.toc.keyframes`. Same keyframe shape, but markers do NOT move when content is trimmed -- they stay at absolute timeline times. The tool falls back to this only if no recording `StitchedMedia` is found in the project.

The writer identifies the right `StitchedMedia` by matching its `attributes.ident` against `.trec` filenames in the project's `sourceBin`. If you have multiple recordings on the timeline, markers go to the first one matched.

`time` is in ticks. The project's `editRate` (top-level field) gives ticks-per-second -- typically `705600000`. So `ticks = seconds * editRate`.

## Files in this skill

- `detect_fillers.py` — Stage 1 detector. Reads video/audio, outputs `segments.json`.
- `write_markers.py` — Stage 2 writer. Reads `segments.json` + `.tscproj`, writes markers in place.
- `duplicate_project.ps1` — example PowerShell to copy a `.tscproj` folder before writing (Windows).
- `requirements.txt` — pinned Python dependencies.
- `README.md` — user-facing setup and usage.

## Dependencies

- **ffmpeg** on PATH (or `FFMPEG` env var). The Python script looks for it via `shutil.which("ffmpeg")` then falls back to `FFMPEG`.
- **Python 3.10+** with `faster-whisper`, `panns_inference`, `librosa`, `soundfile` (see `requirements.txt`).

## Known limitations

- Whisper's `.en` models drop disfluencies. The detector uses `small` (multilingual) with `condition_on_previous_text=False` and an `initial_prompt` nudging verbatim output. Still misses some ums.
- Retake detection uses 4-word ngrams. Shorter repeats (1-3 words) aren't flagged to avoid false positives.
- The `.trec` is a standard MP4 container so ffmpeg reads the AAC audio directly; no special Camtasia export needed.
- Markers are written as **clip-level** by default (attached to the recording's `StitchedMedia`). Camtasia auto-adjusts them when content is trimmed, so they stay aligned. If the user passes `--timeline-markers` they get the older absolute-time behavior, which drifts on trim.

## Verification

After writing markers, sample check:
1. Open the modified `.tscproj` in Camtasia
2. Press `Ctrl+]` to jump through markers
3. Confirm `RETAKE START` / `RETAKE KEEPER` pairs land at real phrase repeats
4. Confirm `SILENCE` markers land in actual dead air on the waveform
5. If detection is wrong: note the timestamps and ask what was actually said there

## What's NOT in this skill

- **Project templating is handled by Camtasia natively**, not this skill. For repeating template-driven videos, save your reference project as a `.camtemplate` via `File → Save Project as Template`, then create new videos via `File → New Project from Template` and run this skill on top for auto-markers. Programmatic `.tscproj` generation was scoped at 8-15 hours of fragile custom code; Camtasia's built-in template feature does the same job natively.
- **Auto-cut** (programmatically deleting filler/retake/silence ranges from the timeline). Markers-only is intentional — keeps editorial control with the user. Could be added later as `--cut-retakes` / `--cut-long-silences` flags if needed.
