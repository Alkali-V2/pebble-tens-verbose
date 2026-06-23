#include "derived.h"

static const int DAYS_IN_MONTH[12] = {31, 28, 31, 30, 31, 30,
                                      31, 31, 30, 31, 30, 31};

static bool is_leap(int year) {
  return (year % 4 == 0 && year % 100 != 0) || (year % 400 == 0);
}

static int days_in_month(int year, int month) {  // month 1..12
  if (month == 2 && is_leap(year)) return 29;
  return DAYS_IN_MONTH[month - 1];
}

static int days_in_year(int year) { return is_leap(year) ? 366 : 365; }

static int day_of_year(int year, int month, int day) {  // 1-based
  int d = day;
  for (int m = 1; m < month; m++) d += days_in_month(year, m);
  return d;
}

// Day count from a fixed base year; only differences are meaningful.
static int absolute_days(int year, int month, int day) {
  int total = 0;
  for (int y = 1900; y < year; y++) total += days_in_year(y);
  return total + day_of_year(year, month, day);
}

static int clamp_permille(int v) {
  if (v < 0) return 0;
  if (v > 1000) return 1000;
  return v;
}

void tens_derive(const struct tm *now, const TensSettings *cfg,
                 TensDerived *out) {
  int year = now->tm_year + 1900;
  int month = now->tm_mon + 1;
  int day = now->tm_mday;
  int minutes_of_day = now->tm_hour * 60 + now->tm_min;

  out->ten_minute_index = minutes_of_day / 10;
  out->minute_of_box = now->tm_min % 10;

  // tm_wday is Sunday(0)..Saturday(6). Index the week from the configured start
  // day: Monday-start shifts so Monday is 0; Sunday-start uses tm_wday as-is.
  int wday = (cfg->start_of_week == TENS_WEEK_SUNDAY) ? now->tm_wday
                                                      : (now->tm_wday + 6) % 7;
  out->frac_week = wday * 1000 / 7;
  out->frac_month = (day - 1) * 1000 / days_in_month(year, month);
  out->frac_year = (day_of_year(year, month, day) - 1) * 1000 / days_in_year(year);

  int age_days = absolute_days(year, month, day) -
                 absolute_days(cfg->birth_year, cfg->birth_month, cfg->birth_day);
  int life_days = cfg->life_span_years * 365;
  if (life_days < 1) life_days = 1;
  out->frac_life = clamp_permille(age_days * 1000 / life_days);
}
