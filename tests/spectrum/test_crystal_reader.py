"""crystal_out: real outputs of CRYSTAL17 and of TOPOND (CRYSTAL14) (tests/data/crystal)."""

from pathlib import Path

import pytest

from modules.compass.chemistry import crystal as cr
from modules.spectrum.readers import crystal_out as co

DATA = Path(__file__).resolve().parents[1] / 'data' / 'crystal'


def text(name):
    return (DATA / name).read_text(encoding='utf-8', errors='replace')


def test_an_optimization_under_pressure():
    # solid chlorine at 10 GPa: PBE0 with 8 % of Fock exchange, the atoms and the cell optimized in 23 points
    t = text('chlorine-10gpa.out')
    assert co.is_crystal(t) and not co.is_topond(t)
    r = co.read(t)
    assert r.version.startswith('CRYSTAL17') and r.space_group == 'C M C A' and r.title == 'Chlorine 100K'
    assert r.method.endswith('8 % HF') and r.optimization and r.converged and r.steps == 23 and r.done and not r.error
    assert r.energy == pytest.approx(-1839.604325688)
    assert r.external == pytest.approx(10.0, abs=1e-3)  # EXTPRESS: 0.3398930E-03 hartree/bohr³
    assert r.gap == pytest.approx(3.3340) and r.gap_kind == 'indirect'
    assert r.cell[:3] == pytest.approx((3.33171581, 3.33171581, 7.71268037)) and len(r.atoms) == 4
    assert r.conventional[:3] == pytest.approx((5.5575732, 3.67623464, 7.71268037)) and len(r.unique) == 1
    steps = co.steps(t)
    assert len(steps) == 23 and steps[0][0] == pytest.approx(-1839.8111136486) and all(len(s[2]) == 4 for s in steps)
    assert steps[1][0] == pytest.approx(-1839.5521678598)


def test_the_last_structure_in_its_cell_and_group():
    # «C M C A» of CRYSTAL is C m c e (№ 64) since 2002: the conventional cell holds twice the atoms of the primitive
    r = co.read(text('chlorine-10gpa.out'))
    crystal = co.final_crystal(r, 'Cl2')
    assert crystal.number == 64 and crystal.space_group.replace(' ', '') == 'Cmce'
    assert len(cr.unit_cell(crystal)) == 2 * len(r.atoms)
    assert crystal.cell.volume() == pytest.approx(2 * r.volume, rel=1e-5)
    p1 = co.final_crystal(co.Result(cell=r.cell, atoms=r.atoms))  # without the crystallographic cell: P 1
    assert p1.space_group == 'P 1' and len(p1.sites) == 4


def test_the_elastic_constants():
    t = text('rubsud-elastic.out')
    r = co.read(t)
    assert r.method == 'PBE0' and r.pressure == pytest.approx(20.0) and r.gap_kind == 'direct'
    c = r.elastic
    assert len(c) == 6 and c[0][0] == pytest.approx(149.493) and all(c[i][j] == c[j][i] for i in range(6) for j in range(6))
    assert r.moduli['K_H'] == pytest.approx(107.27) and r.moduli['v_H'] == pytest.approx(0.319)
    assert co.steps(t) == []  # the strained cells are no steps of an optimization


def test_the_critical_points_of_topond():
    t = text('brbenz-topond.outp')
    assert co.is_topond(t) and not co.is_crystal(t)
    points = co.topond(t)
    assert len(points) == 10 and [p.kind for p in points[:6]] == ['(3,-3)'] * 6
    bond = points[7]  # CP 8: the C–Br bond
    assert bond.kind == '(3,-1)' and bond.rho == pytest.approx(0.1635) and bond.laplacian == pytest.approx(-0.15286)
    assert bond.h == pytest.approx(0.062582 - 0.16338) and bond.ratio == pytest.approx(0.16338 / 0.062582)
    assert [s for _, s, _ in bond.neighbours[:2]] == ['C', 'Br'] and bond.fractions == pytest.approx((0.25786, -0.17816,
                                                                                                        0.047196))
    weak = points[6]  # CP 7: a Br…Br contact, closed shells
    assert weak.laplacian > 0 and weak.h > 0 and weak.ratio < 1 and weak.neighbours[0][1] == 'Br'


def test_an_output_whose_banner_comes_late():
    # the script of the queue and the echo of the input with its basis
    # sets come before the banner — 55 000 characters; the file was taken for ORCA
    text = (DATA / 'chlorine-10gpa.out').read_text(errors='replace')
    late = 'date Mon Mar 14 19:14:20 YEKT 2022\nPcrystal executable in /share/simulation/Crystal17/\n' + \
        '  1238.40169380    0.0054568832082\n' * 2000 + text
    assert co.is_crystal(late) and not co.is_topond(late)


def test_a_primitive_group_keeps_its_space_group():
    # P C A B prints
    # no «CRYSTALLOGRAPHIC CELL» — the asymmetric unit of the last geometry with the operations of Pcab (№ 61) gives
    # back its 72 atoms (it was P 1 with the 72 atoms)
    result = co.read((DATA / 'caform-final.out').read_text())
    crystal = co.final_crystal(result, 'CAFORM')
    assert crystal.number == 61 and len(crystal.sites) == 9 and len(cr.unit_cell(crystal)) == 72
    assert result.space_group == 'P C A B' and len(result.atoms) == 72


def test_the_basis_set_of_an_output():
    # a basis of the library — the name after BASISSET of the input
    # echoed before the banner; one written by hand has only its size in the output, its name may be in the file name
    banner = (DATA / 'chlorine-10gpa.out').read_text(errors='replace')
    named = 'HF3c run\nCRYSTAL\nEND\nBASISSET\nMINIX\nHF3C\nEND\n' + banner
    assert co.read(named).method == 'HF-3c' and co.read(named).basis == 'MINIX' and co.read(banner).basis == '' and co.read(banner).basis_ao == 72
    assert co.basis_from_name('CAFORM_DZVP2-PBE0_3.5GPa.out') == 'DZVP2'
    assert co.basis_from_name('CAFORM05_PBE0_pob-DZVP2_6GPa.out') == 'pob-DZVP2'
    assert co.basis_from_name('chlorine-10gpa.out') == ''
