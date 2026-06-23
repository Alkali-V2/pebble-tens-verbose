"""Derived meaning.

Derived values are *not* stored as independent primary state. They are
computed from ``RuntimeState`` + ``UserConfig`` during preprocessing, then
passed into scene generation.

Mental model:
    RuntimeState = facts from the watch
    UserConfig   = facts from the user
    DerivedState = meaning inferred from those facts
    Scene        = final drawing instructions
"""

from __future__ import annotations

from dataclasses import dataclass

from .state import RuntimeState, UserConfig

# Life is split into four stages; values are each stage's share of the
# lifespan (guessed defaults, easy to retune). They must sum to 1.0.
LIFE_STAGES = (
    ("infancy", 0.15),
    ("first_adulthood", 0.30),
    ("second_adulthood", 0.30),
    ("elder", 0.25),
)


@dataclass(frozen=True)
class DerivedState:
    """Computed values handed to scene generation."""

    age_years: int
    age_days: int
    days_until_birthday: int
    fraction_of_day: float  # 0.0 .. 1.0
    fraction_of_week: float  # 0.0 .. 1.0 (Mon 00:00 -> Sun 24:00)
    fraction_of_month: float  # 0.0 .. 1.0
    fraction_of_year: float  # 0.0 .. 1.0
    fraction_of_life: float  # 0.0 .. 1.0 (clamped)
    ten_minute_index: int  # 0 .. 143  (which 10-minute box of the day)
    minute_of_box: int  # 0 .. 9  (minutes elapsed inside the current box)
    life_stage_fracs: tuple  # infancy, first/second adulthood, elder shares


def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


_DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def _days_in_month(year: int, month: int) -> int:
    if month == 2 and _is_leap(year):
        return 29
    return _DAYS_IN_MONTH[month - 1]


def _days_in_year(year: int) -> int:
    return 366 if _is_leap(year) else 365


def _ordinal(year: int, month: int, day: int) -> int:
    """Proleptic-ish day count usable for differences (not calendar-exact)."""
    days = day
    for m in range(1, month):
        days += _days_in_month(year, m)
    return days


def _day_of_year(year: int, month: int, day: int) -> int:
    return _ordinal(year, month, day)


def _absolute_days(year: int, month: int, day: int) -> int:
    """Total days from a fixed epoch; only differences are meaningful."""
    total = 0
    base = min(year, 1)
    for y in range(base, year):
        total += _days_in_year(y)
    return total + _day_of_year(year, month, day)


def derive(rt: RuntimeState, cfg: UserConfig) -> DerivedState:
    """Compute all derived values from raw runtime state + user config."""
    # Age in whole years (has the birthday occurred yet this year?).
    had_birthday = (rt.month, rt.day) >= (cfg.birth_month, cfg.birth_day)
    age_years = rt.year - cfg.birth_year - (0 if had_birthday else 1)

    age_days = _absolute_days(rt.year, rt.month, rt.day) - _absolute_days(
        cfg.birth_year, cfg.birth_month, cfg.birth_day
    )

    # Days until the next birthday.
    next_bday_year = rt.year + (0 if not had_birthday else 1)
    days_until_birthday = _absolute_days(
        next_bday_year, cfg.birth_month, cfg.birth_day
    ) - _absolute_days(rt.year, rt.month, rt.day)

    minutes_of_day = rt.hour * 60 + rt.minute
    fraction_of_day = minutes_of_day / (24 * 60)

    # rt.weekday is Monday(0)..Sunday(6). For a Sunday-start week, shift so
    # Sunday becomes index 0.
    if cfg.start_of_the_week == "Sunday":
        week_index = (rt.weekday + 1) % 7  # Sunday(0)..Saturday(6)
    else:
        week_index = rt.weekday  # Monday(0)..Sunday(6)
    fraction_of_week = (week_index * 24 * 60 + minutes_of_day) / (7 * 24 * 60)

    fraction_of_month = (rt.day - 1) / _days_in_month(rt.year, rt.month)

    fraction_of_year = (_day_of_year(rt.year, rt.month, rt.day) - 1) / _days_in_year(
        rt.year
    )

    life_days = max(1, cfg.life_span_years * 365)
    fraction_of_life = min(1.0, max(0.0, age_days / life_days))

    ten_minute_index = minutes_of_day // 10
    minute_of_box = rt.minute % 10  # one pixel-row per minute inside the box

    life_stage_fracs = tuple(frac for _, frac in LIFE_STAGES)

    return DerivedState(
        age_years=age_years,
        age_days=age_days,
        days_until_birthday=days_until_birthday,
        fraction_of_day=fraction_of_day,
        fraction_of_week=fraction_of_week,
        fraction_of_month=fraction_of_month,
        fraction_of_year=fraction_of_year,
        fraction_of_life=fraction_of_life,
        ten_minute_index=ten_minute_index,
        minute_of_box=minute_of_box,
        life_stage_fracs=life_stage_fracs,
    )
