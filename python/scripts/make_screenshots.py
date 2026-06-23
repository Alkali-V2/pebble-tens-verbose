#!/usr/bin/env python3
"""Render a series of preview screenshots into img/screenshots/.

Each entry is a named configuration rendered from a fixed sample time, so the
images are deterministic and re-running overwrites them in place. Used for the
README and the app-store listing.

Usage:
    python scripts/make_screenshots.py [-o OUTDIR]
"""

from __future__ import annotations

import argparse
import datetime as _dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tens.derived import derive  # noqa: E402
from tens.preview import render_png  # noqa: E402
from tens.scene import build_scene  # noqa: E402
from tens.state import RuntimeState, SimulatorConfig, UserConfig  # noqa: E402

# Deterministic sample so screenshots are reproducible across runs.
_SAMPLE = _dt.datetime(2026, 8, 12, 15, 37)
_BIRTH = dict(birth_year=1990, birth_month=4, birth_day=12)

# name -> (extra UserConfig kwargs, screen_simulator_mode). Birth date is shared.
SHOTS: dict[str, tuple[dict, bool]] = {
    "light_mode": (dict(), False),
    "dark_mode": (dict(dark_mode=True), False),
    "rainbow": (dict(rainbow=True), False),
    "rainbow_dark": (dict(rainbow=True, dark_mode=True), False),
}


def render_all(out_dir: str | Path) -> list[Path]:
    """Render every screenshot in ``SHOTS`` into ``out_dir`` (one PNG each)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rt = RuntimeState.from_datetime(_SAMPLE)
    written: list[Path] = []
    for name, (kwargs, screen) in SHOTS.items():
        cfg = UserConfig(**_BIRTH, **kwargs)
        sim = SimulatorConfig(screen_simulator_mode=screen)
        scene = build_scene(rt, cfg, derive(rt, cfg))
        written.append(render_png(scene, out_dir / f"{name}.png", sim))
    return written


def main(argv: list[str] | None = None) -> int:
    default_out = Path(__file__).resolve().parents[2] / "img" / "screenshots"
    parser = argparse.ArgumentParser(description="Render Tens preview screenshots.")
    parser.add_argument("-o", "--out", default=str(default_out), help="output directory")
    args = parser.parse_args(argv)
    for path in render_all(args.out):
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
