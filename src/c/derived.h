// Derived values computed from the clock + settings, mirroring
// python/src/tens/derived.py. Fractions are in permille (0..1000) to avoid
// floating point.
#pragma once
#include <pebble.h>
#include "settings.h"

typedef struct {
  int ten_minute_index;  // 0..143 (current ten-minute box)
  int minute_of_box;     // 0..9 (completed minutes inside the current box)
  int frac_day;          // permille through the day (00:00 -> 24:00)
  int frac_week;         // permille through the week (Mon -> Sun)
  int frac_month;        // permille through the month
  int mday;              // calendar day of month (1..31), for bar overlays
  int mon;               // month number (1..12), for bar overlays
  int frac_year;         // permille through the year (Jan 1 -> Dec 31)
  int frac_life;         // permille through the configured lifespan (clamped)
  int frac_slot1;        // permille through hour-slot 1 (0 when hidden today)
  int frac_slot2;        // permille through hour-slot 2 (0 when hidden today)
} TensDerived;

// Whether a slot (TENS_VIS_*) is shown on a weekend / weekday today. Shared by
// the renderer (slot backgrounds) and the slot-progress bars.
bool tens_slot_visible(int visibility, bool is_weekend);

void tens_derive(const struct tm *now, const TensSettings *cfg, TensDerived *out);
