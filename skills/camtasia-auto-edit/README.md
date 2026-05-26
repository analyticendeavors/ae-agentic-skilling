# camtasia-auto-edit

Detect filler words (`um`, `uh`), long silences, and re-take attempts in a Camtasia recording, then drop visible markers on the Camtasia timeline so you can scrub-and-cut.

**Markers only.** This skill never cuts your video automatically. It surfaces the moments worth cutting, you decide what goes.

## What it detects

| Type | How | Default action |
|---|---|---|
| `filler` | Whisper word-level transcript matches `um/uh/er/ah/hmm/mm` | Marker named `FILLER: um` |
| `silence` | ffmpeg `silencedetect` at -30 dB, gap ≥ 2 seconds | Marker named `SILENCE: 2.34s gap` |
| `retake_start` | Phrase repetition: 4-word ngram appearing 2+ times within 15s | Marker at the **first attempt** |
| `retake_keeper` | Same retake event, last occurrence | Marker at the **last attempt's start** (you cut from START to KEEPER) |
| `mistake` | Regex on transcript: "let me try that again", "scratch that", etc. | Marker |
| `static` | ffmpeg `freezedetect` ≥ 3s of no pixel change | Marker |

A cough/breath detector via PANNs is implemented but **disabled by default** (`--skip-panns`) — on typical microphone setups it finds zero hits in 20+ minutes of speech and the 327 MB model just adds ~60s per run. Enable it explicitly if you have a noisy mic.

## Install

1. **Python 3.10+** (tested on 3.13)
2. **ffmpeg** on PATH:
   - Windows: `winget install Gyan.FFmpeg`
   - macOS: `brew install ffmpeg`
   - Linux: your distro's package manager
3. **Python deps**:
   ```bash
   cd skills/camtasia-auto-edit
   pip install -r requirements.txt
   ```

## Usage

### 1. Detect

```bash
python detect_fillers.py path/to/recording.trec --out segments.json --skip-panns
```

Accepts `.trec` (Camtasia recording), `.mp4`, `.wav`, or any format ffmpeg can read.

Outputs a JSON of segments — example:

```json
[
  {"start": 25.36, "end": 25.62, "type": "filler", "text": "um", "confidence": 0.62},
  {"start": 124.30, "end": 132.84, "type": "retake_start", "text": "\"what are visual calculations\""},
  {"start": 132.84, "end": 132.84, "type": "retake_keeper", "text": "\"what are visual calculations\" (cut to here)"},
  {"start": 349.60, "end": 509.02, "type": "silence", "text": "159.42s gap"}
]
```

### 2. Write markers into a Camtasia project

```bash
python write_markers.py path/to/project.tscproj --segments segments.json --replace
```

The script accepts either the `.tscproj` folder or the inner `.tscproj` JSON file. Use `--replace` to wipe existing markers. **Close Camtasia first**, or write to a duplicated project folder (see `duplicate_project.ps1`).

### 3. Open the project in Camtasia

Markers appear on the timeline ruler. Navigate with `Ctrl+]` / `Ctrl+[`.

## Limitations

- **Tested on Windows.** Should work on macOS/Linux but has not been verified there.
- **Whisper aggressively drops disfluencies.** The detector uses `small` (multilingual, not `.en`) with `condition_on_previous_text=False` and a verbatim prompt. Still misses some ums.
- **Retake detection uses 4-word ngrams.** Shorter repeats (1-3 words) aren't flagged to avoid false positives.
- **Marker drift after trimming.** Camtasia stores markers at absolute timeline times. When you ripple-delete content, markers stay put while audio shifts left — so markers after your cut become misaligned. Workaround: edit markers top-down (earliest first). Tracked as [issue #1](https://github.com/analyticendeavors/ae-agentic-skilling/issues/1).

## Files in this skill

- `detect_fillers.py` — Stage 1 detector. Reads video/audio, outputs `segments.json`.
- `write_markers.py` — Stage 2 writer. Reads `segments.json` + `.tscproj`, writes markers in place.
- `duplicate_project.ps1` — example PowerShell to copy a `.tscproj` folder before writing (Windows).
- `requirements.txt` — pinned Python dependencies.
- `SKILL.md` — agent-facing metadata and invocation instructions.

## License

MIT — see [repo root](../../LICENSE).
