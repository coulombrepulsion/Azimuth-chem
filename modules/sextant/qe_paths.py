"""The path through the Brillouin zone for a band structure of Quantum ESPRESSO.

§1 THEORY The bands E_n(k) are drawn along straight segments between the points of high symmetry of the Brillouin zone
    (the letters of Bradley & Cracknell; the paths of Setyawan & Curtarolo, Comput. Mater. Sci. 49 (2010) 299). The
    points are given here in fractions of the reciprocal vectors of the conventional cell of the file (b_i·a_j = 2π
    δ_ij): for the cubic F lattice X = (0, 1, 0), L = (½, ½, ½), W = (½, 1, 0), K = (¾, ¾, 0), U = (¼, 1, ¼); for cubic
    I H = (0, 0, 1), N = (½, ½, 0), P = (½, ½, ½); for the primitive lattices the faces and corners of the reciprocal
    cell. A point k = f·B of the conventional reciprocal basis B has the fractions f' = f·Pᵀ in the reciprocal basis of
    a primitive cell with rows P (in fractions of the conventional cell): k·a'_j = f·B·(P A)ᵀ_j = 2π (f Pᵀ)_j.
§2 ALGORITHM lattice(crystal) — the crystal system (crystal_symmetry.analyse) and the centring: 'cP', 'cF', 'cI', 'hP'
    (γ = 120°; a layer with vacuum along c — Γ–M–K–Γ in its plane only), 'tP', 'tI' (body-centred tetragonal — anatase: the points depend on c/a, body_centred_tetragonal), 'oP'; any other lattice — 'other', the general path Γ–X–Γ–Y–Γ–Z along the reciprocal axes (X = (½,
    0, 0) …), said so. path(crystal, basis=None, step=STEP) -> Path: the points of the segments every ≈ step Å⁻¹ (at
    least 2 per segment), their fractions in the basis of the calculation, the distance x along the path (Å⁻¹, a jump
    «|» adds no distance), the ticks (x, label) and the kind.
§4 SPECIFICATION
    STEP = 0.025 Å⁻¹; LATTICES {kind: (points {label: f}, segments [[labels], …])}; lattice(crystal) -> str;
    Path(kind, fractions [(f1, f2, f3)], x [Å⁻¹], ticks [(x, label)], general: bool, breaks [index]); path(crystal,
    basis, step)
    -> Path; kpoints_card(path) -> text of «K_POINTS crystal».
§7 TESTS
    tests/sextant/test_qe_paths.py — the fcc path of silicon: X and L at |k| = 2π/a · 1 and 2π/a · √3/2; the
    fractions of X in the primitive cell of crystal.primitive.
"""

from dataclasses import dataclass, field

STEP = 0.025  # Å⁻¹ between the points of a segment
G = 'Γ'

LATTICES = {
    'cP': ({G: (0, 0, 0), 'X': (0, 0.5, 0), 'M': (0.5, 0.5, 0), 'R': (0.5, 0.5, 0.5)},
           [[G, 'X', 'M', G, 'R', 'X'], ['M', 'R']]),
    'cF': ({G: (0, 0, 0), 'X': (0, 1, 0), 'W': (0.5, 1, 0), 'K': (0.75, 0.75, 0), 'L': (0.5, 0.5, 0.5),
            'U': (0.25, 1, 0.25)},
           [[G, 'X', 'W', 'K', G, 'L', 'U', 'W', 'L', 'K'], ['U', 'X']]),
    'cI': ({G: (0, 0, 0), 'H': (0, 0, 1), 'N': (0.5, 0.5, 0), 'P': (0.5, 0.5, 0.5)},
           [[G, 'H', 'N', G, 'P', 'H'], ['P', 'N']]),
    'hP': ({G: (0, 0, 0), 'M': (0.5, 0, 0), 'K': (1 / 3, 1 / 3, 0), 'A': (0, 0, 0.5), 'L': (0.5, 0, 0.5),
            'H': (1 / 3, 1 / 3, 0.5)},
           [[G, 'M', 'K', G, 'A', 'L', 'H', 'A'], ['L', 'M'], ['K', 'H']]),
    'tP': ({G: (0, 0, 0), 'X': (0, 0.5, 0), 'M': (0.5, 0.5, 0), 'Z': (0, 0, 0.5), 'R': (0, 0.5, 0.5),
            'A': (0.5, 0.5, 0.5)},
           [[G, 'X', 'M', G, 'Z', 'R', 'A', 'Z'], ['X', 'R'], ['M', 'A']]),
    'oP': ({G: (0, 0, 0), 'X': (0.5, 0, 0), 'Y': (0, 0.5, 0), 'Z': (0, 0, 0.5), 'S': (0.5, 0.5, 0), 'U': (0.5, 0, 0.5),
            'T': (0, 0.5, 0.5), 'R': (0.5, 0.5, 0.5)},
           [[G, 'X', 'S', 'Y', G, 'Z', 'U', 'R', 'T', 'Z'], ['Y', 'T'], ['U', 'X'], ['S', 'R']]),
    'other': ({G: (0, 0, 0), 'X': (0.5, 0, 0), 'Y': (0, 0.5, 0), 'Z': (0, 0, 0.5)},
              [[G, 'X'], [G, 'Y'], [G, 'Z']]),
}


