"""Search engine registry for Search In Project."""

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import Base


def get_engine(name: str, settings) -> "Base":
    """Instantiate a search engine by module name.

    Args:
        name: Module name under ``searchengines`` (e.g. ``"ripgrep"``).
        settings: Sublime Text ``Settings`` object.

    Returns:
        Configured engine instance.

    Raises:
        ImportError: If the engine module does not exist.
        AttributeError: If the module lacks ``engine_class``.
    """
    module = importlib.import_module(f".{name}", package=__name__)
    return module.engine_class(settings)
