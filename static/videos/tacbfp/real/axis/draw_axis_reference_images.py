from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import math


ROOT = Path(__file__).resolve().parent
DEFAULT_FRAME = ROOT / "reference_frames" / "middle_tennis_t2.jpg"
DEFAULT_OUTPUT_DIR = ROOT / "axis_reference_images"


SCALE = 4
PANEL_PX = (28, 18, 222, 160)
AXIS_COLORS = {
    "x": (230, 40, 38),
    "y": (34, 170, 76),
    "z": (48, 92, 235),
}
ROTATION_COLOR = (0, 0, 0)
DARK = (15, 23, 42)


COMMANDS = [
    ("axis_pos_x.jpg", "x", 1, "[1,0,0]"),
    ("axis_neg_x.jpg", "x", -1, "[-1,0,0]"),
    ("axis_pos_y.jpg", "y", 1, "[0,1,0]"),
    ("axis_neg_y.jpg", "y", -1, "[0,-1,0]"),
    ("axis_pos_z.jpg", "z", 1, "[0,0,1]"),
    ("axis_neg_z.jpg", "z", -1, "[0,0,-1]"),
]

# Start angles were chosen to keep arrowheads readable and consistent with the
# requested projection: +z left, +y up, +x as a foreshortened out-of-plane arrow.
START_ANGLES = {
    ("x", 1): -115,
    ("x", -1): 135,
    ("y", 1): -145,
    ("y", -1): 105,
    ("z", 1): -35,
    ("z", -1): 215,
}

# The x/y rings need the opposite front/back convention from z under this
# projection. This determines which half of the rotation ring is drawn over the
# active axis and which half is hidden behind it.
FRONT_SIGN = {"x": -1, "y": -1, "z": 1}


def load_fonts(scale: int):
    try:
        axis_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14 * scale
        )
        vector_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14 * scale
        )
    except OSError:
        axis_font = ImageFont.load_default()
        vector_font = ImageFont.load_default()
    return axis_font, vector_font


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


def sharp_arrow(draw, start, tip, color, width, scale, head_len=16, head_half=5):
    width *= scale
    head_len *= scale
    head_half *= scale
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


class AxisReferenceRenderer:
    def __init__(self, frame_path=DEFAULT_FRAME, output_dir=DEFAULT_OUTPUT_DIR, scale=SCALE):
        self.frame_path = Path(frame_path)
        self.output_dir = Path(output_dir)
        self.scale = scale
        self.image = Image.open(self.frame_path).convert("RGB")
        self.width, self.height = self.image.size
        self.panel = tuple(value * self.scale for value in PANEL_PX)
        self.origin = (
            (self.panel[0] + self.panel[2]) / 2,
            (self.panel[1] + self.panel[3]) / 2,
        )
        self.axes = {
            "z": {"vec": (-52 * self.scale, 0 * self.scale), "color": AXIS_COLORS["z"], "label": "+z"},
            "y": {"vec": (0 * self.scale, -48 * self.scale), "color": AXIS_COLORS["y"], "label": "+y"},
            "x": {"vec": (40 * self.scale, 28 * self.scale), "color": AXIS_COLORS["x"], "label": "+x"},
        }
        self.axis_font, self.vector_font = load_fonts(self.scale)

    def draw_axis(self, draw, name, highlight=False):
        axis = self.axes[name]
        sharp_arrow(
            draw,
            self.origin,
            add(self.origin, axis["vec"]),
            axis["color"],
            width=5 if highlight else 4,
            scale=self.scale,
            head_len=17 if name == "x" else 16,
            head_half=5,
        )

    def draw_labels_and_origin(self, draw):
        for name, axis in self.axes.items():
            pos = add(self.origin, axis["vec"], 1.16 if name != "x" else 1.17)
            if name == "x":
                pos = (pos[0] + 5 * self.scale, pos[1] + 2 * self.scale)
            text_center(draw, pos, axis["label"], self.axis_font, axis["color"])
        radius = 4 * self.scale
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
        x, y = 142 * self.scale, 34 * self.scale
        bbox = draw.textbbox((0, 0), text, font=self.vector_font)
        pad = 4 * self.scale
        draw.rounded_rectangle(
            (x - pad, y - pad, x + bbox[2] + pad, y + bbox[3] + pad),
            radius=5 * self.scale,
            fill=(255, 255, 255, 214),
            outline=(30, 41, 59, 170),
            width=self.scale,
        )
        draw.text((x, y), text, font=self.vector_font, fill=DARK)

    def make_rotation_samples(self, axis_name, sign):
        center = add(self.origin, self.axes[axis_name]["vec"], 0.50)
        major_unit, axis_unit = ellipse_basis(axis_name, self.axes)
        major = 15 * self.scale
        minor = 7 * self.scale
        if axis_name == "x":
            major, minor = 14 * self.scale, 9 * self.scale

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

        head_len = 9 * self.scale
        head_half = 3.4 * self.scale
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
                draw.line([p0, p1], fill=ROTATION_COLOR, width=2 * self.scale, joint="curve")

    def draw_rotation_layer(self, draw, samples, triangle, end_is_front, axis_name, layer):
        self.draw_polyline_segments(draw, samples, layer, axis_name)
        if (layer == "front" and end_is_front) or (layer == "back" and not end_is_front):
            draw.polygon(triangle, fill=ROTATION_COLOR)

    def render_one(self, filename, axis_name, sign, vector_label):
        img = self.image.resize(
            (self.width * self.scale, self.height * self.scale),
            Image.Resampling.LANCZOS,
        ).convert("RGBA")
        overlay = Image.new("RGBA", (self.width * self.scale, self.height * self.scale), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rounded_rectangle(
            self.panel,
            radius=10 * self.scale,
            fill=(255, 255, 255, 170),
            outline=(15, 23, 42, 95),
            width=self.scale,
        )
        img = Image.alpha_composite(img, overlay)
        draw = ImageDraw.Draw(img)

        samples, triangle, end_is_front = self.make_rotation_samples(axis_name, sign)

        for name in self.axes:
            if name != axis_name:
                self.draw_axis(draw, name, highlight=False)

        self.draw_rotation_layer(draw, samples, triangle, end_is_front, axis_name, "back")
        self.draw_axis(draw, axis_name, highlight=True)
        self.draw_rotation_layer(draw, samples, triangle, end_is_front, axis_name, "front")
        self.draw_labels_and_origin(draw)
        self.draw_vector_label(draw, vector_label)

        img = img.resize((self.width, self.height), Image.Resampling.LANCZOS).convert("RGB")
        out_path = self.output_dir / filename
        img.save(out_path, quality=96)
        return out_path

    def render_all(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return [self.render_one(*command) for command in COMMANDS]


def main():
    renderer = AxisReferenceRenderer()
    for path in renderer.render_all():
        print(path)


if __name__ == "__main__":
    main()
