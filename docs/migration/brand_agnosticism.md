# Migrating to Contextual Token Resolution

This guide explains how to migrate your brand implementation (e.g., `mim-slides`) from the legacy `SlidePalette` system to the new **Contextual Token Resolver**.

## Why this change?
The previous system coupled frames to specific Python objects (`ON_DARK`, `ON_LIGHT`). This made it difficult to manage contrast safety and required duplicating hex codes in both YAML and Python. 

The new system uses **Semantic Tokens** mapped to **Contrast Profiles**, ensuring that foreground colors always match their background context automatically.

---

## Step-by-Step Migration

### 1. Update your Brand YAML
Replace generic color lists with a `colors` (raw values) and `profiles` (contextual mappings) structure.

**Before:**
```yaml
colors:
  main: ["#413258", "#E6E6E6"]
  secondary: ["#1AD9C7", "#BFA19F"]
```

**After:**
```yaml
colors: # Raw brand ingredients
  purple_dark: "#413258"
  cyan_bright: "#1AD9C7"
  white: "#FFFFFF"
  grey_darkest: "#1A1A1A"

profiles: # Contrast recipes (The new "Palettes")
  light_mode:
    surface.bg: colors.white
    text.main: colors.grey_darkest
    accent.highlight: colors.purple_dark
  dark_mode:
    surface.bg: colors.purple_dark
    text.main: colors.white
    accent.highlight: colors.cyan_bright
```

### 2. Remove `palettes.py`
Delete the file containing hardcoded hex constants and `SlidePalette` instances. All this information now lives in the YAML.

### 3. Update Frame Definitions
Frames no longer assign a palette object. They declare which **profile** they use.

**Before:**
```python
from . import palettes

class DarkSectionFrame(Frame):
    palette = palettes.ON_DARK
```

**After:**
```python
class DarkSectionFrame(Frame):
    profile = "dark_mode" # Matches the key in your YAML profiles
```

### 4. Update Element Rendering logic
Stop using index-based lookups (e.g., `palette.main[0]`). Instead, request a semantic token via the resolver provided in the context.

**Before:**
```python
# Fragile: depends on the order of the tuple in palettes.py
color = self.palette.main[0] 
```

**After:**
```python
from slides_factory.core.tokens import ThemeToken

# ctx.theme is the ThemeResolver, ctx.profile is set by the current Frame
color = ctx.theme.resolve(ThemeToken.BRAND_PRIMARY, ctx.profile)
```

---

## Token Reference Table

| Token | Purpose | Example Usage |
| :--- | :--- | :--- |
| `SURFACE_BG` | The base background color of the slide | Frame backgrounds |
| `TEXT_MAIN` | Primary content text (ensures contrast vs BG) | Headings, body text |
| `BRAND_PRIMARY` | The main brand identity color | Logos, primary accents |
| `ACCENT_HIGHLIGHT`| High-contrast callout color | Key data points, highlights |
| `TEXT_INVERTED` | Text specifically for high-contrast overlays | Captions on dark buttons |
