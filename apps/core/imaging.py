"""Image helpers: WebP variants, responsive URLs, and optimization."""
import os
from pathlib import Path

from django.conf import settings

ALLOWED_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp")

# Max dimensions per asset type (width, height)
IMAGE_PRESETS = {
    "hero": {"full": (1920, 1080), "medium": (1280, 720), "thumb": (640, 360)},
    "dashboard_banner": {"full": (1600, 900), "medium": (1024, 576), "thumb": (512, 288)},
    "course_cover": {"full": (800, 450), "medium": (640, 360), "thumb": (400, 225)},
    "thumbnail": {"full": (400, 225), "medium": (320, 180), "thumb": (200, 112)},
    "feature_card": {
        "thumb": (640, 360),
        "medium": (1280, 720),
        "full": (1920, 1080),
        "ultra": (3840, 2160),
    },
    "partner_logo": {"full": (500, 500), "medium": (320, 320), "thumb": (160, 160)},
}

# Legacy aliases used by model save hooks
COVER_MAX_SIZE = IMAGE_PRESETS["course_cover"]["full"]
THUMB_MAX_SIZE = IMAGE_PRESETS["thumbnail"]["full"]
WEBP_QUALITY = 82


def static_url(relative_path: str) -> str:
    base = (settings.STATIC_URL or "/static/").rstrip("/")
    return f"{base}/{relative_path.lstrip('/')}"


def _is_cloudinary_field(image_field):
    try:
        return bool(image_field and image_field.name and "cloudinary" in str(type(image_field.storage)).lower())
    except Exception:
        return False


def _cloudinary_variant_url(image_field, width, height):
    try:
        from cloudinary import CloudinaryImage

        return CloudinaryImage(image_field.name).build_url(
            width=width, height=height, crop="fill", format="webp", quality="auto"
        )
    except Exception:
        return image_field.url


def _variant_filename(original_name, size_key):
    path = Path(original_name)
    return str(path.with_name(f"{path.stem}_{size_key}.webp"))


def generate_image_variants(image_field, preset="course_cover"):
    """Create thumb/medium/full WebP siblings for a local uploaded image."""
    if not image_field or not image_field.name:
        return {}
    if _is_cloudinary_field(image_field):
        return {}

    try:
        from PIL import Image
    except ImportError:
        return {}

    try:
        source_path = image_field.path
    except (NotImplementedError, ValueError, AttributeError):
        return {}

    if not os.path.isfile(source_path):
        return {}

    sizes = IMAGE_PRESETS.get(preset, IMAGE_PRESETS["course_cover"])
    urls = {}
    try:
        with Image.open(source_path) as img:
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            media_root = Path(settings.MEDIA_ROOT)
            for key, max_size in sizes.items():
                variant_name = _variant_filename(image_field.name, key)
                variant_path = media_root / variant_name
                variant_path.parent.mkdir(parents=True, exist_ok=True)
                copy = img.copy()
                copy.thumbnail(max_size, Image.LANCZOS)
                copy.save(variant_path, format="WEBP", quality=WEBP_QUALITY, method=6)
                urls[key] = f"{settings.MEDIA_URL.rstrip('/')}/{variant_name}"
    except Exception:
        return {}
    return urls


def responsive_static_image_data(relative_stem, preset="feature_card"):
    """Return src/srcset for pre-generated static WebP variants (e.g. images/features/video-lessons)."""
    sizes = IMAGE_PRESETS.get(preset, IMAGE_PRESETS["feature_card"])
    responsive_sizes = "(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
    srcset_parts = []
    for key, dims in sizes.items():
        srcset_parts.append(f"{static_url(f'{relative_stem}-{key}.webp')} {dims[0]}w")
    return {
        "src": static_url(f"{relative_stem}-full.webp"),
        "srcset": ", ".join(srcset_parts),
        "sizes": responsive_sizes,
    }


def responsive_image_data(image_field, preset="course_cover", placeholder=None):
    """Return src/srcset/sizes dict for responsive <img> or <picture>."""
    placeholder = placeholder or static_url("images/course-placeholder.svg")
    if not image_field:
        return {
            "src": placeholder,
            "srcset": "",
            "sizes": "(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw",
            "is_placeholder": True,
        }

    sizes = IMAGE_PRESETS.get(preset, IMAGE_PRESETS["course_cover"])
    responsive_sizes = "(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"

    if _is_cloudinary_field(image_field):
        thumb = _cloudinary_variant_url(image_field, *sizes["thumb"])
        medium = _cloudinary_variant_url(image_field, *sizes["medium"])
        full = _cloudinary_variant_url(image_field, *sizes["full"])
        return {
            "src": medium,
            "srcset": f"{thumb} {sizes['thumb'][0]}w, {medium} {sizes['medium'][0]}w, {full} {sizes['full'][0]}w",
            "sizes": responsive_sizes,
            "is_placeholder": False,
        }

    variants = generate_image_variants(image_field, preset)
    if variants:
        thumb = variants.get("thumb", image_field.url)
        medium = variants.get("medium", image_field.url)
        full = variants.get("full", image_field.url)
        return {
            "src": medium,
            "srcset": f"{thumb} {sizes['thumb'][0]}w, {medium} {sizes['medium'][0]}w, {full} {sizes['full'][0]}w",
            "sizes": responsive_sizes,
            "is_placeholder": False,
        }

    return {
        "src": image_field.url,
        "srcset": "",
        "sizes": responsive_sizes,
        "is_placeholder": False,
    }


def optimize_image_field(image_field, max_size=COVER_MAX_SIZE, quality=WEBP_QUALITY, preset=None):
    """Resize/compress the main upload, then write WebP thumb/medium/full variants."""
    if not image_field:
        return
    if _is_cloudinary_field(image_field):
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
        with Image.open(path) as img:
            img_format = (img.format or "JPEG").upper()
            if img_format in ("JPEG", "JPG") and img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            elif img.mode not in ("RGB", "L", "RGBA"):
                img = img.convert("RGB")
            img.thumbnail(max_size, Image.LANCZOS)
            save_kwargs = {"optimize": True}
            if img_format in ("JPEG", "JPG", "WEBP"):
                save_kwargs["quality"] = quality
            img.save(path, format=img_format if img_format != "JPG" else "JPEG", **save_kwargs)
    except Exception:
        return

    if preset:
        generate_image_variants(image_field, preset)
