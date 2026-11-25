"""Measured spectra from the NIST Chemistry WebBook (modules/spectrum/readers/nist.py) — a fake server."""

import io
import urllib.parse

import numpy as np

from modules.spectrum.analysis import experiment
from modules.spectrum.readers import nist

LIST = """<html><body><h1>Search Results</h1><p>A total of 2 matching species were found.</p><ol>
<li><a href="/cgi/cbook.cgi?ID=C58082&amp;Units=SI">Caffeine</a> (C<sub>8</sub>H<sub>10</sub>N<sub>4</sub>O<sub>2</sub>)</li>
<li><a href="/cgi/cbook.cgi?ID=C479189&amp;Units=SI">1,3,9-Trimethyl&shy;xanthine</a></li>
</ol></body></html>"""
PAGE = """<html><body><h1 id="Top">Caffeine</h1><ul><li><a href="/cgi/cbook.cgi?ID=C58082&amp;Units=SI&amp;Mask=80#IR-Spec">IR Spectrum</a></li></ul></body></html>"""
JCAMP = """##TITLE=Caffeine
##JCAMP-DX=4.24
##DATA TYPE=INFRARED SPECTRUM
##ORIGIN=NIST/EPA Gas-Phase Infrared Database
##STATE=gas
##XUNITS=1/CM
##YUNITS=ABSORBANCE
##XFACTOR=1
##YFACTOR=0.0001
##FIRSTX=1000
##LASTX=1008
##NPOINTS=9
##XYDATA=(X++(Y..Y))
1000 0 10 100 1000 3000 1000 100 10 0
##END=
"""


class Answer(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def server(pages):
    asked = []

    def urlopen(url, timeout):
        asked.append(url)
        query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
        return Answer(pages(query).encode('utf-8'))

    return urlopen, asked


def test_the_query_is_a_formula_a_name_or_a_cas_number():
    assert nist.query('C8H10N4O2') == ('Formula', 'C8H10N4O2')
    assert nist.query('58-08-2') == ('ID', 'C58082')
    assert nist.query('caffeine') == ('Name', 'caffeine')
    assert nist.query('Benzene') == ('Name', 'Benzene') and nist.query('Water') == ('Name', 'Water')
    assert 'NoIon=on' in nist.search_url('H2O') and 'Name=caffeine' in nist.search_url('caffeine')


def test_compounds_of_a_list_and_of_a_page():
    assert nist.compounds(LIST) == [('C58082', 'Caffeine'), ('C479189', '1,3,9-Trimethyl\xadxanthine')]
    assert nist.compounds(PAGE) == [('C58082', 'Caffeine')]
    assert nist.compounds('<html>No matching species found</html>') == []


def test_the_spectra_of_a_compound_until_there_is_none():
    def pages(query):
        if 'JCAMP' in query:
            return JCAMP if query['Index'] == '0' else '##TITLE=Spectrum not found.\n##END=\n'
        return LIST

    urlopen, asked = server(pages)
    assert nist.search('C8H10N4O2', urlopen=urlopen)[0] == ('C58082', 'Caffeine')
    found = nist.spectra('C58082', 'IR', urlopen=urlopen)
    assert len(found) == 1 and found[0][1] == 'gas · NIST/EPA Gas-Phase Infrared Database'
    assert 'JCAMP=C58082' in asked[-1] and 'Index=1' in asked[-1] and 'Type=IR' in asked[-1]
    measured = experiment.parse(found[0][2], 'Caffeine · NIST')
    x, y = experiment.on_axis(measured, 'cm-1')
    assert x[np.argmax(y)] == 1004 and y.max() == 1


def test_uv_vis_of_nist_is_lg_epsilon():
    text = """##TITLE=test
##XUNITS=NANOMETERS
##YUNITS=LOGARITHM EPSILON
##XYPOINTS=(XY..XY)
200, 2.0
250, 4.0
300, 3.0
350, 2.0
400, 1.0
##END=
"""
    measured = experiment.parse(text)
    assert measured.y_unit == 'log' and measured.x_unit == 'nm'
    x, y = experiment.on_axis(measured, 'nm')
    assert x[np.argmax(y)] == 250 and abs(y[2] - 990 / 9990) < 1e-9  # (10³ − 10¹) / (10⁴ − 10¹): the baseline off


def test_the_request_names_a_browser():
    # NIST refuses the default «Python-urllib» agent (403)
    made = nist.request(nist.search_url('caffeine'))
    assert 'Mozilla' in made.get_header('User-agent') and 'Python-urllib' not in made.get_header('User-agent')
    assert made.full_url.startswith('https://webbook.nist.gov/cgi/cbook.cgi?Name=caffeine')
