"""Grid solver: turn a resolved GridStyle + region into EMU cell boxes.

The grid is positioned inside a region (the frame's playground, in EMU). Column
and row ratios, gaps, and padding come from a :class:`GridStyle`; each cell is
placed by span with row-major auto-placement and optional explicit start. RTL
decks mirror columns within the region.

Functions:
    compute_cells — Resolve cell placements into EMU :class:`Cell` boxes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from slides_factory.exceptions import GridOverflowError
from slides_factory.geometry import Box
from slides_factory.styling.tokens import CellStyle, GridStyle


@dataclass(frozen=True)
class Cell:
    """A placed grid cell with its EMU box and logical coordinates."""

    left: int
    top: int
    width: int
    height: int
    row: int
    col: int
    row_span: int
    col_span: int

    @property
    def box(self) -> Box:
        """Return the cell rectangle as a :class:`Box`."""
        return Box(self.left, self.top, self.width, self.height)


def _tracks(
    total: int, ratios: tuple[float, ...], gap_fraction: float
) -> tuple[list[float], list[float]]:
    """Return (starts, sizes) for one axis given a total length and ratios."""
    count = len(ratios)
    gap = gap_fraction * total
    available = total - gap * (count - 1)
    if available <= 0:
        raise GridOverflowError("grid gaps exceed the available region size")
    ratio_sum = sum(ratios)
    sizes = [available * ratio / ratio_sum for ratio in ratios]
    starts: list[float] = []
    cursor = 0.0
    for index, size in enumerate(sizes):
        starts.append(cursor)
        cursor += size + (gap if index < count - 1 else 0.0)
    return starts, sizes


def compute_cells(
    region: Box,
    grid: GridStyle,
    cells: list[CellStyle],
    *,
    rtl: bool = False,
) -> list[Cell]:
    """Resolve ``cells`` into EMU boxes within ``region``.

    Cells are placed in order using row-major auto-placement; explicit
    ``col_start`` / ``row_start`` pin a coordinate. Spans extend across tracks
    (including the gaps between them). RTL mirrors columns within the region.
    """
    region_left, region_top, region_w, region_h = region

    pad_left = grid.pad_x * region_w
    pad_top = grid.pad_y * region_h
    inner_left = region_left + pad_left
    inner_top = region_top + pad_top
    inner_w = region_w - 2 * pad_left
    inner_h = region_h - 2 * pad_top
    if inner_w <= 0 or inner_h <= 0:
        raise GridOverflowError("grid padding exceeds the available region size")

    ncols = len(grid.columns)

    if grid.auto_rows:
        # Determine the minimum number of rows needed for the given cells.
        nrows = max(
            math.ceil(len(cells) / ncols),
            max(
                (
                    (style.row_start or 1) + style.row_span - 1
                    for style in cells
                    if style.row_start is not None
                ),
                default=0,
            ),
        )
        if nrows < 1:
            nrows = 0
        rows_ratios = tuple(1.0 for _ in range(nrows))
    else:
        nrows = len(grid.rows)
        rows_ratios = grid.rows

    col_starts, col_sizes = _tracks(inner_w, grid.columns, grid.col_gap)
    row_starts, row_sizes = _tracks(inner_h, rows_ratios, grid.row_gap)

    occupied: set[tuple[int, int]] = set()
    placed: list[Cell] = []

    for style in cells:
        col_span = style.col_span
        row_span = style.row_span
        if col_span > ncols or row_span > nrows:
            raise GridOverflowError(f"cell span {col_span}x{row_span} exceeds grid {ncols}x{nrows}")
        row0, col0 = _place(
            occupied, nrows, ncols, row_span, col_span, style.row_start, style.col_start
        )
        for r in range(row0, row0 + row_span):
            for c in range(col0, col0 + col_span):
                occupied.add((r, c))

        if rtl:
            phys_start = ncols - (col0 + col_span)
            phys_end = ncols - col0 - 1
        else:
            phys_start = col0
            phys_end = col0 + col_span - 1

        left = inner_left + col_starts[phys_start]
        right = inner_left + col_starts[phys_end] + col_sizes[phys_end]
        top = inner_top + row_starts[row0]
        bottom = inner_top + row_starts[row0 + row_span - 1] + row_sizes[row0 + row_span - 1]

        placed.append(
            Cell(
                left=int(round(left)),
                top=int(round(top)),
                width=int(round(right - left)),
                height=int(round(bottom - top)),
                row=row0,
                col=col0,
                row_span=row_span,
                col_span=col_span,
            )
        )

    return placed


def _fits(
    occupied: set[tuple[int, int]], r0: int, c0: int, rs: int, cs: int, nrows: int, ncols: int
) -> bool:
    if r0 + rs > nrows or c0 + cs > ncols:
        return False
    for r in range(r0, r0 + rs):
        for c in range(c0, c0 + cs):
            if (r, c) in occupied:
                return False
    return True


def _place(
    occupied: set[tuple[int, int]],
    nrows: int,
    ncols: int,
    rs: int,
    cs: int,
    row_start: int | None,
    col_start: int | None,
) -> tuple[int, int]:
    """Return the (row, col) top-left for a cell, honoring explicit starts."""
    fixed_r = None if row_start is None else row_start - 1
    fixed_c = None if col_start is None else col_start - 1

    if fixed_r is not None and fixed_c is not None:
        if not _fits(occupied, fixed_r, fixed_c, rs, cs, nrows, ncols):
            raise ValueError(f"explicit cell at row {row_start}, col {col_start} does not fit")
        return fixed_r, fixed_c

    row_range = [fixed_r] if fixed_r is not None else range(nrows)
    col_range_factory = (lambda: [fixed_c]) if fixed_c is not None else (lambda: range(ncols))

    for r in row_range:
        for c in col_range_factory():
            if _fits(occupied, r, c, rs, cs, nrows, ncols):
                return r, c

    raise ValueError("not enough free grid cells for the requested layout")
