# Skill 06 — CLI & Testing

## CLI Integration

The CLI is auto-generated from the `SlideFactory` instance. No manual command
definition is needed — the framework creates Typer commands from your
registered templates, frames, and elements.

### Running the CLI

```console
$ python -m slides_factory my_slides --help

 Usage: slides_factory my_slides [OPTIONS] COMMAND [ARGS]...

╭─ Commands ────────────────────────────────────────╮
│ brand    Inspect the active brand                  │
│ doc      Create, inspect, and edit slide documents │
│ preview  Launch an interactive streamlit preview   │
╰────────────────────────────────────────────────────╯
```

The `doc` command has sub-commands for each operation:

```console
$ python -m slides_factory my_slides doc --help

 Usage: doc [OPTIONS] COMMAND [ARGS]...

╭─ Commands ────────────────────────────────────────╮
│ create      Create a new blank presentation       │
│ add         Add a slide to an existing document   │
│ info        List all slides in a document         │
│ get         Show metadata for one slide           │
│ set         Edit an existing slide                │
│ rm          Remove a slide by index               │
│ set-rtl     Set the document-level RTL flag       │
╰────────────────────────────────────────────────────╯
```

### Creating a Slide

```console
$ python -m slides_factory my_slides doc create -o deck.pptx

$ python -m slides_factory my_slides doc add deck.pptx \
    --template kpi \
    --set heading.text="Q3 Revenue" \
    --set revenue.title="Revenue" \
    --set revenue.value="$1.2M" \
    --frame branded \
    --json
```

### Adding a Frame Slide (with info + style)

```console
$ python -m slides_factory my_slides doc add deck.pptx \
    --frame branded \
    --frame-set title="Q3 Review" \
    --frame-set subtitle="Executive Summary" \
    --frame-style background_group=main \
    --json
```

### Console Script

For a nicer user experience, register a console script in `pyproject.toml`:

```toml
[project.scripts]
my-slides = "slides_factory.cli:main"
```

```console
$ my-slides my_slides doc create -o deck.pptx
```

### JSON Output

Pass `--json` to get machine-readable output from any command:

```json
{"ok": true, "data": {"slide_index": 0, "kind": "frame", ...}}
```

---

## Testing

### Test Fixture Structure

The core test suite at `tests/` provides a template for how to structure tests.

**1. Create an isolated `SlideFactory`:**

```python
# tests/conftest.py or tests/fixtures/app.py
from slides_factory.app import SlideFactory

# Templates, frames, and elements under tests/fixtures/templates/,
# tests/fixtures/frames/, and tests/fixtures/elements/ are
# auto-discovered lazily — no explicit discovery calls needed.
app = SlideFactory("my_slides_test")
```

**2. Set it as the active app in conftest:**

```python
# tests/conftest.py
import importlib
import pytest
import slides_factory.app as app_module
from tests.fixtures.app import app


@pytest.fixture(autouse=True)
def _activate_test_app():
    app_module._active_app = app
    yield


@pytest.fixture
def test_app():
    return app
```

**3. Define minimal palettes for frames:**

```python
# tests/fixtures/palettes.py
from slides_factory.palette import SlidePalette

TEST_PALETTE = SlidePalette(
    text="#111111",
    highlight="#222222",
    main=("#CCCCCC",),
    extras=("#AAAAAA", "#BBBBBB"),
)
```

### Testing Templates

```python
from pathlib import Path
from pptx import Presentation
from pptx.util import Emu, Inches
from slides_factory import document
from slides_factory.render_context import RenderContext
from slides_factory.layout.pct import LogoPlacement, PctBox


class TestKpiTemplate:
    def test_build_layout(self, test_app):
        """Template.build() should produce the correct Layout."""
        template = test_app.get_template("kpi")
        data = template.validate_data({
            "heading": {"text": "Q3"},
            "revenue": {"title": "Revenue", "value": "$1.2M"},
        })
        layout = template.build(data)

        assert len(layout.cells) == 2
        assert layout.cells[0].element.kind == "text"
        assert layout.cells[0].element.props["text"] == "Q3"
        assert layout.cells[1].element.kind == "card"
        assert layout.cells[1].element.props["value"] == "$1.2M"

    def test_render_creates_shapes(self, test_app):
        """After rendering, the slide should have shapes."""
        prs = Presentation()
        prs.slide_width = Emu(9144000)
        prs.slide_height = Emu(5400000)
        slide = prs.slides.add_slide(prs.slide_layouts[0])

        template = test_app.get_template("kpi")
        data = template.validate_data({
            "heading": {"text": "Test"},
            "revenue": {"title": "Revenue", "value": "$1.2M"},
        })
        ctx = RenderContext(
            slide=slide,
            palette=TEST_PALETTE,
        )
        template.render(slide, data, ctx)

        assert len(slide.shapes) > 0
```

### Testing Frames

```python
class TestBrandedFrame:
    def test_render_applies_background(self, test_app):
        prs = Presentation()
        prs.slide_width = Emu(9144000)
        prs.slide_height = Emu(5400000)
        slide = prs.slides.add_slide(prs.slide_layouts[0])

        frame = test_app.get_frame("branded")
        ctx = RenderContext(slide=slide, palette=TEST_PALETTE)
        frame.render(slide, ctx)

        # Should have background shape + content
        assert len(slide.shapes) >= 1
```

### Testing Elements (Integration)

```python
class TestProgressBarElement:
    def test_render(self, test_app):
        prs = Presentation()
        prs.slide_width = Emu(9144000)
        prs.slide_height = Emu(5400000)
        slide = prs.slides.add_slide(prs.slide_layouts[0])

        element = test_app.get_element("progress_bar")
        props = element.validate_props({
            "label": "Test", "current": 50, "target": 100,
        })
        style = element.validate_style({"bar_color": "highlight"})

        ctx = RenderContext(slide=slide, palette=TEST_PALETTE)
        element.render(slide, (0, 0, 9144000, 5400000), props, style, ctx)

        assert len(slide.shapes) == 3  # bg bar, fill bar, label
```

### Testing the Full Document API

```python
class TestDocumentRoundTrip:
    def test_add_and_read_slide(self, test_app, tmp_path):
        output = tmp_path / "test.pptx"

        # Create document
        prs = document.create_document()
        document.save_document(prs, output)

        # Add a slide
        template = test_app.get_template("kpi")
        data = template.validate_data({
            "heading": {"text": "Hello"},
            "revenue": {"title": "Revenue", "value": "$1.2M"},
        })
        result = document.add_slide(prs, "kpi", data, frame="branded")
        document.save_document(prs, output)

        assert result["template_id"] == "kpi"
        assert result["slide_index"] == 0

        # Re-open and verify metadata
        prs2 = document.open_document(output)
        info = document.get_slide_info(prs2, 0)
        assert info["template_id"] == "kpi"
        assert info["data"]["heading"]["text"] == "Hello"
```

### Running Tests

```console
$ uv run pytest tests/ -x --tb=short
```

## Best Practices

| Practice | Why |
|----------|-----|
| Use an isolated `SlideFactory` per test suite | Avoid polluting the global `_active_app` |
| Set `_active_app` in a conftest fixture | Ensures `get_app()` returns your test instance |
| Test with real `Presentation` objects | python-pptx objects are fast to create in-memory |
| Validate frame `playground_box` EMU values | Ensures percent-based placement is correct |
| Always call `template.validate_data()` | Tests both validation and rendering paths |
| Test brand-aware behavior with `minimal_brand_yaml` | Ensure frames degrade gracefully without brand |
| Test RTL with `ctx=replace(ctx, rtl=True)` | Verify mirroring logic independently |
