"""Tests for the grid solver (ratios, gaps, spans, auto-placement, RTL)."""

from __future__ import annotations

import pytest

from slides_factory.layout.grid import compute_cells
from slides_factory.styling.tokens import parse_cell, parse_grid


def _cells(class_str: str, count: int):
    return [parse_cell(class_str) for _ in range(count)]


def test_two_equal_columns_no_gap():
    region = (0, 0, 1000, 1000)
    placed = compute_cells(region, parse_grid("grid-cols-2"), _cells("", 2))
    assert placed[0].box == (0, 0, 500, 1000)
    assert placed[1].box == (500, 0, 500, 1000)


def test_columns_with_gap():
    region = (0, 0, 1000, 1000)
    placed = compute_cells(region, parse_grid("grid-cols-2 gap-4"), _cells("", 2))
    # gap = 0.05 * 1000 = 50 -> each column 475 wide
    assert placed[0].box == (0, 0, 475, 1000)
    assert placed[1].box == (525, 0, 475, 1000)


def test_ratio_columns():
    region = (0, 0, 900, 1000)
    placed = compute_cells(region, parse_grid("grid-cols-[2_1]"), _cells("", 2))
    assert placed[0].width == 600
    assert placed[1].width == 300
    assert placed[1].left == 600


def test_column_span_covers_tracks():
    region = (0, 0, 900, 900)
    cells = [parse_cell("col-span-2"), parse_cell("")]
    placed = compute_cells(region, parse_grid("grid-cols-3"), cells)
    assert placed[0].box == (0, 0, 600, 900)
    # second cell auto-flows into the remaining third column
    assert placed[1].box == (600, 0, 300, 900)


def test_row_major_auto_placement():
    region = (0, 0, 1000, 1000)
    placed = compute_cells(region, parse_grid("grid-cols-2 grid-rows-2"), _cells("", 4))
    coords = [(cell.row, cell.col) for cell in placed]
    assert coords == [(0, 0), (0, 1), (1, 0), (1, 1)]


def test_explicit_start_pins_position():
    region = (0, 0, 1000, 1000)
    cells = [parse_cell("col-start-2 row-start-2")]
    placed = compute_cells(region, parse_grid("grid-cols-2 grid-rows-2"), cells)
    assert (placed[0].row, placed[0].col) == (1, 1)
    assert placed[0].left == 500
    assert placed[0].top == 500


def test_padding_insets_the_grid():
    region = (0, 0, 1000, 1000)
    placed = compute_cells(region, parse_grid("p-4"), _cells("", 1))
    assert placed[0].box == (50, 50, 900, 900)


def test_rtl_mirrors_columns():
    region = (0, 0, 1000, 1000)
    ltr = compute_cells(region, parse_grid("grid-cols-2"), _cells("", 1))
    rtl = compute_cells(region, parse_grid("grid-cols-2"), _cells("", 1), rtl=True)
    # First logical column sits on the left in LTR, mirrored to the right in RTL.
    assert ltr[0].left == 0
    assert rtl[0].left == 500


def test_span_larger_than_grid_raises():
    region = (0, 0, 1000, 1000)
    with pytest.raises(ValueError, match="exceeds grid"):
        compute_cells(region, parse_grid("grid-cols-2"), [parse_cell("col-span-3")])


def test_auto_rows_calculates_row_count():
    """auto_rows with 2 cols and 4 cells creates 2 rows."""
    region = (0, 0, 1000, 1000)
    placed = compute_cells(
        region, parse_grid("grid-cols-2 grid-rows-auto"), _cells("", 4)
    )
    assert len(placed) == 4
    # Verify row-major placement: 2 cells per row, 2 rows
    assert placed[0].row == 0 and placed[0].col == 0
    assert placed[1].row == 0 and placed[1].col == 1
    assert placed[2].row == 1 and placed[2].col == 0
    assert placed[3].row == 1 and placed[3].col == 1
    # All cells should occupy equal boxes in a uniform grid
    assert placed[0].box == (0, 0, 500, 500)
    assert placed[3].box == (500, 500, 500, 500)


def test_auto_rows_uneven():
    """auto_rows with 2 cols and 3 cells creates 2 rows (2+1)."""
    region = (0, 0, 1000, 1000)
    placed = compute_cells(
        region, parse_grid("grid-cols-2 grid-rows-auto"), _cells("", 3)
    )
    assert len(placed) == 3
    assert placed[0].row == 0
    assert placed[2].row == 1  # Third cell wraps to second row
    # With 2 rows, each row is 500 EMU tall
    assert placed[0].top == 0
    assert placed[2].top == 500


def test_auto_rows_single_column():
    """auto_rows with 1 col and 4 cells creates 4 rows (stacked)."""
    region = (0, 0, 800, 1200)
    placed = compute_cells(
        region, parse_grid("grid-cols-1 grid-rows-auto"), _cells("", 4)
    )
    assert len(placed) == 4
    # Single column, so all cells are stacked vertically
    for i in range(4):
        assert placed[i].col == 0
        assert placed[i].row == i
    assert placed[0].width == 800
    assert placed[0].height == 300  # 1200 / 4


def test_auto_rows_explicit_start():
    """auto_rows with explicit row-start-4 creates at least 4 rows."""
    region = (0, 0, 1000, 1000)
    cells = [parse_cell("row-start-4 col-span-2")]
    placed = compute_cells(
        region, parse_grid("grid-cols-2 grid-rows-auto"), cells
    )
    assert len(placed) == 1
    # Row indices are 0-based, row-start-4 → row 3
    assert placed[0].row == 3
    assert placed[0].col == 0
    # 4 rows means each row is 250 EMU tall
    assert placed[0].top == 750


def test_auto_rows_overfull_raises():
    """auto_rows still raises if explicit spans exceed computed grid."""
    region = (0, 0, 1000, 1000)
    # 1 cell in 1 column → 1 row, but cell spans 3 rows
    with pytest.raises(ValueError, match="exceeds grid"):
        compute_cells(
            region,
            parse_grid("grid-cols-1 grid-rows-auto"),
            [parse_cell("row-span-3")],
        )


def test_overfull_grid_raises():
    region = (0, 0, 1000, 1000)
    with pytest.raises(ValueError, match="not enough free grid cells"):
        compute_cells(region, parse_grid("grid-cols-1 grid-rows-1"), _cells("", 2))
