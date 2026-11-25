"""The Hirshfeld surface and the fingerprint plot (modules/compass/chemistry/crystal_hirshfeld.py).

Oracles, independent of the tested code:
  * the free-atom density integrates to the number of electrons Z, and its Fourier transform
    f(s) = ∫ ρ(r) sin(4πsr)/(4πsr) 4πr² dr (numerical) is the scattering factor of Waasmaier & Kirfel written out here
    from their formula c + Σ a exp(−b s²), within 0.02 electron up to s = 1 Å⁻¹ (only the core is replaced — §1);
  * marching tetrahedra on the field |r|: the sphere of radius R has the area 4πR²;
  * argon in a primitive cubic cell a = 3.8 Å: between two equal atoms the surface is the plane halfway — the closest
    point is the middle of a face, d_i = d_e = a/2, so min(d_i + d_e) = a and min d_norm = 2 (a/2 − 1.88)/1.88
    (Bondi radius of Ar 1.88 Å); on the surface ρ_A equals the sum of the others, so no other atom is nearer than A
    (d_e ≥ d_i); the surface lies inside the cell of the atom (volume < a³);
  * benzoic acid (the example, P 2₁/n, Z = 4): the surfaces of a crystal nearly fill it (Spackman & Jayatilaka 2009:
    above 95 %) — V between 93 and 100 % of V_cell/Z; the red spots (d_norm < −0.3) only at the O–H···O bonds, and
    the shortest d_i + d_e of O/H is the H···O distance that the contacts module finds (H at neutron distances in both).
"""

from math import pi
from pathlib import Path

import numpy as np
import pytest

from modules.compass.chemistry import crystal as cr
from modules.compass.chemistry import crystal_contacts as cc
from modules.compass.chemistry import crystal_hirshfeld as hs
from modules.compass.chemistry import crystal_hydrogens, powder


def argon(a):
    return cr.Crystal('Ar', cr.Cell(a, a, a), (cr.Site('Ar1', 'Ar', 0.0, 0.0, 0.0),), (cr.operation('x, y, z'),),
                      'P 1', (), 1, 'Ar', 1)


def benzoic():
    path = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals' / 'benzoic_acid.cif'
    return cr.parse_cif(path.read_text(encoding='utf-8'))


def test_the_density_of_a_free_atom():
    r = np.linspace(0, 14, 140001)
    table = powder._f0()
    for symbol in ('H', 'C', 'N', 'O', 'S', 'Cl', 'Fe', 'Ar'):
        rho = hs.density(symbol, r)
        assert np.all(rho > 0)
        z, c, a, b = table[symbol]
        assert abs(np.trapezoid(4 * pi * r * r * rho, r) - z) < 1e-6
        for s in (0.1, 0.3, 0.6, 1.0):
            q = 4 * pi * s
            ours = np.trapezoid(4 * pi * r * r * rho * np.sinc(q * r / pi), r)
            want = c + sum(ak * np.exp(-bk * s * s) for ak, bk in zip(a, b))
            assert abs(ours - want) < 0.02, (symbol, s, ours, want)


def test_marching_tetrahedra_on_a_sphere():
    step, radius = 0.1, 2.0
    axis = np.arange(-3, 3 + step / 2, step)
    x, y, z = np.meshgrid(axis, axis, axis, indexing='ij')
    field = -np.sqrt(x * x + y * y + z * z)  # inside above the level
    tris = hs.triangles(field, -radius, (-3, -3, -3), step)
    area = 0.5 * np.linalg.norm(np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]), axis=1).sum()
    assert abs(area / (4 * pi * radius ** 2) - 1) < 0.01
    assert np.allclose(np.linalg.norm(tris.reshape(-1, 3), axis=1), radius, atol=0.01)


def test_argon_in_a_cubic_cell():
    a = 3.8
    s = hs.surface(argon(a), step=0.1)
    assert abs((s.d_i + s.d_e).min() - a) < 0.01
    assert abs(s.d_norm.min() - 2 * (a / 2 - 1.88) / 1.88) < 0.01
    assert np.all(s.d_e >= s.d_i - 0.01)  # ρ_A = Σ ρ_others ≥ ρ of the nearest other: it is not nearer than A
    assert 0.85 * a ** 3 < s.volume < a ** 3 and list(s.fractions()) == ['Ar···Ar']
    assert abs(s.fingerprint(0.4, 3.4).sum() - s.total_area) < 1e-6 * s.total_area  # every point within 0.4–3.4 Å


