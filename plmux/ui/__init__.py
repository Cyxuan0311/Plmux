"""UI package: import submodules directly (e.g. `plmux.ui.renderer`) to avoid cycles."""

from plmux.ui.theme import Theme, load_theme

__all__ = ["Theme", "load_theme"]
