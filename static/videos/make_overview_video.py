#!/usr/bin/env python3
"""Build a sub-60-second academic overview video for the TacBFP project page.

The script expects the videos referenced by index.html to exist under:
  static/videos/tacbfp/

It uses ffmpeg/ffprobe only, so it does not require moviepy or OpenCV.
Run from the project-page root:

  python static/videos/make_overview_video.py

Optional:
  python static/videos/make_overview_video.py --update-index

The output is:
  static/videos/tacbfp/overview_tacbfp.mp4
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VIDEO_ROOT = ROOT / "static" / "videos" / "tacbfp"
OUTPUT = VIDEO_ROOT / "overview_tacbfp.mp4"
FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
WIDTH = 1920
HEIGHT = 1080
FPS = 30


@dataclass(frozen=True)
class ClipSpec:
    rel_path: str
    caption: str
    seconds: float
    speed: float = 1.25
    start_frac: float = 0.15
    x_focus: float = 0.50


@dataclass(frozen=True)
class GridSpec:
    clips: tuple[ClipSpec, ...]
    caption: str
    seconds: float
    rows: int
    cols: int
    subcaption: str | None = None


TIMELINE: list[ClipSpec | GridSpec] = [
    ClipSpec(
        "sim/multi_sphere.mp4",
        "Stage 1: multi-scale sphere specialists teach reusable contact behavior",
        4.0,
        speed=7.5,
        start_frac=0.10,
    ),
    GridSpec(
        clips=(
            ClipSpec("sim/a2a_block03.mp4", "block_03", 7.0, speed=2.0, start_frac=0.12, x_focus=0.86),
            ClipSpec("sim/a2a_block05.mp4", "block_05", 7.0, speed=2.0, start_frac=0.12, x_focus=0.86),
            ClipSpec("sim/a2a_bottle01.mp4", "bottle_01", 7.0, speed=2.0, start_frac=0.12, x_focus=0.86),
            ClipSpec("sim/a2a_cube.mp4", "corner block", 7.0, speed=2.0, start_frac=0.12, x_focus=0.86),
            ClipSpec("sim/a2a_fruit02.mp4", "fruit_02", 7.0, speed=2.0, start_frac=0.12, x_focus=0.86),
            ClipSpec("sim/a2a_trashcan02.mp4", "trash_can_02", 7.0, speed=2.0, start_frac=0.12, x_focus=0.86),
        ),
        caption="Downstream residual latent control transfers to diverse object geometries",
        subcaption="A compact residual latent action adapts the tactile prior to anisotropic shapes and harder contacts",
        seconds=7.0,
        rows=2,
        cols=3,
    ),
    ClipSpec(
        "sim/multi_type.mp4",
        "One prior-centered interface supports multi-object downstream rotation",
        4.0,
        speed=3.5,
        start_frac=0.12,
        x_focus=0.15,
    ),
    GridSpec(
        clips=(
            ClipSpec("sim/axis_condition/block_03.mp4", "block_03", 8.0, speed=6.5, start_frac=0.00, x_focus=0.500),
            ClipSpec("sim/axis_condition/block_08.mp4", "block_08", 8.0, speed=6.5, start_frac=0.00, x_focus=0.500),
            ClipSpec("sim/axis_condition/block_14.mp4", "block_14", 8.0, speed=6.5, start_frac=0.00, x_focus=0.500),
            ClipSpec("sim/axis_condition/bottle_02.mp4", "bottle_02", 8.0, speed=6.5, start_frac=0.00, x_focus=0.500),
            ClipSpec("sim/axis_condition/corner_block.mp4", "corner block", 8.0, speed=6.5, start_frac=0.00, x_focus=0.500),
            ClipSpec("sim/axis_condition/strawberry.mp4", "strawberry", 8.0, speed=6.5, start_frac=0.00, x_focus=0.500),
        ),
        caption="Continuous axis-command control in simulation",
        subcaption="The same tactile prior follows scheduled +x/-x/+y/-y/+z/-z commands across objects",
        seconds=8.0,
        rows=2,
        cols=3,
    ),
    GridSpec(
        clips=(
            ClipSpec("real/axis/small_tennis_axis.mp4", "small tennis", 7.0, speed=4.0, start_frac=0.08, x_focus=0.15),
            ClipSpec("real/axis/middle_tennis_axis.mp4", "middle tennis", 7.0, speed=4.0, start_frac=0.08, x_focus=0.15),
            ClipSpec("real/axis/tennis_axis.mp4", "standard tennis", 7.0, speed=4.0, start_frac=0.08, x_focus=0.15),
            ClipSpec("real/axis/corner_block_axis.mp4", "corner block", 7.0, speed=4.0, start_frac=0.05, x_focus=0.15),
            ClipSpec("real/axis/multiface_axis.mp4", "multiface", 7.0, speed=4.0, start_frac=0.08, x_focus=0.15),
            ClipSpec("real/axis/strawberry_axis.mp4", "strawberry", 7.0, speed=3.4, start_frac=0.08, x_focus=0.15),
        ),
        caption="Continuous axis-command control on the real robot",
        subcaption="TacBFP maintains reusable tactile behavior across objects with different size and compliance",
        seconds=7.0,
        rows=2,
        cols=3,
    ),
    GridSpec(
        clips=(
            ClipSpec("real/comparison/processed/clips/multiface_pos_x_ours.mp4", "TacBFP +x", 6.0, speed=1.4, start_frac=0.0, x_focus=0.0),
            ClipSpec("real/comparison/processed/clips/multiface_pos_x_notac.mp4", "No tactile +x", 6.0, speed=1.4, start_frac=0.0, x_focus=0.0),
            ClipSpec("real/comparison/processed/clips/multiface_pos_x_scratch.mp4", "From scratch +x", 6.0, speed=1.4, start_frac=0.0, x_focus=0.0),
            ClipSpec("real/comparison/processed/clips/multiface_pos_y_ours.mp4", "TacBFP +y", 6.0, speed=1.4, start_frac=0.0, x_focus=0.0),
            ClipSpec("real/comparison/processed/clips/multiface_pos_y_notac.mp4", "No tactile +y", 6.0, speed=1.4, start_frac=0.0, x_focus=0.0),
            ClipSpec("real/comparison/processed/clips/multiface_pos_y_scratch.mp4", "From scratch +y", 6.0, speed=1.4, start_frac=0.0, x_focus=0.0),
        ),
        caption="Single-axis real-robot comparisons on the multiface object",
        subcaption="TacBFP preserves rolling contact while baselines drop, stall, or enter OOD postures",
        seconds=6.0,
        rows=2,
        cols=3,
    ),
    GridSpec(
        clips=(
            ClipSpec("real/comparison/processed/clips/multiface_neg_x_ours.mp4", "TacBFP -x", 5.0, speed=1.2, start_frac=0.0, x_focus=0.0),
            ClipSpec("real/comparison/processed/clips/multiface_neg_x_notac.mp4", "No tactile -x", 5.0, speed=1.2, start_frac=0.0, x_focus=0.0),
            ClipSpec("real/comparison/processed/clips/multiface_neg_x_scratch.mp4", "From scratch -x", 5.0, speed=1.2, start_frac=0.0, x_focus=0.0),
            ClipSpec("real/comparison/processed/clips/smalltennis_z_ours.mp4", "TacBFP tennis", 5.0, speed=1.2, start_frac=0.0, x_focus=0.0),
            ClipSpec("real/comparison/processed/clips/smalltennis_z_notac.mp4", "No tactile tennis", 5.0, speed=1.2, start_frac=0.0, x_focus=0.0),
            ClipSpec("real/comparison/processed/clips/smalltennis_z_scratch.mp4", "From scratch tennis", 5.0, speed=1.2, start_frac=0.0, x_focus=0.0),
        ),
        caption="Single-axis comparison on challenging real contact regimes",
        subcaption="Small objects and faceted contacts expose slow, stuck, and drop failure modes",
        seconds=5.0,
        rows=2,
        cols=3,
    ),
]


def run(cmd: list[str]) -> None:
    print("[run]", " ".join(cmd))
    subprocess.run(cmd, check=True)


def check_tools() -> None:
    missing = [tool for tool in ("ffmpeg", "ffprobe") if shutil.which(tool) is None]
    if missing:
        raise SystemExit(f"Missing required command(s): {', '.join(missing)}")


def ffprobe_duration(path: Path) -> float:
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(proc.stdout)
    return float(data["format"]["duration"])


def ffmpeg_escape_text(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace(",", "\\,")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )


def drawtext_filter(text: str, y: str, fontsize: int, color: str = "white") -> str:
    font_part = f"fontfile={FONT}:" if FONT.exists() else ""
    return (
        "drawtext="
        f"{font_part}"
        f"text='{ffmpeg_escape_text(text)}':"
        "x=70:"
        f"y={y}:"
        f"fontsize={fontsize}:"
        f"fontcolor={color}:"
        "shadowcolor=black@0.55:"
        "shadowx=2:"
        "shadowy=2"
    )


def normalize_chain(duration: float, x_focus: float = 0.5, caption: str | None = None) -> str:
    filters = [
        f"fps={FPS}",
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase",
        f"crop={WIDTH}:{HEIGHT}:x='(iw-ow)*{x_focus:.3f}':y='(ih-oh)/2'",
        "setsar=1",
        "format=yuv420p",
        "fade=t=in:st=0:d=0.25",
        f"fade=t=out:st={max(duration - 0.35, 0):.3f}:d=0.35",
    ]
    if caption:
        filters.extend(
            [
                "drawbox=x=0:y=ih-175:w=iw:h=175:color=black@0.44:t=fill",
                drawtext_filter(caption, "h-118", 44),
            ]
        )
    return ",".join(filters)


def tile_chain(tile_w: int, tile_h: int, label: str | None = None, x_focus: float = 0.5) -> str:
    filters = [
        f"fps={FPS}",
        f"scale={tile_w}:{tile_h}:force_original_aspect_ratio=increase",
        f"crop={tile_w}:{tile_h}:x='(iw-ow)*{x_focus:.3f}':y='(ih-oh)/2'",
        "setsar=1",
        "format=yuv420p",
    ]
    if label:
        filters.extend(
            [
                "drawbox=x=0:y=0:w=iw:h=58:color=black@0.36:t=fill",
                drawtext_filter(label, "16", 28),
            ]
        )
    return ",".join(filters)


def make_title_segment(path: Path, duration: float) -> None:
    subtitle = "Tactile-conditioned Behavior Foundation Prior for Dexterous Reorientation"
    filter_complex = (
        f"color=c=#f8fbff:s={WIDTH}x{HEIGHT}:r={FPS}:d={duration},format=yuv420p,"
        "drawbox=x=0:y=0:w=iw:h=ih:color=white@0.0:t=fill,"
        + drawtext_filter("Tac", "(h/2)-95", 96, "#FF7A1A")
        + ","
        + drawtext_filter("BFP", "(h/2)-95", 96, "#3A8DDE").replace("x=70", "x=255")
        + ","
        + drawtext_filter(subtitle, "(h/2)+25", 42, "#18324a")
        + ","
        + drawtext_filter("Distill contact behavior once; reuse it as a latent action interface", "(h/2)+92", 34, "#475569")
        + ",fade=t=in:st=0:d=0.3,"
        f"fade=t=out:st={duration - 0.35:.3f}:d=0.35"
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=#f8fbff:s={WIDTH}x{HEIGHT}:r={FPS}:d={duration}",
            "-vf",
            filter_complex.split(",", 1)[1],
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ]
    )


def make_clip_segment(spec: ClipSpec, index: int, tmp: Path) -> Path:
    src = VIDEO_ROOT / spec.rel_path
    total = ffprobe_duration(src)
    source_need = spec.seconds * spec.speed
    max_start = max(total - source_need - 0.05, 0.0)
    start = min(max(total * spec.start_frac, 0.0), max_start)
    source_duration = min(source_need, max(total - start, 0.2))
    output_duration = source_duration / spec.speed
    if output_duration <= 0.3:
        raise RuntimeError(f"Video is too short for overview segment: {src}")

    out = tmp / f"segment_{index:02d}.mp4"
    vf = (
        f"setpts=PTS/{spec.speed:.4f},"
        + normalize_chain(output_duration, x_focus=spec.x_focus, caption=spec.caption)
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{start:.3f}",
            "-t",
            f"{source_duration:.3f}",
            "-i",
            str(src),
            "-vf",
            vf,
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            str(out),
        ]
    )
    return out


def make_tile_segment(spec: ClipSpec, index: int, tmp: Path, tile_w: int, tile_h: int, seconds: float) -> Path:
    src = VIDEO_ROOT / spec.rel_path
    total = ffprobe_duration(src)
    source_need = seconds * spec.speed
    if total + 0.05 < source_need:
        raise RuntimeError(
            f"Grid tile source is too short and would freeze: {src} "
            f"needs {source_need:.2f}s at {spec.speed:.2f}x for {seconds:.2f}s output, "
            f"but has {total:.2f}s."
        )
    max_start = max(total - source_need - 0.05, 0.0)
    start = min(max(total * spec.start_frac, 0.0), max_start)
    source_duration = min(source_need, max(total - start, 0.2))
    out = tmp / f"tile_{index:02d}.mp4"
    vf = f"setpts=PTS/{spec.speed:.4f}," + tile_chain(tile_w, tile_h, label=spec.caption, x_focus=spec.x_focus)
    run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{start:.3f}",
            "-t",
            f"{source_duration:.3f}",
            "-i",
            str(src),
            "-vf",
            vf,
            "-an",
            "-t",
            f"{seconds:.3f}",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            str(out),
        ]
    )
    return out


def make_grid_segment(spec: GridSpec, index: int, tmp: Path) -> Path:
    if len(spec.clips) > spec.rows * spec.cols:
        raise ValueError("Grid has more clips than cells.")
    tile_w = WIDTH // spec.cols
    tile_h = HEIGHT // spec.rows
    tiles = [
        make_tile_segment(clip, index * 10 + tile_idx, tmp, tile_w, tile_h, spec.seconds)
        for tile_idx, clip in enumerate(spec.clips)
    ]
    out = tmp / f"segment_{index:02d}_grid.mp4"
    inputs: list[str] = []
    for tile in tiles:
        inputs.extend(["-i", str(tile)])

    positions = []
    for i in range(len(tiles)):
        row = i // spec.cols
        col = i % spec.cols
        positions.append(f"{col * tile_w}_{row * tile_h}")

    xstack = f"xstack=inputs={len(tiles)}:layout={'|'.join(positions)}:fill=black"
    overlay = [
        xstack,
        "format=yuv420p",
        "drawbox=x=0:y=0:w=iw:h=ih:color=white@0.42:t=4",
    ]
    for col in range(1, spec.cols):
        x = col * tile_w
        overlay.append(f"drawbox=x={x - 3}:y=0:w=6:h=ih:color=white@0.58:t=fill")
    for row in range(1, spec.rows):
        y = row * tile_h
        overlay.append(f"drawbox=x=0:y={y - 3}:w=iw:h=6:color=white@0.58:t=fill")
    overlay.extend(
        [
        "drawbox=x=0:y=ih-190:w=iw:h=190:color=black@0.46:t=fill",
        drawtext_filter(spec.caption, "h-132", 42),
        ]
    )
    if spec.subcaption:
        overlay.append(drawtext_filter(spec.subcaption, "h-72", 32, "#dbeafe"))
    overlay.extend(
        [
            "fade=t=in:st=0:d=0.25",
            f"fade=t=out:st={max(spec.seconds - 0.35, 0):.3f}:d=0.35",
        ]
    )
    run(
        [
            "ffmpeg",
            "-y",
            *inputs,
            "-filter_complex",
            ",".join(overlay),
            "-an",
            "-t",
            f"{spec.seconds:.3f}",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            str(out),
        ]
    )
    return out


def make_outro_segment(path: Path, duration: float) -> None:
    text1 = "TacBFP"
    text2 = "A tactile-conditioned prior for reusable dexterous manipulation"
    vf = (
        f"format=yuv420p,"
        + drawtext_filter("Tac", "(h/2)-70", 92, "#FF7A1A")
        + ","
        + drawtext_filter("BFP", "(h/2)-70", 92, "#3A8DDE").replace("x=70", "x=255")
        + ","
        + drawtext_filter(text2, "(h/2)+45", 40, "#18324a")
        + ","
        + drawtext_filter("prior-centered residual latent control", "(h/2)+108", 34, "#475569")
        + ",fade=t=in:st=0:d=0.25,"
        f"fade=t=out:st={duration - 0.35:.3f}:d=0.35"
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=#ffffff:s={WIDTH}x{HEIGHT}:r={FPS}:d={duration}",
            "-vf",
            vf,
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ]
    )


def concat_segments(segments: list[Path], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    list_file = output.parent / ".overview_concat.txt"
    list_file.write_text(
        "\n".join(f"file '{segment.as_posix()}'" for segment in segments) + "\n",
        encoding="utf-8",
    )
    try:
        run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file),
                "-c",
                "copy",
                str(output),
            ]
        )
    finally:
        list_file.unlink(missing_ok=True)


def update_index_html(output: Path) -> None:
    index_path = ROOT / "index.html"
    rel = "./" + output.relative_to(ROOT).as_posix()
    html = index_path.read_text(encoding="utf-8")
    old = './static/videos/tacbfp/sim/multi_sphere.mp4'
    if old not in html:
        print("[warn] Could not find original teaser source in index.html; leaving it unchanged.")
        return
    html = html.replace(old, rel, 1)
    index_path.write_text(html, encoding="utf-8")
    print(f"[ok] Updated first teaser video in index.html -> {rel}")


def iter_required_clips(items: list[ClipSpec | GridSpec]) -> list[ClipSpec]:
    clips: list[ClipSpec] = []
    for item in items:
        if isinstance(item, ClipSpec):
            clips.append(item)
        else:
            clips.extend(item.clips)
    return clips


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--update-index", action="store_true")
    parser.add_argument(
        "--skip-missing",
        action="store_true",
        help="Use available clips only. By default, missing clips abort the render.",
    )
    args = parser.parse_args()

    check_tools()
    required = iter_required_clips(TIMELINE)
    missing = [VIDEO_ROOT / spec.rel_path for spec in required if not (VIDEO_ROOT / spec.rel_path).exists()]
    if missing and not args.skip_missing:
        print("[error] Missing required overview source videos:", file=sys.stderr)
        for path in missing:
            print(f"  - {path}", file=sys.stderr)
        print("\nPlace the videos under static/videos/tacbfp/ or rerun with --skip-missing.", file=sys.stderr)
        return 2

    available: list[ClipSpec | GridSpec] = []
    for item in TIMELINE:
        if isinstance(item, ClipSpec):
            if (VIDEO_ROOT / item.rel_path).exists():
                available.append(item)
        else:
            present = tuple(clip for clip in item.clips if (VIDEO_ROOT / clip.rel_path).exists())
            if present:
                available.append(
                    GridSpec(
                        clips=present,
                        caption=item.caption,
                        seconds=item.seconds,
                        rows=item.rows,
                        cols=item.cols,
                        subcaption=item.subcaption,
                    )
                )
    if not available:
        print("[error] No source videos are available; cannot build overview.", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="tacbfp_overview_") as tmp_name:
        tmp = Path(tmp_name)
        segments: list[Path] = []
        intro = tmp / "segment_00_intro.mp4"
        make_title_segment(intro, 2.5)
        segments.append(intro)

        for i, item in enumerate(available, start=1):
            if isinstance(item, ClipSpec):
                segments.append(make_clip_segment(item, i, tmp))
            else:
                segments.append(make_grid_segment(item, i, tmp))

        outro = tmp / "segment_99_outro.mp4"
        make_outro_segment(outro, 2.5)
        segments.append(outro)

        concat_segments(segments, args.output)

    duration = ffprobe_duration(args.output)
    print(f"[ok] Wrote {args.output} ({duration:.2f}s)")
    if duration > 60.0:
        print("[warn] Output is longer than 60s. Reduce segment durations in TIMELINE.", file=sys.stderr)
    if args.update_index:
        update_index_html(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
