// Geometry on the 200x228 emery (Pebble Time 2) display, mirroring
// python/src/tens/layout.py. The layout is chosen at runtime from the
// hour-fill direction, so a TensLayout is built once per render.
#pragma once
#include <pebble.h>

#define TENS_CANVAS_W 200
#define TENS_CANVAS_H 228
#define TENS_BOX 10        // edge of one ten-minute box, px
#define TENS_CELL_GAP 3    // gap between boxes inside an hour-block
#define TENS_BLOCK_GAP 8   // gap between hour-blocks
#define TENS_SLOT_BG_MARGIN 4  // hour-slot background grows past its block by this

typedef struct {
  int blocks_x, blocks_y;   // hour-blocks across / down
  int cell_x, cell_y;       // boxes inside one block
  int block_w, block_h;
  int grid_w, grid_h;
  int ox, oy;               // grid origin (centered)
  bool hours_horizontal;    // hour-block order: row-major vs column-major
} TensLayout;

// layout_4x6=true  -> "4x6": 4 cols x 6 rows, cells 3x2, horizontal half-hours.
// layout_4x6=false -> "6x4": 6 cols x 4 rows, cells 2x3, vertical half-hours.
// hours_horizontal sets the order hour-blocks populate the grid.
void tens_layout_init(TensLayout *layout, bool layout_4x6, bool hours_horizontal);

GRect tens_day_rect(const TensLayout *layout);
GRect tens_hour_block(const TensLayout *layout, int hour);
GRect tens_ten_minute_cell(const TensLayout *layout, int index);
GRect tens_month_bar(const TensLayout *layout);  // left half of the top bar
GRect tens_year_bar(const TensLayout *layout);   // right half of the top bar
GRect tens_life_bar(const TensLayout *layout);   // the long bottom bar
