"""Core domain logic for label generation."""

from __future__ import annotations

import os
import platform
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from .errors import DependencyError, GenerationError, ValidationError


DEFAULT_DPI = 300
TRIM_WIDTH_MM = 40.0
TRIM_HEIGHT_MM = 30.0
BLEED_MM = 0.75
LABEL_WIDTH_MM = TRIM_WIDTH_MM + BLEED_MM * 2
LABEL_HEIGHT_MM = TRIM_HEIGHT_MM + BLEED_MM * 2
DM_SIZE_MM = 15
LEFT_MARGIN_MM = 1.0
BOTTOM_MARGIN_MM = 1.0
TEXT_BLOCK_LEFT_MM = 18.0
TEXT_FONT_PT = 26.0
LINE_SPACING_PT = 28.0
PREFIXES = ["LD", "RD", "FD", "BD"]

PREFIX_PATTERN = re.compile(r"^[A-Z]{1,4}$")
NUMBER_PATTERN = re.compile(r"^\d+$")


@dataclass(frozen=True)
class RangeConfig:
    """Single prefix range for CLI mode."""

    prefix: str
    start: int
    end: int


@dataclass(frozen=True)
class BatchJob:
    """Single batch task for GUI mode."""

    prefix: str
    middle_code: str
    start_serial_text: str
    quantity: int
    output_root: Path


def mm_to_px(mm: float, dpi: int) -> int:
    """Convert mm to px."""
    return round(mm * dpi / 25.4)


def pt_to_px(pt: float, dpi: int) -> int:
    """Convert point to px."""
    return round(pt * dpi / 72.0)


def ensure_output_dir(path: Path) -> None:
    """Create directory tree if needed."""
    path.mkdir(parents=True, exist_ok=True)


def ensure_output_path(path: Path, overwrite: bool) -> None:
    """Fail fast on duplicates in large batch mode."""
    if path.exists() and not overwrite:
        raise GenerationError(
            f"Output file already exists: {path}. Clear target folder or use overwrite mode."
        )


def normalize_prefix(prefix: str) -> str:
    """Normalize and validate prefix."""
    normalized = prefix.strip().upper()
    if not PREFIX_PATTERN.fullmatch(normalized):
        raise ValidationError("Prefix must be 1-4 uppercase letters.")
    return normalized


def normalize_middle_code(middle_code: str) -> str:
    """Validate the middle code segment."""
    normalized = middle_code.strip()
    if not normalized:
        raise ValidationError("Middle code cannot be empty.")
    if not NUMBER_PATTERN.fullmatch(normalized):
        raise ValidationError("Middle code must be numeric.")
    return normalized


def normalize_serial_text(serial_text: str) -> str:
    """Validate serial input text."""
    normalized = serial_text.strip()
    if not normalized:
        raise ValidationError("Start serial cannot be empty.")
    if not NUMBER_PATTERN.fullmatch(normalized):
        raise ValidationError("Start serial must be numeric.")
    return normalized


def parse_positive_int(value: str, field_name: str) -> int:
    """Parse positive integer from UI text."""
    normalized = value.strip()
    if not NUMBER_PATTERN.fullmatch(normalized):
        raise ValidationError(f"{field_name} must be a positive integer.")
    parsed = int(normalized)
    if parsed <= 0:
        raise ValidationError(f"{field_name} must be greater than zero.")
    return parsed


def parse_range_spec(prefix: str, value: Optional[str]) -> Optional[RangeConfig]:
    """Parse CLI range string like 75-80."""
    if value is None:
        return None
    parts = value.split("-", 1)
    if len(parts) != 2:
        raise ValidationError(f"{prefix} range must be start-end, e.g. 75-80.")
    try:
        start = int(parts[0].strip())
        end = int(parts[1].strip())
    except ValueError as exc:
        raise ValidationError(f"{prefix} range must be integers.") from exc
    if start < 0 or end < 0:
        raise ValidationError(f"{prefix} range cannot be negative.")
    if end < start:
        raise ValidationError(f"{prefix} end cannot be less than start.")
    return RangeConfig(prefix=normalize_prefix(prefix), start=start, end=end)


def build_range_configs(args) -> List[RangeConfig]:
    """Build CLI range configs; keep backward compatibility."""
    configs: List[RangeConfig] = []
    for prefix in PREFIXES:
        value = getattr(args, f"{prefix.lower()}_range")
        cfg = parse_range_spec(prefix, value)
        if cfg is not None:
            configs.append(cfg)
    if configs:
        return configs
    if args.quantity <= 0:
        raise ValidationError("quantity must be greater than zero.")
    if args.start < 0:
        raise ValidationError("start cannot be negative.")
    end = args.start + args.quantity - 1
    return [RangeConfig(prefix=p, start=args.start, end=end) for p in PREFIXES]


