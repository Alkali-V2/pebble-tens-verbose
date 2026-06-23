// Semantic palette for the Tens watchface, mirroring python/src/tens/palette.py.
// Emery (Pebble Time 2) renders 64 colors; GColorFromRGB() quantizes 8-bit
// channels to the 2-bit-per-channel gamut.
#pragma once
#include <pebble.h>

// The two accent colors, one shade each. A bar or slot whose user-chosen
// color1/color2 is "orange"/"blue" draws in these; "gray" resolves to a gray
// instead (the contrasty "gray" for bars, the soft "muted" for slot
// backgrounds) -- see resolve_*_color() in render.c. Mirrors _ORANGE/_BLUE in
// python/src/tens/palette.py. (background/ink/muted grays are chosen from
// dark_mode directly in render.c.)
#define TENS_ORANGE GColorFromRGB(0xFF, 0xAA, 0x55)  // #FFAA55 (GColorRajah)
#define TENS_BLUE   GColorFromRGB(0x55, 0xAA, 0xFF)  // #55AAFF (GColorPictonBlue)

// --- Spectral ramp (life bar + rainbow grid mask) ----------------------------
#define TENS_SPECTRAL_STOPS 6
static const uint8_t TENS_SPECTRAL[TENS_SPECTRAL_STOPS][3] = {
  {255, 0, 0},     // red
  {255, 85, 0},    // orange
  {255, 170, 0},   // yellow
  {85, 170, 85},   // green
  {85, 170, 170},  // light blue
  {0, 85, 170},    // blue
};

// Spectral color at position t in [0, 1000] along the ramp.
static inline GColor tens_spectral(int32_t t) {
  if (t < 0) t = 0;
  if (t > 1000) t = 1000;
  const int seg = TENS_SPECTRAL_STOPS - 1;          // 5 segments
  int32_t pos = t * seg;                            // 0..5000
  int idx = pos / 1000;
  if (idx >= seg) idx = seg - 1;
  int32_t frac = pos - (int32_t)idx * 1000;         // 0..1000
  const uint8_t *a = TENS_SPECTRAL[idx];
  const uint8_t *b = TENS_SPECTRAL[idx + 1];
  int r = a[0] + ((int)b[0] - (int)a[0]) * frac / 1000;
  int g = a[1] + ((int)b[1] - (int)a[1]) * frac / 1000;
  int bl = a[2] + ((int)b[2] - (int)a[2]) * frac / 1000;
  return GColorFromRGB(r, g, bl);
}
