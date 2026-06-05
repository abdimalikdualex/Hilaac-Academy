"""Image helpers: web optimization and static placeholder URLs."""
from django.conf import settings

ALLOWED_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp")
COVER_MAX_SIZE = (1280, 720)
THUMB_MAX_SIZE = (640, 360)
JPEG_QUALITY = 82


def static_url(relative_path: str) -> str:
    """Build a static URL from STATIC_URL without relying on the manifest."""
    base = (settings.STATIC_URL or "/static/").rstrip("/")
    return f"{base}/{relative_path.lstrip('/')}"


def optimize_image_field(image_field, max_size=COVER_MAX_SIZE, quality=JPEG_QUALITY):
    """Resize/compress an image in place for web delivery.

    Safely no-ops for remote storages (e.g. Cloudinary) that have no local
    filesystem path, since those services optimize on their own.
    """
    if not image_field:
        return
    try:
        from PIL import Image
    except ImportError:
        return

    try:
        path = image_field.path
    except (NotImplementedError, ValueError):
        return

    try:
        img = Image.open(path)
        img_format = (img.format or "JPEG").upper()
        if img_format in ("JPEG", "JPG") and img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img.thumbnail(max_size, Image.LANCZOS)
        save_kwargs = {"optimize": True}
        if img_format in ("JPEG", "JPG", "WEBP"):
            save_kwargs["quality"] = quality
        img.save(path, format=img_format, **save_kwargs)
    except Exception:
        # Never block a save because optimization failed.
        return
