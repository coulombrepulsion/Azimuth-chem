"""The best conformer of each structure of a queue before its calculation (modules/sextant/batch_conformers.py)."""

import math
import threading

import pytest

from azimuth.core import Atom, Molecule, read_xyz
from modules.compass.chemistry import conformers as cf
from modules.compass.chemistry import library
from modules.sextant import batch_conformers as bc
from tests.fake_programs import fake_program
from tests.sextant.test_binding import crown

# a fake xtb: the «optimized» structure is the one given; its energy grows with the distance of the first and the last
# carbon (so the turns with the ends close are the lowest), the structure number 0 gets a bond broken (a C–H pulled out)
FAKE_XTB = '''
import math
text = open(args[0]).read().split(chr(10))
n = int(text[0])
rows = [line.split() for line in text[2:2 + n]]
carbons = [[float(v) for v in r[1:4]] for r in rows if r[0] == 'C']
energy = -10.0 + 0.01 * math.dist(carbons[0], carbons[-1])
if os.path.exists('../broken') and not os.path.exists('../broken.used'):
    open('../broken.used', 'w').close()
    rows[-1][3] = str(float(rows[-1][3]) + 3.0)
    energy -= 1.0
with open('xtbopt.xyz', 'w') as out:
    out.write(str(n) + chr(10) + 'energy: ' + repr(energy) + chr(10))
    for r in rows:
        out.write(' '.join(r) + chr(10))
echo('          | TOTAL ENERGY  ' + repr(energy) + ' Eh   |')
echo('normal termination of xtb')
'''


def butane():
    return library.molecule(next(k for k in library.keys() if k.startswith('Бутан')))


class TestMethod:
    def test_picks_the_turns_when_molecule_has_one_rotor(self):
        # Arrange, Act, Assert
        assert bc.method_for('auto', butane()) == 'scan'

    def test_picks_crest_when_molecule_is_a_large_ring_without_rotors(self):
        # Arrange
        ring = crown()
        # Act, Assert
        assert not cf.rotors(ring) and bc.largest_ring(ring) == 18
        assert bc.method_for('auto', ring) == 'crest'

    def test_searches_nothing_when_molecule_is_small(self):
        # Arrange
        water = read_xyz('3\nwater\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0\n')
        # Act, Assert
        assert bc.method_for('auto', water) is None and bc.method_for('crest', water) is None


class TestBest:
    def test_takes_the_lowest_with_the_same_bonds_when_turns_are_optimized(self, tmp_path):
        # Arrange
        program = fake_program(tmp_path / 'bin', FAKE_XTB, name='xtb')
        start = butane()
        candidates = [m for m, _ in cf.candidates(start, 120, bc.SCAN_LIMIT)]
        root = tmp_path / 'search'
        root.mkdir()
        (root / 'broken').write_text('')

        def ends(m):
            carbons = [a.position for a in m.atoms if a.symbol == 'C']
            return math.dist(carbons[0], carbons[-1])

        # Act
        found, note = bc.best('scan', start, 0, 1, root, bc.Programs(xtb=program))
        # Assert
        assert found is not None and bc.same_bonds(found, start)
        assert ends(found) == pytest.approx(min(ends(m) for m in candidates), abs=1e-4)
        assert str(len(candidates)) in note

    def test_stops_when_cancelled(self, tmp_path):
        # Arrange
        program = fake_program(tmp_path / 'bin', FAKE_XTB, name='xtb')
        cancel = threading.Event()
        cancel.set()
        # Act, Assert
        with pytest.raises(InterruptedError):
            bc.best('scan', butane(), 0, 1, tmp_path / 'search', bc.Programs(xtb=program), cancel)

    def test_says_where_to_set_xtb_when_it_is_missing(self, tmp_path):
        # Arrange, Act, Assert
        with pytest.raises(ValueError, match='xtb'):
            bc.best('scan', butane(), 0, 1, tmp_path, bc.Programs())
