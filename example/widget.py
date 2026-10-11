"""Browser widget metadata, read by the Pytincture backend without importing it.

Service mode resolves the widgetset wheel to install in the browser by walking
the entrypoint's imports for literal __widgetset__/__version__ assignments, so
py_ui.py imports this module. Both values must be literals.

The browser installs the matching wheel vendored next to this file: the wapyt
release published on PyPI under this version, unmodified.
"""

__widgetset__ = "wapyt"
__version__ = "0.2.0"
