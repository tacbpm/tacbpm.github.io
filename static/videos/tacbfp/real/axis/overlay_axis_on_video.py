import argparse
import json
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = ROOT / "corner_block_axis_segments.json"

AXIS_COLORS = {
    "x": (230, 40, 38, 255),
    "y": (34, 170, 76, 255),
    "z": (48, 92, 235, 255),
}
ROTATION_COLOR = (0, 0, 0, 255)
DARK = (15, 23, 42, 255)

START_ANGLES = {
    ("x", 1): -115,
    ("x", -1): 135,
    ("y", 1): -145,
    ("y", -1): 105,
    ("z", 1): -35,
    ("z", -1): 215,
}
FRONT_SIGN = {"x": -1, "y": -1, "z": 1}


def load_font(size):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    except OSError:
        return ImageFont.load_default()


def add(point, vector, scale=1.0):
    return (point[0] + vector[0] * scale, point[1] + vector[1] * scale)


def norm(vector):
    length = math.hypot(vector[0], vector[1])
    return (vector[0] / length, vector[1] / length) if length else (1, 0)


def angle_between(start, end):
    return math.atan2(end[1] - start[1], end[0] - start[0])


def text_center(draw, xy, text, font, color):
    bbox = draw.textbbox((0, 0), text, font=font)
    draw.text(
        (xy[0] - (bbox[2] - bbox[0]) / 2, xy[1] - (bbox[3] - bbox[1]) / 2),
        text,
        font=font,
        fill=color,
    )


def sharp_arrow(draw, start, tip, color, width, head_len=16, head_half=5):
    angle = angle_between(start, tip)
    base = (
        tip[0] - head_len * math.cos(angle),
        tip[1] - head_len * math.sin(angle),
    )
    draw.line([start, base], fill=color, width=width)
    normal = (-math.sin(angle), math.cos(angle))
    draw.polygon(
        [
            tip,
            (base[0] + head_half * normal[0], base[1] + head_half * normal[1]),
            (base[0] - head_half * normal[0], base[1] - head_half * normal[1]),
        ],
        fill=color,
    )


def ellipse_basis(axis_name, axes):
    axis_unit = norm(axes[axis_name]["vec"])
    major_unit = (-axis_unit[1], axis_unit[0])
    return major_unit, axis_unit


def ellipse_point(cx, cy, major, minor, major_unit, axis_unit, degrees):
    theta = math.radians(degrees)
    return (
        cx + major * math.cos(theta) * major_unit[0] + minor * math.sin(theta) * axis_unit[0],
        cy + major * math.cos(theta) * major_unit[1] + minor * math.sin(theta) * axis_unit[1],
    )


def ellipse_tangent(major, minor, major_unit, axis_unit, degrees, direction):
    theta = math.radians(degrees)
    dx = -major * math.sin(theta) * major_unit[0] + minor * math.cos(theta) * axis_unit[0]
    dy = -major * math.sin(theta) * major_unit[1] + minor * math.cos(theta) * axis_unit[1]
    if direction < 0:
        dx, dy = -dx, -dy
    return math.atan2(dy, dx)


def depth_value(degrees):
    return math.sin(math.radians(degrees))


def parse_direction(direction):
    direction = direction.strip().lower()
    if len(direction) != 2 or direction[0] not in "+-" or direction[1] not in "xyz":
        raise ValueError(f"Invalid direction {direction!r}; expected one of +x, -x, +y, -y, +z, -z.")
    return direction[1], 1 if direction[0] == "+" else -1


