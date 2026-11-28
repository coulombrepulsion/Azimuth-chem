"""The measured values of any molecule NIST CCCBDB knows — found on the network, for «Опыт» of Spectrum when the
molecule is not one of the 30 of the course (analysis/measured.py has those without the network).

§1 PURPOSE
    About two thousand molecules of CCCBDB have a page «Experimental data» with the enthalpy of formation, the
    vibrational fundamentals (and for some the harmonic frequencies), the geometry, the dipole moment and the
    ionization energy. The page is found by the CAS number of the molecule; the number — from PubChem by the SMILES
    of the structure.
§2 ALGORITHM
    find(molecule): SMILES of the structure (pubchem.to_smiles) → the CAS numbers among the synonyms of PubChem
    (/rest/pug/compound/smiles/…/synonyms/JSON, the names of the form 7732-18-5) → for each, the page
    exp2x.asp?casno=… → parse(html) → the entry is taken only when the graph of the SMILES on the page is the graph
    of the structure (measured.signature): CCCBDB answers an unknown number with the page of the molecule asked
    before (the session of the site), so its answer is always checked. The entry has the form of those of
    data/measured_molecules.json (measured.compare reads it) and 'harmonic' — the harmonic frequencies where the page
    has them. Kept in the folder of the user (CACHE / <InChIKey or SMILES>.json): the network once per molecule; a
    molecule not found is kept too (with 'missing') for a day.
    parse(html): the tables of the page by their headers — «Hfg(298.15K)», the vibrations (the header «Fundamental»:
    mode, symmetry, fundamental, harmonic, reference …), the internal coordinates (the header «Connectivity»: name,
    value …; the bonds — the names r<Element><Element>), the dipole («Dipole (Debye)»: the total of the row of the
    experimental minimum, else the first one with a value), the ionization energies.
§4 SPECIFICATION
    parse(html, cas='') -> dict (raises ValueError: not a page of experimental data); cas_numbers(smiles, timeout,
    urlopen) -> [str]; page(cas, timeout, urlopen) -> str; find(molecule, folder=None, timeout=20, urlopen=None) ->
    dict | None (None: CCCBDB has no such molecule; ValueError — the network said no, with what to do);
    cached(molecule, folder=None) -> dict | None (no network); cache_folder().
§7 TESTS tests/spectrum/test_cccbdb.py — the pages of water, ethanol and chloroform as the site gave them
    (tests/data/cccbdb), a fake urlopen: no network in the tests.
"""

from __future__ import annotations

import json
import re
import time
from html.parser import HTMLParser
from pathlib import Path

PAGE = 'https://cccbdb.nist.gov/exp2x.asp?casno={}'
SYNONYMS = 'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{}/synonyms/JSON'
CAS = re.compile(r'^\d{2,7}-\d{2}-\d$')
MISSING_DAYS = 1.0


def cache_folder():
    from azimuth.window_control import state_file

    return state_file().parent / 'cccbdb'


