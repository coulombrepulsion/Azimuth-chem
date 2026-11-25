"""Local web server: static Atlas pages plus the calculation API.

HEADER
    Serves ``quas_atlas/web`` and answers ``POST /api/<endpoint>`` by calling
    ``quas_atlas.api.call``. Standard library only (http.server), so a
    student needs nothing but Python to run the Atlas. Wilkinson
    convention, §8' (no numerics).

§1 THEORY
    In v1.0 the pages computed everything in the browser. Since v2.0 the
    numerical model is Python; the browser sends parameters as JSON and
    receives results as JSON. JSON numbers written by Python's ``repr`` of
    a float are the shortest round-trip strings, and JavaScript's
    ``JSON.parse`` reads them back to the same float64: transport is exact.

§2 ALGORITHM
    GET /api/health -> {"ok": true, "version": ...}
    GET /api/endpoints -> {name: doc}
    POST /api/<name> -> body (<= 1 MiB) parsed as a JSON object ->
                             api.call -> 200 JSON | 4xx {"error": message}
                             | 500 {"error": "internal error: ..."}
    GET anything else -> static file under web/ (index.html for "/");
                             explicit Content-Type map (Windows registry
                             may map .js to text/plain otherwise).
    serve(): bind host:port; if the port is busy try the next 20 ports;
    optionally open the default browser at the hub page.

§3 APPLICATIONS
    ``python atlas.py`` (cli.serve) for students; tests start it on port 0.

§4 SPECIFICATION
    make_server(host="127.0.0.1", port=8765, tries=20) -> ThreadingHTTPServer
        (raises OSError if no port in [port, port + tries) is free).
    serve(host, port, open_browser: bool, lang: str | None) -> None (blocks
        until Ctrl+C).
    Responses carry ``Cache-Control: no-cache`` so edited pages are picked up.

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    * ThreadingHTTPServer: a long calculation does not block page loads; a queue of 128 waiting connections
      (Server.request_queue_size; socketserver's 5 lost files of a page on macOS).
    * Default bind address is 127.0.0.1 (not reachable from the network).
      ``--host 0.0.0.0`` exposes it to the LAN (classroom use); the server
      only computes and serves files, it never writes to disk.
    * All console output is ASCII (Windows consoles, see
      docs/TROUBLESHOOTING.md).
§7 TEST CASES (tests/test_server.py)
    health, endpoint list, a POST round trip compared with a direct call
    (bitwise), 404 for unknown endpoint, 400 for bad JSON, static file with
    the right Content-Type, path traversal attempt -> 404.
§8' ROBUSTNESS
    Body larger than 1 MiB -> 413; non-object JSON -> 400; exceptions in a
    model -> 500 with the exception type and message (no traceback to the
    client; traceback printed to the console with --debug).
"""
from __future__ import annotations

import http.server
import json
import sys
import threading
import traceback
import webbrowser
from pathlib import Path

from . import __version__, api

# Azimuth the endpoints (quas_atlas.pages: numpy and the tables the models build on import, ~0.4 s) are
# imported in a thread of their own once the server is made, not with this module: the window of Azimuth starts this
# server while it builds itself, and the window waited for them. A request comes later (after the page has loaded)
# and, if they are not there yet, waits for them.
_pages_lock = threading.Lock()
_pages_ready = False


def load_pages() -> None:
    """Import quas_atlas.pages (registers the endpoints) once; any thread may ask, the others wait."""
    global _pages_ready
    if _pages_ready:
        return
    with _pages_lock:
        if not _pages_ready:
            from . import pages as _pages  # noqa: F401  (registers endpoints)

            _pages_ready = True


def preload_pages() -> None:
    """Import the endpoints in a thread of their own (nothing to do when they are there)."""
    if not _pages_ready:
        threading.Thread(target=_load_pages_quietly, name="quas-atlas-pages", daemon=True).start()


def _load_pages_quietly() -> None:
    try:
        load_pages()
    except Exception:  # reported again, with the reason, by the first request that needs them
        pass

WEB = Path(__file__).resolve().parent / "web"
MAX_BODY = 1 << 20
CTYPES = {
    ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml", ".png": "image/png", ".webp": "image/webp",
    ".woff2": "font/woff2", ".txt": "text/plain; charset=utf-8", ".ico": "image/x-icon",
}
DEBUG = False


