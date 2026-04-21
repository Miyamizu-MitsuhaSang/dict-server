import hashlib
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageOps

from settings import ROOT_DIR

BANNER_MAX_WIDTH = 1280
BANNER_MAX_HEIGHT = 720
BANNER_WEBP_QUALITY = 82


def build_optimized_banner_image_url(image_url: str | None) -> str | None:
    if not image_url or not image_url.startswith("/media/"):
        return image_url

    src_path = (ROOT_DIR / image_url.lstrip("/")).resolve()
    if not src_path.exists() or not src_path.is_file():
        return image_url

    src_suffix = src_path.suffix.lower()
    if src_suffix == ".webp":
        return image_url

    month_dir = datetime.now().strftime("%Y%m")
    relative_dir = Path("article/banners") / month_dir
    output_dir = ROOT_DIR / "media" / relative_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    digest = hashlib.md5(str(src_path).encode("utf-8")).hexdigest()[:10]
    output_name = f"banner_{src_path.stem}_{digest}.webp"
    output_path = output_dir / output_name

    if output_path.exists():
        return f"/media/{(relative_dir / output_name).as_posix()}"

    try:
        with Image.open(src_path) as img:
            optimized = ImageOps.exif_transpose(img)
            if optimized.mode not in ("RGB", "RGBA"):
                optimized = optimized.convert("RGB")
            optimized.thumbnail((BANNER_MAX_WIDTH, BANNER_MAX_HEIGHT), Image.Resampling.LANCZOS)
            optimized.save(output_path, format="WEBP", quality=BANNER_WEBP_QUALITY, method=6)
    except Exception:
        return image_url

    return f"/media/{(relative_dir / output_name).as_posix()}"
