#!/usr/bin/env python3
"""Generate an arcade-style goal counter preview for the 50-goal video."""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VIDEO_DIR = ROOT / "static" / "videos" / "tacbfp" / "arm"
INPUT_VIDEO = VIDEO_DIR / "50_goals.mp4"
ASS_PATH = VIDEO_DIR / "50_goals_goal_counter.ass"
OUTPUT_VIDEO = VIDEO_DIR / "50_goals_goal_counter_preview.mp4"

VIDEO_DURATION = 92.763
MAX_GOALS = 50

# Times are in seconds:frames at 60 fps, following the user's notation.
GOAL_TIMES = [
    "6:00",
    "8:20",
    "9:12",
    "10:05",
    "12:07",
    "12:27",
    "14:16",
    "16:00",
    "17:10",
    "18:10",
    "22:16",
    "25:06",
    "26:20",
    "28:09",
    "29:13",
    "29:29",
    "32:20",
    "33:26",
    "36:00",
    "37:21",
    "39:04",
    "45:10",
    "47:03",
    "47:29",
    "49:15",
    "50:13",
    "51:08",
    "52:24",
    "54:03",
    "55:04",
    "55:27",
    "57:06",
    "59:05",
    "61:03",
    "62:28",
    "64:15",
    "65:20",
    "66:20",
    "70:10",
    "71:23",
    "75:20",
    "77:20",
    "81:00",
    "84:05",
    "85:18",
    "86:20",
    "88:00",
    "88:20",
    "91:15",
    "92:00",
]


def parse_time(value: str) -> float:
    seconds, frames = value.split(":")
    return int(seconds) + int(frames) / 60.0


def ass_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centiseconds = int(round((seconds - int(seconds)) * 100))
    if centiseconds == 100:
        secs += 1
        centiseconds = 0
    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"


def plural_goal(count: int) -> str:
    return "GOAL!" if count == 1 else "GOALS!"


def build_ass(goal_seconds: list[float]) -> str:
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1600
PlayResY: 912
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Arcade,DejaVu Sans,86,&H003BD4FF,&H000000FF,&H00161616,&H66000000,1,0,0,0,100,100,1,0,1,7,5,8,30,30,80,1
Style: Scoreboard,DejaVu Sans,42,&H00FFFFFF,&H000000FF,&H00161616,&H99000000,1,0,0,0,100,100,0,0,3,8,0,9,30,48,34,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    events: list[str] = []
    for idx, start in enumerate(goal_seconds, start=1):
        next_start = goal_seconds[idx] if idx < len(goal_seconds) else VIDEO_DURATION
        scoreboard_end = min(VIDEO_DURATION, next_start)
        pop_end = min(VIDEO_DURATION, start + 1.10)

        # Persistent counter until the next goal.
        events.append(
            "Dialogue: 0,{start},{end},Scoreboard,,0,0,0,,"
            "{{\\an9\\pos(1540,48)}}GOALS {idx}/{total}".format(
                start=ass_time(start),
                end=ass_time(scoreboard_end),
                idx=idx,
                total=MAX_GOALS,
            )
        )

        # Arcade pop-up with a scale-up and settle animation.
        events.append(
            "Dialogue: 1,{start},{end},Arcade,,0,0,0,,"
            "{{\\an8\\pos(800,120)\\fad(35,320)\\fscx65\\fscy65"
            "\\t(0,180,\\fscx142\\fscy142)\\t(180,520,\\fscx100\\fscy100)}}"
            "{idx} {label}".format(
                start=ass_time(start),
                end=ass_time(pop_end),
                idx=idx,
                label=plural_goal(idx),
            )
        )

    return header + "\n".join(events) + "\n"


def main() -> None:
    if not INPUT_VIDEO.exists():
        raise FileNotFoundError(INPUT_VIDEO)

    goal_times = sorted(parse_time(t) for t in GOAL_TIMES)
    if len(goal_times) != MAX_GOALS:
        raise ValueError(f"Expected {MAX_GOALS} goal timestamps, got {len(goal_times)}")

    ASS_PATH.write_text(build_ass(goal_times), encoding="utf-8")

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(INPUT_VIDEO),
        "-vf",
        f"ass={ASS_PATH}",
        "-c:v",
        "libx264",
        "-crf",
        "18",
        "-preset",
        "medium",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "copy",
        str(OUTPUT_VIDEO),
    ]
    subprocess.run(cmd, check=True)
    print(f"Wrote {OUTPUT_VIDEO}")


if __name__ == "__main__":
    main()