class AxisOverlayRenderer:
    def __init__(self, width=230, height=170, scale=4, visual_scale=None):
        self.width = width
        self.height = height
        self.scale = scale
        self.visual_scale = visual_scale if visual_scale is not None else min(width / 230, height / 170)
        self.unit = scale * self.visual_scale
        self.canvas_size = (width * scale, height * scale)
        self.panel = (0, 0, width * scale, height * scale)
        self.origin = (width * scale * 0.50, height * scale * 0.50)
        self.axes = {
            "z": {
                "vec": (-52 * self.unit, 0 * self.unit),
                "color": AXIS_COLORS["z"],
                "label": "+z",
            },
            "y": {
                "vec": (0 * self.unit, -48 * self.unit),
                "color": AXIS_COLORS["y"],
                "label": "+y",
            },
            "x": {
                "vec": (40 * self.unit, 28 * self.unit),
                "color": AXIS_COLORS["x"],
                "label": "+x",
            },
        }
        self.axis_font = load_font(round(14 * self.unit))
        self.vector_font = load_font(round(14 * self.unit))

    def draw_axis(self, draw, name, highlight=False):
        axis = self.axes[name]
        sharp_arrow(
            draw,
            self.origin,
            add(self.origin, axis["vec"]),
            axis["color"],
            width=round((5 if highlight else 4) * self.unit),
            head_len=(17 if name == "x" else 16) * self.unit,
            head_half=5 * self.unit,
        )

    def draw_labels_and_origin(self, draw):
        for name, axis in self.axes.items():
            pos = add(self.origin, axis["vec"], 1.16 if name != "x" else 1.17)
            if name == "y":
                pos = add(self.origin, axis["vec"], 0.98)
            if name == "x":
                pos = (pos[0] + 5 * self.unit, pos[1] + 2 * self.unit)
            text_center(draw, pos, axis["label"], self.axis_font, axis["color"])
        radius = 4 * self.unit
        draw.ellipse(
            (
                self.origin[0] - radius,
                self.origin[1] - radius,
                self.origin[0] + radius,
                self.origin[1] + radius,
            ),
            fill=DARK,
        )

    def draw_vector_label(self, draw, text):
        y = 16 * self.unit
        bbox = draw.textbbox((0, 0), text, font=self.vector_font)
        pad = 4 * self.unit
        center_x = self.width * self.scale * 0.75
        x = center_x - bbox[2] / 2
        draw.rounded_rectangle(
            (x - pad, y - pad, x + bbox[2] + pad, y + bbox[3] + pad),
            radius=5 * self.unit,
            fill=(255, 255, 255, 214),
            outline=(30, 41, 59, 170),
            width=round(self.scale),
        )
        draw.text((x, y), text, font=self.vector_font, fill=DARK)

    def make_rotation_samples(self, axis_name, sign):
        center = add(self.origin, self.axes[axis_name]["vec"], 0.50)
        major_unit, axis_unit = ellipse_basis(axis_name, self.axes)
        major = 15 * self.unit
        minor = 7 * self.unit
        if axis_name == "x":
            major, minor = 14 * self.unit, 9 * self.unit

        start = START_ANGLES[(axis_name, sign)]
        extent = 250 * sign
        end = start + extent
        tip = ellipse_point(center[0], center[1], major, minor, major_unit, axis_unit, end)
        tangent = ellipse_tangent(
            major,
            minor,
            major_unit,
            axis_unit,
            end,
            1 if extent > 0 else -1,
        )

        head_len = 9 * self.unit
        head_half = 3.4 * self.unit
        base = (
            tip[0] - head_len * math.cos(tangent),
            tip[1] - head_len * math.sin(tangent),
        )
        theta = math.radians(end)
        local_speed = math.hypot(-major * math.sin(theta), minor * math.cos(theta))
        trim = math.degrees(head_len / max(local_speed, 1.0))
        arc_end = end - trim * (1 if extent > 0 else -1)

        samples = []
        for index in range(151):
            degrees = start + (arc_end - start) * index / 150
            samples.append(
                (
                    ellipse_point(
                        center[0], center[1], major, minor, major_unit, axis_unit, degrees
                    ),
                    degrees,
                )
            )
        samples.append((base, arc_end))

        normal = (-math.sin(tangent), math.cos(tangent))
        triangle = [
            tip,
            (base[0] + head_half * normal[0], base[1] + head_half * normal[1]),
            (base[0] - head_half * normal[0], base[1] - head_half * normal[1]),
        ]
        end_is_front = depth_value(end) * FRONT_SIGN[axis_name] >= 0
        return samples, triangle, end_is_front

    def draw_polyline_segments(self, draw, samples, layer, axis_name):
        for (p0, t0), (p1, t1) in zip(samples, samples[1:]):
            midpoint_t = (t0 + t1) / 2
            is_front = depth_value(midpoint_t) * FRONT_SIGN[axis_name] >= 0
            if (layer == "front" and is_front) or (layer == "back" and not is_front):
                draw.line([p0, p1], fill=ROTATION_COLOR, width=round(2 * self.unit), joint="curve")

    def draw_rotation_layer(self, draw, samples, triangle, end_is_front, axis_name, layer):
        self.draw_polyline_segments(draw, samples, layer, axis_name)
        if (layer == "front" and end_is_front) or (layer == "back" and not end_is_front):
            draw.polygon(triangle, fill=ROTATION_COLOR)

    def render_direction(self, direction, output_path):
        axis_name, sign = parse_direction(direction)
        vector_label = f"[{sign if axis_name == 'x' else 0},{sign if axis_name == 'y' else 0},{sign if axis_name == 'z' else 0}]"

        image = Image.new("RGBA", self.canvas_size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle(
            self.panel,
            radius=10 * self.scale,
            fill=(255, 255, 255, 170),
            outline=(15, 23, 42, 95),
            width=round(self.scale),
        )

        samples, triangle, end_is_front = self.make_rotation_samples(axis_name, sign)
        for name in self.axes:
            if name != axis_name:
                self.draw_axis(draw, name, highlight=False)
        self.draw_rotation_layer(draw, samples, triangle, end_is_front, axis_name, "back")
        self.draw_axis(draw, axis_name, highlight=True)
        self.draw_rotation_layer(draw, samples, triangle, end_is_front, axis_name, "front")
        self.draw_labels_and_origin(draw)
        self.draw_vector_label(draw, vector_label)

        image = image.resize((self.width, self.height), Image.Resampling.LANCZOS)
        image.save(output_path)
        return output_path


def resolve_path(base_dir, value):
    path = Path(value)
    return path if path.is_absolute() else (base_dir / path).resolve()


def build_ffmpeg_command(config_path, config, overlay_paths):
    base_dir = config_path.parent
    input_video = resolve_path(base_dir, config["input_video"])
    output_video = resolve_path(base_dir, config["output_video"])
    overlay = config.get("overlay", {})
    x = int(overlay.get("x", 28))
    y = int(overlay.get("y", 18))

    command = ["ffmpeg", "-y", "-i", str(input_video)]
    for path in overlay_paths:
        command.extend(["-i", str(path)])

    filters = []
    trim_start = config.get("trim_start")
    trim_end = config.get("trim_end")
    if trim_start is not None or trim_end is not None:
        trim_args = []
        if trim_start is not None:
            trim_args.append(f"start={float(trim_start):g}")
        if trim_end is not None:
            trim_args.append(f"end={float(trim_end):g}")
        filters.append(f"[0:v]trim={':'.join(trim_args)},setpts=PTS-STARTPTS[base]")
        current = "base"
    else:
        current = "0:v"

    for index, segment in enumerate(config["segments"], start=1):
        out_label = f"v{index}"
        start = float(segment["start"])
        end = float(segment["end"])
        enable = f"between(t\\,{start:g}\\,{end:g})"
        filters.append(f"[{current}][{index}:v]overlay={x}:{y}:enable='{enable}'[{out_label}]")
        current = out_label

    output_args = [
        "-filter_complex",
        ";".join(filters),
        "-map",
        f"[{current}]",
    ]
    if trim_start is not None or trim_end is not None:
        output_args.append("-an")
    else:
        output_args.extend(["-map", "0:a?", "-c:a", "copy"])

    output_args.extend(
        [
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "20",
            "-preset",
            "medium",
            "-movflags",
            "+faststart",
            str(output_video),
        ]
    )
    command.extend(output_args)
    return command, output_video


def render_overlays(config_path, config):
    overlay = config.get("overlay", {})
    width = int(overlay.get("width", 230))
    height = int(overlay.get("height", 170))
    visual_scale = overlay.get("visual_scale")
    renderer = AxisOverlayRenderer(
        width=width,
        height=height,
        visual_scale=float(visual_scale) if visual_scale is not None else None,
    )

    output_dir = config_path.parent / "generated_axis_overlays" / config_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)

    overlay_paths = []
    for index, segment in enumerate(config["segments"]):
        direction = segment["direction"]
        clean_direction = direction.replace("+", "pos_").replace("-", "neg_")
        output_path = output_dir / f"{index:02d}_{clean_direction}.png"
        renderer.render_direction(direction, output_path)
        overlay_paths.append(output_path)
    return overlay_paths


def main():
    parser = argparse.ArgumentParser(description="Overlay time-varying axis direction widgets onto a video.")
    parser.add_argument(
        "config",
        nargs="?",
        default=DEFAULT_CONFIG,
        type=Path,
        help="Path to a JSON segment config.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate overlays and print ffmpeg command without running it.",
    )
    args = parser.parse_args()

    config_path = args.config.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    overlay_paths = render_overlays(config_path, config)
    command, output_video = build_ffmpeg_command(config_path, config, overlay_paths)

    if args.dry_run:
        print(" ".join(command))
        return

    subprocess.run(command, check=True)
    print(output_video)


if __name__ == "__main__":
    main()