def test_benzoic_acid():
    data = benzoic()
    s = hs.surface(data)
    per_molecule = data.cell.volume() / 4
    assert 0.93 * per_molecule < s.volume < per_molecule
    shares = s.fractions()
    assert abs(sum(shares.values()) - 1) < 1e-9 and next(iter(shares)) == 'H···H'
    assert {(a, b) for a, b in zip(s.inside[s.d_norm < -0.3], s.outside[s.d_norm < -0.3])} == {('O', 'H'), ('H', 'O')}
    normal, _ = crystal_hydrogens.normalized(data)
    bond = min(c.distance for c in cc.contacts(normal) if c.kind == 'hydrogen')
    pairs = ((s.inside == 'O') & (s.outside == 'H')) | ((s.inside == 'H') & (s.outside == 'O'))
    shortest = (s.d_i[pairs] + s.d_e[pairs]).min()
    assert bond - 1e-6 <= shortest < bond + 0.05
    spike = s.fingerprint(pair=('O', 'H'))
    assert spike.sum() == pytest.approx(s.area[(s.inside == 'O') & (s.outside == 'H')].sum())
    assert 0.7 < s.globularity < 1


def test_a_molecule_alone_has_no_surface():
    with pytest.raises(ValueError):
        hs.surface(argon(20.0))


def test_the_curvatures_of_level_surfaces():
    # 0.175.0 — Koenderink & van Doorn 1992: a sphere of radius R seen from outside S = +1 (a cap), from inside −1 (a
    # cup), C = (2/π) ln(1/R); a saddle κ = ±1 — S = 0, C = 0; a cylinder (κ = 1/R, 0) — S = ½ (a ridge). The
    # gradient and the Hessian written out here: f = |r| at (R, 0, 0): g = (1, 0, 0), H = (I − ggᵀ)/R; f = z − (x² −
    # y²)/2 at 0: g = (0, 0, 1), H = diag(−1, 1, 0); f = √(x² + y²) at (R, 0, 0): H = diag(0, 1/R, 0)
    radius = 2.0
    g = np.array([[1.0, 0, 0]])
    sphere = (np.eye(3) - np.outer(g[0], g[0]))[None] / radius
    s, c = hs.shape_curvedness(*hs.level_curvatures(g, sphere))
    assert s[0] == pytest.approx(1.0) and c[0] == pytest.approx(2 / pi * np.log(1 / radius))
    assert hs.shape_curvedness(*hs.level_curvatures(-g, -sphere))[0][0] == pytest.approx(-1.0)
    s, c = hs.shape_curvedness(*hs.level_curvatures(np.array([[0, 0, 1.0]]), np.diag([-1.0, 1, 0])[None]))
    assert s[0] == pytest.approx(0.0, abs=1e-12) and c[0] == pytest.approx(0.0, abs=1e-12)
    s, _ = hs.shape_curvedness(*hs.level_curvatures(g, np.diag([0, 1 / radius, 0])[None]))
    assert s[0] == pytest.approx(0.5)


def test_the_derivatives_of_the_weight_against_finite_differences():
    # the analytic gradient and Hessian of w against central differences of w and of the gradient (h = 1e-4 Å)
    inner = [('C', 0.0, 0.0, 0.0), ('O', 1.2, 0.0, 0.0)]
    outer = [('H', -1.5, 1.2, 0.3), ('N', 2.9, 0.5, -0.4), ('C', 0.4, -2.8, 0.2)]
    point, h = np.array([[0.3, 0.9, 0.5]]), 1e-4
    _, gradient, hessian = hs.weight_derivatives(point, inner, outer)
    for k in range(3):
        step = h * np.eye(3)[k]
        plus, minus = hs.weight_derivatives(point + step, inner, outer), hs.weight_derivatives(point - step, inner, outer)
        assert (plus[0] - minus[0])[0] / (2 * h) == pytest.approx(gradient[0, k], abs=1e-7)
        assert np.allclose((plus[1] - minus[1])[0] / (2 * h), hessian[0, k], atol=1e-6)


def test_flat_faces_and_convex_corners():
    # argon, primitive cubic a = 3.8 Å: the surface is nearly the cube of the cell of the atom — flat at the middles
    # of the faces (C far below −1), convex at the corners (S > ½); benzene stacked face to face along c (3.6 Å): the
    # surface over the ring, facing the next ring, is flat too
    from tests.compass.test_crystal_rings import benzene_crystal

    s = hs.surface(argon(3.8), step=0.2)
    shape, curved = s.shape_index(), s.curvedness()
    u = s.triangles.mean(1) - np.array(s.atoms[0][1:])
    u /= np.linalg.norm(u, axis=1)[:, None]
    face = np.abs(u).max(1) > 0.98
    corner = np.all(np.abs(np.abs(u) - 1 / np.sqrt(3)) < 0.05, axis=1)
    assert face.any() and corner.any()
    assert curved[face].max() < -3 and shape[corner].min() > 0.5 and curved[corner].mean() > curved[face].mean() + 3
    b = hs.surface(benzene_crystal(), step=0.2)
    centre = np.array([a[1:] for a in b.atoms]).mean(0)
    c = b.triangles.mean(1) - centre
    over = (np.abs(c[:, 2]) > 1.3) & (np.linalg.norm(c[:, :2], axis=1) < 1.0)
    assert over.any() and b.curvedness()[over].mean() < -3
    grid = hs.property_grid(b, 'shape_index')
    assert grid.shape == b.weight.shape and -1 <= grid.min() and grid.max() <= 1
