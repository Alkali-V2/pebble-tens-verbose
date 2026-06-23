// User settings, mirroring python/src/tens/state.py UserConfig. Loaded from
// persistent storage and updated from the PebbleKit JS config page.
#pragma once
#include <pebble.h>

// Which three metrics the bars show.
enum {
  TENS_BARS_MONTH_YEAR_LIFE = 0,  // month | year, then life
  TENS_BARS_WEEK_MONTH_YEAR = 1,  // week  | month, then year
};

// Day the week bar starts on (mirrors UserConfig.start_of_the_week).
enum {
  TENS_WEEK_MONDAY = 0,
  TENS_WEEK_SUNDAY = 1,
};

typedef struct {
  bool rainbow;          // spectral gradient mask over the inked grid/life bar
  bool dark_mode;        // true=black background/white ink, false=white/black
  bool layout_4x6;       // true="4x6" (3x2 cells), false="6x4" (2x3 cells).
                         // Drives the box + minute-line fill axis.
  bool hours_horizontal; // hour-block order: true=row-major, false=column-major
  bool fill_invert;      // horizontal fill: false=from left, true=from right
                         // vertical fill:   false=from top,  true=from bottom
  bool bars_missing_fill; // month/year/life bars' missing part:
                          //   false=outline, true=muted fill
  bool grid_missing_fill; // current 10-min block's missing part:
                          //   false=outline, true=muted fill
  int bar_set;           // TENS_BARS_* : which trio the three bars show
  int start_of_week;     // TENS_WEEK_* : day the week bar starts on
  int birth_year;
  int birth_month;       // 1..12
  int birth_day;         // 1..31
  int life_span_years;
} TensSettings;

// Access the current settings (valid after tens_settings_init).
const TensSettings *tens_settings(void);

// Load from persistent storage, falling back to defaults.
void tens_settings_init(void);

// Apply an incoming config dictionary (from pkjs), then persist it.
// Returns true if anything changed (caller should redraw).
bool tens_settings_apply(DictionaryIterator *iter);
