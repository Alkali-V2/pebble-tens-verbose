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

# name -> extra UserConfig kwargs. Birth date is shared. Screen-simulator mode
# (the muted on-panel look) is a render option, applied to every shot via the
# --screen-sim flag rather than baked per shot.
SHOTS: dict[str, dict] = {
    "s01_light_mode": dict(),
    "s02_dark_mode": dict(dark_mode=True),
    "s03_light_mode_slot_muted": dict(slot1_visibility="always", slot1_color="muted"),
    "s04_light_mode_slots": dict(slot1_visibility="always", slot2_visibility="always"),
    "s05_dark_mode_slots": dict(dark_mode=True, slot1_visibility="always", slot2_visibility="always"),
    "s06_rainbow": dict(rainbow=True),
    "s07_rainbow_dark": dict(rainbow=True, dark_mode=True),
    "s08_rainbow_slots": dict(rainbow=True, slot1_visibility="always"),
    "s09_rainbow_slots_dark": dict(rainbow=True, dark_mode=True, slot1_visibility="always"),
}


def render_all(out_dir: str | Path, screen: bool = False) -> list[Path]:
    """Render every screenshot in ``SHOTS`` into ``out_dir`` (one PNG each).

    ``screen`` turns on screen-simulator mode (colors as the emery panel
    displays them) for the whole batch.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rt = RuntimeState.from_datetime(_SAMPLE)
    sim = SimulatorConfig(screen_simulator_mode=screen)
    written: list[Path] = []
    for name, kwargs in SHOTS.items():
        cfg = UserConfig(**_BIRTH, **kwargs)
        scene = build_scene(rt, cfg, derive(rt, cfg))
        written.append(render_png(scene, out_dir / f"{name}.png", sim))
    return written


def main(argv: list[str] | None = None) -> int:
    default_out = Path(__file__).resolve().parents[2] / "img" / "screenshots"
    parser = argparse.ArgumentParser(description="Render Tens preview screenshots.")
    parser.add_argument("-o", "--out", default=str(default_out), help="output directory")
    parser.add_argument(
        "--screen-sim", action="store_true",
        help="render colors as the emery panel displays them (screen simulator)",
    )
    args = parser.parse_args(argv)
    for path in render_all(args.out, screen=args.screen_sim):
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
