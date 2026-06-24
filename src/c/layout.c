#include "layout.h"

// Bars below the grid.
#define TOP_BAR_H_TALL 18   // top row when numbered: fits the 14px system font
#define TOP_BAR_H_SHORT 10  // top row otherwise: stock thin bar
#define LIFE_BAR_H 10  // the thin full-width life bar (no text, stays slim)
#define GRID_BAR_GAP 10
#define BAR_GAP 6
#define SUB_GAP TENS_BLOCK_GAP   // gap between the two top bars == hour-block gap

void tens_layout_init(TensLayout *L, bool layout_4x6, bool hours_horizontal,
                      bool tall_top_bar) {
  if (layout_4x6) {  // "4x6": 4 cols x 6 rows, cells 3x2
    L->blocks_x = 4;
    L->blocks_y = 6;
    L->cell_x = 3;
    L->cell_y = 2;
  } else {  // "6x4": 6 cols x 4 rows, cells 2x3
    L->blocks_x = 6;
    L->blocks_y = 4;
    L->cell_x = 2;
    L->cell_y = 3;
  }
  L->hours_horizontal = hours_horizontal;
  L->top_bar_h = tall_top_bar ? TOP_BAR_H_TALL : TOP_BAR_H_SHORT;
  L->block_w = L->cell_x * TENS_BOX + (L->cell_x - 1) * TENS_CELL_GAP;
  L->block_h = L->cell_y * TENS_BOX + (L->cell_y - 1) * TENS_CELL_GAP;
  L->grid_w = L->blocks_x * L->block_w + (L->blocks_x - 1) * TENS_BLOCK_GAP;
  L->grid_h = L->blocks_y * L->block_h + (L->blocks_y - 1) * TENS_BLOCK_GAP;
  L->ox = (TENS_CANVAS_W - L->grid_w) / 2;
  int bars_total = GRID_BAR_GAP + L->top_bar_h + BAR_GAP + LIFE_BAR_H;
  L->oy = (TENS_CANVAS_H - (L->grid_h + bars_total)) / 2;
}

GRect tens_day_rect(const TensLayout *L) {
  return GRect(L->ox, L->oy, L->grid_w, L->grid_h);
}

GRect tens_hour_block(const TensLayout *L, int hour) {
  int bcol, brow;
  if (L->hours_horizontal) {  // row-major
    bcol = hour % L->blocks_x;
    brow = hour / L->blocks_x;
  } else {  // column-major
    brow = hour % L->blocks_y;
    bcol = hour / L->blocks_y;
  }
  int x = L->ox + bcol * (L->block_w + TENS_BLOCK_GAP);
  int y = L->oy + brow * (L->block_h + TENS_BLOCK_GAP);
  return GRect(x, y, L->block_w, L->block_h);
}

GRect tens_ten_minute_cell(const TensLayout *L, int index) {
  int hour = index / 6;
  int sub = index % 6;  // 0..5 within the hour
  GRect block = tens_hour_block(L, hour);
  int ccol, crow;
  if (L->cell_x == 3) {  // 3-wide: half-hour is a horizontal row of three
    ccol = sub % 3;
    crow = sub / 3;
  } else {  // 2-wide: half-hour is a vertical column of three
    crow = sub % 3;
    ccol = sub / 3;
  }
  int x = block.origin.x + ccol * (TENS_BOX + TENS_CELL_GAP);
  int y = block.origin.y + crow * (TENS_BOX + TENS_CELL_GAP);
  return GRect(x, y, TENS_BOX, TENS_BOX);
}

// The top bar that carries the day | month numbers; height set in init.
static GRect top_bar(const TensLayout *L) {
  int top = L->oy + L->grid_h + GRID_BAR_GAP;
  return GRect(L->ox, top, L->grid_w, L->top_bar_h);
}

// Top bar split into two halves with SUB_GAP between them.
static GRect half(const TensLayout *L, int i) {
  GRect bar = top_bar(L);
  int left_w = (bar.size.w - SUB_GAP) / 2;
  if (i == 0) return GRect(bar.origin.x, bar.origin.y, left_w, bar.size.h);
  int right_x = bar.origin.x + left_w + SUB_GAP;
  int right = bar.origin.x + bar.size.w;
  return GRect(right_x, bar.origin.y, right - right_x, bar.size.h);  // absorbs remainder
}

GRect tens_month_bar(const TensLayout *L) { return half(L, 0); }
GRect tens_year_bar(const TensLayout *L)  { return half(L, 1); }

// The life bar sits below the top bar, offset by its full height plus the gap.
GRect tens_life_bar(const TensLayout *L) {
  int top = L->oy + L->grid_h + GRID_BAR_GAP + L->top_bar_h + BAR_GAP;
  return GRect(L->ox, top, L->grid_w, LIFE_BAR_H);
}
