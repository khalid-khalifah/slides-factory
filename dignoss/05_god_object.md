# 05: The God Object (document.py)

## The Issue
The `document.py` module has become a "God Object." it is responsible for:
1. File I/O (Opening and saving presentations).
2. Slide lifecycle management (Inserting, deleting, reordering slides).
3. Render coordination (Resolving frames, styles, and calling the layout engine).
4. Metadata management (RTL settings, theme defaults).

## Why it Matters
Monolithic modules are difficult to test, maintain, and extend:
- **Fragility**: A change in how slides are deleted might accidentally break how templates are rendered because they share the same stateful module.
- **Testing Difficulty**: To test a simple render function, you often have to initialize a full `Presentation` object and mock out half of the `document.py` utility functions.
- **Cognitive Load**: The file is too large for a developer to hold the entire logic in their head at once.

## Proposed Solutions

### Option A: Domain Decomposition (Strategic)
Split the functionality into four distinct, single-responsibility classes:

1. **`PresentationSession`**: Handles raw `.pptx` file operations and session state.
2. **`SlideManager`**: Manages the collection of slides and their ordering.
3. **`LayoutEngine`**: The pure logic that converts a `LayoutSpec` into PPT shapes.
4. **`DocumentFacade`**: A thin API layer that maintains the existing interface for the rest of the app but delegates all work to the three classes above.

### Option B: Service-Based Architecture (Advanced)
Move rendering and document management into separate "Services" injected via the `RenderContext`. This would allow you to swap out the PowerPoint backend for another format (e.g., PDF or Google Slides) by simply swapping the `DocumentService` implementation.
