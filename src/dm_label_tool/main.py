"""Unified entrypoint for CLI and GUI."""

from __future__ import annotations

import sys
from pathlib import Path

from .cli import build_parser, run_cli
from .core import DEFAULT_DPI


def should_launch_gui(args) -> bool:
    """Default to GUI unless explicit CLI generation flags are present."""
    if args.cli:
        return False
    if args.gui:
        return True
    cli_flags = any(
        [
            args.ld_range,
            args.rd_range,
            args.fd_range,
            args.bd_range,
            args.start != 1,
            args.quantity != 1,
            args.output != "dm_labels",
            args.middle_code != "4000",
            args.overwrite,
            bool(args.font),
            args.dpi != DEFAULT_DPI,
        ]
    )
    return not cli_flags


def main() -> None:
    """Tool entrypoint."""
    args = build_parser().parse_args()
    project_root = Path(__file__).resolve().parents[2]
    try:
        if should_launch_gui(args):
            from .gui import launch_gui  # import lazily for CLI-only environments

            launch_gui(project_root=project_root)
        else:
            run_cli(args)
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
