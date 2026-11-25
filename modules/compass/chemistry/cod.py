"""Crystal structures from the Crystallography Open Database (COD) — the search and the CIF.

§1 THEORY
    COD (Gražulis et al., Nucleic Acids Res. 40, D420, 2012; www.crystallography.net) is an open collection of about
    half a million crystal structures — organic, inorganic, minerals, metal–organic — each a CIF under a seven-digit
    number, free to use (the open alternative to the paid CSD of Mercury). Its RESTful interface (the COD wiki,
    «RESTful API», read 2026-11-14):
        https://www.crystallography.net/cod/result?<criteria>&format=json — the entries found;
        https://www.crystallography.net/cod/<number>.cif — the CIF of an entry.
    The criteria used here: text (words of the name, the mineral, the title, the authors), formula (the summary
    formula as COD writes it: elements in Hill's order — C, H, then alphabetical; without carbon all alphabetical —
    separated by spaces, «C7 H6 O2», «O2 Ti»), el1 … el8 (elements that must be present), nel1 … (absent — not used)
    and strictmin/strictmax (the number of distinct elements).
§2 ALGORITHM
    hill(text) turns «C7H6O2», «C7 H6 O2», «TiO2» into the formula of COD (counts of 1 not written). url(...) joins
    the criteria; search() reads the JSON — a list of records, one per entry — and keeps of each the number
    ('file'), the formula (COD writes it «- C7 H6 O2 -»: the dashes taken off), the names (chemname, commonname,
    mineral), the space group (sg), the cell (a, b, c, alpha, beta, gamma), the year, the journal and the DOI.
    The names of the fields were checked against the server on 'file', 'formula'
    («- C7 H6 O2 -»), 'chemname', 'commonname', 'mineral', 'sg', 'a' … 'gamma' (text), 'year', 'journal', 'doi',
    'title' and more; a missing field is left empty, and 'cod_id' is also taken for the number.
    0.180.0 — by the cell: the form «search by cell» of COD sends amin, amax, bmin, bmax, cmin, cmax, alpmin, alpmax,
    betmin, betmax, gamin, gamax (Å, °; checked on the same day: a 5.4–5.6, b 5.0–5.2, c 21.8–22.0 finds benzoic acid,
    7133168, and two more). cell_query: each length ± tolerance % of it, each angle ± angle_tolerance °; with
    any_order the lengths are tried in their six orders (another setting of the cell; the angles then left out) — one
    request each, the entries merged by number.
§3 APPLICATIONS
    modules/compass/actions/cod_window.py: «Файл → Найти кристалл в COD…» of «Компас · Кристалл».
§4 SPECIFICATION
    hill(text) -> str ('' for an empty text); ValueError for a text that is not a formula.
    url(text='', formula='', elements=(), exact=False, cell=None, tolerance=TOLERANCE, angle_tolerance=ANGLE) -> str;
    ValueError without any criterion. Parse_cell(text) -> (a, b, c) or (a, b, c, α, β, γ) (ValueError);
    cell_query(cell, tolerance, angle_tolerance) -> [(key, value)]; urls(…, any_order=False) -> [str].
    Entry(number, formula, name, group, cell (a, b, c, α, β, γ) | None, year, journal, doi).
    search(text='', formula='', elements=(), exact=False, timeout=30.0, urlopen=pubchem._urlopen, limit=LIMIT,
        cell=None, tolerance=TOLERANCE, angle_tolerance=ANGLE, any_order=False) -> (entries (at most limit), the
        number found).
    cif_url(number) -> str; fetch(number, timeout=30.0, urlopen=...) -> the text of the CIF (ValueError if the
        answer is not a CIF).
§5 PROCEDURES - below.
§6 NOTES
    Only when the user asks (the button of the window), in a worker thread; nothing about the user is sent but the
    words of the search. The certificates: those of pubchem._ssl_context (the Python of python.org on macOS).
§7 TESTS
    tests/compass/test_cod.py — with a fake server (no network in the tests): the URL of the criteria, the reading of
    the records, the CIF read by the crystal module.
§8' ROBUSTNESS / ERRORS
    OSError (URLError, timeout) when COD cannot be reached — the window says which (pubchem.reason).
"""

from dataclasses import dataclass
import json
import re
import urllib.parse

from azimuth.i18n import tr
from modules.compass.chemistry import pubchem

SEARCH = 'https://www.crystallography.net/cod/result'
CIF = 'https://www.crystallography.net/cod/{}.cif'
PAGE = 'https://www.crystallography.net/cod/{}.html'
LIMIT = 500
TOLERANCE, ANGLE = 1.0, 1.0  # % of a length, degrees of an angle
ELEMENT = re.compile(r'([A-Z][a-z]?)(\d*\.?\d*)')


@dataclass(frozen=True)
class Entry:
    number: str
    formula: str
    name: str
    group: str
    cell: tuple | None
    year: str
    journal: str
    doi: str


def hill(text):
    text = (text or '').strip()
    if not text:
        return ''
    squeezed = re.sub(r'[\s\-]+', '', text)
    count = {}
    position = 0
    for m in ELEMENT.finditer(squeezed):
        if m.start() != position or not m.group(0):
            raise ValueError(tr('Формула «{}» не читается: напишите её как C7H6O2 или TiO2.').format(text))
        number = m.group(2)
        count[m.group(1)] = count.get(m.group(1), 0) + (float(number) if number else 1)
        position = m.end()
    if position != len(squeezed) or not count:
        raise ValueError(tr('Формула «{}» не читается: напишите её как C7H6O2 или TiO2.').format(text))
    order = (['C', 'H'] + sorted(k for k in count if k not in ('C', 'H'))) if 'C' in count else sorted(count)
    parts = []
    for element in order:
        if element in count:
            n = count[element]
            parts.append(element + ('' if n == 1 else (str(int(n)) if n == int(n) else f'{n:g}')))
    return ' '.join(parts)


