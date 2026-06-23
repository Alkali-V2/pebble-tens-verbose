import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "python" / "src"))

from tens.derived import derive
from tens.state import RuntimeState, UserConfig


def _rt(year=2026, month=6, day=18, weekday=3, hour=14, minute=30):
    return RuntimeState(year, month, day, weekday, hour, minute)


def test_ten_minute_index():
    cfg = UserConfig(birth_year=1990, birth_month=4, birth_day=12)
    # 14:30 -> (14*60 + 30) // 10 = 87
    assert derive(_rt(hour=14, minute=30), cfg).ten_minute_index == 87
    assert derive(_rt(hour=0, minute=0), cfg).ten_minute_index == 0
    assert derive(_rt(hour=23, minute=59), cfg).ten_minute_index == 143


def test_age_before_and_after_birthday():
    cfg = UserConfig(birth_year=1990, birth_month=6, birth_day=20)
    # Birthday not yet reached this year.
    assert derive(_rt(year=2026, month=6, day=18), cfg).age_years == 35
    # Birthday passed.
    assert derive(_rt(year=2026, month=6, day=21), cfg).age_years == 36


def test_days_until_birthday_nonnegative():
    cfg = UserConfig(birth_year=1990, birth_month=6, birth_day=20)
    d = derive(_rt(year=2026, month=6, day=18), cfg)
    assert d.days_until_birthday == 2


def test_fractions_in_range():
    cfg = UserConfig(birth_year=1990, birth_month=4, birth_day=12)
    d = derive(_rt(), cfg)
    for f in (d.fraction_of_day, d.fraction_of_month, d.fraction_of_year, d.fraction_of_life):
        assert 0.0 <= f <= 1.0


def test_start_of_week_shifts_week_fraction():
    base = dict(birth_year=1990, birth_month=4, birth_day=12)
    # Sunday (weekday 6) at midnight: full week elapsed Monday-start, fresh start
    # (0) Sunday-start.
    sun = _rt(weekday=6, hour=0, minute=0)
    assert derive(sun, UserConfig(**base, start_of_the_week="Monday")).fraction_of_week == 6 / 7
    assert derive(sun, UserConfig(**base, start_of_the_week="Sunday")).fraction_of_week == 0.0
    # Monday (weekday 0) at midnight: fresh start Monday-start, day 1 Sunday-start.
    mon = _rt(weekday=0, hour=0, minute=0)
    assert derive(mon, UserConfig(**base, start_of_the_week="Monday")).fraction_of_week == 0.0
    assert derive(mon, UserConfig(**base, start_of_the_week="Sunday")).fraction_of_week == 1 / 7
