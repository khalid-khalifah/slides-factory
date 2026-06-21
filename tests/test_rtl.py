"""Edge cases for RTL mirroring and RenderContext."""

from slides_factory.layout.rtl import RTLLayout
from slides_factory.render_context import RenderContext


def test_mirror_left_is_identity_in_ltr():
    ctx = RenderContext(rtl=False, slide_width=9144000)
    assert ctx.mirror_left(1000, 500) == 1000


def test_mirror_left_flips_in_rtl():
    ctx = RenderContext(rtl=True, slide_width=9144000)
    assert ctx.mirror_left(1000, 500) == 9144000 - 1000 - 500


def test_mirror_row_reorders_positions_rtl():
    ctx = RenderContext(rtl=True, slide_width=9144000)
    layout = RTLLayout(ctx)
    ltr_lefts = [457200, 3200400, 5943600]
    mirrored = layout.mirror_row(ltr_lefts, 2621280)
    assert len(mirrored) == 3
    assert mirrored[0] > mirrored[1] > mirrored[2]


def test_with_palette_returns_new_context():
    from tests.fixtures.palettes import TEST_LIGHT

    ctx = RenderContext(rtl=False, slide_width=1000, slide_height=750)
    with_palette = ctx.with_palette(TEST_LIGHT)
    assert with_palette.palette is TEST_LIGHT
    assert ctx.palette is None
