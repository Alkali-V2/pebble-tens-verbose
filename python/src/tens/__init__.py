"""Tens — Python authoring toolchain for the Tens Pebble watchface.

Treat this package as a watchface compiler: raw state goes in, and a
deterministic scene plus preview/export artifacts come out. The Pebble C
runtime consumes the generated structures.
"""

from .state import RuntimeState, SimulatorConfig, UserConfig
from .derived import DerivedState, derive
from .scene import (
    Scene,
    Op,
    FillRect,
    StrokeRect,
    Line,
    Text,
    Bitmap,
    Pdc,
    Gradient,
    FramebufferPatch,
    build_scene,
)
from .palette import Palette, PaletteColor

__all__ = [
    "RuntimeState",
    "UserConfig",
    "SimulatorConfig",
    "DerivedState",
    "derive",
    "Scene",
    "Op",
    "FillRect",
    "StrokeRect",
    "Line",
    "Text",
    "Bitmap",
    "Pdc",
    "Gradient",
    "FramebufferPatch",
    "build_scene",
    "Palette",
    "PaletteColor",
]

__version__ = "0.1.0"
