"""crystal_energetics: the Madelung constants of the textbooks, bond valence sums, Shannon radii and Pauling's rules."""

from pathlib import Path

import pytest

from modules.compass.chemistry import crystal as cr
from modules.compass.chemistry import crystal_energetics as ce

FCC = [(0, 0, 0), (0.5, 0.5, 0), (0.5, 0, 0.5), (0, 0.5, 0.5)]
EXAMPLES = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals'


def cubic(a, sites):
    return cr.Crystal('t', cr.Cell(a, a, a), tuple(cr.Site(f'{s}{i}', s, *f) for i, (s, f) in enumerate(sites)),
                      (cr.operation('x,y,z'),))


def cscl(a=4.12):
    return cubic(a, [('Cs', (0, 0, 0)), ('Cl', (0.5, 0.5, 0.5))])


def nacl(a=5.64):
    return cubic(a, [('Na', f) for f in FCC] + [('Cl', (f[0] + 0.5, f[1], f[2])) for f in FCC])


def caf2(a=5.46):
    return cubic(a, [('Ca', f) for f in FCC] + [('F', (x, y, z)) for x in (.25, .75) for y in (.25, .75)
                                                 for z in (.25, .75)])


def perovskite(a_ion, a=3.905):
    return cubic(a, [(a_ion, (0, 0, 0)), ('Ti', (0.5, 0.5, 0.5)), ('O', (0.5, 0.5, 0)), ('O', (0.5, 0, 0.5)),
                     ('O', (0, 0.5, 0.5))])


@pytest.mark.parametrize('make, constant', [(cscl, 1.762675), (nacl, 1.747565), (caf2, 2.519394)])
def test_madelung_constants_of_the_textbooks(make, constant):
    result = ce.madelung(make())
    assert result.constant == pytest.approx(constant, abs=2e-6)


def test_the_ewald_sum_does_not_depend_on_eta():
    one, _ = ce.ewald(nacl(), [1] * 4 + [-1] * 4, eta=0.4)
    two, _ = ce.ewald(nacl(), [1] * 4 + [-1] * 4, eta=1.3)
    assert one == pytest.approx(two, abs=1e-8)


def test_the_energy_and_the_potentials_of_cscl():
    result = ce.madelung(cscl())
    r0 = 4.12 * 3 ** 0.5 / 2
    assert result.energy_unit == pytest.approx(-1.762675 * ce.K_E / r0, rel=1e-6) and result.units == 1
    (_, cs, q_cs, phi_cs), (_, cl, q_cl, phi_cl) = result.sites
    assert (cs, q_cs, cl, q_cl) == ('Cs', 1.0, 'Cl', -1.0) and phi_cs < 0 < phi_cl
    assert result.formula == 'CsCl'


def test_a_charged_cell_is_refused():
    with pytest.raises(ValueError):
        ce.ewald(cscl(), [1, -0.5])


def test_oxidation_states():
    assert ce.oxidation_states(perovskite('Ba')) == {'Ba': 2, 'Ti': 4, 'O': -2}
    assert ce.oxidation_states(caf2()) == {'Ca': 2, 'F': -1}
    with pytest.raises(ValueError, match='органические молекулы или ионы'):
        ce.oxidation_states(cr.parse_cif((EXAMPLES / 'benzoic_acid.cif').read_text(encoding='utf-8')))
    with pytest.raises(ValueError, match='Простое вещество'):
        ce.oxidation_states(cr.parse_cif((EXAMPLES / 'graphite_P1.cif').read_text(encoding='utf-8')))


def test_bond_valence_sums():
    # NaCl: 6 × exp((2.15 − 2.82)/0.37) = 0.981 (R₀ of bvparm2020); BaTiO₃ at 4.00 Å: Ba overbonded, Ti underbonded
    result = ce.bond_valences(nacl())
    assert all(v == pytest.approx(6 * 2.718281828 ** ((2.15 - 2.82) / 0.37), abs=1e-6) for *_, v, _ in result.sites)
    assert result.gii < 0.1 and not result.missing
    bto = ce.bond_valences(perovskite('Ba', 4.00))
    sums = {ion: v for _, ion, _, v, _ in bto.sites}
    assert sums['Ba2+'] > 2.5 and sums['Ti4+'] < 3.8 and bto.gii > 0.2
    assert ce.bond_valences(perovskite('Sr')).gii < 0.15


