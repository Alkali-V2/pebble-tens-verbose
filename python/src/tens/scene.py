"""Scene and operation dataclasses.

A ``Scene`` is a fully resolved render plan: an ordered display list of small,
explicit drawing operations. It is not a UI tree and not a raster. Pebble
drawing is painterly (later ops paint over earlier ones), so order is
significant.

Design rules for every op:
- All coordinates and sizes are absolute integer pixels.
- Colors are semantic palette keys, never raw RGB.
- Draw order is explicit; there is no hidden auto-layout.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import layout
from .derived import DerivedState, slot_visible
from .palette import Palette, resolve
from .state import RuntimeState, UserConfig


# --- Operations --------------------------------------------------------------

@dataclass(frozen=True)
class Op:
    """Base class for drawing operations. ``kind`` tags the op for export."""

    kind: str = field(init=False, default="op")


@dataclass(frozen=True)
class FillRect(Op):
    x: int
    y: int
    w: int
    h: int
    color: str  # palette key
    radius: int = 0
    kind: str = field(init=False, default="fill_rect")


@dataclass(frozen=True)
class StrokeRect(Op):
    x: int
    y: int
    w: int
    h: int
    color: str
    radius: int = 0
    kind: str = field(init=False, default="stroke_rect")


@dataclass(frozen=True)
class Line(Op):
    x1: int
    y1: int
    x2: int
    y2: int
    color: str
    width: int = 1
    kind: str = field(init=False, default="line")


@dataclass(frozen=True)
class Text(Op):
    x: int
    y: int
    w: int
    h: int
    text: str
    color: str
    font: str = "GOTHIC_18"  # Pebble system font key
    align: str = "left"  # left | center | right
    kind: str = field(init=False, default="text")


@dataclass(frozen=True)
class Bitmap(Op):
    x: int
    y: int
    resource: str  # resource id declared in package.json
    kind: str = field(init=False, default="bitmap")


@dataclass(frozen=True)
class Pdc(Op):
    """Pebble Draw Command (vector) resource."""

    x: int
    y: int
    resource: str
    kind: str = field(init=False, default="pdc")


@dataclass(frozen=True)
class Gradient(Op):
    """A dithered multi-stop gradient fill (named in palette.GRADIENTS).

    Used for the structured bars. The preview renders it with Floyd-Steinberg
    dithering to the Pebble gamut; on-device this maps to a precomputed bitmap
    or a dithered fill routine.
    """

    x: int
    y: int
    w: int
    h: int
    gradient: str  # key into palette.GRADIENTS
    axis: str = "h"  # "h" (left->right) or "v" (top->bottom)
    span: int = 0  # full extent the ramp maps over; 0 means == w
    offset: int = 0  # source x into the baked grid ramp (== window start on axis)
    src_y: int = 0  # source y into the baked grid ramp (top row this slice samples)
    kind: str = field(init=False, default="gradient")


@dataclass(frozen=True)
class FramebufferPatch(Op):
    """Direct pixel-level control. Use only when truly required."""

    x: int
    y: int
    w: int
    h: int
    data_resource: str
    kind: str = field(init=False, default="framebuffer_patch")


# --- Scene -------------------------------------------------------------------

@dataclass
class Scene:
    width: int
    height: int
    background: str  # palette key
    dark_mode: bool = False  # white-on-black when True
    ops: list[Op] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    def add(self, op: Op) -> "Scene":
        self.ops.append(op)
        return self

    def palette(self) -> Palette:
        return resolve(self.dark_mode)


# --- Builder -----------------------------------------------------------------

def build_scene(
    rt: RuntimeState,
    cfg: UserConfig,
    derived: DerivedState,
    placeholder: str = "dot",
) -> Scene:
    """Create an ordered scene from resolved state.

    This is the single place that turns meaning into drawing instructions.
    Geometry comes entirely from ``layout``; nothing is computed inline.

    ``placeholder`` controls how not-yet-reached (empty) boxes render:
    "dot" (centered 4x4 muted), "block" (muted 10x10), or "outline".
    """
    scene = Scene(
        width=layout.CANVAS_W,
        height=layout.CANVAS_H,
        background="background",
        dark_mode=cfg.dark_mode,
        meta={
            "version": 1,
            "time": f"{rt.hour:02d}:{rt.minute:02d}",
            "date": f"{rt.year:04d}-{rt.month:02d}-{rt.day:02d}",
        },
    )

    # Ten-minute boxes. Each box is BOX x BOX px and fills one pixel-row per
    # minute, so the box holding "now" shows minute_of_box rows of fill:
    #   - completed boxes  -> solid (all rows)
    #   - the current box  -> minute_of_box lines
    #   - future boxes     -> placeholder (see _placeholder)
    # cfg.layout sets the cell shape (3x2 vs 2x3) and thus the box/minute fill
    # axis; cfg.hours_direction sets how hour-blocks populate the grid. Filled
    # areas are "ink"; with cfg.rainbow they instead reveal a spectral gradient
    # spanning the whole grid (the ink acts as a mask).
    layout_key = cfg.layout
    grid = layout.day_rect(layout_key)
    fill_axis = layout.fill_axis(layout_key)

    # Hour-slot backgrounds. Drawn first so everything else paints over them:
    # each hour covered by an active slot gets a muted-accent rectangle behind
    # its hour-block, inflated by SLOT_BG_MARGIN on every side. ``slotted_hours``
    # then lets empty marks (placeholders / the current box's missing part) use
    # the page background instead of "muted", so they read as blank against the
    # slot color.
    slotted_hours = _slot_backgrounds(scene, cfg, rt, layout_key)

    if cfg.rainbow:
        # The spectral gradient is one baked image the size of the whole day
        # grid; every gradient op samples a slice of it (see ``Gradient.offset``
        # / ``Gradient.src_y``). Recording the size here lets the preview rebuild
        # the exact same image the device blits, so they stay pixel-identical.
        scene.meta["spectral_w"] = grid.w
        scene.meta["spectral_h"] = grid.h
    for i in range(144):
        cell = layout.ten_minute_cell(i, layout_key, cfg.hours_direction)
        # Empty marks sit on the page background, or on the slot background when
        # this hour is slotted -> draw them in that color so they read as blank.
        hour = i // layout.BOXES_PER_HOUR
        empty_color = "background" if hour in slotted_hours else "muted"
        if i < derived.ten_minute_index:
            _ink_rect(scene, cell.x, cell.y, cell.w, cell.h, grid, cfg.rainbow)
        elif i == derived.ten_minute_index:
            # Show the whole current box (its missing part as outline or fill),
            # then the completed-minute lines on top.
            if cfg.box_missing_style == "fill":
                scene.add(FillRect(cell.x, cell.y, cell.w, cell.h, empty_color))
            else:
                scene.add(StrokeRect(cell.x, cell.y, cell.w, cell.h, empty_color))
            _fill_lines(
                scene, cell, derived.minute_of_box,
                fill_axis, grid, cfg.rainbow,
            )
        else:
            _placeholder(scene, cell, placeholder, empty_color)

    # Three bars under the grid: a top bar split in half (left | right) and the
    # long bottom bar. Each fills up to its progress over a "muted" track. What
    # each shows is set by cfg.bars_identity ("left|right|long"); the colors are
    # positional regardless of identity -> left takes color1, right takes color2
    # ("orange"/"blue"/"gray" are palette keys, used directly), and the long bar
    # is solid ink. In rainbow mode both top bars become the contrasty gray and
    # the long bar is the spectral gradient (mirroring the boxes).
    ms = cfg.bars_missing_style
    fractions = {
        "day": derived.fraction_of_day,
        "week": derived.fraction_of_week,
        "month": derived.fraction_of_month,
        "year": derived.fraction_of_year,
        "life": derived.fraction_of_life,
        "slot1": derived.fraction_of_slot1,
        "slot2": derived.fraction_of_slot2,
    }
    left_id, right_id, long_id = cfg.bars_identity.split("|")
    left_color = "gray" if cfg.rainbow else cfg.color1
    right_color = "gray" if cfg.rainbow else cfg.color2
    _structured_bar(scene, layout.month_bar(layout_key), [(1.0, left_color)],
                    fractions[left_id], ms)
    _structured_bar(scene, layout.year_bar(layout_key), [(1.0, right_color)],
                    fractions[right_id], ms)
    long_bar = layout.life_bar(layout_key)
    if cfg.rainbow:
        _gradient_bar(scene, long_bar, "spectral", fractions[long_id], ms)
    else:
        _structured_bar(scene, long_bar, [(1.0, "ink")], fractions[long_id], ms)

    return scene


# --- Hour-slot backgrounds ---------------------------------------------------

def _slot_hours(start: int, end: int) -> list[int]:
    """Hours covered by a slot: start inclusive, end exclusive, wrapping past
    midnight (e.g. 23->7 is 23,0,1..6). start == end means an empty slot."""
    hours: list[int] = []
    h = start
    while h != end:
        hours.append(h)
        h = (h + 1) % layout.HOURS_PER_DAY
    return hours


def _slot_backgrounds(
    scene: Scene, cfg: UserConfig, rt: RuntimeState, layout_key: str
) -> set[int]:
    """Paint a colored rectangle behind every hour-block covered by an active
    slot, using the slot's resolved color1/color2. Slots are applied in order
    (1->4), so a later slot's color overrides an earlier one for any hour they
    share. Returns the set of hours that got a background."""
    is_weekend = rt.weekday >= 5  # weekday: 0=Mon .. 6=Sun
    slots = (
        (cfg.slot1_start, cfg.slot1_end, cfg.slot1_visibility, cfg.slot1_color),
        (cfg.slot2_start, cfg.slot2_end, cfg.slot2_visibility, cfg.slot2_color),
        (cfg.slot3_start, cfg.slot3_end, cfg.slot3_visibility, cfg.slot3_color),
        (cfg.slot4_start, cfg.slot4_end, cfg.slot4_visibility, cfg.slot4_color),
    )
    # Resolve, per hour, the color of the last active slot covering it. A slot
    # set to "muted" is always the soft gray; otherwise it references color1 or
    # color2, where "orange"/"blue" draw as themselves and "gray" also reads as
    # "muted". Rainbow mode drops accents everywhere (like the month/year bars),
    # so every slot falls back to "muted".
    hour_color: dict[int, str] = {}
    for start, end, visibility, color_ref in slots:
        if not slot_visible(visibility, is_weekend):
            continue
        if cfg.rainbow or color_ref == "muted":
            slot_color = "muted"
        else:
            choice = cfg.color1 if color_ref == "color1" else cfg.color2
            slot_color = "muted" if choice == "gray" else choice
        for hour in _slot_hours(start, end):
            hour_color[hour] = slot_color

    m = layout.SLOT_BG_MARGIN
    for hour, color in hour_color.items():
        block = layout.hour_block(hour, layout_key, cfg.hours_direction)
        scene.add(FillRect(
            block.x - m, block.y - m, block.w + 2 * m, block.h + 2 * m, color
        ))
    return set(hour_color)


# Size of the centered "dot" placeholder, px.
PLACEHOLDER_DOT = 4


def _placeholder(
    scene: Scene, cell: layout.Rect, style: str, color: str = "muted"
) -> None:
    """Render an empty (not-yet-reached) box in ``color`` (muted by default, or
    the page background when the box sits on a slot background).

    "dot"     -> centered PLACEHOLDER_DOT square
    "block"   -> full fill
    "outline" -> outline
    """
    if style == "block":
        scene.add(FillRect(cell.x, cell.y, cell.w, cell.h, color))
    elif style == "outline":
        scene.add(StrokeRect(cell.x, cell.y, cell.w, cell.h, color))
    else:  # "dot"
        d = PLACEHOLDER_DOT
        ox = cell.x + (cell.w - d) // 2
        oy = cell.y + (cell.h - d) // 2
        scene.add(FillRect(ox, oy, d, d, color))


def _ink_rect(
    scene: Scene, x: int, y: int, w: int, h: int,
    grid: layout.Rect, rainbow: bool,
) -> None:
    """Draw a filled grid region: solid ink, or a slice of the grid-wide
    spectral gradient when ``rainbow`` is set (the region masks the gradient).
    """
    if rainbow:
        # Slice of the grid-wide baked ramp at this region's position: source x
        # is offset, source y is the row within the grid (matches the device's
        # blit from (x - grid.x, y - grid.y)).
        scene.add(Gradient(
            x, y, w, h, "spectral", "h",
            span=grid.w, offset=x - grid.x, src_y=y - grid.y,
        ))
    else:
        scene.add(FillRect(x, y, w, h, "ink"))


def _fill_lines(
    scene: Scene,
    cell: layout.Rect,
    count: int,
    axis: str,
    grid: layout.Rect,
    rainbow: bool,
) -> None:
    """Fill ``count`` 1px lines of a box (1 line == 1 completed minute).

    axis "vertical"   -> horizontal rows stacked from the top.
    axis "horizontal" -> vertical columns stacked from the left.
    """
    if axis == "horizontal":
        cols = min(cell.w, max(0, count))
        if cols == 0:
            return
        _ink_rect(scene, cell.x, cell.y, cols, cell.h, grid, rainbow)
    else:  # vertical
        rows = min(cell.h, max(0, count))
        if rows == 0:
            return
        _ink_rect(scene, cell.x, cell.y, cell.w, rows, grid, rainbow)


def _missing_track(scene: Scene, rect: layout.Rect, missing_style: str) -> None:
    """Render the bar's missing background: muted outline border or muted fill."""
    if missing_style == "fill":
        scene.add(FillRect(rect.x, rect.y, rect.w, rect.h, "muted"))
    else:  # "outline"
        scene.add(StrokeRect(rect.x, rect.y, rect.w, rect.h, "muted"))


