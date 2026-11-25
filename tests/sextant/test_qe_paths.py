"""The band path and the steps of the bands and the density of states.

Oracles: for the fcc lattice X = (0, 1, 0) and L = (½, ½, ½) of the conventional reciprocal basis are at |k| = 2π/a and
2π/a·√3/2 from Γ (Bradley & Cracknell); in the primitive cell of crystal.primitive (rows P) the fractions are f·Pᵀ —
X of silicon is (½, 0, ½) there by hand: (0, 1, 0)·Pᵀ with P = ((½, ½, 0), (½, 0, −½), (0, ½, −½)).
The outputs of pw.x 7.6 for silicon (tests/data/qe): 297 k-points of 8 bands, the top of the valence band 6.2016 eV at
Γ.
"""

from math import pi, sqrt
from pathlib import Path

from modules.compass.chemistry import crystal as cr
from modules.sextant import qe_inputs, qe_paths
from modules.spectrum.readers import qe
from tests.sextant.test_qe_inputs import silicon

DATA = Path(__file__).resolve().parents[1] / 'data' / 'qe'


def test_the_fcc_path_of_silicon():
    si = silicon()
    assert qe_paths.lattice(si) == 'cF'
    basis = cr.primitive_basis(si)
    p = qe_paths.path(si, basis)
    labels = [label for _, label in p.ticks]
    assert labels == ['Γ', 'X', 'W', 'K', 'Γ', 'L', 'U', 'W', 'L', 'K|U', 'X']
    x = [t for t, _ in p.ticks]
    a = si.cell.a
    assert abs(x[1] - 2 * pi / a) < 1e-9  # Γ–X
    assert abs(x[5] - x[4] - 2 * pi / a * sqrt(3) / 2) < 1e-9  # Γ–L
    ticks = {'K|U': x[9]}
    x_point = p.fractions[p.x.index(x[1])]
    expected = tuple(sum(f * b for f, b in zip((0, 1, 0), row)) for row in basis)
    assert all(abs(u - v) < 1e-9 for u, v in zip(x_point, expected)) and abs(expected[0] - 0.5) < 1e-9
    assert p.breaks == [p.x.index(ticks['K|U']) + 1] and len(p.fractions) == len(p.x)


def test_a_general_lattice_gets_the_general_path():
    from tests.compass.test_crystal_contacts import water_chain

    p = qe_paths.path(water_chain())  # P 1 — triclinic
    assert p.general and [label for _, label in p.ticks] == ['Γ', 'X|Γ', 'Y|Γ', 'Z']


def test_the_steps_of_the_bands_and_of_the_density_of_states(tmp_path):
    (tmp_path / 'Si.upf').write_text('<PP_HEADER z_valence="4.000000000000000E+000" />', encoding='utf-8')
    prim = cr.primitive(silicon())
    pseudo = {'Si': ('Si.upf', 30.0, 240.0)}
    assert qe_inputs.valence(tmp_path / 'Si.upf') == 4.0 and qe_inputs.bands_count(prim, pseudo, tmp_path) == 8
    bands = qe_inputs.steps(prim, qe_inputs.BANDS_TASK, pseudo, str(tmp_path), basis=cr.primitive_basis(silicon()),
                            conventional=silicon())
    assert [s[:2] for s in bands] == [('scf.in', 'pw.x'), ('bands.in', 'pw.x')]
    assert "calculation = 'bands'" in bands[1][2] and 'nbnd = 8' in bands[1][2] and 'tstress' not in bands[1][2]
    dos = qe_inputs.steps(prim, qe_inputs.DOS_TASK, pseudo, str(tmp_path))
    assert [s[1] for s in dos] == ['pw.x', 'pw.x', 'dos.x', 'projwfc.x'] and "fildos = 'azimuth.dos'" in dos[2][2]
    assert "filpdos = 'azimuth'" in dos[3][2] and qe_inputs.OPTIONAL == {'projwfc.x': 'projwfc.out'}
    assert "occupations = 'tetrahedra_opt'" in dos[1][2] and 'smearing' not in dos[1][2]


def test_the_bands_and_the_dos_of_pw76():
    text = (DATA / 'si_bands_pw76.out').read_text(encoding='utf-8')
    assert len(qe.runs(text)) == 2 and qe.read(qe.runs(text)[0]).highest == 6.2012
    found = qe.bands(text)
    assert len(found.k) == 297 and all(len(e) == 8 for e in found.energies)
    assert found.energies[0][:4] == [-5.7594, 6.2016, 6.2016, 6.2016]  # Γ: the triply degenerate top of the valence band
    gap = min(e[4] for e in found.energies) - max(e[3] for e in found.energies)
    assert abs(gap - 0.5741) < 1e-4
    dos = qe.read_dos((DATA / 'si_dos_pw76.dos').read_text(encoding='utf-8'))
    assert dos.fermi == 6.651 and len(dos.energies) == 2207 and abs(dos.integrated[-1] - 16.0) < 1e-6