def test_radii_and_pauling():
    result = ce.radii(nacl())
    assert result.ions == (('Na+', 6, 1.02, 6), ('Cl−', 6, 1.81, 6))
    (_, _, ratio, predicted, observed, total, shortest), = result.pairs
    assert ratio == pytest.approx(1.02 / 1.81) and predicted == observed == 6
    assert total == pytest.approx(2.83) and shortest == pytest.approx(2.82)
    assert ce.radii(cscl()).pairs[0][3:5] == (8, 8)
    # the second rule: the O of a perovskite — 2 Ti (4/6) and 4 Sr (2/12) = 2
    sto = ce.radii(perovskite('Sr'))
    assert all(total == pytest.approx(2) for _, total, _ in sto.electrostatic)
    assert sto.tolerance == pytest.approx((1.44 + 1.40) / (2 ** 0.5 * (0.605 + 1.40)))
    assert ce.radii(perovskite('Ba', 4.0)).tolerance > 1.02 and ce.radii(nacl()).tolerance is None
    assert ce.predicted_cn(0.3) == 4 and ce.predicted_cn(1.2) == 12


def test_packing_and_the_comparison():
    p = ce.packing(cscl())
    assert p.ionic == pytest.approx(4 / 3 * 3.14159265 * (1.74 ** 3 + 1.81 ** 3) / 4.12 ** 3, rel=1e-6)
    rows = {name: (x, y, d) for name, x, y, d, _ in ce.compare(cscl(4.12), cscl(4.1418))}
    assert rows['a'][2] == pytest.approx(100 * (4.1418 / 4.12 - 1))
    assert rows['α'][2] == 0
    # a supercell: only the volume and the density per formula unit
    big = cubic(8.24, [(s, ((x + i) / 2, (y + j) / 2, (z + k) / 2)) for s, (x, y, z) in
                       (('Cs', (0, 0, 0)), ('Cl', (.5, .5, .5))) for i in (0, 1) for j in (0, 1) for k in (0, 1)])
    rows = {name: d for name, _, _, d, _ in ce.compare(cscl(4.12), big)}
    assert 'a' not in rows and rows['V на формульную единицу'] == pytest.approx(0, abs=1e-9)


def test_site_symmetry_and_labels():
    nacl_cif = cr.parse_cif((EXAMPLES / 'NaCl_rock_salt.cif').read_text(encoding='utf-8'))
    assert ce.site_symmetry(nacl_cif) == {'Na1': (4, 'm-3m'), 'Cl1': (4, 'm-3m')}
    model = cr.build(nacl_cif, (1, 1, 1), True)
    points = [(a.symbol, a.position) for a in model.atoms]
    assert set(ce.model_labels(nacl_cif, points, 'oxidation')) == {'+1', '−1'}
    assert set(ce.model_labels(nacl_cif, points, 'bvs')) == {0.98}
    a = nacl_cif.cell.a  # an atom of the far face is labelled by its own fractions; a point that is no atom — None
    assert ce.model_labels(nacl_cif, [('Na', (0, 0, 0)), ('Na', (a, 0, 0)), ('Na', (1.0, 1.0, 1.0)), ('Cl', (0, 0, 0))],
                           'fractional') == ['0 0 0', '1 0 0', None, None]
    assert ce.model_labels(nacl_cif, [('Cl', (2.82, 0, 0))], 'site') == ['Cl1 · 4 · m-3m']


def test_what_the_ionic_model_does_not_take_is_said_before_a_click():
    # the menus grey out by ionic_problem
    assert ce.ionic_problem(caf2()) is None
    benzoic = cr.parse_cif((EXAMPLES / 'benzoic_acid.cif').read_text(encoding='utf-8'))
    assert 'органические' in ce.ionic_problem(benzoic)
    assert 'Простое вещество' in ce.ionic_problem(cr.parse_cif((EXAMPLES / 'graphite_P1.cif').read_text(encoding='utf-8')))