class _Tables(HTMLParser):
    """Every <table> as rows of cell texts (the text of the tags inside joined); the <h1> of the page."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self._stack, self.title, self._in_title = [], [], '', False

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self._stack.append({'id': dict(attrs).get('id', '') or dict(attrs).get('ID', ''), 'rows': []})
        elif tag == 'tr' and self._stack:
            self._stack[-1]['rows'].append([])
        elif tag in ('td', 'th') and self._stack and self._stack[-1]['rows']:
            self._stack[-1]['rows'][-1].append('')
        elif tag == 'h1':
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == 'table' and self._stack:
            table = self._stack.pop()
            table['rows'] = [[' '.join(c.split()) for c in row] for row in table['rows'] if row]
            self.tables.append(table)
        elif tag == 'h1':
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._stack and self._stack[-1]['rows'] and self._stack[-1]['rows'][-1]:
            self._stack[-1]['rows'][-1][-1] += data


def _number(text):
    found = re.match(r'^\s*(-?\d+(?:\.\d+)?)', (text or '').replace('\xa0', ' '))
    return float(found.group(1)) if found else None


def _header(table):
    return ' '.join(' '.join(row) for row in table['rows'][:2])


def _elements(name):
    """'rOH' -> ('O', 'H'); 'rCCl' -> ('C', 'Cl'); None when not a bond of two elements."""
    found = re.fullmatch(r'r([A-Z][a-z]?)([A-Z][a-z]?)', name or '')
    return (found.group(1), found.group(2)) if found else None


def parse(html, cas=''):
    reader = _Tables()
    reader.feed(html)
    title = ' '.join(reader.title.split())
    if not title.startswith('Experimental data for'):
        raise ValueError('not a page of experimental data of CCCBDB')
    entry = {'key': 'cccbdb-' + cas.replace('-', ''), 'cas': cas, 'formula': '', 'smiles': '', 'inchikey': '',
             'name': {}, 'hf298_kj': None, 'hf298_unc': None, 'hf0_kj': None, 'hf_source': '', 'fundamentals': [],
             'harmonic': [], 'bonds': [], 'dipole_debye': None, 'ie_ev': None, 'vertical_ie_ev': None, 'note': '',
             'online': True}
    found = re.match(r'Experimental data for (\S+)(?:\s*\((.*)\))?', title)
    if found:
        entry['formula'] = found.group(1)
        named = (found.group(2) or found.group(1)).strip()
        entry['name'] = {'ru': named, 'en': named, 'zh': named}
    for table in reader.tables:
        rows, head = table['rows'], _header(table)
        if table['id'].lower() == 'idents' and len(rows) > 1 and len(rows[1]) >= 3:
            entry['inchikey'], entry['smiles'] = rows[1][1], rows[1][2]
        elif any(row and row[0].startswith('Hfg(298.15K)') for row in rows):
            row = next(row for row in rows if row and row[0].startswith('Hfg(298.15K)'))
            entry['hf298_kj'] = _number(row[1]) if len(row) > 1 else None
            entry['hf298_unc'] = _number(row[2]) if len(row) > 2 else None
            entry['hf_source'] = row[4] if len(row) > 4 else ''
            zero = next((row for row in rows if row and row[0].startswith('Hfg(0K)')), None)
            entry['hf0_kj'] = _number(zero[1]) if zero and len(zero) > 1 else None
        elif 'Fundamental' in head and 'Symmetry' in head:
            for row in rows:
                if len(row) >= 4 and row[0].strip().isdigit():
                    nu, omega = _number(row[2]), _number(row[3])
                    if nu is not None:
                        entry['fundamentals'].append([row[1].replace(' ', ''), int(round(nu))])
                    if omega is not None:
                        entry['harmonic'].append([row[1].replace(' ', ''), int(round(omega))])
        elif 'Connectivity' in head:
            for row in rows:
                pair = _elements(row[0]) if row else None
                value = _number(row[1]) if len(row) > 1 else None
                if pair and value:
                    entry['bonds'].append([pair[0], pair[1], value])
        elif 'Dipole (Debye)' in head and entry['dipole_debye'] is None:
            best = None
            for row in rows:
                if len(row) >= 9 and row[0].strip().isdigit():
                    total = _number(row[8])
                    if total is not None and (best is None or row[4].strip() == 'True'):
                        best = total
                        if row[4].strip() == 'True':
                            break
            entry['dipole_debye'] = best
        elif rows and rows[0] and rows[0][0] == 'Ionization Energy' and len(rows) > 1:
            entry['ie_ev'] = _number(rows[1][0])
            entry['vertical_ie_ev'] = _number(rows[1][2]) if len(rows[1]) > 2 else None
    return entry


def _open(urlopen, url, timeout):
    import urllib.request

    if urlopen is None:
        from modules.compass.chemistry.pubchem import _urlopen as urlopen
    request = urllib.request.Request(url, headers={'User-Agent': 'Azimuth (teaching program; cccbdb lookup)'})
    with urlopen(request, timeout) as response:
        return response.read().decode('utf-8', errors='replace')


def cas_numbers(smiles, timeout=20.0, urlopen=None):
    import urllib.error
    import urllib.parse

    try:
        text = _open(urlopen, SYNONYMS.format(urllib.parse.quote(smiles, safe='')), timeout)
    except urllib.error.HTTPError as error:
        if error.code in (400, 404):  # PubChem does not know the structure
            return []
        raise
    found = []
    for info in json.loads(text).get('InformationList', {}).get('Information', []):
        found += [s for s in info.get('Synonym', []) if CAS.match(s) and s not in found]
    return found


def page(cas, timeout=20.0, urlopen=None):
    return _open(urlopen, PAGE.format(cas.replace('-', '')), timeout)


def _key(molecule):
    from modules.compass.chemistry.pubchem import to_smiles

    smiles = to_smiles(molecule)
    return smiles, re.sub(r'[^A-Za-z0-9=#()\[\]@+-]', '_', smiles)[:120] or 'molecule'


def find(molecule, folder=None, timeout=20.0, urlopen=None):
    """The entry of CCCBDB for the structure, or None when CCCBDB has no page of it. ValueError — the network failed
    (the message says what to do)."""
    import urllib.error

    from modules.spectrum.analysis import measured

    smiles, name = _key(molecule)
    folder = Path(folder) if folder else cache_folder()
    kept = folder / f'{name}.json'
    try:
        known = json.loads(kept.read_text(encoding='utf-8'))
        if not known.get('missing'):
            return known
        if time.time() - float(known.get('at', 0)) < MISSING_DAYS * 86400:
            return None
    except (OSError, ValueError, TypeError):
        pass
    mine = measured.signature(molecule)
    try:
        numbers = cas_numbers(smiles, timeout, urlopen)
        entry = None
        for cas in numbers[:5]:
            try:
                candidate = parse(page(cas, timeout, urlopen), cas)
            except ValueError:
                continue
            if candidate['smiles'] and measured.smiles_signature(candidate['smiles']) == mine:
                entry = candidate
                break
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        from azimuth.i18n import tr
        from modules.compass.chemistry.pubchem import reason

        why = {'certificate': tr('не проверен сертификат сайта'), 'timeout': tr('сайт не ответил вовремя'),
               'server': tr('сайт ответил ошибкой')}.get(reason(exc), tr('нет связи'))
        raise ValueError(tr('Поиск в CCCBDB не удался: {}. Проверьте интернет и попробуйте ещё раз.').format(why)) from None
    try:
        folder.mkdir(parents=True, exist_ok=True)
        kept.write_text(json.dumps(entry if entry is not None else {'missing': True, 'at': time.time(), 'smiles': smiles},
                                   ensure_ascii=False), encoding='utf-8')
    except OSError:
        pass  # not kept: asked again next time
    return entry


def cached(molecule, folder=None):
    """The entry kept from an earlier search of the structure (no network), or None."""
    try:
        _smiles, name = _key(molecule)
        known = json.loads(((Path(folder) if folder else cache_folder()) / f'{name}.json').read_text(encoding='utf-8'))
    except (OSError, ValueError, TypeError, AttributeError):
        return None
    return None if known.get('missing') else known
