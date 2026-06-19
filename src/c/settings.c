#include "settings.h"
#include <string.h>
#include <stdlib.h>

#define SETTINGS_PERSIST_KEY 1

static TensSettings s_settings;

static void set_defaults(void) {
  s_settings = (TensSettings){
      .rainbow = false,
      .dark_mode = false,
      .layout_4x6 = false,  // "6x4" = 6 columns x 4 rows
      .hours_horizontal = true,
      .fill_invert = false,
      .missing_fill = false,
      .birth_year = 1990,
      .birth_month = 4,
      .birth_day = 12,
      .life_span_years = 80,
  };
}

const TensSettings *tens_settings(void) { return &s_settings; }

static int clampi(int v, int lo, int hi) {
  return v < lo ? lo : (v > hi ? hi : v);
}

// Clamp numeric fields to sane ranges. Settings arrive from user input (Clay
// sends parseInt-or-0) and from persisted blobs that may predate a struct
// change, so an out-of-range birth_month would index DAYS_IN_MONTH[] out of
// bounds and a garbage birth_year would spin absolute_days() into a watchdog
// reset (boot loop). Validate here, the single boundary the rest trusts.
static void sanitize(void) {
  s_settings.birth_year = clampi(s_settings.birth_year, 1900, 2200);
  s_settings.birth_month = clampi(s_settings.birth_month, 1, 12);
  s_settings.birth_day = clampi(s_settings.birth_day, 1, 31);
  s_settings.life_span_years = clampi(s_settings.life_span_years, 1, 200);
}

void tens_settings_init(void) {
  set_defaults();
  // Only trust the persisted blob if it matches the current struct size. After
  // a struct-layout change the old blob would load garbage into our fields.
  if (persist_exists(SETTINGS_PERSIST_KEY) &&
      persist_get_size(SETTINGS_PERSIST_KEY) == (int)sizeof(s_settings)) {
    persist_read_data(SETTINGS_PERSIST_KEY, &s_settings, sizeof(s_settings));
  }
  sanitize();
}

// Decode an integer tuple at the width PebbleKit JS actually sent it in. JS
// numbers arrive in the smallest signed type that fits (1/2/4 bytes), so
// reading value->int32 unconditionally pulls in adjacent bytes whenever fewer
// were sent. On real hardware that corrupts the value (the emulator's JS shim
// sends a full 4 bytes, which is why the bug only shows on device). Read by
// t->length instead.
static int32_t tuple_to_int(const Tuple *t) {
  // A number sent as a JS string arrives as a cstring; parse it rather than
  // reinterpreting its bytes as an integer.
  if (t->type == TUPLE_CSTRING) return atoi(t->value->cstring);
  switch (t->length) {
    case 1: return (t->type == TUPLE_UINT) ? t->value->uint8 : t->value->int8;
    case 2: return (t->type == TUPLE_UINT) ? t->value->uint16 : t->value->int16;
    default:
      return (t->type == TUPLE_UINT) ? (int32_t)t->value->uint32 : t->value->int32;
  }
}

// Read a boolean tuple keyed by `key`; pkjs sends 1/0 as an int.
static bool read_bool(DictionaryIterator *iter, uint32_t key, bool current) {
  Tuple *t = dict_find(iter, key);
  return t ? (tuple_to_int(t) != 0) : current;
}

static int read_int(DictionaryIterator *iter, uint32_t key, int current) {
  Tuple *t = dict_find(iter, key);
  return t ? (int)tuple_to_int(t) : current;
}

bool tens_settings_apply(DictionaryIterator *iter) {
  TensSettings prev = s_settings;
  s_settings.rainbow = read_bool(iter, MESSAGE_KEY_RAINBOW, s_settings.rainbow);
  s_settings.dark_mode =
      read_bool(iter, MESSAGE_KEY_DARK_MODE, s_settings.dark_mode);
  s_settings.layout_4x6 =
      read_bool(iter, MESSAGE_KEY_LAYOUT_4X6, s_settings.layout_4x6);
  s_settings.hours_horizontal =
      read_bool(iter, MESSAGE_KEY_HOURS_HORIZONTAL, s_settings.hours_horizontal);
  s_settings.fill_invert =
      read_bool(iter, MESSAGE_KEY_FILL_INVERT, s_settings.fill_invert);
  s_settings.missing_fill =
      read_bool(iter, MESSAGE_KEY_MISSING_STYLE, s_settings.missing_fill);
  s_settings.birth_year =
      read_int(iter, MESSAGE_KEY_BIRTH_YEAR, s_settings.birth_year);
  s_settings.birth_month =
      read_int(iter, MESSAGE_KEY_BIRTH_MONTH, s_settings.birth_month);
  s_settings.birth_day =
      read_int(iter, MESSAGE_KEY_BIRTH_DAY, s_settings.birth_day);
  s_settings.life_span_years =
      read_int(iter, MESSAGE_KEY_LIFE_SPAN_YEARS, s_settings.life_span_years);
  sanitize();

  persist_write_data(SETTINGS_PERSIST_KEY, &s_settings, sizeof(s_settings));
  return memcmp(&prev, &s_settings, sizeof(s_settings)) != 0;
}
