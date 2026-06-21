"""Domain-specific exception classes for slides-factory."""


class SlidesFactoryError(Exception):
    """Base exception for all slides-factory errors."""


class AppNotConfiguredError(SlidesFactoryError, RuntimeError):
    """Raised when no SlideFactory app is active."""


class BrandRequiredError(SlidesFactoryError, ValueError):
    """Raised when a brand theme is required but not present."""


class GridOverflowError(SlidesFactoryError, ValueError):
    """Raised when grid cells cannot fit within the available region."""


class UnknownElementError(SlidesFactoryError, KeyError):
    """Raised when referencing an unregistered element kind."""


class UnknownTemplateError(SlidesFactoryError, KeyError):
    """Raised when referencing an unregistered template id."""


class UnknownFrameError(SlidesFactoryError, KeyError):
    """Raised when referencing an unregistered frame id."""


class FontEmbeddingError(SlidesFactoryError, RuntimeError):
    """Raised when font embedding fails for a .pptx file."""
