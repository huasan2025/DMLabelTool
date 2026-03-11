"""Core behavior tests for label tool."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from dm_label_tool.core import (  # noqa: E402
    allocate_batch_output_dir,
    preview_batch_range,
    validate_batch_job,
)


class CoreTestCase(unittest.TestCase):
    """Non-graphics deterministic tests."""

    def test_preview_range_from_total_quantity(self) -> None:
        job = validate_batch_job("ld", "4000", "0035", "1000", Path("/tmp/out"))
        start, end = preview_batch_range(job)
        self.assertEqual(start, "LD40000035")
        self.assertEqual(end, "LD40001034")

    def test_batch_folder_increment(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = allocate_batch_output_dir("LD", root, when=datetime(2026, 3, 11))
            first.mkdir()
            second = allocate_batch_output_dir("LD", root, when=datetime(2026, 3, 11))
            self.assertEqual(first.name, "LD-20260311")
            self.assertEqual(second.name, "LD-20260311(1)")

    def test_invalid_prefix_rejected(self) -> None:
        with self.assertRaises(Exception):
            validate_batch_job("L1", "4000", "0035", "10", Path("/tmp/out"))


if __name__ == "__main__":
    unittest.main()

