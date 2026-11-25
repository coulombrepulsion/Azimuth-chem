"""The density of states of a molecule — total, by fragments (PDOS) and the overlap population between two (OPDOS)
.

§1 THEORY
    The molecular orbitals ψ_i = Σ_μ c_μi χ_μ with energies ε_i are lines; broadened by a Gaussian (or Lorentzian) of
    full width at half maximum w they give the density of states DOS(E) = Σ_i g(E − ε_i). A fragment A (atoms) takes
    of every orbital its Mulliken share p_iA = Σ_{μ∈A} c_μi (S c_i)_μ (Σ_A p_iA = 1; a basis without overlap — the
    ZDO of MOPAC — c_μi²), so PDOS_A(E) = Σ_i p_iA g(E − ε_i) and the PDOS of all the fragments add up to the DOS. The
    overlap population of A and B in ψ_i, OP_iAB = 2 Σ_{μ∈A, ν∈B} c_μi c_νi S_μν, is positive for a bonding orbital
    and negative for an antibonding one: OPDOS_AB(E) = Σ_i OP_iAB g(E − ε_i) (Hoffmann's COOP). The curves are as in
    Multiwfn's «Plot density-of-states» with the Mulliken partition (Lu, Chen, J. Comput. Chem. 33, 580 (2012));
    the Gaussian is normalized (its area is 1 state), so the area of the DOS over a window is the number of
    orbitals in it.
§2 ALGORITHM
    The overlap matrix of the basis (modules/spectrum/analysis/orbitals.overlap), the shares of the atoms by the owners
    of the basis functions, the curves on an even grid of the energy (eV) over the window. An unrestricted wavefunction:
    α and β separately (spin='alpha' | 'beta').
§3 APPLICATIONS
    modules/spectrum/views/dos_view.py — the tab «Плотность состояний» of Spectrum.
§4 SPECIFICATION
    HARTREE_EV; atom_shares(orbital_set) -> (n_orbitals, n_atoms) Mulliken shares;
    overlap_population(orbital_set, a, b) -> (n_orbitals); by_element(molecule) -> [(name, atoms)];
    broaden(energies, weights, x, fwhm, shape='gauss' | 'lorentz') -> y;
    curves(orbital_set, fragments, fwhm=0.3, shape='gauss', window=None, points=1500, spin='alpha', pair=None) ->
    {'x', 'total', 'parts': [(name, y)], 'opdos': y | None, 'levels': [(eV, occupation)], 'homo', 'lumo'}.
§7 TESTS tests/spectrum/test_dos.py.
"""

import numpy as np

HARTREE_EV = 27.211386245988  # CODATA 2018


def _owners(orbital_set):
    return np.concatenate([[s.centre] * s.size for s in orbital_set.shells]).astype(int)


def atom_shares(orbital_set):
    """(n_orbitals, n_atoms): the Mulliken share of every atom in every orbital (each row adds up to 1)."""
    c = np.asarray(orbital_set.coefficients, dtype=float)
    if orbital_set.zdo:
        per_function = c * c
    else:
        per_function = c * (orbital_set.overlap() @ c)
    owners = _owners(orbital_set)
    count = len(orbital_set.molecule.atoms)
    shares = np.zeros((c.shape[1], count))
    for atom in range(count):
        shares[:, atom] = per_function[owners == atom].sum(axis=0)
    return shares


def overlap_population(orbital_set, a, b):
    """(n_orbitals,): 2 Σ_{μ∈A, ν∈B} c_μ c_ν S_μν — positive bonding, negative antibonding between the fragments."""
    c = np.asarray(orbital_set.coefficients, dtype=float)
    owners = _owners(orbital_set)
    in_a, in_b = np.isin(owners, list(a)), np.isin(owners, list(b))
    if orbital_set.zdo:
        return np.zeros(c.shape[1])
    s = orbital_set.overlap()[np.ix_(in_a, in_b)]
    return 2.0 * np.einsum('mi,mn,ni->i', c[in_a], s, c[in_b])


def by_element(molecule):
    """The fragments by element, the heaviest first (a metal of a complex leads): [(symbol, (atoms…))]."""
    from azimuth.core import Z

    groups = {}
    for k, a in enumerate(molecule.atoms):
        groups.setdefault(a.symbol, []).append(k)
    return [(symbol, tuple(atoms)) for symbol, atoms in sorted(groups.items(), key=lambda item: -Z.get(item[0], 0))]


def broaden(energies, weights, x, fwhm, shape='gauss'):
    energies = np.asarray(energies, dtype=float)[:, None]
    weights = np.asarray(weights, dtype=float)[:, None]
    d = np.asarray(x, dtype=float)[None, :] - energies
    if shape == 'lorentz':
        gamma = fwhm / 2.0
        g = gamma / np.pi / (d * d + gamma * gamma)
    else:
        sigma = fwhm / (2.0 * np.sqrt(2.0 * np.log(2.0)))
        g = np.exp(-0.5 * (d / sigma) ** 2) / (sigma * np.sqrt(2.0 * np.pi))
    return (weights * g).sum(axis=0)


def curves(orbital_set, fragments, fwhm=0.3, shape='gauss', window=None, points=1500, spin='alpha', pair=None):
    """The DOS, the PDOS of the fragments and (pair = (a, b) of fragment indices) the OPDOS of an orbital set, eV."""
    rows = [k for k, o in enumerate(orbital_set.orbitals) if (o.spin or 'alpha') == spin]
    if not rows:
        raise ValueError('no orbitals of this spin')
    energies = np.array([orbital_set.orbitals[k].energy for k in rows]) * HARTREE_EV
    occupations = np.array([orbital_set.orbitals[k].occupation for k in rows])
    occupied = energies[occupations > 1e-6]
    empty = energies[occupations <= 1e-6]
    homo = float(occupied.max()) if occupied.size else None
    lumo = float(empty.min()) if empty.size else None
    if window is None:
        low = (homo if homo is not None else energies.min()) - 15.0
        high = (lumo if lumo is not None else energies.max()) + 8.0
        window = (max(low, energies.min() - 2 * fwhm), min(high, energies.max() + 2 * fwhm))
    x = np.linspace(window[0], window[1], points)
    shares = atom_shares(orbital_set)[rows]
    parts = []
    for name, atoms in fragments:
        parts.append((name, broaden(energies, shares[:, list(atoms)].sum(axis=1), x, fwhm, shape)))
    opdos = None
    if pair is not None:
        a, b = fragments[pair[0]][1], fragments[pair[1]][1]
        opdos = broaden(energies, overlap_population(orbital_set, a, b)[rows], x, fwhm, shape)
    return {'x': x, 'total': broaden(energies, np.ones(len(rows)), x, fwhm, shape), 'parts': parts, 'opdos': opdos,
            'levels': [(float(e), float(n)) for e, n in zip(energies, occupations)], 'homo': homo, 'lumo': lumo}
