#!/usr/bin/env python3
"""
Crea mini-fixture di test dalla parte1 di Detour per test veloci.

Genera N clip di ~2 minuti ciascuna dal video Detour_parte1.mp4
con i relativi sottotitoli EN/IT, salvandoli in Test_Subs/fixtures/.

Uso:
    python3 create_test_fixtures.py
"""

import re
import subprocess
import json
from pathlib import Path

# ─── Configurazione ───────────────────────────────────────────────────────────
FIXTURES_DIR = Path(__file__).parent / "fixtures"
SERIE_DIR = Path(__file__).parent / "SERIE_TV"
CLIP_DURATION_SECS = 120  # 2 minuti per clip
NUM_CLIPS = 5             # 5 clip = 10 minuti totali (su 23 min)


# ─── SRT Parsing ──────────────────────────────────────────────────────────────

def srt_time_to_seconds(t_str: str) -> float:
    h, m, s_ms = t_str.split(":")
    s, ms = s_ms.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def seconds_to_srt_time(seconds: float) -> str:
    total_ms = max(0, int(round(seconds * 1000)))
    h = total_ms // 3_600_000
    total_ms %= 3_600_000
    m = total_ms // 60_000
    total_ms %= 60_000
    s = total_ms // 1000
    ms = total_ms % 1000
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def parse_srt(path: Path):
    text = path.read_text(encoding="utf-8")
    text = text.replace("\r\n", "\n")

    pattern = re.compile(
        r"(\d+)\n"
        r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})\n"
        r"(.*?)(?=\n\n\d+\n|\Z)",
        re.DOTALL,
    )

    cues = []
    for match in pattern.finditer(text):
        start = srt_time_to_seconds(match.group(2))
        end = srt_time_to_seconds(match.group(3))
        body = match.group(4).strip("\n")
        cues.append((start, end, body))
    return cues


def write_srt(path: Path, cues):
    lines = []
    for idx, (start, end, body) in enumerate(cues, start=1):
        lines.append(str(idx))
        lines.append(f"{seconds_to_srt_time(start)} --> {seconds_to_srt_time(end)}")
        lines.append(body)
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def split_srt(cues, segment_start: float, segment_end: float):
    out = []
    for cue_start, cue_end, body in cues:
        overlap_start = max(cue_start, segment_start)
        overlap_end = min(cue_end, segment_end)
        if overlap_end <= overlap_start:
            continue
        local_start = overlap_start - segment_start
        local_end = overlap_end - segment_start
        out.append((local_start, local_end, body))
    return out


def split_video_ffmpeg(video_path: Path, out_path: Path, start: float, end: float):
    duration = max(0.0, end - start)
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start:.3f}",
        "-i", str(video_path),
        "-t", f"{duration:.3f}",
        "-c", "copy",
        "-an",  # niente audio per velocizzare i test
        str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def main():
    FIXTURES_DIR.mkdir(exist_ok=True)

    video_file = SERIE_DIR / "Detour_parte1.mp4"
    en_srt = SERIE_DIR / "Detour-en_parte1.srt"
    it_srt = SERIE_DIR / "Detour-it_parte1.srt"

    for f in [video_file, en_srt, it_srt]:
        if not f.exists():
            raise FileNotFoundError(f"File mancante: {f}")

    # Ottieni la durata del video
    probe_cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_file),
    ]
    result = subprocess.run(probe_cmd, check=True, capture_output=True, text=True)
    total_duration = float(result.stdout.strip())

    print(f"Video duration: {total_duration:.1f}s")
    print(f"Creating {NUM_CLIPS} clips of {CLIP_DURATION_SECS}s each...")

    en_cues = parse_srt(en_srt)
    it_cues = parse_srt(it_srt)

    manifest = {
        "source_video": str(video_file),
        "source_en_srt": str(en_srt),
        "source_it_srt": str(it_srt),
        "total_duration_secs": total_duration,
        "clip_duration_secs": CLIP_DURATION_SECS,
        "clips": [],
    }

    for i in range(NUM_CLIPS):
        seg_start = i * CLIP_DURATION_SECS
        seg_end = min((i + 1) * CLIP_DURATION_SECS, total_duration)

        if seg_start >= total_duration:
            print(f"  Clip {i+1}: skipped (beyond video duration)")
            break

        clip_name = f"clip_{i+1:02d}"
        out_video = FIXTURES_DIR / f"{clip_name}.mp4"
        out_en = FIXTURES_DIR / f"{clip_name}_en.srt"
        out_it = FIXTURES_DIR / f"{clip_name}_it.srt"

        # Video
        print(f"  Clip {i+1}: {seg_start:.0f}s - {seg_end:.0f}s -> {out_video.name}")
        split_video_ffmpeg(video_file, out_video, seg_start, seg_end)

        # SRT
        en_split = split_srt(en_cues, seg_start, seg_end)
        it_split = split_srt(it_cues, seg_start, seg_end)
        write_srt(out_en, en_split)
        write_srt(out_it, it_split)

        manifest["clips"].append({
            "name": clip_name,
            "start_secs": seg_start,
            "end_secs": seg_end,
            "video": out_video.name,
            "en_srt": out_en.name,
            "it_srt": out_it.name,
            "en_count": len(en_split),
            "it_count": len(it_split),
        })

    # Salva manifest
    manifest_path = FIXTURES_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nManifest saved to {manifest_path}")
    print(f"Total clips: {len(manifest['clips'])}")


if __name__ == "__main__":
    main()
