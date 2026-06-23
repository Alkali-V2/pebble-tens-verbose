#include "render.h"
#include "derived.h"
#include "layout.h"
#include "palette.h"

static int rect_right(GRect r) { return r.origin.x + r.size.w; }
static int rect_bottom(GRect r) { return r.origin.y + r.size.h; }

static int clampi(int v, int lo, int hi) {
  return v < lo ? lo : (v > hi ? hi : v);
}

// Blit the slice of a baked spectral bitmap that lines up with `dst`.
// The bitmap covers the whole day-grid, so a cell at (x, y) samples gradient
// pixel (x - src_origin.x, y - src_origin.y). For the grid, `src_origin` is the
// grid origin; the life bar sits below the grid and passes its own origin so it
// samples the bitmap's top rows (the ramp is horizontal, so any band works).
static void draw_gradient_rect(GContext *ctx, GRect dst, GBitmap *grad,
                               GPoint src_origin) {
  if (!grad || dst.size.w <= 0 || dst.size.h <= 0) return;
  GRect src = GRect(dst.origin.x - src_origin.x, dst.origin.y - src_origin.y,
                    dst.size.w, dst.size.h);
  // Shares the parent's pixel data (no copy); just retargets the draw window.
  GBitmap *sub = gbitmap_create_as_sub_bitmap(grad, src);
  if (!sub) return;
  graphics_draw_bitmap_in_rect(ctx, sub, dst);
  gbitmap_destroy(sub);
}

// Fill a grid rect: a slice of the precomputed spectral gradient when rainbow
// is on (`grad` non-NULL), otherwise solid ink. The gradient image is the
// day-grid, so `grid.origin` aligns the slice to this cell's position.
static void draw_ink_rect(GContext *ctx, GRect r, GRect grid, GBitmap *grad,
                          GColor ink) {
  if (r.size.w <= 0 || r.size.h <= 0) return;
  if (grad) {
    draw_gradient_rect(ctx, r, grad, grid.origin);
    return;
  }
  graphics_context_set_fill_color(ctx, ink);
  graphics_fill_rect(ctx, r, 0, GCornerNone);
}

// The missing (unfilled) part of a bar/box: muted outline border or muted fill.
static void draw_missing(GContext *ctx, GRect bar, bool missing_fill,
                         GColor muted) {
  if (missing_fill) {
    graphics_context_set_fill_color(ctx, muted);
    graphics_fill_rect(ctx, bar, 0, GCornerNone);
  } else {
    graphics_context_set_stroke_color(ctx, muted);
    graphics_draw_rect(ctx, bar);
  }
}

// A solid color bar filled up to progress over a muted track.
static void fill_solid_bar(GContext *ctx, GRect bar, int progress, GColor color,
                           bool missing_fill, GColor muted) {
  draw_missing(ctx, bar, missing_fill, muted);
  progress = clampi(progress, 0, 1000);
  int fill_w = bar.size.w * progress / 1000;
  if (fill_w > 0) {
    graphics_context_set_fill_color(ctx, color);
    graphics_fill_rect(ctx, GRect(bar.origin.x, bar.origin.y, fill_w, bar.size.h),
                       0, GCornerNone);
  }
}

// A spectral-gradient bar filled up to progress over a muted track. The baked
// gradient image is the day-grid and the life bar is the same width and left
// edge as the grid, so the bar's colors align column-for-column with the grid;
// we sample the bitmap's top rows (src origin == bar origin -> src y 0).
static void fill_gradient_bar(GContext *ctx, GRect bar, int progress,
                              GBitmap *grad, bool missing_fill, GColor muted) {
  draw_missing(ctx, bar, missing_fill, muted);
  progress = clampi(progress, 0, 1000);
  int fill_w = bar.size.w * progress / 1000;
  if (fill_w > 0) {
    GRect fill = GRect(bar.origin.x, bar.origin.y, fill_w, bar.size.h);
    draw_gradient_rect(ctx, fill, grad, bar.origin);
  }
}

