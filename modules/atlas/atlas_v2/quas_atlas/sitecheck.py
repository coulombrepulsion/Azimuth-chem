"""Static consistency check of the web pages.

HEADER
    ``python atlas.py check`` and tests/test_site_static.py.  Wilkinson
    convention, §8'.

§1 THEORY
    v1.0 broke in ways no single page shows: links that only worked inside
    the shell, language suffixes computed in JavaScript, assets loaded from
    the Internet.  These are global properties of the file tree and can be
    checked without a browser.

§2 ALGORITHM
    1. Page list = ``PAGES`` array of web/index.html (id, file).
    2. For each language folder: every page file exists.
    3. Every ``href``/``src`` attribute and every CSS ``url(...)`` that is a
       relative path resolves to an existing file (relative to the file
       that contains it).
    4. Every ``data-goto`` value and every glossary target id is a page id.
    5. Every endpoint named in ``QC.api('x')``/``QC.live('x')`` is
       registered.
    6. No reference to fonts.googleapis.com or other remote origins in
       ``<link>``/``<script src>`` (the Atlas must work offline).

§3 APPLICATIONS
    Before packaging; in CI; after editing pages by hand.

§4 SPECIFICATION
    run(web: Path = server.WEB) -> list[str] of human-readable problems
    (empty = OK).  Read-only.

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    Attribute values built in JavaScript (``'a/'+x``) are not seen; the
    browser test covers those.
§7 TEST CASES
    tests/test_site_static.py: the shipped tree has no problems; a tree with
    a deleted image reports exactly that image.
§8' ROBUSTNESS
    Unreadable files are reported as problems, not raised.
"""
from __future__ import annotations

import re
from pathlib import Path

LANGS = ("ru", "en", "zh")
ATTR = re.compile(r'(?:href|src)="([^"]+)"')
CSSURL = re.compile(r"url\(([^)]+)\)")
API = re.compile(r"QC\.(?:api|live)\(\s*'([\w.]+)'")


def _local(u: str) -> bool:
    return not (u.startswith(("http:", "https:", "mailto:", "data:", "#", "javascript:", "blob:", "/api/"))
                or "'" in u or "+" in u or u.startswith("{"))


def run(web: Path | None = None) -> list[str]:
    from . import api
    from . import pages as _pages  # noqa: F401
    if web is None:
        from .server import WEB as web
    probs: list[str] = []
    hub = (web / "index.html").read_text(encoding="utf-8")
    pages = re.findall(r"\{id:'([\w-]+)',file:'([^']+)'", hub)
    ids = {i for i, _ in pages}
    if not pages:
        probs.append("index.html: PAGES list not found")
    for L in LANGS:
        for _, f in pages:
            if not (web / L / f).is_file():
                probs.append(f"missing page {L}/{f}")
    for path in sorted(web.rglob("*")):
        if path.suffix not in (".html", ".css", ".js") or "fonts" in path.parts:
            continue
        try:
            t = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            probs.append(f"{path.relative_to(web)}: unreadable ({e})")
            continue
        rel = path.relative_to(web)
        refs = ATTR.findall(t) if path.suffix == ".html" else []
        refs += [u.strip("'\"") for u in CSSURL.findall(t)] if path.suffix == ".css" else []
        for u in refs:
            u = u.split("#", 1)[0].split("?", 1)[0]
            if not u or not _local(u):
                continue
            if not (path.parent / u).resolve().is_file():
                probs.append(f"{rel}: broken reference {u}")
        for m in re.findall(r'<(?:link|script)[^>]+(?:href|src)="(https?://[^"]+)"', t):
            probs.append(f"{rel}: remote resource {m}")
        for g in re.findall(r'data-goto="([\w-]+)"', t):
            if g not in ids:
                probs.append(f"{rel}: data-goto to unknown page '{g}'")
        for name in API.findall(t):
            if name not in api.REGISTRY:
                probs.append(f"{rel}: unknown API endpoint '{name}'")
    for L in LANGS:
        g = web / "assets" / "js" / f"glossary.{L}.js"
        if g.is_file():
            for tgt in re.findall(r'"(\w+)", "[\w-]+\.html"', g.read_text(encoding="utf-8")):
                if tgt not in ids:
                    probs.append(f"glossary.{L}.js: link to unknown page '{tgt}'")
    return probs
