"""Raw input state.

Two kinds of raw facts feed the watchface:

- ``RuntimeState`` comes from the watch clock and tick events.
- ``UserConfig`` comes from the phone-side settings page (PebbleKit JS).

Neither holds derived meaning. Season, age, and progress values live in
``derived.py`` and are computed during preprocessing.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeState:
    """Facts that come directly from the watch clock / tick events."""

    year: int
    month: int  # 1-12
    day: int  # 1-31
    weekday: int  # 0=Monday .. 6=Sunday
    hour: int  # 0-23
    minute: int  # 0-59

    def __post_init__(self) -> None:
        _check("month", self.month, 1, 12)
        _check("day", self.day, 1, 31)
        _check("weekday", self.weekday, 0, 6)
        _check("hour", self.hour, 0, 23)
        _check("minute", self.minute, 0, 59)

    @classmethod
    def from_datetime(cls, dt) -> "RuntimeState":
        """Build from a ``datetime.datetime`` (handy for previews/tests)."""
        return cls(
            year=dt.year,
            month=dt.month,
            day=dt.day,
            weekday=dt.weekday(),
            hour=dt.hour,
            minute=dt.minute,
        )


@dataclass(frozen=True)
class UserConfig:
    """Facts entered by the user in the phone-side settings page.

    Birth date is kept as structured integer fields rather than a formatted
    string so age and progress calculations are easy in both Python and C.
    """

    birth_year: int = 1990
    birth_month: int = 4  # 1-12
    birth_day: int = 12  # 1-31
    life_span_years: int = 80  # for life-progress bars / span metrics
    # Appearance / behavior knobs (extend as the settings schema grows).
    # Rainbow: color the inked boxes/minute-lines by a spectral gradient that
    # spans the whole day grid (the ink acts as a mask over the gradient).
    rainbow: bool = False
    dark_mode: bool = False  # False=white bg/black boxes, True=black bg/white boxes
    # Hour-block layout. "4x6" = 3x2 cells (half-hour is a horizontal row),
    # "6x4" = 2x3 cells (half-hour is a vertical column). This drives the box
    # and minute-line fill direction.
    layout: str = "6x4"  # "4x6" | "6x4"
    # Order the hour-blocks populate the grid: "vertical" = column-major (hour
    # 1 below hour 0), "horizontal" = row-major (hour 1 right of hour 0).
    hours_direction: str = "horizontal"  # "vertical" | "horizontal"
    # How the incomplete (missing) part renders, split to mirror the C defaults
    # (settings.c): the bars default to a filled track, the current box to an
    # outline. Each is "outline" (border) or "fill" (light gray).
    bars_missing_style: str = "fill"  # month/year/life bars' missing track
    box_missing_style: str = "fill"  # current box's missing part
    # Which day the week bar starts on.
    start_of_the_week: str = "Monday"  # "Monday" | "Sunday"
    # The two accent colors that bars and slots pick from. The first top bar
    # (month) uses color1, the second (year) uses color2; slots reference
    # color1/color2 via their slotN_color. "gray" resolves per context: bars
    # draw it as "gray", slot backgrounds as "muted".
    color1: str = "orange"  # "orange" | "blue" | "gray"
    color2: str = "blue"  # "orange" | "blue" | "gray"
    # bars identity
    bars_identity: str = "month|year|life" 

    # Coloring of hour slots. Each slot go from o'clock hour X to hour Y,
    # inclusive of the start and exclusive of the end.
    # Every slot will color with a rectangle 4 pixel wider than the 3x2 block,
    # in the background using the muted accent color.
    # The slot's visibility can be "never", "weekdays", "weekends", or "always".
    slot1_start: int = 9
    slot1_end: int = 17
    slot2_start: int = 23
    slot2_end: int = 7
    slot3_start: int = 0
    slot3_end: int = 0
    slot4_start: int = 0
    slot4_end: int = 0
    slot1_visibility: str = "never" # "never" | "weekdays" | "weekends" | "always"
    slot2_visibility: str = "never" # "never" | "weekdays" | "weekends" | "always"
    slot3_visibility: str = "never" # "never" | "weekdays" | "weekends" | "always"
    slot4_visibility: str = "never" # "never" | "weekdays" | "weekends" | "always"
    slot1_color: str = "color1" # "color1" | "color2" | "muted"
    slot2_color: str = "color2" # "color1" | "color2" | "muted"
    slot3_color: str = "muted" # "color1" | "color2" | "muted"
    slot4_color: str = "muted" # "color1" | "color2" | "muted"

    _SLOT_VISIBILITY_CHOICES = ("never", "weekdays", "weekends", "always")
    _COLOR_CHOICES = ("orange", "blue", "gray")
    _BARS_IDENTITIES = ("month|year|life", "week|month|year", "slot1|week|month", "slot1|slot2|week")
    _SLOT_COLOR_CHOICES = ("color1", "color2", "muted")

    def __post_init__(self) -> None:
        _check("birth_month", self.birth_month, 1, 12)
        _check("birth_day", self.birth_day, 1, 31)
        if self.life_span_years <= 0:
            raise ValueError("life_span_years must be positive")
        if self.layout not in ("4x6", "6x4"):
            raise ValueError("layout must be '4x6' or '6x4'")
        if self.hours_direction not in ("vertical", "horizontal"):
            raise ValueError("hours_direction must be 'vertical' or 'horizontal'")
        for name in ("bars_missing_style", "box_missing_style"):
            if getattr(self, name) not in ("outline", "fill"):
                raise ValueError(f"{name} must be 'outline' or 'fill'")
        if self.start_of_the_week not in ("Monday", "Sunday"):
            raise ValueError("start_of_the_week must be 'Monday' or 'Sunday'")
        if self.bars_identity not in self._BARS_IDENTITIES:
            raise ValueError(
                "bars_identity must be one of " + ", ".join(self._BARS_IDENTITIES)
            )
        for name in ("color1", "color2"):
            if getattr(self, name) not in self._COLOR_CHOICES:
                raise ValueError(f"{name} must be 'orange', 'blue', or 'gray'")
        for i in (1, 2, 3, 4):
            _check(f"slot{i}_start", getattr(self, f"slot{i}_start"), 0, 23)
            _check(f"slot{i}_end", getattr(self, f"slot{i}_end"), 0, 23)
            if getattr(self, f"slot{i}_visibility") not in self._SLOT_VISIBILITY_CHOICES:
                raise ValueError(
                    f"slot{i}_visibility must be 'never', 'weekdays', "
                    "'weekends', or 'always'"
                )
            if getattr(self, f"slot{i}_color") not in self._SLOT_COLOR_CHOICES:
                raise ValueError(
                    f"slot{i}_color must be 'color1', 'color2', or 'muted'"
                )


@dataclass(frozen=True)
class SimulatorConfig:
    """Preview-only options with no on-watch equivalent.

    These tune how the desktop preview is *rendered*, not the watchface itself,
    so unlike ``UserConfig`` they never round-trip to the device or persistent
    storage and have no C mirror.
    """

    # Recall palette colors as the emery panel actually displays them rather
    # than the uncorrected nominal RGB we store. See ``palette.resolve``.
    screen_simulator_mode: bool = False


def _check(name: str, value: int, lo: int, hi: int) -> None:
    if not (lo <= value <= hi):
        raise ValueError(f"{name}={value} out of range [{lo}, {hi}]")
