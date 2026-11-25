"""SMILES of the built structure and its IUPAC name from PubChem, for what iupac.py cannot name.

§1 THEORY
    A SMILES string (Weininger 1988) writes the heavy-atom graph depth-first: branches in parentheses,
    ring closures as digits, bond orders '=' and '#', hydrogens implicit when an atom of the organic
    subset (B C N O P S F Cl Br I) has the smallest normal valence that fits its bonds (B 3; C 4; N 3, 5;
    O 2; P 3, 5; S 2, 4, 6; halogens 1); every other atom is written in brackets with its H count.
    PubChem PUG REST answers a name for a SMILES:
        https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/<SMILES>/property/IUPACName/txt
    (verified the PUG REST tutorial, LibreTexts "Accessing PubChem through PUG-REST", and a
    live request for CC(=O)C, which answered "propan-2-one"); the name is English only (computed by
    PubChem's own naming program). ASSUMPTION: an unknown structure answers HTTP 404
    (PUGREST.NotFound) and a SMILES PubChem cannot read HTTP 400 (PUGREST.BadRequest), as the tutorial
    describes; not observed here.
§2 ALGORITHM
    to_smiles: bond orders as in Compass (editing.perceived_orders), aromatic rings back to alternating
    single/double bonds (formats.kekule), a depth-first walk from the lowest-numbered heavy atom of each
    component; components joined with '.'. lookup: GET with a timeout, the first line of the body.
§3 APPLICATIONS
    workspace.show_iupac_name (in a worker thread, so the window does not wait for the network).
§4 SPECIFICATION
    to_smiles(molecule) -> str ('' for an empty structure). A lone H atom is '[H]', H2 is '[H][H]'.
    lookup(smiles, timeout=8.0) -> str | None: None when PubChem does not know the structure (HTTP 404)
        or gives an empty answer. OSError (URLError, timeout) when it cannot be reached: the caller says so.
    reason(error) -> 'certificate' | 'timeout' | 'server' | 'network' (the message says which).
    by_name(name, timeout=10.0) -> ('sdf', text) | ('smiles', text) | None («Молекула по названию…»).
    The request uses an SSL context with root certificates (_ssl_context: default, certifi, or macOS's
    own roots via /usr/bin/security) — the Python of python.org has none by default.
    URL is the request template.
§5 PROCEDURES - below.
§6 NOTES
    Sends the structure to an outside server, only when the user presses the button and iupac.py has
    no name. ASSUMPTION: PubChem's limits (5 requests/s, 400/min per the usage policy as remembered, not
    re-checked) are far above one request per click.
§7 TESTS
    tests/compass/test_iupac.py: to_smiles read back with names.smiles_graph (an independent parser written
    earlier for the names table) gives the same graph; lookup with a fake urlopen (no network in tests).
§8' ROBUSTNESS
    Charges are not stored in Compass structures, so an ion is sent as the neutral radical with the same
    H count; PubChem then names the radical or nothing.
"""

import urllib.error
import urllib.parse
import urllib.request

from modules.compass.chemistry.editing import perceived_orders
from modules.compass.chemistry.formats import kekule

URL = 'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{}/property/IUPACName/txt'
NORMAL = {
    'B': (3,),
    'C': (4,),
    'N': (3, 5),
    'O': (2,),
    'P': (3, 5),
    'S': (2, 4, 6),
    'F': (1,),
    'Cl': (1,),
    'Br': (1,),
    'I': (1,),
}
BOND = {1: '', 2: '=', 3: '#'}


