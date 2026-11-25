"""Web endpoints, one module per Atlas page.  Importing this package registers them all.

Each module is a thin adapter: it declares parameters (types, ranges) and
returns plain dicts/lists built from ``quas_atlas.core``.  The physics and its
documentation (Wilkinson §1-§8) live in the core modules.
"""
import importlib
import pkgutil

for _m in pkgutil.iter_modules(__path__):
    importlib.import_module(f"{__name__}.{_m.name}")
