#!/usr/bin/env python3
"""Extract 16:9 PNG snapshots from a video at specified timestamps."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
from pathlib import Path


def parse_times(value: str) -> list[float]:
    """Accept either a JSON list like '[1.2,2,3.5]' or '1.2,2,3.5'."""
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        parsed = [item.strip() for item in value.split(",") if item.strip()]

    if not isinstance(parsed, list):
        raise argparse.ArgumentTypeError("times must be a list, e.g. '[1.2,2,3.5]'")

    try:
        times = [float(item) for item in parsed]
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("times must contain only numbers") from exc

    if any(time < 0 for time in times):
        raise argparse.ArgumentTypeError("times must be non-negative")
    return times


def require_command(command: str) -> None:
    if shutil.which(command) is None:
        raise SystemExit(f"Error: required command not found: {command}")


def probe_video_size(video_path: Path) -> tuple[int, int]:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=s=x:p=0",
            str(video_path),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    size = result.stdout.strip().splitlines()[0]
    width_text, height_text = size.split("x", maxsplit=1)
    return int(width_text), int(height_text)


def even_floor(value: float) -> int:
    return max(2, int(math.floor(value)) // 2 * 2)


def build_crop_filter(width: int, height: int, up_shift_px: int) -> str:
    target_ratio = 16 / 9
    video_ratio = width / height

    if video_ratio > target_ratio:
        crop_h = even_floor(height)
        crop_w = even_floor(crop_h * target_ratio)
    else:
        crop_w = even_floor(width)
        crop_h = even_floor(crop_w / target_ratio)

    x = max(0, (width - crop_w) // 2)
    centered_y = (height - crop_h) // 2
    y = min(max(0, centered_y - up_shift_px), height - crop_h)
    return f"crop={crop_w}:{crop_h}:{x}:{y}"


def output_name(video_path: Path, timestamp: float, index: int) -> str:
    timestamp_text = f"{timestamp:.3f}".rstrip("0").rstrip(".").replace(".", "p")
    return f"{video_path.stem}_{index:02d}_{timestamp_text}s.png"


def extract_frame(
    video_path: Path,
    timestamp: float,
    output_path: Path,
    crop_filter: str,
    overwrite: bool,
) -> None:
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(video_path),
        "-ss",
        str(timestamp),
        "-frames:v",
        "1",
        "-vf",
        crop_filter,
    ]
    if overwrite:
        command.append("-y")
    else:
        command.append("-n")
    command.append(str(output_path))

    subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract 16:9 PNG snapshots from a video at specified timestamps."
    )
    parser.add_argument("video", type=Path, help="Video path, e.g. new_adjust/cross_perturbationv2.mp4")
    parser.add_argument("times", type=parse_times, help="Timestamp list, e.g. '[1.2,2,3.5]'")
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("exp_overview"),
        help="Directory for PNG outputs. Defaults to exp_overview.",
    )
    parser.add_argument(
        "--up-shift-px",
        type=int,
        default=150,
        help="Move the centered 16:9 crop upward by this many pixels. Defaults to 38, about 1cm at 96dpi.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing PNG files.")
    args = parser.parse_args()

    require_command("ffmpeg")
    require_command("ffprobe")

    video_path = args.video.expanduser()
    output_dir = args.output_dir.expanduser()

    if not video_path.exists():
        raise SystemExit(f"Error: video not found: {video_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    width, height = probe_video_size(video_path)
    crop_filter = build_crop_filter(width, height, args.up_shift_px)

    for index, timestamp in enumerate(args.times, start=1):
        output_path = output_dir / output_name(video_path, timestamp, index)
        extract_frame(video_path, timestamp, output_path, crop_filter, args.overwrite)
        print(output_path)


if __name__ == "__main__":
    main()
