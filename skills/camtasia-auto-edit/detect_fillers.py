"""
Stage 1: Detect filler words, coughs, and breaths in a video/audio file.

Outputs a JSON list of segments: [{ start, end, type, text?, confidence? }]
where type is one of: filler | breath | cough | throat_clear.

Usage:
    python detect_fillers.py <input.mp4 | input.wav> [--out segments.json]

Tested on Windows with Python 3.13. Should work on macOS/Linux with ffmpeg
installed and on PATH.

ffmpeg lookup order:
    1. FFMPEG environment variable (full path to ffmpeg executable)
    2. shutil.which("ffmpeg") -- finds ffmpeg on PATH
    3. If neither, errors with install instructions
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, asdict
from pathlib import Path


def _find_ffmpeg() -> str:
    """Locate the ffmpeg executable, preferring the FFMPEG env var, then PATH."""
    env_path = os.environ.get("FFMPEG")
    if env_path and Path(env_path).exists():
        return env_path
    which_path = shutil.which("ffmpeg")
    if which_path:
        return which_path
    print(
        "ERROR: ffmpeg not found.\n"
        "Install ffmpeg and ensure it's on PATH, or set the FFMPEG environment\n"
        "variable to the full path of the ffmpeg executable.\n"
        "  Windows: winget install Gyan.FFmpeg\n"
        "  macOS:   brew install ffmpeg\n"
        "  Linux:   apt install ffmpeg  (or your distro's package manager)\n",
        file=sys.stderr,
    )
    sys.exit(2)


FFMPEG = _find_ffmpeg()

FILLER_PATTERN = re.compile(r"^(um+|uh+|er+|ah+|hmm+|mm+|uhh+|umm+)[\.,!?]?$", re.IGNORECASE)

MISTAKE_PHRASES = [
    r"\blet me try (that |this )?again\b",
    r"\bsorry,? let me\b",
    r"\bsorry,? i (meant|mean)\b",
    r"\bactually,? (that's|that is) wrong\b",
    r"\bone more time\b",
    r"\bscratch that\b",
    r"\bwait,? (no|let me|hold on)\b",
    r"\bi misspoke\b",
    r"\bstart (over|again)\b",
]
MISTAKE_RE = re.compile("|".join(MISTAKE_PHRASES), re.IGNORECASE)

PANNS_LABELS_OF_INTEREST: dict[str, str] = {}


@dataclass
class Segment:
    start: float
    end: float
    type: str
    text: str | None = None
    confidence: float | None = None
    source: str | None = None


def extract_wav(input_path: Path, wav_path: Path) -> None:
    """Pull a 16 kHz mono WAV out of any input ffmpeg understands."""
    cmd = [
        FFMPEG, "-y", "-i", str(input_path),
        "-ac", "1", "-ar", "16000",
        "-vn", str(wav_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def detect_fillers_whisper(wav_path: Path, model_size: str = "small") -> list[Segment]:
    """Use faster-whisper word-level timestamps to find filler tokens.

    Uses the multilingual model (not .en) because the English-only models
    aggressively strip disfluencies. `condition_on_previous_text=False` stops
    the model from collapsing repeated 'um's. `initial_prompt` nudges it to
    keep them.
    """
    from faster_whisper import WhisperModel

    print(f"[whisper] loading model ({model_size}, cpu int8)...", file=sys.stderr)
    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    print("[whisper] transcribing (verbatim mode)...", file=sys.stderr)
    segments, info = model.transcribe(
        str(wav_path),
        word_timestamps=True,
        vad_filter=False,
        beam_size=1,
        condition_on_previous_text=False,
        initial_prompt="Um, uh, er, hmm. Verbatim transcript with disfluencies preserved.",
        language="en",
    )

    out: list[Segment] = []
    word_count = 0
    all_segments: list = []
    for seg in segments:
        if not seg.words:
            continue
        all_segments.append(seg)
        for w in seg.words:
            word_count += 1
            token = w.word.strip().lower()
            stripped = re.sub(r"[^a-z]", "", token)
            if not stripped:
                continue
            if FILLER_PATTERN.match(token) or FILLER_PATTERN.match(stripped):
                out.append(Segment(
                    start=round(float(w.start), 3),
                    end=round(float(w.end), 3),
                    type="filler",
                    text=w.word.strip(),
                    confidence=getattr(w, "probability", None),
                    source="whisper",
                ))

    # Mistake phrases: regex over the full transcript with word-timestamps to find spans.
    full_text_with_idx: list[tuple[int, int, float, float]] = []  # (char_start, char_end, t_start, t_end)
    pieces: list[str] = []
    cursor = 0
    for seg in all_segments:
        for w in seg.words:
            piece = w.word
            full_text_with_idx.append((cursor, cursor + len(piece), float(w.start), float(w.end)))
            pieces.append(piece)
            cursor += len(piece)
    full_text = "".join(pieces)

    for m in MISTAKE_RE.finditer(full_text):
        m_start, m_end = m.span()
        t_start = next((t[2] for t in full_text_with_idx if t[1] > m_start), None)
        t_end = next((t[3] for t in reversed(full_text_with_idx) if t[0] < m_end), None)
        if t_start is not None and t_end is not None:
            out.append(Segment(
                start=round(t_start, 3),
                end=round(t_end, 3),
                type="mistake",
                text=m.group(0),
                source="whisper",
            ))

    # Re-take detection: sliding-window phrase repetition.
    # If a 4-7 word sequence appears twice within ~15 seconds, the second one is likely a re-take.
    # Emits paired markers: RETAKE START at first attempt, RETAKE KEEPER at last attempt.
    out += detect_retakes(all_segments)

    filler_n = sum(1 for s in out if s.type == "filler")
    mist_n = sum(1 for s in out if s.type == "mistake")
    ret_n = sum(1 for s in out if s.type == "retake")
    print(f"[whisper] {word_count} words: {filler_n} fillers, {mist_n} mistakes, {ret_n} retakes", file=sys.stderr)
    return out


def detect_retakes(all_segments: list, ngram_size: int = 4, max_gap_s: float = 15.0) -> list[Segment]:
    """Find phrase repeats: a sliding ngram_size window appearing 2+ times within max_gap_s.

    Returns paired Segments per retake event:
      - retake_start  at the first attempt
      - retake_keeper at the last attempt (the take the user kept)
    Multiple attempts of the same retake collapse into one start + one keeper.
    """
    flat: list[tuple[float, float, str]] = []
    for seg in all_segments:
        for w in seg.words:
            tok = re.sub(r"[^a-z0-9]", "", w.word.lower())
            if tok:
                flat.append((float(w.start), float(w.end), tok))

    if len(flat) < ngram_size * 2:
        return []

    ngrams: dict[tuple, list[int]] = {}
    for i in range(len(flat) - ngram_size + 1):
        key = tuple(flat[j][2] for j in range(i, i + ngram_size))
        if any(len(t) < 2 for t in key):
            continue
        ngrams.setdefault(key, []).append(i)

    # Collect raw retake events: (first_word_idx, last_word_idx, phrase)
    raw_events: list[tuple[int, int, str]] = []
    for key, positions in ngrams.items():
        if len(positions) < 2:
            continue
        # Group positions that fall within max_gap_s of the previous one
        group: list[int] = [positions[0]]
        for p in positions[1:]:
            if flat[p][0] - flat[group[-1]][0] <= max_gap_s and flat[p][0] - flat[group[0]][0] <= max_gap_s * 2:
                group.append(p)
            else:
                if len(group) >= 2:
                    raw_events.append((group[0], group[-1], " ".join(key)))
                group = [p]
        if len(group) >= 2:
            raw_events.append((group[0], group[-1], " ".join(key)))

    # Merge events from the same retake. An event belongs to the previous retake if its
    # first attempt or its last attempt falls inside the previous event's [first, last] span.
    # We keep the widest span (earliest first, latest last) and the first phrase as the label.
    raw_events.sort(key=lambda e: flat[e[0]][0])
    merged_events: list[tuple[int, int, str]] = []
    for first_idx, last_idx, phrase in raw_events:
        t_first = flat[first_idx][0]
        t_last = flat[last_idx][0]
        if merged_events:
            prev_first, prev_last, prev_phrase = merged_events[-1]
            prev_t_first = flat[prev_first][0]
            prev_t_last = flat[prev_last][0]
            # Nested or overlapping with prior retake span
            if (prev_t_first - 1.0 <= t_first <= prev_t_last + 3.0 or
                prev_t_first - 1.0 <= t_last <= prev_t_last + 3.0):
                merged_events[-1] = (
                    min(prev_first, first_idx, key=lambda i: flat[i][0]),
                    max(prev_last, last_idx, key=lambda i: flat[i][0]),
                    prev_phrase,
                )
                continue
        merged_events.append((first_idx, last_idx, phrase))

    # Emit paired START + KEEPER markers
    out: list[Segment] = []
    for first_idx, last_idx, phrase in merged_events:
        t_first = flat[first_idx][0]
        t_last = flat[last_idx][0]
        out.append(Segment(
            start=round(t_first, 3),
            end=round(t_first, 3),
            type="retake_start",
            text=f'"{phrase}"',
            source="whisper",
        ))
        out.append(Segment(
            start=round(t_last, 3),
            end=round(t_last, 3),
            type="retake_keeper",
            text=f'"{phrase}" (cut to here)',
            source="whisper",
        ))

    return out


def detect_freezes(video_path: Path, min_freeze_s: float = 3.0, noise: float = 0.003) -> list[Segment]:
    """ffmpeg freezedetect: find static-screen sections in the video."""
    if video_path.suffix.lower() == ".wav":
        return []
    cmd = [
        FFMPEG, "-i", str(video_path),
        "-vf", f"freezedetect=n={noise}:d={min_freeze_s}",
        "-map", "0:v:0",
        "-f", "null", "-",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    stderr = res.stderr

    starts = [float(m.group(1)) for m in re.finditer(r"freeze_start:\s*([\d.]+)", stderr)]
    ends_durs = [
        (float(m.group(1)), float(m.group(2)))
        for m in re.finditer(r"freeze_end:\s*([\d.]+)\s*\|\s*freeze_duration:\s*([\d.]+)", stderr)
    ]

    out: list[Segment] = []
    for (s, (e, d)) in zip(starts, ends_durs):
        out.append(Segment(start=round(s, 3), end=round(e, 3), type="static", text=f"{d:.1f}s static screen", source="ffmpeg"))
    print(f"[freeze] {len(out)} static-screen sections >= {min_freeze_s}s", file=sys.stderr)
    return out


def detect_silences(wav_path: Path, min_silence_s: float = 2.0, noise_db: int = -30) -> list[Segment]:
    """ffmpeg silencedetect: returns long-silence ranges (potential breaths/pauses)."""
    cmd = [
        FFMPEG, "-i", str(wav_path),
        "-af", f"silencedetect=noise={noise_db}dB:d={min_silence_s}",
        "-f", "null", "-",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    stderr = res.stderr

    starts = [float(m.group(1)) for m in re.finditer(r"silence_start:\s*([\d.]+)", stderr)]
    ends_durs = [
        (float(m.group(1)), float(m.group(2)))
        for m in re.finditer(r"silence_end:\s*([\d.]+)\s*\|\s*silence_duration:\s*([\d.]+)", stderr)
    ]

    out: list[Segment] = []
    for (s, (e, d)) in zip(starts, ends_durs):
        if d < min_silence_s:
            continue
        out.append(Segment(start=round(s, 3), end=round(e, 3), type="silence", text=f"{d:.2f}s gap", source="ffmpeg"))
    print(f"[silence] {len(out)} gaps >= {min_silence_s}s", file=sys.stderr)
    return out


def detect_panns(wav_path: Path, threshold: float = 0.15, window_s: float = 1.0) -> list[Segment]:
    """PANNs CNN14 audio tagging to spot coughs / throat clears / breaths."""
    try:
        import numpy as np
        import librosa
        from panns_inference import AudioTagging, labels
    except Exception as e:
        print(f"[panns] import failed: {e}. Skipping.", file=sys.stderr)
        return []

    print("[panns] loading model (CNN14, cpu)...", file=sys.stderr)
    at = AudioTagging(checkpoint_path=None, device="cpu")

    print("[panns] loading audio at 32 kHz...", file=sys.stderr)
    audio, sr = librosa.load(str(wav_path), sr=32000, mono=True)

    win = int(window_s * sr)
    hop = win // 2
    out: list[Segment] = []
    total_windows = max(1, (len(audio) - win) // hop + 1)
    label_to_idx = {lab: i for i, lab in enumerate(labels)}
    interest_idx = {label_to_idx[lab]: kind for lab, kind in PANNS_LABELS_OF_INTEREST.items() if lab in label_to_idx}

    print(f"[panns] scanning {total_windows} windows of {window_s}s (hop {window_s/2}s)...", file=sys.stderr)
    for i in range(total_windows):
        chunk = audio[i*hop : i*hop + win]
        if len(chunk) < win:
            chunk = np.pad(chunk, (0, win - len(chunk)))
        clipwise, _ = at.inference(chunk[None, :])
        scores = clipwise[0]
        for idx, kind in interest_idx.items():
            score = float(scores[idx])
            if score >= threshold:
                start = round(i * hop / sr, 3)
                end = round(start + window_s, 3)
                out.append(Segment(start=start, end=end, type=kind, confidence=round(score, 3), source="panns"))

    out = merge_adjacent(out, max_gap_s=0.25)
    print(f"[panns] {len(out)} events (after merge)", file=sys.stderr)
    return out


def merge_adjacent(segs: list[Segment], max_gap_s: float = 0.25) -> list[Segment]:
    """Merge same-type segments that touch or overlap."""
    if not segs:
        return segs
    segs = sorted(segs, key=lambda s: (s.type, s.start))
    merged: list[Segment] = []
    for s in segs:
        if merged and merged[-1].type == s.type and s.start - merged[-1].end <= max_gap_s:
            merged[-1].end = max(merged[-1].end, s.end)
            if s.confidence is not None and (merged[-1].confidence is None or s.confidence > merged[-1].confidence):
                merged[-1].confidence = s.confidence
        else:
            merged.append(s)
    return merged


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--skip-panns", action="store_true", help="Skip PANNs cough/breath detector")
    ap.add_argument("--keep-wav", action="store_true")
    args = ap.parse_args()

    if not args.input.exists():
        print(f"input not found: {args.input}", file=sys.stderr)
        return 2

    out_path = args.out or args.input.with_suffix(".segments.json")

    tmpdir = Path(tempfile.mkdtemp(prefix="camtasia_ae_"))
    try:
        wav = tmpdir / "audio.wav"
        if args.input.suffix.lower() == ".wav":
            shutil.copy2(args.input, wav)
        else:
            print(f"[ffmpeg] extracting audio -> {wav}", file=sys.stderr)
            extract_wav(args.input, wav)

        all_segs: list[Segment] = []
        all_segs += detect_fillers_whisper(wav)
        all_segs += detect_silences(wav)
        all_segs += detect_freezes(args.input)
        if not args.skip_panns:
            all_segs += detect_panns(wav)

        all_segs.sort(key=lambda s: s.start)
        out_path.write_text(json.dumps([asdict(s) for s in all_segs], indent=2), encoding="utf-8")

        by_type: dict[str, int] = {}
        for s in all_segs:
            by_type[s.type] = by_type.get(s.type, 0) + 1
        print(f"\nWrote {len(all_segs)} segments to {out_path}")
        for k, v in sorted(by_type.items()):
            print(f"  {k}: {v}")

        if args.keep_wav:
            kept = out_path.with_suffix(".wav")
            shutil.copy2(wav, kept)
            print(f"  audio kept at {kept}")

        return 0
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