def to_smiles(molecule):
    atoms = molecule.atoms
    symbols = [a.symbol for a in atoms]
    bonds = kekule(len(atoms), perceived_orders(molecule), symbols)
    heavy = [i for i, s in enumerate(symbols) if s != 'H']
    adj = {i: {} for i in range(len(atoms))}
    hcount = dict.fromkeys(heavy, 0)
    lone_h = []
    for i, j, o in bonds:
        adj[i][j] = adj[j][i] = int(o)
    for i, s in enumerate(symbols):
        if s == 'H':
            partners = [j for j in adj[i] if symbols[j] != 'H']
            if partners:
                hcount[partners[0]] += 1
            else:
                lone_h.append(i)
    heavy_adj = {i: {j: o for j, o in adj[i].items() if symbols[j] != 'H'} for i in heavy}

    def atom_text(i):
        s, h = symbols[i], hcount[i]
        used = sum(heavy_adj[i].values())
        if s in NORMAL:
            implicit = next((v - used for v in NORMAL[s] if v >= used), 0)
            if implicit == h:
                return s
        return f'[{s}H{h}]' if h > 1 else (f'[{s}H]' if h == 1 else f'[{s}]')

    parts, seen = [], set()
    for start in heavy:
        if start in seen:
            continue
        # ring closures: edges that close a cycle in a depth-first tree
        parent, order, closures = {start: None}, [], {}
        stack = [start]
        tree = {}
        while stack:
            u = stack.pop()
            if u in seen:
                continue
            seen.add(u)
            order.append(u)
            tree.setdefault(u, [])
            if parent[u] is not None:
                tree[parent[u]].append(u)
            for v in sorted(heavy_adj[u], reverse=True):
                if v not in seen:
                    parent[v] = u
                    stack.append(v)
        tree_edges = {frozenset((u, v)) for u in tree for v in tree[u]}
        digit = 0
        for u in order:
            for v in heavy_adj[u]:
                e = frozenset((u, v))
                if e not in tree_edges and e not in closures:
                    digit += 1
                    closures[e] = digit
        marks = {}
        for e, d in closures.items():
            for a in e:
                marks.setdefault(a, []).append((d, heavy_adj[min(e)][max(e)]))
        opened = set()

        def write(u):
            text = atom_text(u)
            for d, o in sorted(marks.get(u, [])):
                label = str(d) if d < 10 else f'%{d:02d}'
                if d in opened:
                    text += label
                else:
                    opened.add(d)
                    text += BOND[o] + label
            kids = tree[u]
            for k, v in enumerate(kids):
                branch = BOND[heavy_adj[u][v]] + write(v)
                text += branch if k == len(kids) - 1 else '(' + branch + ')'
            return text

        parts.append(write(start))
    for i in lone_h:  # H2 once per pair, a free H atom alone
        mates = [j for j in adj[i] if symbols[j] == 'H']
        if not mates:
            parts.append('[H]')
        elif mates[0] > i:
            parts.append('[H][H]')
    return '.'.join(parts)


def _ssl_context():
    """An SSL context that knows the root certificates.

    The Python of python.org on macOS brings no certificates of its own until «Install Certificates.command»
    is run, so every https request failed with CERTIFICATE_VERIFY_FAILED and Compass said «PubChem недоступен»
    while the browser reached PubChem. Order: the default context if it has certificates; else certifi when
    installed; else, on macOS, the system root certificates read with the system tool `security`.
    """
    import ssl
    import sys

    context = ssl.create_default_context()
    if context.cert_store_stats().get('x509_ca', 0):
        return context
    try:
        import certifi

        context.load_verify_locations(cafile=certifi.where())
        return context
    except (ImportError, OSError, ssl.SSLError):
        pass
    if sys.platform == 'darwin':
        import subprocess

        pem = ''
        for keychain in ('/System/Library/Keychains/SystemRootCertificates.keychain', '/Library/Keychains/System.keychain'):
            try:
                pem += subprocess.run(
                    ['/usr/bin/security', 'find-certificate', '-a', '-p', keychain],
                    capture_output=True, text=True, timeout=10, check=False, encoding='utf-8', errors='replace',
                ).stdout
            except (OSError, subprocess.SubprocessError):
                continue
        if 'BEGIN CERTIFICATE' in pem:
            try:
                context.load_verify_locations(cadata=pem)
            except ssl.SSLError:
                pass
    return context


_CONTEXT = []


def _urlopen(url, timeout):
    """urllib.request.urlopen with _ssl_context (made once)."""
    if not _CONTEXT:
        _CONTEXT.append(_ssl_context())
    return urllib.request.urlopen(url, timeout=timeout, context=_CONTEXT[0])


