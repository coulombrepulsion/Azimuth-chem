"""Measured IR and UV-Vis spectra from the NIST Chemistry WebBook.

§1 PURPOSE
    A measured spectrum to lay over the computed one without a file of one's own: «Найти в NIST…» of the button
    «Эксперимент и конформеры» — the compound by its formula, name
    or CAS number, its spectra, one of them laid over the plot, with no file downloaded by hand.
§1 SOURCE
    NIST Chemistry WebBook, NIST Standard Reference Database 69 (webbook.nist.gov): IR spectra mostly of the gas phase
    (the NIST/EPA Gas-Phase Infrared Database; for some compounds the condensed phase, Coblentz Society, PNNL), and
    UV-Vis. The search: cbook.cgi?Name=… | Formula=…&NoIon=on | ID=<CAS>, with Units=SI — a list of compounds (links
    cbook.cgi?ID=C58082…), or the page of the compound itself when only one is found (its heading h1 id="Top"). The
    spectrum: cbook.cgi?JCAMP=<ID>&Index=<0, 1, …>&Type=IR | UVVis — a JCAMP-DX file; no spectrum of that index —
    «##TITLE=Spectrum not found.». ASSUMPTION (not observed: no network where this was written):
    the forms of the pages and of the answers as the WebBook has had them for years and as the scripts that read it
    (nistchempy) take them; a change of the site shows as «ничего не найдено», never as a wrong spectrum.
§4 SPECIFICATION
    query(text) -> (key, value): a CAS number → ('ID', 'C58082'); a formula (only elements and counts) → ('Formula', …);
      else ('Name', text). search_url(text), spectrum_url(ident, kind, index).
    compounds(html) -> [(ident, name)]; search(text, timeout, urlopen) -> [(ident, name)].
    spectrum(ident, kind, index, …) -> the text of the JCAMP-DX or None; spectra(ident, kind, limit=6, …) ->
      [(index, description, text)] — the description from ##STATE, ##SAMPLING PROCEDURE, ##ORIGIN, ##TITLE.
    KINDS {'IR', 'UVVis'}. Network errors are raised (the window says them as for PubChem).
§6 NOTES
    Only the words of the search and the identifier of the compound are sent — no structure, no file of the user.
§7 TESTS
    tests/spectrum/test_nist.py (a fake urlopen: no network in the tests).
"""

import html as html_lib
import re
import urllib.error
import urllib.parse

BASE = 'https://webbook.nist.gov/cgi/cbook.cgi'
PAGE = 'https://webbook.nist.gov/cgi/cbook.cgi?ID={}&Units=SI'
KINDS = ('IR', 'UVVis')
NOT_FOUND = 'spectrum not found'
ELEMENT = r'(?:A[cglmrstu]|B[aehikr]?|C[adeflmnorsu]?|D[bsy]|E[rsu]|F[elmr]?|G[ade]|H[efgos]?|I[nr]?|Kr?|L[airuv]|' \
          r'M[cdgnot]|N[abdehiop]?|O[gs]?|P[abdmortu]?|R[abefghnu]|S[bcegimnr]?|T[abcehilms]|U|V|W|Xe|Yb?|Z[nr])'


# the WebBook refuses the default «Python-urllib/3.x»
# of urllib — the request goes with the name of a browser, the program named after it, as a browser's would
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) '
                  'Version/17.0 Safari/605.1.15 Azimuth',
    'Accept': 'text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.8',
}


def request(url):
    import urllib.request

    return urllib.request.Request(url, headers=HEADERS)


def _urlopen(url, timeout):
    from modules.compass.chemistry.pubchem import _urlopen as opener  # the SSL context that knows the roots

    return opener(request(url), timeout)


def query(text):
    text = (text or '').strip()
    cas = re.fullmatch(r'(\d{2,7})-(\d{2})-(\d)', text)
    if cas:
        return 'ID', 'C' + ''.join(cas.groups())
    if re.fullmatch(rf'(?:{ELEMENT}\d*)+', text) and re.search(r'\d|[A-Z].*[A-Z]', text):
        return 'Formula', text
    return 'Name', text


def search_url(text):
    key, value = query(text)
    fields = {key: value, 'Units': 'SI'}
    if key == 'Formula':
        fields['NoIon'] = 'on'
    return BASE + '?' + urllib.parse.urlencode(fields)


def spectrum_url(ident, kind, index):
    return BASE + '?' + urllib.parse.urlencode({'JCAMP': ident, 'Index': index, 'Type': kind})


def _text(fragment):
    return ' '.join(html_lib.unescape(re.sub(r'<[^>]+>', '', fragment)).split())


def compounds(page):
    """The compounds of an answer of the search: the list, or the one compound of its own page."""
    heading = re.search(r'<h1[^>]*id=["\']Top["\'][^>]*>(.*?)</h1>', page, re.S | re.I)
    if heading:
        ident = re.search(r'[?&;]ID=([A-Z]\d+)', page)
        return [(ident.group(1), _text(heading.group(1)))] if ident else []
    found, seen = [], set()
    for ident, name in re.findall(r'<li>\s*<a\s+href=["\'][^"\']*cbook\.cgi\?ID=([A-Z]\d+)[^"\']*["\']\s*>(.*?)</a>',
                                  page, re.S | re.I):
        if ident not in seen:
            seen.add(ident)
            found.append((ident, _text(name)))
    return found


def _read(url, timeout, urlopen):
    with urlopen(url, timeout) as response:
        return response.read().decode('utf-8', 'replace')


def search(text, timeout=20.0, urlopen=_urlopen):
    if not (text or '').strip():
        return []
    try:
        return compounds(_read(search_url(text), timeout, urlopen))
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return []
        raise


def spectrum(ident, kind='IR', index=0, timeout=20.0, urlopen=_urlopen):
    if kind not in KINDS:
        raise ValueError(kind)
    try:
        text = _read(spectrum_url(ident, kind, index), timeout, urlopen)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise
    if NOT_FOUND in text.lower() or not re.search(r'##\s*(XYDATA|XYPOINTS|PEAK\s*TABLE)', text, re.I):
        return None
    return text


def describe(text):
    from modules.spectrum.analysis.experiment import _labels

    labels = _labels(text)
    parts = [labels.get(key, '') for key in ('STATE', 'SAMPLINGPROCEDURE', 'ORIGIN')]
    parts = [p for p in parts if p]
    return ' · '.join(parts) or labels.get('TITLE', '')


def spectra(ident, kind='IR', limit=6, timeout=20.0, urlopen=_urlopen):
    found = []
    for index in range(limit):
        text = spectrum(ident, kind, index, timeout, urlopen)
        if text is None:
            break
        found.append((index, describe(text), text))
    return found
