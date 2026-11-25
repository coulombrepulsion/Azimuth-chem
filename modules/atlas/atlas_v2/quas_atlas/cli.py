"""Command line of the Azimuth Atlas (``python atlas.py ...``).

HEADER
    One entry point for students and the author. Wilkinson convention,
    §8' (no numerics).

§1 THEORY
    The Atlas is a set of web pages backed by Python calculations. Students
    need one command that starts everything; the author also needs to check
    the site and to call any calculation without a browser.

§2 ALGORITHM
    argparse with sub-commands; no sub-command means ``serve``.
      serve : server.serve(host, port, open_browser, lang, debug)
      list : print every endpoint with its one-line description
      calc : api.call(name, json.loads(params)) -> JSON on stdout
      check : sitecheck.run() -> problems on stdout, exit 1 if any
      version: print the version

§3 APPLICATIONS
    python atlas.py # start, open the browser
    python atlas.py serve --port 9000 --no-browser
    python atlas.py calc h2.point '{"R": 1.4}'
    python atlas.py check

§4 SPECIFICATION
    main(argv: list[str] | None) -> int exit status (0 ok, 1 problems,
    2 usage error). ``calc`` prints JSON with ensure_ascii=True so that the
    output is safe in any console encoding.

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    Endpoints are registered by importing quas_atlas.pages (done in server).
§7 TEST CASES (tests/test_cli.py)
    ``calc h2.point {"R":1.4}`` returns the same JSON as the HTTP API;
    ``list`` contains h2.scan; ``check`` exits 0 on the shipped site.
§8' ROBUSTNESS
    Invalid JSON for calc -> message and exit 2; API errors -> message
    and exit 1; Ctrl+C in serve -> clean stop.
"""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="atlas.py", description="Azimuth Atlas: interactive quantum chemistry pages")
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("serve", help="start the local server and open the browser (default)")
    s.add_argument("--host", default="127.0.0.1", help="bind address (0.0.0.0 = whole local network)")
    s.add_argument("--port", type=int, default=8765)
    s.add_argument("--no-browser", action="store_true")
    s.add_argument("--lang", choices=("ru", "en", "zh"))
    s.add_argument("--debug", action="store_true", help="log every request and print tracebacks")
    sub.add_parser("list", help="list calculation endpoints")
    c = sub.add_parser("calc", help="run one calculation and print JSON")
    c.add_argument("name")
    c.add_argument("params", nargs="?", default="{}", help='JSON object, e.g. \'{"R": 1.4}\'')
    sub.add_parser("check", help="check the web pages (links, assets, endpoints)")
    sub.add_parser("version")
    a = ap.parse_args(argv)

    if a.cmd in (None, "serve"):
        from .server import serve
        if a.cmd is None:
            serve()
        else:
            serve(a.host, a.port, not a.no_browser, a.lang, a.debug)
        return 0
    if a.cmd == "version":
        print(__version__)
        return 0
    from . import api
    from . import pages as _pages  # noqa: F401
    if a.cmd == "list":
        for k, v in sorted(api.REGISTRY.items()):
            print(f"{k:28s} {v.doc}".encode("ascii", "replace").decode())
        return 0
    if a.cmd == "calc":
        try:
            params = json.loads(a.params)
        except json.JSONDecodeError as e:
            print(f"params: invalid JSON: {e}", file=sys.stderr)
            return 2
        try:
            res = api.call(a.name, params)
        except api.ApiError as e:
            print(f"error {e.status}: {e.message}", file=sys.stderr)
            return 1
        print(json.dumps(api.to_json(res), ensure_ascii=True, indent=1))
        return 0
    if a.cmd == "check":
        from . import sitecheck
        problems = sitecheck.run()
        for p in problems:
            print(p.encode("ascii", "backslashreplace").decode())
        print(f"[check] {len(problems)} problem(s)")
        return 1 if problems else 0
    ap.print_help()
    return 2
