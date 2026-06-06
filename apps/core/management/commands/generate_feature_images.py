"""Build feature card WebP variants up to 4K from high-resolution source PNGs."""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

# Legacy: crop boxes for the old low-res marketing composite (1024px wide)
CROP_BOXES = {
    "video-lessons": (30, 92, 332, 228),
    "online-quizzes": (356, 92, 658, 228),
    "certificates": (682, 92, 984, 228),
    "mobile-learning": (30, 329, 332, 465),
    "expert-instructors": (356, 329, 658, 465),
    "continuous-support": (682, 329, 984, 465),
}

VARIANTS = {
    "thumb": (640, 360),
    "medium": (1280, 720),
    "full": (1920, 1080),
    "ultra": (3840, 2160),
}


def _cover_resize(img, target):
    from PIL import Image

    tw, th = target
    sw, sh = img.size
    scale = max(tw / sw, th / sh)
    nw, nh = int(sw * scale), int(sh * scale)
    resized = img.resize((nw, nh), Image.LANCZOS)
    left = (nw - tw) // 2
    top = (nh - th) // 2
    return resized.crop((left, top, left + tw, top + th))


SOURCE_FILES = [
    ("video-lessons-4k.png", "video-lessons"),
    ("online-quizzes-4k.png", "online-quizzes"),
    ("certificates-4k.png", "certificates"),
    ("mobile-learning-4k.png", "mobile-learning"),
    ("expert-instructors-4k.png", "expert-instructors"),
    ("continuous-support-4k.png", "continuous-support"),
]


class Command(BaseCommand):
    help = "Generate sharp feature card WebP variants (640px–4K) from high-res source PNGs"

    def add_arguments(self, parser):
        parser.add_argument(
            "--source-dir",
            default="static/images/features/sources",
            help="Directory with *-4k.png source images (preferred)",
        )
        parser.add_argument(
            "--composite",
            default="",
            help="Optional legacy composite path (low quality — not recommended)",
        )

    def handle(self, *args, **options):
        try:
            from PIL import Image, ImageEnhance, ImageFilter
        except ImportError:
            self.stderr.write("Pillow is required: pip install Pillow")
            return

        out_dir = Path(settings.BASE_DIR) / "static" / "images" / "features"
        out_dir.mkdir(parents=True, exist_ok=True)

        source_dir = Path(settings.BASE_DIR) / options["source_dir"]
        if source_dir.is_dir() and any(source_dir.glob("*-4k.png")):
            self._from_high_res_sources(source_dir, out_dir, Image, ImageEnhance, ImageFilter)
        elif options["composite"]:
            self._from_composite(Path(options["composite"]), out_dir, Image)
        else:
            self.stderr.write(
                "Place *-4k.png files in static/images/features/sources/ "
                "or pass --composite for the legacy crop workflow."
            )
            return

        self.stdout.write(self.style.SUCCESS("Feature images generated (up to 3840×2160)."))

    def _from_high_res_sources(self, source_dir, out_dir, Image, ImageEnhance, ImageFilter):
        for filename, stem in SOURCE_FILES:
            path = source_dir / filename
            if not path.is_file():
                self.stderr.write(f"Missing source: {path}")
                continue
            img = Image.open(path).convert("RGB")
            master = _cover_resize(img, (3840, 2160))
            master = ImageEnhance.Sharpness(master).enhance(1.2)
            master = master.filter(ImageFilter.UnsharpMask(radius=1.0, percent=110, threshold=2))
            master.save(out_dir / f"{stem}.png", optimize=True)
            for key, size in VARIANTS.items():
                variant = master if key == "ultra" else _cover_resize(master, size)
                variant.save(out_dir / f"{stem}-{key}.webp", "WEBP", quality=92, method=4)
            self.stdout.write(self.style.SUCCESS(f"  {stem} → 4K master + variants"))

    def _from_composite(self, source, out_dir, Image):
        if not source.is_file():
            source = Path(settings.BASE_DIR) / source
        if not source.is_file():
            self.stderr.write(f"Composite not found: {source}")
            return
        composite = Image.open(source).convert("RGB")
        for name, box in CROP_BOXES.items():
            crop = composite.crop(box)
            crop.save(out_dir / f"{name}.png", optimize=True)
            for key, size in VARIANTS.items():
                variant = _cover_resize(crop, size)
                variant.save(out_dir / f"{name}-{key}.webp", "WEBP", quality=85, method=4)
            self.stdout.write(self.style.SUCCESS(f"  {name} → variants (legacy composite)"))
