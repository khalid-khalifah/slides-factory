"""Spatial primitives — the Box type used by layout, elements, and rendering.

``Box`` is an immutable (frozen) geometry rectangle with helper properties
and derivation methods.  It supports tuple unpacking for backward compatibility
with code that destructures as ``left, top, width, height``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Box:
    """Immutable EMU rectangle (left, top, width, height).

    Properties:
        right, bottom — derived edges.
        center_x, center_y — rectangle centre coordinates (float).

    Methods:
        inset  — shrink from all edges (returns new Box).
        with_margin — shrink with directional margins (returns new Box).
    """

    left: int
    top: int
    width: int
    height: int

    @property
    def right(self) -> int:
        """Right edge EMU coordinate."""
        return self.left + self.width

    @property
    def bottom(self) -> int:
        """Bottom edge EMU coordinate."""
        return self.top + self.height

    @property
    def center_x(self) -> float:
        """Horizontal centre coordinate."""
        return self.left + self.width / 2.0

    @property
    def center_y(self) -> float:
        """Vertical centre coordinate."""
        return self.top + self.height / 2.0

    # -- tuple-like protocol for backward compatibility --------------------

    def __eq__(self, other: object) -> bool:
        """Support equality with tuples for backward compatibility."""
        if isinstance(other, Box):
            return (
                self.left == other.left
                and self.top == other.top
                and self.width == other.width
                and self.height == other.height
            )
        if isinstance(other, tuple) and len(other) == 4:
            return (
                self.left == other[0]
                and self.top == other[1]
                and self.width == other[2]
                and self.height == other[3]
            )
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self.left, self.top, self.width, self.height))

    def __iter__(self):
        """Yield ``(left, top, width, height)`` for tuple unpacking."""
        yield self.left
        yield self.top
        yield self.width
        yield self.height

    # -- derivation methods -----------------------------------------------

    def inset(self, x: int, y: int) -> Box:
        """Return a new Box shrunk by *x* EMU on the left/right and *y* on top/bottom."""
        return Box(
            left=self.left + x,
            top=self.top + y,
            width=max(0, self.width - 2 * x),
            height=max(0, self.height - 2 * y),
        )

    def with_margin(
        self,
        top: int = 0,
        right: int = 0,
        bottom: int = 0,
        left: int = 0,
    ) -> Box:
        """Return a new Box inset by directional margins (all default to 0)."""
        return Box(
            left=self.left + left,
            top=self.top + top,
            width=max(0, self.width - left - right),
            height=max(0, self.height - top - bottom),
        )
