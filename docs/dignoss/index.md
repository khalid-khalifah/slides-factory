# Project Diagnostics & Architectural Debt

This directory contains a detailed breakdown of the critical architectural issues identified in the current version of `slides-factory`, along with proposed strategies for resolution.

## Identified Issues

1. [The Framework Trap (Over-Engineering)](01_over_engineering.md)
   - **Focus:** DSL complexity vs. functional utility.
2. [Dynamic Model Magic](02_dynamic_models.md)
   - **Focus:** Loss of static type safety and IDE support.
3. [The CSS Grid Impedance Mismatch](03_grid_impedance.md)
   - **Focus:** The conflict between flow-based layouts and coordinate-based slides.
4. [Brand Agnosticism vs. Coupling](04_brand_agnosticism.md)
   - **Focus:** Moving from configuration files to a true token-based theme system.
5. [The God Object (document.py)](05_god_object.md)
   - **Focus:** Decomposition of the monolithic document management logic.

## How to use this guide
Each file follows a structured format:
- **The Issue**: What is currently happening in the code.
- **Why it Matters**: The long-term risks (maintenance, bugs, developer experience).
- **Proposed Solutions**: One or more paths toward fixing the problem, ranging from "surgical" to "complete re-architecture."
