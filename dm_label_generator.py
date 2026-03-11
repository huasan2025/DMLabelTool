#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Backward-compatible launcher for local usage."""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from dm_label_tool.main import main  # noqa: E402


if __name__ == "__main__":
    main()