def build_code(prefix: str, middle_code: str, serial_number: int) -> Tuple[str, List[str]]:
    """Build full code and 3 text lines."""
    normalized_prefix = normalize_prefix(prefix)
    normalized_middle = normalize_middle_code(middle_code)
    if serial_number < 0:
        raise ValidationError("serial cannot be negative.")
    serial_text = str(serial_number).zfill(4)
    full_code = f"{normalized_prefix}{normalized_middle}{serial_text}"
    return full_code, [normalized_prefix, normalized_middle, serial_text]


def _prepare_platform_runtime() -> None:
    """Best-effort runtime path setup for libdmtx."""
    system = platform.system()
    if system == "Darwin":
        candidates = ["/opt/homebrew/opt/libdmtx/lib", "/usr/local/opt/libdmtx/lib"]
        existing = [path for path in candidates if Path(path).exists()]
        if existing:
            current = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
            parts = [part for part in current.split(":") if part]
            for path in existing:
                if path not in parts:
                    parts.append(path)
            os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = ":".join(parts)
    elif system == "Windows":
        # Allow PyInstaller bundle and common install locations.
        path_env = os.environ.get("PATH", "")
        extra = []
        bundle_root = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else None  # type: ignore[attr-defined]
        if bundle_root:
            extra.append(str(bundle_root))
        for candidate in [Path.cwd(), Path.cwd() / "libs", Path("C:/Program Files/libdmtx/bin")]:
            if candidate.exists():
                extra.append(str(candidate))
        if extra:
            os.environ["PATH"] = os.pathsep.join(extra + [path_env])


def _get_encode_func() -> Callable[[bytes], object]:
    """Load pylibdmtx lazily with friendly errors."""
    _prepare_platform_runtime()
    try:
        from pylibdmtx.pylibdmtx import encode  # pylint: disable=import-outside-toplevel

        return encode
    except Exception as exc:
        raise DependencyError(
            "Unable to load pylibdmtx/libdmtx runtime. "
            "Install dependencies first (README -> Runtime Dependencies)."
        ) from exc


def load_font(font_path: Optional[str] = None, font_size: int = 120) -> ImageFont.FreeTypeFont:
    """Load label font with fallback chain."""
    candidates: List[str] = []
    if font_path:
        candidates.append(font_path)
    candidates.extend(
        [
            "arialbd.ttf",
            "Arial Bold.ttf",
            "Arialbd.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
            "DejaVuSans-Bold.ttf",
        ]
    )
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, font_size)
        except Exception:
            continue
    return ImageFont.load_default()


def generate_datamatrix_image(data: str, target_size_px: int) -> Image.Image:
    """Generate square Data Matrix image."""
    encode = _get_encode_func()
    encoded = encode(data.encode("utf-8"))
    dm_img = Image.frombytes("RGB", (encoded.width, encoded.height), encoded.pixels)
    bbox = dm_img.convert("L").point(lambda value: 0 if value > 250 else 255).getbbox()
    if bbox:
        dm_img = dm_img.crop(bbox)
    return dm_img.resize((target_size_px, target_size_px), Image.Resampling.NEAREST)


def draw_label(
    full_code: str,
    text_lines: List[str],
    output_path: Path,
    dpi: int = DEFAULT_DPI,
    font_path: Optional[str] = None,
) -> None:
    """Draw a single label image."""
    label_w_px = mm_to_px(LABEL_WIDTH_MM, dpi)
    label_h_px = mm_to_px(LABEL_HEIGHT_MM, dpi)
    trim_w_px = mm_to_px(TRIM_WIDTH_MM, dpi)
    trim_h_px = mm_to_px(TRIM_HEIGHT_MM, dpi)
    bleed_px = mm_to_px(BLEED_MM, dpi)
    dm_px = mm_to_px(DM_SIZE_MM, dpi)
    left_margin_px = mm_to_px(LEFT_MARGIN_MM, dpi)
    bottom_margin_px = mm_to_px(BOTTOM_MARGIN_MM, dpi)

    image = Image.new("RGB", (label_w_px, label_h_px), "white")
    draw = ImageDraw.Draw(image)

    dm_img = generate_datamatrix_image(full_code, dm_px)
    # All layout coordinates are defined on the 40x30 mm trim box, then shifted by bleed.
    trim_left = bleed_px
    trim_top = bleed_px
    trim_bottom = trim_top + trim_h_px

    dm_x = trim_left + left_margin_px
    dm_y = trim_bottom - bottom_margin_px - dm_px
    image.paste(dm_img, (dm_x, dm_y))

    text_left = trim_left + mm_to_px(TEXT_BLOCK_LEFT_MM, dpi)
    font_px = pt_to_px(TEXT_FONT_PT, dpi)
    line_spacing_px = pt_to_px(LINE_SPACING_PT, dpi)
    font = load_font(font_path=font_path, font_size=font_px)

    bboxes = [draw.textbbox((0, 0), line, font=font) for line in text_lines]
    line_widths = [bbox[2] - bbox[0] for bbox in bboxes]
    top_offsets = [bbox[1] for bbox in bboxes]
    bottom_offsets = [bbox[3] for bbox in bboxes]

    visible_block_h = ((len(text_lines) - 1) * line_spacing_px) + (
        max(bottom_offsets) - min(top_offsets)
    )
    first_line_y = trim_top + (trim_h_px - visible_block_h) / 2.0 - min(top_offsets)

    dm_right = dm_x + dm_px
    if text_left <= dm_right:
        raise GenerationError("Text block overlaps DM region with current layout.")
    trim_right = trim_left + trim_w_px
    if text_left + max(line_widths) > trim_right:
        raise GenerationError("Text block exceeds label width with current layout.")

    current_y = first_line_y
    for line, bbox in zip(text_lines, bboxes):
        draw.text((text_left - bbox[0], current_y), line, fill="black", font=font)
        current_y += line_spacing_px

    image.save(output_path, format="PNG", dpi=(dpi, dpi))


