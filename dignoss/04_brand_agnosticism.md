# 04: Brand Agnosticism vs. Coupling

## The Issue
While described as "brand-agnostic," the system is heavily coupled to specific palette definitions and YAML structures. Elements often request colors directly from a palette, making the "Brand" essentially a set of hardcoded color maps.

## Why it Matters
True brand agnosticism means that the *logic* of an element remains identical regardless of the brand; only the *visual interpretation* changes. 
- **Coupling**: If a new brand requires a different logic (e.g., using gradients instead of flat colors), you have to change the core rendering code rather than just the configuration.
- **Scalability**: As more brands are added, the palette system becomes a massive list of keys that are hard to manage and audit across different templates.

## Proposed Solutions

### Option A: Tokenized Theme Resolver (Recommended)
Introduce an abstraction layer between the element and the color. Elements should request "Tokens" (e.g., `brand-primary`, `accent-highlight`) rather than colors.

**Example:**
```python
# Element logic:
color = ctx.theme.resolve("brand-primary")

# Theme Resolver (Brand A):
return "#003366"

# Theme Resolver (Brand B):
return "#FF5733"
```

### Option B: CSS Variable Implementation
Implement a system similar to CSS Variables where the "Brand YAML" defines a set of variables, and the rendering engine performs a global substitution pass before drawing. This would allow for much more flexible branding (including fonts, line weights, and spacing) without touching Python code.