def body_centred_tetragonal(a, c):
    """(points, segments) of the body-centred tetragonal lattice (anatase): the points depend on c/a. Setyawan &
    Curtarolo: BCT₁ for c < a (η = (1 + c²/a²)/4), BCT₂ for c > a (η = (1 + a²/c²)/4, ζ = a²/(2c²)). Their fractions
    (p₁, p₂, p₃) of the primitive reciprocal vectors are written here in those of the conventional cell:
    f = (p₂ + p₃, p₁ + p₃, p₁ + p₂), since the conventional edges are sums of two primitive vectors."""
    if c < a:
        eta = (1 + c * c / (a * a)) / 4
        points = {G: (0, 0, 0), 'M': (1, 0, 0), 'N': (0.5, 0, 0.5), 'P': (0.5, 0.5, 0.5), 'X': (0.5, 0.5, 0),
                  'Z': (0, 0, 2 * eta), 'Z₁': (1, 0, 1 - 2 * eta)}
        return points, [[G, 'X', 'M', G, 'Z', 'P', 'N', 'Z₁', 'M'], ['X', 'P']]
    eta, zeta = (1 + a * a / (c * c)) / 4, a * a / (2 * c * c)
    points = {G: (0, 0, 0), 'N': (0.5, 0, 0.5), 'P': (0.5, 0.5, 0.5), 'X': (0.5, 0.5, 0), 'Z': (0, 0, 1),
              'Σ': (2 * eta, 0, 0), 'Σ₁': (1 - 2 * eta, 0, 1), 'Y': (0.5 + zeta, 0.5 - zeta, 0),
              'Y₁': (0.5 - zeta, 0.5 - zeta, 1)}
    return points, [[G, 'X', 'Y', 'Σ', G, 'Z', 'Σ₁', 'N', 'P', 'Y₁', 'Z'], ['X', 'P']]


@dataclass
class Path:
    kind: str
    fractions: list = field(default_factory=list)
    x: list = field(default_factory=list)
    ticks: list = field(default_factory=list)
    general: bool = False
    breaks: list = field(default_factory=list)  # the indices of the points that start a new run (after «|»)


def lattice(crystal):
    from modules.compass.chemistry import crystal_symmetry as cs

    s = cs.analyse(crystal)
    system = {v: k for k, v in cs.SYSTEMS.items()}.get(s.system, '')
    centring = s.centring
    c = crystal.cell
    if system == 'cubic' and centring in ('P', 'F', 'I'):
        return 'c' + centring
    if system in ('hexagonal', 'trigonal') and centring == 'P' and abs(c.gamma - 120) < 0.5:
        return 'hP'
    if system == 'tetragonal' and centring == 'P':
        return 'tP'
    if system == 'tetragonal' and centring == 'I':
        return 'tI'
    if system == 'orthorhombic' and centring == 'P':
        return 'oP'
    # a cell written without its symmetry (group P 1: a monolayer cut out of a crystal, a slab, a supercell) with the
    # metric of a hexagonal lattice — the path of that lattice: its points are those of the reciprocal cell
    if centring == 'P' and abs(c.gamma - 120) < 0.01 and abs(c.alpha - 90) < 0.01 and abs(c.beta - 90) < 0.01 \
            and abs(c.a - c.b) < 1e-4 * c.a:
        return 'hP'
    return 'other'


def path(crystal, basis=None, step=STEP):
    import numpy as np

    kind = lattice(crystal)
    points, segments = body_centred_tetragonal(crystal.cell.a, crystal.cell.c) if kind == 'tI' else LATTICES[kind]
    if kind == 'hP':  # a layer with vacuum along c (graphene): the path in its plane only
        from modules.compass.chemistry import layer

        if layer.vacuum_axis(crystal) == 2:
            segments = [[G, 'M', 'K', G]]
    reciprocal = 2 * np.pi * np.linalg.inv(np.array(crystal.cell.vectors(), dtype=float)).T  # rows b_i, Å⁻¹
    to_calc = np.eye(3) if basis is None else np.array(basis, dtype=float).T  # f' = f Pᵀ
    result = Path(kind, general=kind == 'other')
    x = 0.0
    for run in segments:
        for n, (start, end) in enumerate(zip(run, run[1:])):
            a, b = np.array(points[start], dtype=float), np.array(points[end], dtype=float)
            length = float(np.linalg.norm((b - a) @ reciprocal))
            count = max(2, int(round(length / step)) + 1)
            first = 0 if n == 0 else 1  # the start of a segment is the end of the one before
            if n == 0:
                if result.fractions:
                    result.breaks.append(len(result.fractions))
                if result.ticks and abs(result.ticks[-1][0] - x) < 1e-9:  # a jump: «X|M» at one place
                    result.ticks[-1] = (x, result.ticks[-1][1] + '|' + start)
                else:
                    result.ticks.append((x, start))
            for k in range(first, count):
                t = k / (count - 1)
                f = a + (b - a) * t
                result.fractions.append(tuple(float(v) for v in f @ to_calc))
                result.x.append(x + length * t)
            x += length
            result.ticks.append((x, end))
    return result


def kpoints_card(p):
    lines = ['K_POINTS crystal', f'  {len(p.fractions)}']
    lines += [f'  {f[0]:.8f} {f[1]:.8f} {f[2]:.8f} 1' for f in p.fractions]
    return '\n'.join(lines)
