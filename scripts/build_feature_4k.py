"""Build sharp 4K feature card assets from high-resolution source PNGs."""
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT.parent / ".cursor" / "projects" / "c-Users-ABDIMALIK-Documents-HILAAC-ACADEMY" / "assets"
# Fallback: assets colocated with generated images in cursor project path
CURSOR_ASSETS = Path(
    r"C:\Users\ABDIMALIK\.cursor\projects\c-Users-ABDIMALIK-Documents-HILAAC-ACADEMY\assets"
)
OUT = ROOT / "static" / "images" / "features"

SOURCES = [
    ("video-lessons-4k.png", "video-lessons"),
    ("online-quizzes-4k.png", "online-quizzes"),
    ("certificates-4k.png", "certificates"),
    ("mobile-learning-4k.png", "mobile-learning"),
    ("expert-instructors-4k.png", "expert-instructors"),
    ("continuous-support-4k.png", "continuous-support"),
]

VARIANTS = {
    "thumb": (640, 360),
    "medium": (1280, 720),
    "full": (1920, 1080),
    "ultra": (3840, 2160),
}
TARGET_4K = (3840, 2160)
WEBP_QUALITY = 92


def asset_dir():
    if CURSOR_ASSETS.is_dir():
        return CURSOR_ASSETS
    return ASSETS


def cover_resize(img, target):
    tw, th = target
    sw, sh = img.size
    scale = max(tw / sw, th / sh)
    nw, nh = int(sw * scale), int(sh * scale)
    resized = img.resize((nw, nh), Image.LANCZOS)
    left = (nw - tw) // 2
    top = (nh - th) // 2
    return resized.crop((left, top, left + tw, top + th))


def enhance(img):
    img = ImageEnhance.Sharpness(img).enhance(1.2)
    img = ImageEnhance.Contrast(img).enhance(1.04)
    return img.filter(ImageFilter.UnsharpMask(radius=1.0, percent=110, threshold=2))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    src_dir = asset_dir()

    for filename, stem in SOURCES:
        path = src_dir / filename
        if not path.is_file():
            raise FileNotFoundError(path)

        img = Image.open(path).convert("RGB")
        print(f"{stem}: source {img.size}")

        master = enhance(cover_resize(img, TARGET_4K))
        master.save(OUT / f"{stem}.png", optimize=True)

        for key, size in VARIANTS.items():
            variant = master if key == "ultra" else cover_resize(master, size)
            variant.save(
                OUT / f"{stem}-{key}.webp",
                "WEBP",
                quality=WEBP_QUALITY,
                method=4,
            )
        print(f"  -> wrote 4K master + variants")


if __name__ == "__main__":
    main()