def parse_cell(text):
    values = []
    for part in re.split(r'[\s;,]+', (text or '').replace('°', ' ').strip()):
        if not part:
            continue
        try:
            values.append(float(part.split('(')[0]))
        except ValueError:
            raise ValueError(tr('Ячейка: три длины (Å) или три длины и три угла (°), например 5.50 5.14 21.93 90 97.4 90.')) from None
    if len(values) not in (3, 6) or any(v <= 0 for v in values) or any(not 0 < v < 180 for v in values[3:]):
        raise ValueError(tr('Ячейка: три длины (Å) или три длины и три угла (°), например 5.50 5.14 21.93 90 97.4 90.'))
    return tuple(values)


def _fixed(value):
    return f'{value:.4f}'.rstrip('0').rstrip('.')


def cell_query(cell, tolerance=TOLERANCE, angle_tolerance=ANGLE):
    query = []
    for key, value in zip(('a', 'b', 'c'), cell[:3]):
        spread = value * tolerance / 100
        query += [(key + 'min', _fixed(value - spread)), (key + 'max', _fixed(value + spread))]
    for key, value in zip(('alp', 'bet', 'ga'), cell[3:6]):
        query += [(key + 'min', _fixed(value - angle_tolerance)), (key + 'max', _fixed(value + angle_tolerance))]
    return query


def url(text='', formula='', elements=(), exact=False, cell=None, tolerance=TOLERANCE, angle_tolerance=ANGLE):
    query = []
    if text.strip():
        query.append(('text', text.strip()))
    if formula.strip():
        query.append(('formula', hill(formula)))
    chosen = [e.strip().capitalize() for e in elements if e.strip()]
    for k, element in enumerate(chosen[:8], 1):
        query.append((f'el{k}', element))
    if chosen and exact:
        query += [('strictmin', str(len(chosen[:8]))), ('strictmax', str(len(chosen[:8])))]
    if cell:
        query += cell_query(cell, tolerance, angle_tolerance)
    if not query:
        raise ValueError(tr('Задайте хотя бы одно условие поиска: слова, формулу, элементы или ячейку.'))
    query.append(('format', 'json'))
    return SEARCH + '?' + urllib.parse.urlencode(query, quote_via=urllib.parse.quote)


def _text(record, *keys):
    for key in keys:
        value = record.get(key)
        if value not in (None, ''):
            return str(value).strip()
    return ''


def _number(value):
    try:
        return float(str(value).split('(')[0])
    except (TypeError, ValueError):
        return None


def entry(record):
    number = _text(record, 'file', 'cod_id', 'id')
    formula = _text(record, 'formula', 'calcformula').strip('- ').strip()
    cell = tuple(_number(record.get(k)) for k in ('a', 'b', 'c', 'alpha', 'beta', 'gamma'))
    name = _text(record, 'mineral', 'commonname', 'chemname', 'title')
    return Entry(number, formula, name, _text(record, 'sg', 'space_group', 'sgHall'),
                 cell if all(v is not None for v in cell) else None, _text(record, 'year'), _text(record, 'journal'),
                 _text(record, 'doi'))


def urls(text='', formula='', elements=(), exact=False, cell=None, tolerance=TOLERANCE, angle_tolerance=ANGLE,
         any_order=False):
    if not cell or not any_order:
        return [url(text, formula, elements, exact, cell, tolerance, angle_tolerance)]
    from itertools import permutations

    orders = list(dict.fromkeys(permutations(cell[:3])))
    return [url(text, formula, elements, exact, order, tolerance, angle_tolerance) for order in orders]


def search(text='', formula='', elements=(), exact=False, timeout=30.0, urlopen=pubchem._urlopen, limit=LIMIT,
           cell=None, tolerance=TOLERANCE, angle_tolerance=ANGLE, any_order=False):
    entries, seen = [], set()
    for address in urls(text, formula, elements, exact, cell, tolerance, angle_tolerance, any_order):
        with urlopen(address, timeout) as response:
            body = response.read().decode('utf-8', errors='replace')
        body = body.strip()
        records = json.loads(body) if body else []
        if isinstance(records, dict):  # one record, or {'data': [...]}
            records = records.get('data', [records]) if isinstance(records.get('data', None), list) else [records]
        for found in (entry(r) for r in records if isinstance(r, dict)):
            if found.number and found.number not in seen:
                seen.add(found.number)
                entries.append(found)
    return entries[:limit], len(entries)


def cif_url(number):
    number = str(number).strip()
    if not number.isdigit():
        raise ValueError(tr('Номер COD — семь цифр, например 2100301.'))
    return CIF.format(number)


def fetch(number, timeout=30.0, urlopen=pubchem._urlopen):
    with urlopen(cif_url(number), timeout) as response:
        text = response.read().decode('utf-8', errors='replace')
    if '_cell_length_a' not in text:
        raise ValueError(tr('COD прислал не CIF для номера {}.').format(number))
    return text
