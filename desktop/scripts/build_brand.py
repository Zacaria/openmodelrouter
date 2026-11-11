"""Derive only desktop assets from the supplied PNG; uv/Pillow 12.0.0."""

import argparse
from collections import deque
import hashlib
import io
from pathlib import Path
from typing import Iterable, cast
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "design/originals/upload_3smffdyj.png"
SOURCE_SHA256 = "e07bb3cfb80edc8e5be8ec2f74959330784a934bf9f850ae08450c86ee8bfd05"


def derivatives():
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("The approved source image has changed")
    original = Image.open(SOURCE).convert("RGBA")
    # Remove only connected near-black exterior, not dark interior details.
    pixels = original.load()
    assert pixels is not None
    width, height = original.size
    queue = deque([(0, 0)])
    seen = set()
    while queue:
        x, y = queue.popleft()
        if (x, y) in seen or not (0 <= x < width and 0 <= y < height):
            continue
        seen.add((x, y))
        r, g, b, _ = cast(tuple[int, int, int, int], pixels[x, y])
        if max(r, g, b) > 16:
            continue
        pixels[x, y] = (r, g, b, 0)
        queue.extend([(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)])
    # Square framing; do not stretch the artwork or approximate its geometry.
    master = original.crop((80, 80, 1174, 1174)).resize(
        (1024, 1024), Image.Resampling.LANCZOS
    )
    yield (
        "src-tauri/icons/icon.png",
        master.resize((512, 512), Image.Resampling.LANCZOS),
        "PNG",
        {},
    )
    yield (
        "src-tauri/icons/icon.ico",
        master,
        "ICO",
        {"sizes": [(n, n) for n in (16, 24, 32, 48, 64, 128, 256)]},
    )
    yield "src-tauri/icons/icon.icns", master, "ICNS", {}
    yield (
        "public/brand/app-128.png",
        master.resize((128, 128), Image.Resampling.LANCZOS),
        "PNG",
        {},
    )
    # Pixel-derived complete routing sign, not an isolated generic Y.
    center = Image.open(SOURCE).convert("RGB").crop((180, 220, 1120, 1010))
    mask = Image.new("L", center.size)
    mask.putdata(
        [
            255 if max(pixel) > 100 and max(pixel) - min(pixel) > 40 else 0
            for pixel in cast(Iterable[tuple[int, int, int]], center.getdata())
        ]
    )
    # Keep substantial source components (input, hub/routes, lower output),
    # removing small disconnected reflections from the surrounding tile.
    points = {
        (x, y)
        for y in range(mask.height)
        for x in range(mask.width)
        if cast(int, mask.getpixel((x, y))) > 120
    }
    retained = set()
    while points:
        first = points.pop()
        component = {first}
        pending = [first]
        while pending:
            x, y = pending.pop()
            for neighbour in [(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)]:
                if neighbour in points:
                    points.remove(neighbour)
                    component.add(neighbour)
                    pending.append(neighbour)
        if len(component) >= 5000:
            retained.update(component)
    mask = Image.new("L", center.size)
    for point in retained:
        mask.putpixel(point, 255)
    # Optical weight only; never redraw paths or destination blocks.
    mask = mask.filter(ImageFilter.MaxFilter(9))
    bounds = mask.getbbox()
    if bounds is None:
        raise ValueError("Routing sign could not be extracted")
    mask = mask.crop(bounds)
    mask.thumbnail((40, 28), Image.Resampling.LANCZOS)
    alpha = Image.new("L", (44, 32))
    alpha.paste(mask, ((44 - mask.width) // 2, (32 - mask.height) // 2))
    template = Image.new("RGBA", alpha.size, (0, 0, 0, 0))
    template.putalpha(alpha)
    yield "src-tauri/icons/tray-template.png", template, "PNG", {}
    tray = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    ImageDraw.Draw(tray).rounded_rectangle((4, 4, 123, 123), radius=25, fill="#131a1b")
    tray = tray.resize((32, 32), Image.Resampling.LANCZOS)
    alpha.thumbnail((28, 28), Image.Resampling.LANCZOS)
    colour_alpha = Image.new("L", (32, 32))
    colour_alpha.paste(alpha, ((32 - alpha.width) // 2, (32 - alpha.height) // 2))
    mark = Image.new("RGBA", (32, 32), "#cff66a")
    mark.putalpha(colour_alpha)
    tray.alpha_composite(mark)
    yield "src-tauri/icons/tray.png", tray, "PNG", {}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for name, image, fmt, options in derivatives():
        buffer = io.BytesIO()
        image.save(buffer, format=fmt, **options)
        data = buffer.getvalue()
        path = ROOT / name
        if args.check:
            if not path.is_file() or path.read_bytes() != data:
                raise SystemExit(f"Stale or missing derivative: {name}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        print(
            f"{'Verified' if args.check else 'Generated'} {name} {hashlib.sha256(data).hexdigest()}"
        )


if __name__ == "__main__":
    main()
