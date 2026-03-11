"""CLI entry helpers."""

from __future__ import annotations

import argparse
from pathlib import Path

from .core import DEFAULT_DPI, PREFIXES, build_range_configs, generate_labels


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(description="Data Matrix Label Generator")
    parser.add_argument("-s", "--start", type=int, default=1, help="legacy mode start serial")
    parser.add_argument(
        "-q",
        "--quantity",
        type=int,
        default=1,
        help="legacy mode quantity per prefix",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="dm_labels",
        help="CLI output root (prefix folders created under this path)",
    )
    parser.add_argument("--ld-range", type=str, default=None, help="LD range, e.g. 75-80")
    parser.add_argument("--rd-range", type=str, default=None, help="RD range, e.g. 75-80")
    parser.add_argument("--fd-range", type=str, default=None, help="FD range, e.g. 75-80")
    parser.add_argument("--bd-range", type=str, default=None, help="BD range, e.g. 75-80")
    parser.add_argument("--middle-code", type=str, default="4000", help="middle code segment")
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI, help="output DPI")
    parser.add_argument("--font", type=str, default=None, help="optional font file path")
    parser.add_argument("--overwrite", action="store_true", help="overwrite existing files")
    parser.add_argument("--gui", action="store_true", help="force GUI mode")
    parser.add_argument("--cli", action="store_true", help="force CLI mode")
    return parser


def run_cli(args: argparse.Namespace) -> None:
    """Execute CLI generation."""
    output_dir = Path(args.output)
    ranges = build_range_configs(args)
    generated = generate_labels(
        range_configs=ranges,
        output_dir=output_dir,
        middle_code=args.middle_code,
        dpi=args.dpi,
        font_path=args.font,
        overwrite=args.overwrite,
    )
    total = sum(len(files) for files in generated.values())
    print("=" * 60)
    print("Generation complete")
    print(f"Output root: {output_dir.resolve()}")
    print(f"Total files: {total}")
    for prefix in PREFIXES:
        files = generated[prefix]
        if not files:
            continue
        print(f"{prefix} folder: {(output_dir / prefix).resolve()}")
        print(f"{prefix} count: {len(files)}")
        print(f"{prefix} range: {files[0].stem} -> {files[-1].stem}")
    print("=" * 60)