def _structured_bar(
    scene: Scene,
    rect: layout.Rect,
    segments: list[tuple[float, str]],
    progress: float,
    missing_style: str = "outline",
) -> None:
    """Draw a bar split into solid color ``segments`` (no inner margin).

    ``segments`` is a list of (width_fraction, color_key). The missing part is
    drawn first (outline border or light-gray fill); solid segments are then
    emitted left-to-right up to ``progress`` (0..1).
    """
    progress = min(1.0, max(0.0, progress))
    _missing_track(scene, rect, missing_style)
    fill_right = rect.x + round(rect.w * progress)
    x = rect.x
    for i, (frac, color) in enumerate(segments):
        # Last segment absorbs rounding so a full bar reaches the right edge.
        seg_w = (rect.right - x) if i == len(segments) - 1 else round(rect.w * frac)
        draw_w = min(seg_w, fill_right - x)
        if draw_w > 0:
            scene.add(FillRect(x, rect.y, draw_w, rect.h, color))
        x += seg_w
        if x >= fill_right:
            break


def _gradient_bar(
    scene: Scene,
    rect: layout.Rect,
    gradient: str,
    progress: float,
    missing_style: str = "outline",
) -> None:
    """Draw a single continuous gradient bar revealed up to ``progress``.

    The ramp maps across the full bar width (``span``) but only the filled
    portion is drawn, so the colors stay anchored to the whole span as it
    fills. The missing tail is an outline border or light-gray fill.
    """
    progress = min(1.0, max(0.0, progress))
    _missing_track(scene, rect, missing_style)
    fill_w = round(rect.w * progress)
    if fill_w > 0:
        scene.add(Gradient(rect.x, rect.y, fill_w, rect.h, gradient, "h", span=rect.w))