def reason(error):
    """'certificate', 'timeout', 'server' or 'network': what a failed lookup ran into, for the message."""
    import socket
    import ssl

    cause = getattr(error, 'reason', error)
    if isinstance(cause, ssl.SSLCertVerificationError) or isinstance(error, ssl.SSLCertVerificationError) or 'CERTIFICATE_VERIFY_FAILED' in str(error):
        return 'certificate'
    if isinstance(cause, (socket.timeout, TimeoutError)) or isinstance(error, (socket.timeout, TimeoutError)):
        return 'timeout'
    if isinstance(error, urllib.error.HTTPError):
        return 'server'
    return 'network'


def lookup(smiles, timeout=8.0, urlopen=_urlopen):
    if not smiles:
        return None
    url = URL.format(urllib.parse.quote(smiles, safe=''))
    try:
        with urlopen(url, timeout=timeout) as response:
            text = response.read().decode('utf-8', 'replace').strip()
    except urllib.error.HTTPError as error:
        if error.code in (400, 404):  # PUGREST.BadRequest / PUGREST.NotFound: no name for it
            return None
        raise
    first = text.splitlines()[0].strip() if text else ''
    return first or None


URL_INCHI = 'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{}/property/InChI,InChIKey/JSON'


def lookup_inchi(smiles, timeout=8.0, urlopen=_urlopen):
    """(InChI, InChIKey) of a structure by its SMILES from PubChem, None when PubChem does not know it
    (400/404); network errors are raised as by lookup()."""
    import json

    if not smiles:
        return None
    url = URL_INCHI.format(urllib.parse.quote(smiles, safe=''))
    try:
        with urlopen(url, timeout=timeout) as response:
            data = json.loads(response.read().decode('utf-8', 'replace'))
    except urllib.error.HTTPError as error:
        if error.code in (400, 404):
            return None
        raise
    except ValueError:
        return None
    rows = (data.get('PropertyTable') or {}).get('Properties') or []
    if not rows or not rows[0].get('InChI'):
        return None
    return rows[0]['InChI'], rows[0].get('InChIKey', '')


# «Файл → Молекула по названию…» — a structure by its name (aspirin, caffeine, 2-butanol)
URL_NAME_SDF = 'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{}/SDF?record_type=3d'
URL_NAME_PROPERTY = 'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{}/property/{}/JSON'
# PubChem renamed its SMILES properties in July 2025 (IsomericSMILES → SMILES/AbsoluteSMILES, CanonicalSMILES →
# ConnectivitySMILES; the PubChemPy issue 107); the new names first, the old ones if a server still wants them
SMILES_PROPERTIES = ('SMILES', 'ConnectivitySMILES', 'IsomericSMILES', 'CanonicalSMILES')


def by_name(name, timeout=10.0, urlopen=_urlopen):
    """(kind, text) of the compound called name: ('sdf', the 3D SDF record of PubChem — its conformer with the
    hydrogens) or, without a 3D record, ('smiles', its SMILES); None when PubChem does not know the name (HTTP 404).
    A property name the server refuses (HTTP 400) — the next one of SMILES_PROPERTIES. Network errors are raised."""
    import json

    name = (name or '').strip()
    if not name:
        return None
    quoted = urllib.parse.quote(name, safe='')
    try:
        with urlopen(URL_NAME_SDF.format(quoted), timeout=timeout) as response:
            text = response.read().decode('utf-8', 'replace')
        if 'V2000' in text or 'V3000' in text:
            return 'sdf', text
    except urllib.error.HTTPError as error:
        if error.code not in (400, 404):
            raise
    for prop in SMILES_PROPERTIES:
        try:
            with urlopen(URL_NAME_PROPERTY.format(quoted, prop), timeout=timeout) as response:
                data = json.loads(response.read().decode('utf-8', 'replace'))
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None  # PUGREST.NotFound: no compound of that name
            if error.code == 400:
                continue  # this property name is not known to the server
            raise
        except ValueError:
            continue
        rows = (data.get('PropertyTable') or {}).get('Properties') or []
        for key, value in (rows[0].items() if rows else ()):
            if 'SMILES' in key and isinstance(value, str) and value.strip():
                return 'smiles', value.strip()
    return None
