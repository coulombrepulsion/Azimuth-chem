"""The bundled Atlas v2 (docs/features/ATLAS.md §4): complete, checked without a browser.

The contract of window.QuASAtlas with the panel of the program (modules/atlas/panel.py) went with that panel
— the Atlas is on the site; the page keeps its API.
"""

from modules.atlas.paths import ATLAS_HOME


def test_bundle_is_complete():
    package = ATLAS_HOME / 'quas_atlas'
    for name in ('server.py', 'api.py', '__init__.py', 'web/index.html', 'web/assets/js/qcapi.js'):
        assert (package / name).is_file(), name
    for lang in ('ru', 'en', 'zh'):
        assert len(list((package / 'web' / lang).glob('*.html'))) == 56, lang  # + NMR, conformers, heavy elements,
        # crystals, Walsh diagrams, the Bloch theorem, bands, the properties of crystals, defects, adsorption, dynamics, ML, the transition state, derivatives, conical intersections, spin states, bonding, errors