def allocate_batch_output_dir(prefix: str, output_root: Path, when: Optional[datetime] = None) -> Path:
    """Create unique folder like LD-20260311 / LD-20260311(1)."""
    timestamp = when or datetime.now()
    normalized_prefix = normalize_prefix(prefix)
    base_name = f"{normalized_prefix}-{timestamp.strftime('%Y%m%d')}"
    candidate = output_root / base_name
    suffix = 0
    while candidate.exists():
        suffix += 1
        candidate = output_root / f"{base_name}({suffix})"
    return candidate


def validate_batch_job(
    prefix: str,
    middle_code: str,
    start_serial_text: str,
    quantity_text: str,
    output_root: Path,
) -> BatchJob:
    """Validate GUI form inputs."""
    validated_prefix = normalize_prefix(prefix)
    validated_middle_code = normalize_middle_code(middle_code)
    validated_start = normalize_serial_text(start_serial_text)
    quantity = parse_positive_int(quantity_text, "quantity")
    if not str(output_root).strip():
        raise ValidationError("output root cannot be empty.")
    return BatchJob(
        prefix=validated_prefix,
        middle_code=validated_middle_code,
        start_serial_text=validated_start,
        quantity=quantity,
        output_root=output_root,
    )


def preview_batch_range(job: BatchJob) -> Tuple[str, str]:
    """Get start/end code for preview."""
    start_serial = int(job.start_serial_text)
    end_serial = start_serial + job.quantity - 1
    start_code, _ = build_code(job.prefix, job.middle_code, start_serial)
    end_code, _ = build_code(job.prefix, job.middle_code, end_serial)
    return start_code, end_code


def generate_batch_job(
    job: BatchJob,
    dpi: int = DEFAULT_DPI,
    font_path: Optional[str] = None,
) -> Tuple[Path, List[Path], str, str]:
    """Generate one GUI batch into one unique folder."""
    ensure_output_dir(job.output_root)
    batch_dir = allocate_batch_output_dir(job.prefix, job.output_root)
    ensure_output_dir(batch_dir)

    start_code, end_code = preview_batch_range(job)
    generated: List[Path] = []
    start_serial = int(job.start_serial_text)
    for offset in range(job.quantity):
        serial = start_serial + offset
        full_code, text_lines = build_code(job.prefix, job.middle_code, serial)
        output_path = batch_dir / f"{full_code}.png"
        ensure_output_path(output_path, overwrite=False)
        draw_label(full_code, text_lines, output_path, dpi=dpi, font_path=font_path)
        generated.append(output_path)
    return batch_dir, generated, start_code, end_code


def generate_labels(
    range_configs: List[RangeConfig],
    output_dir: Path,
    middle_code: str = "4000",
    dpi: int = DEFAULT_DPI,
    font_path: Optional[str] = None,
    overwrite: bool = False,
) -> Dict[str, List[Path]]:
    """Generate labels for CLI range mode."""
    ensure_output_dir(output_dir)
    validated_middle = normalize_middle_code(middle_code)
    generated: Dict[str, List[Path]] = {prefix: [] for prefix in PREFIXES}
    for cfg in range_configs:
        prefix_dir = output_dir / cfg.prefix
        ensure_output_dir(prefix_dir)
        for serial in range(cfg.start, cfg.end + 1):
            full_code, text_lines = build_code(cfg.prefix, validated_middle, serial)
            output_path = prefix_dir / f"{full_code}.png"
            ensure_output_path(output_path, overwrite=overwrite)
            draw_label(full_code, text_lines, output_path, dpi=dpi, font_path=font_path)
            generated[cfg.prefix].append(output_path)
    return generated


def check_runtime_dependencies() -> None:
    """Fast preflight for GUI startup."""
    _get_encode_func()
