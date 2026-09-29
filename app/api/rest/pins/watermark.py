"""Static watermark helpers for Marketplace preview generation."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.config import settings


VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".mkv"}
EVIDENCE_TEXT = "just buy it"


def media_root() -> Path:
    return Path(settings.MEDIA_PATH)


def original_dir() -> Path:
    path = media_root() / "pins" / "original"
    path.mkdir(parents=True, exist_ok=True)
    return path


def preview_dir() -> Path:
    path = media_root() / "pins" / "preview"
    path.mkdir(parents=True, exist_ok=True)
    return path


def watermark_asset_path() -> Path:
    candidates = [
        Path("/fastapi/assets/watermark.png"),
        Path(__file__).resolve().parents[4] / "assets" / "watermark.png",
        media_root() / "assets" / "watermark.png",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    out = Path("/fastapi/assets/watermark.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGBA", (320, 80), (0, 0, 0, 0))
    bar = Image.new("RGBA", (320, 80), (255, 255, 255, 110))
    img.paste(bar, (0, 0), bar)
    img.save(out, format="PNG")
    return out


def is_video_path(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS


def _load_font(size: int) -> ImageFont.ImageFont:
    for name in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ):
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _fade_alpha(img: Image.Image, factor: float) -> Image.Image:
    r, g, b, a = img.split()
    a = a.point(lambda p: int(p * factor))
    return Image.merge("RGBA", (r, g, b, a))


def _diagonal_evidence_layer(width: int, height: int, text: str) -> Image.Image:
    """Subtle diagonal text — visible on crop/theft, soft enough for browsing."""
    font_size = max(16, int(min(width, height) * 0.07))
    font = _load_font(font_size)
    step = max(int(font_size * 2.8), int(min(width, height) * 0.22))

    diag = int((width**2 + height**2) ** 0.5) + step * 2
    canvas = Image.new("RGBA", (diag * 2, diag * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    phrase = f"  {text}  ·  "
    line = phrase * max(12, (diag * 2) // max(1, font_size * 4))

    for row, y in enumerate(range(0, canvas.height, step)):
        x_off = -((row % 3) * (font_size * 2))
        for ox, oy in ((1, 1), (-1, -1)):
            draw.text((x_off + ox, y + oy), line, font=font, fill=(0, 0, 0, 22))
        draw.text((x_off, y), line, font=font, fill=(255, 255, 255, 36))

    rotated = canvas.rotate(-32, resample=Image.Resampling.BICUBIC, expand=False)
    cx, cy = rotated.width // 2, rotated.height // 2
    left = cx - width // 2
    top = cy - height // 2
    return rotated.crop((left, top, left + width, top + height))


def build_preview(src: Path, dest: Path, *, watermark: bool = False) -> None:
    """Write JPEG preview. Watermark only for listed-for-sale pins."""
    base = Image.open(src).convert("RGBA")
    layered = base.copy()

    if watermark:
        mark = Image.open(watermark_asset_path()).convert("RGBA")
        target_w = max(48, int(base.width * 0.28))
        ratio = target_w / mark.width
        target_h = max(20, int(mark.height * ratio))
        mark = mark.resize((target_w, target_h), Image.Resampling.LANCZOS)
        mark = _fade_alpha(mark, 0.32)

        margin = max(8, int(base.width * 0.03))
        x = base.width - mark.width - margin
        y = base.height - mark.height - margin
        layered.alpha_composite(mark, (x, y))
        layered.alpha_composite(
            _diagonal_evidence_layer(base.width, base.height, EVIDENCE_TEXT)
        )

    rgb = layered.convert("RGB")
    dest.parent.mkdir(parents=True, exist_ok=True)
    rgb.save(dest, format="JPEG", quality=88)


def apply_watermark(src: Path, dest: Path) -> None:
    """Backward-compatible alias — always writes a watermarked preview."""
    build_preview(src, dest, watermark=True)
