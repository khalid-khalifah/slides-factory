# Skill 05 — Brand Theme

The brand theme is a YAML file that defines colors, fonts, logos, page
dimensions, and element layout anchors. It's loaded at runtime and passed
to frames and templates through `RenderContext.brand`.

## Brand YAML Structure

```yaml
# my_slides/brand.yaml
name: acme-corp                          # Display name
default_frame: branded                   # Default frame when none specified

base_pptx: themes/default.pptx           # Optional: template for new docs

lock_frame_shapes: true                  # Prevent manual edits on frame shapes

# --- Page dimensions (inches) ---
page:
  width_in: 13.333                       # 16:9 widescreen
  height_in: 7.5

# --- Brand palette ---
colors:
  main:
    - color: "#1A237E"                   # Primary dark blue
      contrast: "#FFFFFF"
    - color: "#3949AB"                   # Medium blue
      contrast: "#FFFFFF"
  secondary:
    - color: "#FF6F00"                   # Amber accent
      contrast: "#FFFFFF"
    - color: "#FF8F00"                   # Light amber
      contrast: "#1A1A1A"
  basic:
    - color: "#FFFFFF"                   # White background
      contrast: "#1A1A1A"
    - color: "#F5F5F5"                   # Light gray
      contrast: "#1A1A1A"

# --- Fonts (file paths resolved relative to brand YAML) ---
fonts:
  title: fonts/Inter-Bold.ttf
  body: fonts/Inter-Regular.ttf
  footer: fonts/Inter-Light.ttf
  mono: fonts/JetBrainsMono-Regular.ttf  # Optional code font

# --- Logos (optional) ---
logos:
  wordmark:
    en: assets/logo-en.svg
    ar: assets/logo-ar.svg
  inverted:
    en: assets/logo-en-white.svg
    ar: assets/logo-ar-white.svg

# --- Element anchors (percent-based positioning) ---
layout:
  logos:
    en:
      left: 6                             # 6% from left
      top: 4                               # 4% from top
      width: 18                            # 18% of slide width
    ar:
      left: 76
      top: 4
      width: 18
  elements:
    title_bg:
      left: 0
      top: 0
      width: 100
      height: 20
```

## Loading the Brand

```python
from slides_factory.brand import load_brand

brand = load_brand(Path("my_slides/brand.yaml"))
print(brand.name)            # "acme-corp"
print(brand.default_frame)   # "branded"
print(brand.colors.get("main", 0).color)   # "#1A237E"
```

Brand themes are typically configured at the document level:

```python
from slides_factory import document

prs = document.create_document(brand=brand)
template = app.get_template("kpi")
data = template.validate_data({"heading": {"text": "Hello"}})
slide = document.add_slide(prs, "kpi", data, frame="branded")
```

## How Frames Use the Brand

When a brand is active, frames can use its colors dynamically:

```python
@app.frame("branded", ...)
def branded(slide, ctx, info):
    # ctx.brand is a BrandTheme instance when available
    if ctx.brand:
        bg_color = ctx.brand.colors.get("main", 0).color
        text_color = ctx.brand.colors.get("main", 0).contrast
    else:
        bg_color = ctx.palette.main[0]
        text_color = ctx.palette.text
```

## Brand Color References in Styles

Element and frame styles can reference brand colors using `group:index` syntax:

```json
{
    "background_color": "main:0",      # first color in the 'main' group
    "highlight_color": "secondary:1",   # second color in 'secondary'
    "contrast_color": "on-main:0"       # contrast (text) color for main:0
}
```

The resolution functions in `slides_factory.brand.theme` handle lookup:

```python
from slides_factory.brand.theme import resolve_color, resolve_contrast

fill = resolve_color(brand, "main", 0)       # "#1A237E"
contrast = resolve_contrast(brand, "main", 0) # "#FFFFFF"
```

## Palette Derivation from Brand

Frames can derive a `SlidePalette` from the brand using `palette_for()`:

```python
palette = MyFrame.palette_for(ctx, frame_style_instance)
```

This creates a palette where the frame's background comes from the brand color
pair, automatically switching text colors to the contrast color for readability.
