"""The rough estimate of the time of a calculation (modules/sextant/estimate.py)."""

from dataclasses import replace

from modules.sextant import estimate
from azimuth.core import Atom, Calculation, Molecule


def benzene():
    atoms = []
    from math import cos, sin, pi

    for k in range(6):
        a = 2 * pi * k / 6
        atoms.append(Atom('C', 1.39 * cos(a), 1.39 * sin(a), 0))
        atoms.append(Atom('H', 2.47 * cos(a), 2.47 * sin(a), 0))
    return Molecule('benzene', tuple(atoms))


def test_basis_functions_of_benzene():
    mol = benzene()
    assert estimate.basis_functions(mol, 'def2-SVP') == 114
    assert estimate.basis_functions(mol, 'aug-cc-pVDZ') > estimate.basis_functions(mol, 'cc-pVDZ')
    assert estimate.basis_functions(mol, 'some-TZ') == estimate.basis_functions(mol, 'def2-TZVP')


def test_estimate_grows_with_method_task_and_basis():
    mol = benzene()
    calc = Calculation(method='B3LYP', basis='def2-SVP', task='Энергия', cores=1)
    single = estimate.seconds(mol, calc)
    assert 5 < single < 50  # calibrated: ~15 s
    assert estimate.seconds(mol, replace(calc, task='Оптимизация + частоты')) > 10 * single
    assert estimate.seconds(mol, replace(calc, basis='def2-TZVP')) > 3 * single  # N^2.3 (RIJCOSX)
    assert estimate.seconds(mol, replace(calc, method='CCSD(T)')) > 100 * single
    # several processes pay mpirun at every module — a small energy is no faster on 8
    # cores, a long job is
    assert estimate.seconds(mol, replace(calc, cores=8)) > 0.8 * single
    long = replace(calc, basis='def2-TZVP', task='Оптимизация + частоты')
    assert estimate.seconds(mol, replace(long, cores=8)) < estimate.seconds(mol, long) / 3
    assert estimate.seconds(mol, calc, 'xtb') < 1
    assert estimate.text(0) == '' and estimate.text(5) == 'меньше минуты'
    assert estimate.text(600).startswith('от ')


def test_a_small_molecule_costs_the_start_of_the_program():
    # measured with ORCA 6.0.1 (one core of a Mac) on water B3LYP/def2-SVP: energy 2 s, optimization 6 s,
    # + frequencies 10 s, TD-DFT 2 s, NMR 2 s; the estimate (its middle) within a factor of 2 of each
    water = Molecule('water', (Atom('O', 0, 0, 0.117), Atom('H', 0, 0.757, -0.467), Atom('H', 0, -0.757, -0.467)))
    for task, measured in (('Энергия', 2), ('Оптимизация', 6), ('Оптимизация + частоты', 10),
                           ('Спектр UV-Vis (TD-DFT)', 2), ('ЯМР (экранирование)', 2)):
        guess = estimate.seconds(water, Calculation(task=task, cores=1))
        assert measured / 2 <= guess <= measured * 2, (task, guess)


def test_the_owners_runs_of_orca():
    # runs of ORCA 6 from the
    # owner's projects (TOTAL RUN TIME) — the middle of the estimate within a factor of 2.5 of each
    water = Molecule('water', (Atom('O', 0, 0, 0.117), Atom('H', 0, 0.757, -0.467), Atom('H', 0, -0.757, -0.467)))
    for task, basis, cores, measured in (('Энергия', 'def2-SVPD', 7, 12.0), ('Оптимизация', 'def2-SVP', 7, 42.5),
                                         ('Оптимизация + частоты', 'def2-SVP', 7, 43.9),
                                         ('Энергия', 'def2-TZVP', 7, 13.2)):
        guess = estimate.seconds(water, Calculation(method='B3LYP', basis=basis, task=task, cores=cores))
        assert measured / 2.5 <= guess <= measured * 2.5, (task, basis, guess)
