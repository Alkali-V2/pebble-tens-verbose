"""Raster preview generation.

Renders a ``Scene`` to a Pebble-sized PNG for desktop iteration. The PNG is a
development/test artifact only — the scene (display list) remains the source of
truth, not the image.
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path

from PIL import Image, ImageDraw

from .derived import derive
from .palette import gradient_stops
from .scene import (
    Bitmap,
    FillRect,
    FramebufferPatch,
    Gradient,
    Line,
    Pdc,
    Scene,
    StrokeRect,
    Text,
    build_scene,
)
from .state import RuntimeState, SimulatorConfig, UserConfig

_ALIGN = {"left": "la", "center": "ma", "right": "ra"}

# Pebble Time 2 renders 2 bits per channel: 4 levels per channel, 64 colors.
_PEBBLE_LEVELS = (0, 85, 170, 255)


def _pebble_palette_image() -> Image.Image:
    """A 'P'-mode image whose palette is the full Pebble 64-color gamut."""
    pal: list[int] = []
    for r in _PEBBLE_LEVELS:
        for g in _PEBBLE_LEVELS:
            for b in _PEBBLE_LEVELS:
                pal += [r, g, b]
    pim = Image.new("P", (1, 1))
    pim.putpalette(pal + [0] * (768 - len(pal)))
    return pim


_PEBBLE_PALETTE = _pebble_palette_image()


def _lerp_stops(stops: list[tuple[int, int, int]], t: float) -> tuple[int, int, int]:
    """Interpolate a multi-stop gradient at position ``t`` in [0, 1]."""
    if len(stops) == 1 or t <= 0:
        return stops[0] if t <= 0 else stops[-1]
    if t >= 1:
        return stops[-1]
    span = t * (len(stops) - 1)
    i = int(span)
    f = span - i
    a, b = stops[i], stops[i + 1]
    return tuple(round(a[c] + (b[c] - a[c]) * f) for c in range(3))


def dither_gradient(
    width: int,
    height: int,
    stops: list[tuple[int, int, int]],
    axis: str = "h",
    span: int = 0,
    offset: int = 0,
) -> Image.Image:
    """Build a smooth multi-stop gradient, then Floyd-Steinberg dither it to the
    Pebble 64-color gamut.

    The ramp is mapped over ``span`` pixels (default ``width`` for "h",
    ``height`` for "v"); only ``width``x``height`` are drawn starting at
    ``offset``, so a window of a larger ramp shows the right slice rather than a
    compressed copy. Shared by the preview (per-op) and the resource baker
    (whole-grid), so both consume the exact same dithering.
    """
    grad = Image.new("RGB", (width, height))
    gd = ImageDraw.Draw(grad)
    if axis == "v":
        n = max(1, (span or height) - 1)
        for j in range(height):
            gd.line([(0, j), (width - 1, j)], fill=_lerp_stops(stops, (offset + j) / n))
    else:
        n = max(1, (span or width) - 1)
        for i in range(width):
            gd.line([(i, 0), (i, height - 1)], fill=_lerp_stops(stops, (offset + i) / n))
    dithered = grad.quantize(palette=_PEBBLE_PALETTE, dither=Image.Dither.FLOYDSTEINBERG)
    return dithered.convert("RGB")


def _render_gradient(op: Gradient, screen: bool = False) -> Image.Image:
    """Dither the gradient op to the Pebble gamut (see ``dither_gradient``).

    ``screen`` selects the muted screen-simulator stop set.
    """
    return dither_gradient(
        op.w, op.h, gradient_stops(op.gradient, screen), op.axis, op.span, op.offset
    )


def render_image(scene: Scene, sim: SimulatorConfig | None = None) -> Image.Image:
    """Render a scene to a Pillow ``Image`` in RGB.

    Spectral gradients are drawn exactly as the device draws them: one baked
    whole-grid ramp (``scene.meta['spectral_w' / 'spectral_h']``) is dithered
    once, and each gradient op blits the same slice the C runtime blits, so the
    preview is pixel-identical to the watch rather than re-dithering per box.

    ``sim.screen_simulator_mode`` draws every color — solid palette colors and
    gradient stops alike — in its muted on-panel form (see ``palette``).
    """
    screen = bool(sim and sim.screen_simulator_mode)
    pal = scene.palette()
    img = Image.new("RGB", (scene.width, scene.height), pal.rgb(scene.background, screen))
    draw = ImageDraw.Draw(img)

    baked: dict[tuple[str, int, int], Image.Image] = {}

    def _baked(name: str, w: int, h: int) -> Image.Image:
        key = (name, w, h)
        if key not in baked:
            baked[key] = dither_gradient(w, h, gradient_stops(name, screen), axis="h")
        return baked[key]

    for op in scene.ops:
        if isinstance(op, FillRect):
            draw.rectangle(
                [op.x, op.y, op.x + op.w - 1, op.y + op.h - 1],
                fill=pal.rgb(op.color, screen),
            )
        elif isinstance(op, StrokeRect):
            draw.rectangle(
                [op.x, op.y, op.x + op.w - 1, op.y + op.h - 1],
                outline=pal.rgb(op.color, screen),
            )
        elif isinstance(op, Line):
            draw.line([op.x1, op.y1, op.x2, op.y2], fill=pal.rgb(op.color, screen),
                      width=op.width)
        elif isinstance(op, Text):
            anchor = _ALIGN.get(op.align, "la")
            tx = op.x if op.align == "left" else (
                op.x + op.w // 2 if op.align == "center" else op.x + op.w
            )
            draw.text((tx, op.y), op.text, fill=pal.rgb(op.color, screen), anchor=anchor)
        elif isinstance(op, Gradient):
            if op.w > 0 and op.h > 0:
                gw = scene.meta.get("spectral_w")
                gh = scene.meta.get("spectral_h")
                if gw and gh:
                    # Blit the device's exact slice of the baked whole-grid ramp.
                    box = (op.offset, op.src_y, op.offset + op.w, op.src_y + op.h)
                    img.paste(_baked(op.gradient, gw, gh).crop(box), (op.x, op.y))
                else:  # standalone op (no baked-grid size) -> dither in place
                    img.paste(_render_gradient(op, screen), (op.x, op.y))
        elif isinstance(op, (Bitmap, Pdc, FramebufferPatch)):
            # Resource-backed ops are placeholders in the preview; draw a marker
            # box so layout is still visible without the bundled asset.
            x, y = op.x, op.y
            draw.rectangle([x, y, x + 8, y + 8], outline=pal.rgb("ink", screen))
        else:  # pragma: no cover - defensive
            raise TypeError(f"cannot preview op {op!r}")

    return img


def render_png(scene: Scene, path: str | Path, sim: SimulatorConfig | None = None) -> Path:
    """Render a scene and write it to ``path`` as PNG."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    render_image(scene, sim).save(path, "PNG")
    return path


def _default_scene() -> Scene:
    """A sample scene for ``main`` (uses today's date, a placeholder birthday)."""
    now = _dt.datetime(2026, 8, 12, 15, 37)  # deterministic sample
    rt = RuntimeState.from_datetime(now)
    cfg = UserConfig(birth_year=1990, birth_month=4, birth_day=12)
    return build_scene(rt, cfg, derive(rt, cfg))


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Render a Tens scene to PNG.")
    parser.add_argument(
        "-o", "--out", default="../previews/current.png", help="output PNG path"
    )
    parser.add_argument(
        "--screen-sim", action="store_true",
        help="render colors as the emery panel displays them (screen simulator)",
    )
    args = parser.parse_args(argv)
    sim = SimulatorConfig(screen_simulator_mode=args.screen_sim)
    out = render_png(_default_scene(), args.out, sim)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
