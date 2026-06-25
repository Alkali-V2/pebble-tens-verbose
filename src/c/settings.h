// User settings, mirroring python/src/tens/state.py UserConfig. Loaded from
// persistent storage and updated from the PebbleKit JS config page.
#pragma once
#include <pebble.h>

// Which trio of metrics the three bars show (left | right | long). Mirrors
// UserConfig.bars_identity / _BARS_IDENTITIES.
enum {
  TENS_BARS_MONTH_YEAR_LIFE = 0,  // month | year  | life
  TENS_BARS_WEEK_MONTH_YEAR = 1,  // week  | month | year
  TENS_BARS_SLOT1_WEEK_MONTH = 2, // slot1 | week  | month
  TENS_BARS_SLOT1_SLOT2_WEEK = 3, // slot1 | slot2 | week
  TENS_BARS_DAY_MONTH_LIFE = 4,   // day   | month | life  (supports number overlays)
};

// Day the week bar starts on (mirrors UserConfig.start_of_the_week).
enum {
  TENS_WEEK_MONDAY = 0,
  TENS_WEEK_SUNDAY = 1,
};

// The accent choice for color1/color2 (mirrors UserConfig.color1/color2).
enum {
  TENS_COLOR_ORANGE = 0,
  TENS_COLOR_BLUE = 1,
  TENS_COLOR_GRAY = 2,
};

// A slot's color reference (mirrors UserConfig.slotN_color).
enum {
  TENS_SLOT_COLOR1 = 0,  // follow color1
  TENS_SLOT_COLOR2 = 1,  // follow color2
  TENS_SLOT_MUTED = 2,   // always the soft "muted" gray
};

// When a slot is shown (mirrors UserConfig.slotN_visibility).
enum {
  TENS_VIS_NEVER = 0,
  TENS_VIS_WEEKDAYS = 1,
  TENS_VIS_WEEKENDS = 2,
  TENS_VIS_ALWAYS = 3,
};

#define TENS_NUM_SLOTS 4

// One hour-slot: o'clock [start, end) (wraps past midnight), a visibility rule,
// and which color it paints its background with.
typedef struct {
  int start;       // 0..23, inclusive
  int end;         // 0..23, exclusive (wraps when end <= start)
  int visibility;  // TENS_VIS_*
  int color;       // TENS_SLOT_*
} TensSlot;

typedef struct {
  bool rainbow;          // spectral gradient mask over the inked grid/long bar
  bool dark_mode;        // true=black background/white ink, false=white/black
  bool layout_4x6;       // true="4x6" (3x2 cells), false="6x4" (2x3 cells).
                         // Drives the box + minute-line fill axis.
  bool hours_horizontal; // hour-block order: true=row-major, false=column-major
  bool bars_missing_fill; // top/long bars' missing part:
                          //   false=outline, true=muted fill
  bool box_missing_fill; // current 10-min block's missing part:
                          //   false=outline, true=muted fill
  bool bar_numbers;      // day/month numbers in the Day/Month/Life bars
  bool minute_number;    // minute-of-block digit in the current 10-min box
  int color1;            // TENS_COLOR_* : left top bar + slots set to color1
  int color2;            // TENS_COLOR_* : right top bar + slots set to color2
  int bar_set;           // TENS_BARS_* : which trio the three bars show
  int start_of_week;     // TENS_WEEK_* : day the week bar starts on
  int birth_year;
  int birth_month;       // 1..12
  int birth_day;         // 1..31
  int life_span_years;
  TensSlot slots[TENS_NUM_SLOTS];
} TensSettings;

// Access the current settings (valid after tens_settings_init).
const TensSettings *tens_settings(void);

// Load from persistent storage, falling back to defaults.
void tens_settings_init(void);

// Apply an incoming config dictionary (from pkjs), then persist it.
// Returns true if anything changed (caller should redraw).
bool tens_settings_apply(DictionaryIterator *iter);
