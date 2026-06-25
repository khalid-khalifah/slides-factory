"""Isolated SlideFactory used only by tests/core (no MIM dependency).

Templates, frames, and elements are auto-discovered from the caller's
package: ``tests.fixtures.templates``, ``tests.fixtures.frames``, and
``tests.fixtures.elements`` are imported automatically on creation.
"""

from slides_factory.app import SlideFactory

app = SlideFactory("test-core")
