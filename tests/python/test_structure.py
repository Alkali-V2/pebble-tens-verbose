import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "python" / "src"))

from tens import layout as L
from tens.derived import derive
from tens.state import RuntimeState, UserConfig


def test_hours_populate_vertically():
    # 6x4 (6 cols, 4 rows): hour 1 sits directly below hour 0 (same x).
    h0, h1 = L.hour_block(0, "6x4"), L.hour_block(1, "6x4")
    assert h0.x == h1.x and h1.y > h0.y
    # With 4 rows, the 5th hour (index 4) starts a new column.
    h4 = L.hour_block(4, "6x4")
    assert h4.x > h0.x and h4.y == h0.y


def test_first_half_hour_is_one_line():
    # 6x4 (2-wide cells): first half-hour (boxes 0-2) is a vertical column.
    cells = [L.ten_minute_cell(i, "6x4") for i in range(6)]
    assert {c.x for c in cells[:3]} == {cells[0].x}  # same column
    assert cells[3].x > cells[0].x  # 2nd half-hour is the next column

    # 4x6 (3-wide cells): first half-hour is a horizontal row.
    cells = [L.ten_minute_cell(i, "4x6") for i in range(6)]
    assert {c.y for c in cells[:3]} == {cells[0].y}  # same row
    assert cells[3].y > cells[0].y  # 2nd half-hour is the next row


def test_fill_axis_follows_layout():
    assert L.fill_axis("6x4") == "vertical"    # 2x3 cells
    assert L.fill_axis("4x6") == "horizontal"  # 3x2 cells


def test_hours_direction_horizontal():
    # 4x6 (4 cols x 6 rows), row-major: hour 1 is right of hour 0.
    h0 = L.hour_block(0, "4x6", "horizontal")
    h1 = L.hour_block(1, "4x6", "horizontal")
    assert h0.y == h1.y and h1.x > h0.x
    # With 4 columns, the 5th hour (index 4) starts a new row.
    h4 = L.hour_block(4, "4x6", "horizontal")
    assert h4.y > h0.y and h4.x == h0.x


def _derived(year=2026, month=6, day=18, weekday=3):
    rt = RuntimeState(year, month, day, weekday, 14, 37)
    return derive(rt, UserConfig(birth_year=1990, birth_month=4, birth_day=12))


def test_life_stage_fracs_sum_to_one():
    d = _derived()
    assert abs(sum(d.life_stage_fracs) - 1.0) < 1e-9


def test_defaults_match_c_settings():
    # Defaults mirror src/c/settings.c set_defaults() so the preview's default
    # render matches the device out of the box.
    from tens.state import UserConfig
    cfg = UserConfig()
    assert (cfg.birth_year, cfg.birth_month, cfg.birth_day) == (1990, 4, 12)
    assert cfg.life_span_years == 80
    assert cfg.layout == "6x4" and cfg.hours_direction == "horizontal"
    assert cfg.dark_mode is False and cfg.rainbow is False and cfg.fill_invert is False
    assert cfg.bars_missing_style == "fill"     # C: bars_missing_fill = true
    assert cfg.grid_missing_style == "outline"  # C: grid_missing_fill = false


def test_rainbow_masks_grid_with_spectral_gradient():
    from tens.scene import Gradient, build_scene
    from tens.state import RuntimeState, UserConfig
    from tens import layout as L
    from tens.derived import derive

    rt = RuntimeState(2026, 6, 18, 3, 18, 37)
    cfg = UserConfig(birth_year=1990, birth_month=4, birth_day=12, rainbow=True)
    scene = build_scene(rt, cfg, derive(rt, cfg))
    grid = L.day_rect(cfg.layout)
    # Filled boxes become spectral gradient slices spanning the whole grid.
    box_grads = [
        op for op in scene.ops
        if isinstance(op, Gradient) and op.gradient == "spectral"
        and op.span == grid.w and op.h <= L.BOX
    ]
    assert len(box_grads) >= 18  # at least the elapsed boxes by 18:37
    # Each slice's offset is its position within the grid-wide ramp.
    g = box_grads[0]
    assert g.offset == g.x - grid.x
