"""Exact geometry on the 200×228 Pebble Time 2 canvas.

All layout decisions are resolved here, before the scene is built. Everything
is integer pixels so geometry is deterministic and the resulting scene
contains no hidden auto-layout.

Mental model — a grid of grids:

    day   = grid of 24 hour-blocks      (e.g. 6 wide x 4 tall)
    hour  = grid of 6 ten-minute boxes  (e.g. 2 wide x 3 tall)
    box   = one BOX x BOX cell

6 x 4 hour-blocks, each holding 2 x 3 boxes, makes a 12 x 12 field of boxes,
which is 144 = one full day of ten-minute intervals.
"""

from __future__ import annotations

from dataclasses import dataclass

# Pebble Time 2 display.
CANVAS_W = 200
CANVAS_H = 228

# --- Unit sizes (tune these; everything else is derived) ---------------------
BOX = 10  # edge of one ten-minute box, px
CELL_GAP = 3  # small gap: between boxes *inside* an hour-block
BLOCK_GAP = 8  # big gap: between hour-blocks
SLOT_BG_MARGIN = 3  # margin around the slots

# Time structure (fixed facts, not style).
HOURS_PER_DAY = 24
BOXES_PER_HOUR = 6


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    w: int
    h: int

    @property
    def right(self) -> int:
        return self.x + self.w

    @property
    def bottom(self) -> int:
        return self.y + self.h


@dataclass(frozen=True)
class GridSpec:
    """How the day's 24 hour-blocks and each block's 6 boxes are arranged.

    ``blocks_x`` x ``blocks_y`` must be 24; ``cell_x`` x ``cell_y`` must be 6.
    """

    blocks_x: int  # hour-blocks across
    blocks_y: int  # hour-blocks down
    cell_x: int  # boxes across, inside one block
    cell_y: int  # boxes down, inside one block

    def __post_init__(self) -> None:
        assert self.blocks_x * self.blocks_y == HOURS_PER_DAY
        assert self.cell_x * self.cell_y == BOXES_PER_HOUR

    # Pixel size of one hour-block.
    @property
    def block_w(self) -> int:
        return self.cell_x * BOX + (self.cell_x - 1) * CELL_GAP

    @property
    def block_h(self) -> int:
        return self.cell_y * BOX + (self.cell_y - 1) * CELL_GAP

    # Pixel size of the whole day field.
    @property
    def grid_w(self) -> int:
        return self.blocks_x * self.block_w + (self.blocks_x - 1) * BLOCK_GAP

    @property
    def grid_h(self) -> int:
        return self.blocks_y * self.block_h + (self.blocks_y - 1) * BLOCK_GAP


# Keys are "columns x rows" of hour-blocks.
LAYOUTS = {
    # 6 cols x 4 rows of hour-blocks; each block 2 wide x 3 tall (2x3 cells).
    # Half-hours are vertical columns -> boxes/minutes fill vertically.
    "6x4": GridSpec(blocks_x=6, blocks_y=4, cell_x=2, cell_y=3),
    # 4 cols x 6 rows of hour-blocks; each block 3 wide x 2 tall (3x2 cells).
    # Half-hours are horizontal rows -> boxes/minutes fill horizontally.
    "4x6": GridSpec(blocks_x=4, blocks_y=6, cell_x=3, cell_y=2),
}

# Fill direction the boxes/minutes populate, derived from the cell shape.
def fill_axis(layout: str = "4x6") -> str:
    return "horizontal" if get_spec(layout).cell_x == 3 else "vertical"

# Two bar slots under the grid: a top bar (split into week/month/year thirds)
# and a bottom bar (life).
BAR_H = 10
GRID_BAR_GAP = 10  # gap between the 10-minute grid and the first bar
BAR_GAP = 6  # gap between the two bars
N_BARS = 2
SUB_GAP = BLOCK_GAP  # gap between week/month/year bars == gap between hour-blocks


def get_spec(layout: str = "4x6") -> GridSpec:
    return LAYOUTS[layout]


# --- Origins -----------------------------------------------------------------
# Center the (grid + bars) block vertically; center the grid horizontally.

