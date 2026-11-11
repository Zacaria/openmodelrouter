"""Regenerate the supplied logo's site derivatives; requires Pillow, not used at build."""
from pathlib import Path
from PIL import Image

SITE = Path(__file__).resolve().parents[1]
with Image.open(SITE / "brand/originals/upload_3smffdyj.png") as original:
    if original.size != (1254, 1254):
        raise ValueError("Expected the supplied square source; never stretch a replacement")
    # Remove exterior black padding only; preserve the full tile and all branches.
    image = original.crop((96, 92, 1156, 1152)).convert("RGB")
    assets = SITE / "assets"
    assets.mkdir(exist_ok=True)
    for size in (32, 128):
        image.resize((size, size), Image.Resampling.LANCZOS).save(
            assets / f"logo-{size}.png", optimize=True
        )
    image.save(SITE / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
