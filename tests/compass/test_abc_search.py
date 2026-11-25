"""The bee colony conformer search (modules/compass/chemistry/abc_search.py) with a model energy instead of xtb.

Oracles: scipy.stats.exponnorm.cdf at chosen points (computed with SciPy 1.18.1 and written here); the
Boltzmann shares by hand; butane with the energy E(φ) = 0.0015 (1 + cos φ) hartree of its C–C–C–C dihedral: anti
(φ = 180°) is the lowest, the two gauche (±60° after a full optimization) are the next.
"""

import pytest

from modules.compass.chemistry import abc_search, library, torsion


def test_exponnorm_cdf_and_shares():
    # scipy.stats.exponnorm.cdf([0, 0.5, 1, 3], K=1, loc=0.5, scale=2)
    expected = [0.177633, 0.238422, 0.307711, 0.611541]
    got = [abc_search.exponnorm_cdf(x, 1.0, 0.5, 2.0) for x in (0.0, 0.5, 1.0, 3.0)]
    assert got == pytest.approx(expected, abs=1e-6)
    assert abc_search.exponnorm_cdf(-1e6, 1.0, 0.0, 1.0) == 0.0
    shares = abc_search.probabilities([-1.0, -1.0 + 1 / 2625.4996394799], 298.15)  # 1 kJ/mol apart
    assert shares[0] / shares[1] == pytest.approx(2.718281828 ** (1 / (0.0083144626 * 298.15)), rel=1e-6)


def butane():
    m = library.molecule(next(k for k in library.keys() if k.startswith('Бутан')))
    return m, (0, 1, 2, 3)


def run(gen, energy, relax):
    """Answer the search as xtb would: a short optimization (cycles > 0) keeps the structure, a full one (0) moves
    the dihedral to the nearest minimum (relax)."""
    request = next(gen)
    count = 0
    try:
        while True:
            molecule, cycles = request
            count += 1
            final = molecule if cycles else relax(molecule)
            request = gen.send((energy(final), final))
    except StopIteration as stop:
        return stop.value, count


def test_butane_anti_then_gauche():
    start, chain = butane()

    def phi(m):
        return torsion.dihedral(m, *chain)

    def energy(m):
        from math import cos, radians

        return -15.0 + 0.0015 * (1 + cos(radians(phi(m))))

    def relax(m):
        target = min((180.0, 60.0, -60.0), key=lambda t: abs((phi(m) - t + 180) % 360 - 180))
        return torsion.set_dihedral(m, *chain, chain[2], target)

    ensemble, count = run(abc_search.search(start, n_confs=3, global_iterations=4, local_iterations=3, seed=7),
                          energy, relax)
    angles = [phi(m) for m, _ in ensemble]
    assert abs(abs(angles[0]) - 180) < 1e-6 and ensemble[0][1] == pytest.approx(-15.0, abs=1e-9)  # anti first
    assert len(ensemble) >= 2 and all(abs(abs(a) - 60) < 1e-6 for a in angles[1:])  # then gauche
    assert [e for _, e in ensemble] == sorted(e for _, e in ensemble) and 10 < count < 400


def test_no_rotors_and_failed_calculations():
    from azimuth.core import read_xyz

    with pytest.raises(ValueError):
        next(abc_search.search(read_xyz('3\nw\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0')))
    start, _ = butane()
    gen = abc_search.search(start, n_confs=2, global_iterations=1, local_iterations=1, seed=1)
    with pytest.raises(ValueError):  # xtb fails for everything: no food at all
        next(gen)
        while True:
            gen.send(None)


def test_broken_bond_is_named():
    """When xtb breaks a bond of every structure, the message names it and the charge."""
    import pytest

    from modules.compass.chemistry import abc_search
    from azimuth.core import Atom, Molecule

    start, _ = butane()
    search = abc_search.search(start, seed=1)
    request = next(search)
    with pytest.raises(ValueError) as caught:
        while True:
            molecule, _ = request
            atoms = list(molecule.atoms)
            far = Atom(atoms[0].symbol, atoms[0].x + 3.0, atoms[0].y, atoms[0].z)  # the first atom flies off
            request = search.send((-10.0, Molecule(molecule.title, (far, *atoms[1:]))))
    assert 'заряд' in str(caught.value) and '–' in str(caught.value)
    assert 'Atom' not in str(caught.value)


def test_energy_window_decides_which_conformers_stay():
    # the window of CREGEN instead of the 5 % share of the original: the model gauche lies 0.00225 hartree
    # = 1.41 kcal/mol above anti — inside 6 kcal/mol, outside 1 kcal/mol
    start, chain = butane()

    def phi(m):
        return torsion.dihedral(m, *chain)

    def energy(m):
        from math import cos, radians

        return -15.0 + 0.0015 * (1 + cos(radians(phi(m))))

    def relax(m):
        target = min((180.0, 60.0, -60.0), key=lambda t: abs((phi(m) - t + 180) % 360 - 180))
        return torsion.set_dihedral(m, *chain, chain[2], target)

    for ewin in (6.0, 1.0):
        ensemble, _ = run(abc_search.search(start, n_confs=3, global_iterations=4, local_iterations=3, seed=7, ewin=ewin),
                          energy, relax)
        assert len(ensemble) >= 2 if ewin == 6.0 else len(ensemble) == 1
        assert all((e - ensemble[0][1]) * 627.5094740631 <= ewin for _, e in ensemble)
    with pytest.raises(ValueError):
        next(abc_search.search(start, ewin=0.0))


def test_progress_says_where_the_search_is():
    # the stage and the number of the local search for the status of the window; local_max = 2 n − 2 is a bound
    start, chain = butane()

    def phi(m):
        return torsion.dihedral(m, *chain)

    def energy(m):
        from math import cos, radians

        return -15.0 + 0.0015 * (1 + cos(radians(phi(m))))

    def relax(m):
        target = min((180.0, 60.0, -60.0), key=lambda t: abs((phi(m) - t + 180) % 360 - 180))
        return torsion.set_dihedral(m, *chain, chain[2], target)

    for n in (2, 4):
        progress, seen = {}, []
        gen = abc_search.search(start, n_confs=n, global_iterations=3, local_iterations=2, seed=3, progress=progress)
        request = next(gen)
        try:
            while True:
                seen.append(dict(progress))
                molecule, cycles = request
                final = molecule if cycles else relax(molecule)
                request = gen.send((energy(final), final))
        except StopIteration:
            pass
        assert seen[0]['stage'] == 'global' and seen[0]['local'] == 0 and seen[0]['local_max'] == 2 * n - 2
        locals_ = [s['local'] for s in seen if s['stage'] == 'local']
        assert locals_ == sorted(locals_) and max(locals_, default=0) <= 2 * n - 2
        # the first conformer comes from the global search: before the k-th local search taken + rejected = k
    assert all(s['taken'] + s['rejected'] == s['local'] for s in seen if s['stage'] == 'local')
