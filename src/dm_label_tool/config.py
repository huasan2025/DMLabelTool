"""Persistent app config for GUI mode."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


CONFIG_PATH = Path.home() / ".dm_label_generator_config.json"


@dataclass
class AppConfig:
    """User persistent settings."""

    output_root: str
    font_path: str = ""


def default_output_root(project_root: Path) -> Path:
    """Default GUI output root."""
    return project_root / "output_gui"


def load_app_config(project_root: Path) -> AppConfig:
    """Load config from user home, fall back safely."""
    fallback = AppConfig(output_root=str(default_output_root(project_root)), font_path="")
    if not CONFIG_PATH.exists():
        return fallback
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return AppConfig(
            output_root=str(data.get("output_root") or fallback.output_root),
            font_path=str(data.get("font_path") or ""),
        )
    except Exception:
        return fallback


def save_app_config(config: AppConfig) -> None:
    """Persist config atomically enough for single-user desktop usage."""
    CONFIG_PATH.write_text(
        json.dumps(asdict(config), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