def _grid_origin(spec: GridSpec) -> tuple[int, int]:
    bars_total = GRID_BAR_GAP + N_BARS * BAR_H + (N_BARS - 1) * BAR_GAP
    content_h = spec.grid_h + bars_total
    origin_x = (CANVAS_W - spec.grid_w) // 2
    origin_y = (CANVAS_H - content_h) // 2
    return origin_x, origin_y


def day_rect(layout: str = "4x6") -> Rect:
    """Bounding rect of the whole 144-box day field."""
    spec = get_spec(layout)
    ox, oy = _grid_origin(spec)
    return Rect(ox, oy, spec.grid_w, spec.grid_h)


def hour_block(hour: int, layout: str = "4x6", direction: str = "vertical") -> Rect:
    """Bounding rect of one hour-block (hour 0..23).

    ``direction`` sets the order hour-blocks populate the grid:
      - "vertical" (column-major): hour 1 is directly below hour 0.
      - "horizontal" (row-major): hour 1 is directly right of hour 0.
    """
    if not (0 <= hour < HOURS_PER_DAY):
        raise ValueError("hour must be in 0..23")
    spec = get_spec(layout)
    ox, oy = _grid_origin(spec)
    if direction == "horizontal":
        bcol = hour % spec.blocks_x
        brow = hour // spec.blocks_x
    else:  # vertical
        brow = hour % spec.blocks_y
        bcol = hour // spec.blocks_y
    x = ox + bcol * (spec.block_w + BLOCK_GAP)
    y = oy + brow * (spec.block_h + BLOCK_GAP)
    return Rect(x, y, spec.block_w, spec.block_h)


def ten_minute_cell(
    index: int, layout: str = "4x6", direction: str = "vertical"
) -> Rect:
    """Box rect for ten-minute slot ``index`` (0..143), chronological order.

    The 6 boxes of an hour are laid out so the first half-hour (boxes 0-2)
    forms a single line of three:
      - 3-wide block (3x2): boxes fill across rows -> top row is the 1st
        half-hour, bottom row the 2nd (half-hours stack vertically).
      - 2-wide block (2x3): boxes fill down columns -> left column is the 1st
        half-hour, right column the 2nd (half-hours sit side by side).
    """
    if not (0 <= index <= 143):
        raise ValueError("ten-minute index must be in 0..143")
    spec = get_spec(layout)
    hour, sub = divmod(index, BOXES_PER_HOUR)  # sub = 0..5 within the hour
    block = hour_block(hour, layout, direction)
    if spec.cell_x == 3:  # 3 wide: half-hour is a horizontal row of three
        ccol, crow = sub % 3, sub // 3
    else:  # 2 wide, 3 tall: half-hour is a vertical column of three
        crow, ccol = sub % 3, sub // 3
    x = block.x + ccol * (BOX + CELL_GAP)
    y = block.y + crow * (BOX + CELL_GAP)
    return Rect(x, y, BOX, BOX)


# --- Progress bars below the grid --------------------------------------------

def _bar_rect(slot: int, layout: str = "4x6") -> Rect:
    """Full-width bar slot; slot 0 is directly under the grid."""
    grid = day_rect(layout)
    top = grid.bottom + GRID_BAR_GAP + slot * (BAR_H + BAR_GAP)
    return Rect(grid.x, top, grid.w, BAR_H)


def _split_halves(rect: Rect) -> list[Rect]:
    """Split a bar into two halves separated by SUB_GAP."""
    left_w = (rect.w - SUB_GAP) // 2
    right_x = rect.x + left_w + SUB_GAP
    left = Rect(rect.x, rect.y, left_w, rect.h)
    right = Rect(right_x, rect.y, rect.right - right_x, rect.h)  # absorbs rounding
    return [left, right]


def month_bar(layout: str = "4x6") -> Rect:
    return _split_halves(_bar_rect(0, layout))[0]


def year_bar(layout: str = "4x6") -> Rect:
    return _split_halves(_bar_rect(0, layout))[1]


def life_bar(layout: str = "4x6") -> Rect:
    """The long bottom bar."""
    return _bar_rect(1, layout)