static void render_grid(GContext *ctx, const TensLayout *L,
                        const TensDerived *d, const TensSettings *cfg,
                        GColor ink, GColor muted, GBitmap *grad) {
  GRect grid = tens_day_rect(L);
  for (int i = 0; i < 144; i++) {
    GRect cell = tens_ten_minute_cell(L, i);
    if (i < d->ten_minute_index) {
      draw_ink_rect(ctx, cell, grid, grad, ink);
    } else if (i == d->ten_minute_index) {
      // Current box: muted missing part, then the completed-minute lines.
      draw_missing(ctx, cell, cfg->grid_missing_fill, muted);
      // Minute lines fill along the cell's long axis (same as the boxes).
      int count = d->minute_of_box;
      GRect fill;
      if (L->cell_x == 3) {
        int cols = clampi(count, 0, cell.size.w);
        int x = cfg->fill_invert ? (rect_right(cell) - cols) : cell.origin.x;
        fill = GRect(x, cell.origin.y, cols, cell.size.h);
      } else {
        int rows = clampi(count, 0, cell.size.h);
        int y = cfg->fill_invert ? (rect_bottom(cell) - rows) : cell.origin.y;
        fill = GRect(cell.origin.x, y, cell.size.w, rows);
      }
      draw_ink_rect(ctx, fill, grid, grad, ink);
    } else {
      // Future box: a centered 4x4 muted dot placeholder.
      int d4 = 4;
      int ox = cell.origin.x + (cell.size.w - d4) / 2;
      int oy = cell.origin.y + (cell.size.h - d4) / 2;
      graphics_context_set_fill_color(ctx, muted);
      graphics_fill_rect(ctx, GRect(ox, oy, d4, d4), 0, GCornerNone);
    }
  }
}

void tens_render(GContext *ctx, GRect bounds, const struct tm *now,
                 const TensSettings *cfg) {
  bool dm = cfg->dark_mode;
  GColor bg = dm ? GColorBlack : GColorWhite;
  GColor ink = dm ? GColorWhite : GColorBlack;
  // Subtle gray (low-contrast): placeholders and unfilled tracks/outlines.
  // Light gray in light mode (on white), dark gray in dark mode (on black).
  GColor muted = dm ? GColorDarkGray : GColorLightGray;
  // Contrasty gray (the inverse of muted): the two top bars' fill in rainbow
  // mode. Dark gray in light mode (on white), light gray in dark mode (on black).
  GColor gray = dm ? GColorLightGray : GColorDarkGray;

  graphics_context_set_fill_color(ctx, bg);
  graphics_fill_rect(ctx, bounds, 0, GCornerNone);

  TensDerived d;
  tens_derive(now, cfg, &d);

  TensLayout L;
  tens_layout_init(&L, cfg->layout_4x6, cfg->hours_horizontal);

  // In rainbow mode the inked grid (and the life bar) reveal a precomputed,
  // dithered spectral gradient instead of solid ink. The image is the day-grid
  // sized for this layout; `grad` stays NULL (solid fallback) if the resource
  // can't be loaded. Loaded once here and freed at the end of the render.
  GBitmap *grad = NULL;
  if (cfg->rainbow) {
    grad = gbitmap_create_with_resource(
        cfg->layout_4x6 ? RESOURCE_ID_SPECTRAL_4X6 : RESOURCE_ID_SPECTRAL_6X4);
  }

  render_grid(ctx, &L, &d, cfg, ink, muted, grad);

  // Three bars in two fixed slots: the top row split into left | right, plus
  // the long bottom bar. The chosen set only decides which metric (and its
  // progress) lands in each slot; the *coloring* is purely positional and the
  // same in both sets:
  //   - bottom full-width bar  -> mirrors the grid: spectral gradient in
  //                               rainbow mode, else ink.
  //   - the two top bars       -> contrasty gray in rainbow mode, else the two
  //                               accent colors (left=accent1, right=accent2).
  int top_left_frac, top_right_frac, bottom_frac;
  if (cfg->bar_set == TENS_BARS_WEEK_MONTH_YEAR) {
    top_left_frac = d.frac_week;
    top_right_frac = d.frac_month;
    bottom_frac = d.frac_year;
  } else {
    top_left_frac = d.frac_month;
    top_right_frac = d.frac_year;
    bottom_frac = d.frac_life;
  }
  GColor top_left_color = cfg->rainbow ? gray : TENS_ACCENT1;
  GColor top_right_color = cfg->rainbow ? gray : TENS_ACCENT2;
  fill_solid_bar(ctx, tens_month_bar(&L), top_left_frac, top_left_color,
                 cfg->bars_missing_fill, muted);
  fill_solid_bar(ctx, tens_year_bar(&L), top_right_frac, top_right_color,
                 cfg->bars_missing_fill, muted);
  if (grad) {
    fill_gradient_bar(ctx, tens_life_bar(&L), bottom_frac, grad,
                      cfg->bars_missing_fill, muted);
  } else {
    fill_solid_bar(ctx, tens_life_bar(&L), bottom_frac, ink,
                   cfg->bars_missing_fill, muted);
  }

  if (grad) gbitmap_destroy(grad);
}