class Handler(http.server.SimpleHTTPRequestHandler):
    server_version = f"QuASAtlas/{__version__}"

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(WEB), **kw)

    # -- quiet, ASCII-only logging ------------------------------------------
    def log_message(self, fmt, *args):
        if DEBUG:
            sys.stderr.write(("[atlas] " + fmt % args + "\n").encode("ascii", "backslashreplace").decode())

    def guess_type(self, path):
        return CTYPES.get(Path(str(path)).suffix.lower(), "application/octet-stream")

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def _json(self, status: int, obj) -> None:
        body = json.dumps(api.to_json(obj), ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/health":
            return self._json(200, {"ok": True, "version": __version__})
        if path == "/api/endpoints":
            load_pages()
            return self._json(200, {k: v.doc for k, v in sorted(api.REGISTRY.items())})
        if path.startswith("/api/"):
            return self._json(405, {"error": "use POST for calculations"})
        return super().do_GET()

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if not path.startswith("/api/"):
            return self._json(404, {"error": "not found"})
        name = path[len("/api/"):]
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return self._json(400, {"error": "bad Content-Length"})
        if n > MAX_BODY:
            return self._json(413, {"error": "request too large"})
        try:
            raw = json.loads(self.rfile.read(n) or b"{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self._json(400, {"error": "body is not valid JSON"})
        try:
            load_pages()
            return self._json(200, api.call(name, raw))
        except api.ApiError as e:
            return self._json(e.status, {"error": e.message})
        except Exception as e:  # model bug: report, keep serving
            if DEBUG:
                traceback.print_exc()
            return self._json(500, {"error": f"internal error: {type(e).__name__}: {e}"})


class Server(http.server.ThreadingHTTPServer):
    """A deep queue of waiting connections. socketserver keeps only 5; a topic page
    asks for 20-30 files at once (scripts, styles, fonts, pictures) while the hub loads its own, and on macOS
    the connections over the queue are refused — the page lost random files (qcapi.js: «QC is not defined»,
    its styles, Quill's picture) and stayed half drawn."""

    request_queue_size = 128
    daemon_threads = True
    # Azimuth 0.108.77 (the first test runs on Windows, a request to the server of the tests was reset
    # while the window of Azimuth was open): HTTPServer asks for SO_REUSEADDR, and on Windows that option lets a
    # second server bind a port another one listens on — the connections go to either. There the port is taken
    # exclusively (SO_EXCLUSIVEADDRUSE), so a port in use is refused and make_server takes the next one; on macOS and
    # Linux SO_REUSEADDR only allows a port left in TIME_WAIT, as before.
    allow_reuse_address = sys.platform != "win32"

    def server_bind(self):
        import socket

        if sys.platform == "win32" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def make_server(host: str = "127.0.0.1", port: int = 8765, tries: int = 20,
                preload: bool = True) -> http.server.ThreadingHTTPServer:
    """Bind the first free port in [port, port + tries). preload: import the endpoints in a thread at once (False:
    at the first request, or when the caller asks — preload_pages; Azimuth 0.109.3)."""
    last: OSError | None = None
    for p in ([0] if port == 0 else range(port, port + tries)):
        try:
            srv = Server((host, p), Handler)
            srv.daemon_threads = True
            if preload:
                preload_pages()
            return srv
        except OSError as e:
            last = e
    raise OSError(f"no free port in {port}..{port + tries - 1}: {last}")


def serve(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True,
          lang: str | None = None, debug: bool = False) -> None:
    """Run the Atlas until Ctrl+C."""
    global DEBUG
    DEBUG = debug
    srv = make_server(host, port)
    shown = "127.0.0.1" if host in ("0.0.0.0", "") else host
    url = f"http://{shown}:{srv.server_address[1]}/" + (f"?lang={lang}" if lang else "")
    print(f"[atlas] Azimuth Atlas {__version__}: open {url}")
    print("[atlas] keep this window open while you use the Atlas; Ctrl+C stops it")
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[atlas] stopped")
    finally:
        srv.server_close()


def start_background(port: int = 0) -> tuple[http.server.ThreadingHTTPServer, str]:
    """Start a server in a daemon thread (tests, verify_install); returns (server, base_url)."""
    srv = make_server("127.0.0.1", port)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


__all__ = ["make_server", "serve", "start_background", "Handler", "Server", "WEB"]
