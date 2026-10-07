"""Browser widget metadata, read by the Pytincture backend without importing it.

Service mode resolves the widgetset wheel to install in the browser by walking
the entrypoint's imports for literal __widgetset__/__version__ assignments, so
py_ui.py imports this module. Both values must be literals.

wapyt 0.2.0 is not on PyPI yet, so the browser installs the wheel vendored next
to this file, built from wapyt main at the commit named in the README.
"""

__widgetset__ = "wapyt"
__version__ = "0.2.0.dev0"
