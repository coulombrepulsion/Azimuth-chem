"""Registry of calculation endpoints exposed to the web pages.

HEADER
    Every numerical result shown on an Atlas page is produced by a Python
    function registered here under a dotted name (``"h2.point"``).  The
    local server (server.py) maps ``POST /api/<name>`` with a JSON object of
    parameters onto that function; the command line (``atlas.py calc``)
    calls the same functions.  Wilkinson convention, §8' (no numerics here).

§1 THEORY
    The pages are a view; the model lives in ``quas_atlas.core``.  A thin,
    explicit registry (instead of exposing modules wholesale) keeps the
    browser-reachable surface small and every parameter validated: an
    endpoint declares its parameters with types and admissible ranges, and
    the registry converts and checks them before the model runs.

§2 ALGORITHM
    endpoint(name, **params) decorates f; params map a parameter name to
    Param(kind, default, check).  call(name, raw):
      1. unknown name -> ApiError(404);
      2. for each declared parameter: take raw value or default (missing
         without default -> ApiError(400)); convert by kind (float/int/str/
         bool/list); run check (False -> ApiError(400) with the description);
      3. unexpected parameter names -> ApiError(400);
      4. return f(**converted); ValueError from the model -> ApiError(400).
    to_json(x): floats that are not finite become null (JSON has no NaN);
    tuples become lists.

§3 APPLICATIONS
    server.py (HTTP), cli.py (``calc``), tests (direct calls).

§4 SPECIFICATION
    Param(kind: "float"|"int"|"str"|"text"|"bool"|"list"|"any", default=REQUIRED,
          check: callable -> bool, doc: str)
    endpoint(name: str, doc: str = "", **params) -> decorator
    call(name: str, raw: dict) -> JSON-serialisable result; raises ApiError.
    ApiError(status: int, message: str).
    REGISTRY: dict name -> Endpoint(fn, params, doc).

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    Endpoints are registered on import of ``quas_atlas.pages``; importing
    this module alone registers nothing.
§7 TEST CASES (tests/test_api.py)
    unknown endpoint -> 404; missing/extra/out-of-range parameter -> 400;
    NaN in a result serialises as null.
§8' ROBUSTNESS
    Parameter conversion rejects bool for float/int (True is an int in
    Python), NaN and infinities for floats, and strings longer than 200
    characters ("text": 200 000, for pasted coordinate files).  Lists are
    limited to 10 000 elements; endpoints check list contents themselves.
    A parameter whose default is None is optional and may be sent as null.
"""
from __future__ import annotations

import copy
import json
import math
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable

REQUIRED = object()


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


@dataclass
class Param:
    kind: str
    default: Any = REQUIRED
    check: Callable[[Any], bool] | None = None
    doc: str = ""


@dataclass
class Endpoint:
    fn: Callable[..., Any]
    params: dict[str, Param] = field(default_factory=dict)
    doc: str = ""
    memo: bool = False  # Azimuth the answers are remembered (a slow, deterministic endpoint)


REGISTRY: dict[str, Endpoint] = {}


def endpoint(name: str, doc: str = "", *, memo: bool = False, **params: Param):
    """Register f as the endpoint ``name`` with declared parameters. memo=True: the same parameters are answered from
    memory (MEMO_SIZE answers, the oldest forgotten first) — only for slow endpoints without randomness."""
    def deco(fn):
        if name in REGISTRY:
            raise RuntimeError(f"endpoint {name} registered twice")
        REGISTRY[name] = Endpoint(fn, params, doc or (fn.__doc__ or "").strip().split("\n")[0], memo)
        return fn
    return deco


def _convert(pname: str, p: Param, v: Any) -> Any:
    k = p.kind
    if v is None and p.default is None:
        return None
    if k == "float":
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ApiError(400, f"{pname}: number expected")
        v = float(v)
        if not math.isfinite(v):
            raise ApiError(400, f"{pname}: finite number expected")
    elif k == "int":
        if isinstance(v, bool) or not isinstance(v, (int, float)) or float(v) != int(v):
            raise ApiError(400, f"{pname}: integer expected")
        v = int(v)
    elif k == "str":
        if not isinstance(v, str) or len(v) > 200:
            raise ApiError(400, f"{pname}: string (<= 200 chars) expected")
    elif k == "text":
        if not isinstance(v, str) or len(v) > 200_000:
            raise ApiError(400, f"{pname}: text (<= 200000 chars) expected")
    elif k == "bool":
        if not isinstance(v, bool):
            raise ApiError(400, f"{pname}: true/false expected")
    elif k == "list":
        if not isinstance(v, list) or len(v) > 10000:
            raise ApiError(400, f"{pname}: list (<= 10000 items) expected")
    elif k == "any":
        pass
    else:
        raise RuntimeError(f"unknown parameter kind {k}")
    if p.check is not None and not p.check(v):
        raise ApiError(400, f"{pname}: value out of range ({p.doc or 'see endpoint documentation'})")
    return v


def call(name: str, raw: dict | None) -> Any:
    """Validate parameters and run the endpoint ``name``."""
    ep = REGISTRY.get(name)
    if ep is None:
        raise ApiError(404, f"unknown endpoint {name}")
    raw = raw or {}
    if not isinstance(raw, dict):
        raise ApiError(400, "parameters must be a JSON object")
    extra = set(raw) - set(ep.params)
    if extra:
        raise ApiError(400, f"unexpected parameters: {sorted(extra)}")
    kw = {}
    for pname, p in ep.params.items():
        if pname in raw:
            kw[pname] = _convert(pname, p, raw[pname])
        elif p.default is REQUIRED:
            raise ApiError(400, f"missing parameter {pname}")
        else:
            kw[pname] = p.default
    key = None
    if ep.memo:
        key = (name, json.dumps(kw, sort_keys=True, default=str))
        with _MEMO_LOCK:
            if key in _MEMO:
                _MEMO.move_to_end(key)
                return copy.deepcopy(_MEMO[key])
    try:
        result = ep.fn(**kw)
    except ValueError as e:
        raise ApiError(400, str(e)) from e
    if key is not None:
        with _MEMO_LOCK:
            _MEMO[key] = copy.deepcopy(result)
            while len(_MEMO) > MEMO_SIZE:
                _MEMO.popitem(last=False)
    return result


MEMO_SIZE = 256
_MEMO: "OrderedDict[tuple, Any]" = OrderedDict()
_MEMO_LOCK = threading.Lock()


def to_json(x: Any) -> Any:
    """Make a result JSON-safe: non-finite floats -> None, tuples -> lists."""
    if isinstance(x, float):
        return x if math.isfinite(x) else None
    if isinstance(x, dict):
        return {str(k): to_json(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [to_json(v) for v in x]
    return x
