"""Semantic palette and Pebble-compatible color mapping.

Scene operations reference *semantic* palette entries (e.g. ``"ink"``,
``"accent"``) rather than arbitrary RGB. That keeps scenes easy to diff and
lets the C exporter emit the matching ``GColor`` constants.

Pebble Time 2 renders 64 colors (2 bits per channel). Each ``PaletteColor``
records the desktop-preview RGB plus the Pebble ``GColor*`` name used in C.

Every color is defined twice: the ``normal`` value (what we author / what the
device framebuffer holds) and a ``screen`` value (how that color actually looks,
more muted, on the emery panel). The preview's screen-simulator mode draws the
``screen`` value; everything else uses ``normal``. Both are written as HTML hex
so they can be pasted straight from a design tool. The same two-value scheme
applies to gradient stops (see ``GRADIENTS``).
"""

from __future__ import annotations

from dataclasses import dataclass


def hex_rgb(s: str) -> tuple[int, int, int]:
    """Parse an HTML hex color (``"#rrggbb"`` or ``"#rgb"``) into an RGB tuple."""
    s = s.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6:
        raise ValueError(f"not a hex color: {s!r}")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


@dataclass(frozen=True)
class PaletteColor:
    """A single semantic color.

    ``rgb`` is the normal color used everywhere except screen-simulator mode.
    ``gcolor`` is the Pebble C constant (e.g. ``GColorWhite``) emitted by the
    exporter. ``screen_rgb`` is the muted on-panel appearance used by the
    preview's screen-simulator mode; when ``None`` it falls back to ``rgb``.
    """

    rgb: tuple[int, int, int]
    gcolor: str
    screen_rgb: tuple[int, int, int] | None = None

    def display_rgb(self, screen: bool = False) -> tuple[int, int, int]:
        """RGB to draw: the muted ``screen_rgb`` in screen-simulator mode (when
        defined), otherwise the normal ``rgb``."""
        if screen and self.screen_rgb is not None:
            return self.screen_rgb
        return self.rgb


def _pc(normal: str, gcolor: str, screen: str | None = None) -> PaletteColor:
    """Build a ``PaletteColor`` from HTML hex (normal + optional screen)."""
    return PaletteColor(hex_rgb(normal), gcolor, hex_rgb(screen) if screen else None)


class Palette:
    """Named collection of semantic colors."""

    def __init__(self, name: str, colors: dict[str, PaletteColor]) -> None:
        if "background" not in colors:
            raise ValueError("palette must define a 'background' color")
        self.name = name
        self._colors = dict(colors)

    def __contains__(self, key: str) -> bool:
        return key in self._colors

    def __getitem__(self, key: str) -> PaletteColor:
        try:
            return self._colors[key]
        except KeyError as exc:
            raise KeyError(f"unknown palette color {key!r}") from exc

    def rgb(self, key: str, screen: bool = False) -> tuple[int, int, int]:
        return self[key].display_rgb(screen)

    def gcolor(self, key: str) -> str:
        return self[key].gcolor

    def names(self) -> list[str]:
        return list(self._colors)


# Fixed colors (independent of dark_mode), defined as (normal, GColor, screen).
# TODO(screen): the screen hex below are placeholders equal to normal — replace
# each with the muted on-panel value (provided separately) to make screen-
# simulator mode differ from normal.
_BLACK = _pc("#000000", "GColorBlack", "#000000")
_WHITE = _pc("#ffffff", "GColorWhite", "#ffffff")
_DARK_GRAY = _pc("#555555", "GColorDarkGray", "#555555")
_LIGHT_GRAY = _pc("#aaaaaa", "GColorLightGray", "#aaaaaa")
# Two accent colors, each with light / medium / dark shades (planned accent
# system). _ACC1 / _ACC2 are the medium shades, used by the two top bars; the
# _LIGHT / _DARK shades are reserved for upcoming minor details (light shade in
# light mode, dark shade in dark mode).
# TODO(accent): _LIGHT / _DARK hex (and their GColor names) are placeholders
# equal to the medium shade — replace with the real values when provided.
_ACC1 = _pc("#FF5500", "GColorOrange", "#E66E6B")
_ACC1_LIGHT = _pc("#FFAA55", "GColorRajah", "#F1AD93")
_ACC1_DARK = _pc("#AA5500", "GColorWindsorTan", "#9D5B4D")
_ACC2 = _pc("#0055FF", "GColorBlueMoon", "#007DCE")
_ACC2_LIGHT = _pc("#55AAFF", "GColorPictonBlue", "#69B5DD")
_ACC2_DARK = _pc("#0000AA", "GColorDukeBlue", "#004387")


# --- Gradients ---------------------------------------------------------------
# Only the life bar / rainbow grid uses a gradient: a continuous "spectral" ramp
# with no divisions. Each stop is a (normal, screen) pair of HTML hex; the
# preview dithers the chosen set down to the Pebble 64-color gamut so
# intermediate colors still read as a smooth ramp. The device's baked bitmap
# uses the normal stops (the panel mutes them physically); screen-simulator mode
# dithers the screen stops to mimic that.
# TODO(screen): screen hex are placeholders equal to normal — replace with the
# muted values.
GRADIENTS: dict[str, list[tuple[str, str]]] = {
    "spectral": [
        ("#ff0000", "#ff0000"),  # red
        ("#ff5500", "#ff5500"),  # orange
        ("#ffaa00", "#ffaa00"),  # yellow
        ("#55aa55", "#55aa55"),  # green
        ("#55aaaa", "#55aaaa"),  # light blue
        ("#0055aa", "#0055aa"),  # blue
    ],
}


def gradient_stops(name: str, screen: bool = False) -> list[tuple[int, int, int]]:
    """Stops for gradient ``name`` as RGB tuples: the muted screen set when
    ``screen``, otherwise the normal set."""
    try:
        pairs = GRADIENTS[name]
    except KeyError as exc:
        raise KeyError(f"unknown gradient {name!r}") from exc
    return [hex_rgb(p[1] if screen else p[0]) for p in pairs]


def resolve(name: str = "default", dark_mode: bool = False) -> Palette:
    """Build the palette for the chosen background.

    dark_mode=False -> white background, black ink (boxes).
    dark_mode=True  -> black background, white ink.

    "muted" is one contrasty gray used for placeholders, unfilled tracks /
    outlines, and the two top bars in rainbow mode: dark gray on a white
    background, light gray on a black one (so it stays visible in both).
    "accent1"/"accent2" (medium shade) are the non-rainbow top-bar colors.
    """
    return Palette(
        name,
        {
            "background": _BLACK if dark_mode else _WHITE,
            "ink": _WHITE if dark_mode else _BLACK,
            "muted": _DARK_GRAY if dark_mode else _LIGHT_GRAY,
            "gray": _LIGHT_GRAY if dark_mode else _DARK_GRAY,
            # Two accents. "accentN" is the medium shade (the two top bars).
            # "accentN_muted" is the light shade on a white background and the
            # dark shade on a black one (so it reads as muted in either mode).
            "accent1": _ACC1,
            "accent1_muted": _ACC1_DARK if dark_mode else _ACC1_LIGHT,
            "accent2": _ACC2,
            "accent2_muted": _ACC2_DARK if dark_mode else _ACC2_LIGHT,
        },
    )
