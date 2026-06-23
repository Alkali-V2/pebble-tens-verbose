#!/usr/bin/env python3
"""Render the current scene to ../previews/current.png.

Usage:
    python scripts/make_preview.py [-o OUT]
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tens.preview import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
