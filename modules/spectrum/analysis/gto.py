"""Contracted Gaussian basis functions: normalization, overlap and values on a grid.

§1 THEORY
    A shell on the centre R with angular momentum l is a set of functions
        phi(r) = A(x, y, z) * sum_i d_i exp(-alpha_i |r - R|^2), (x, y, z) = r - R,
    A a homogeneous polynomial of degree l: one Cartesian monomial x^a y^b z^c (a + b + c = l) or a
    real solid harmonic S_lm (m = -l..l). Every product of monomials and Gaussians integrates in closed
    form; the one-dimensional overlap of x_A^i exp(-a x_A^2) and x_B^j exp(-b x_B^2) is
        s_ij = exp(-mu X^2) sqrt(pi / p) * sum_{i'<=i, j'<=j, i'+j' even} C(i,i') C(j,j')
               PA^(i-i') PB^(j-j') (i'+j'-1)!! / (2p)^((i'+j')/2),
    p = a + b, mu = a b / p, X = A - B, P = (a A + b B) / p, PA = P - A, PB = P - B, and the 3D overlap
    is the product of the three axes. On one centre with one exponent alpha,
        int x^(a+a') y^(b+b') z^(c+c') exp(-2 alpha r^2) = D(k, k') * (pi / (2 alpha))^(3/2) / (4 alpha)^l
    with D = (a+a'-1)!! (b+b'-1)!! (c+c'-1)!! when all three sums are even, else 0. So a primitive is
    normalized by g(alpha, l) = [(2 alpha / pi)^(3/2) (4 alpha)^l]^(1/2) times an angular vector t with
    t^T D t = 1: the radial and the angular normalization separate.
    Real solid harmonics (Helgaker, Jorgensen, Olsen, Molecular Electronic-Structure Theory, eq. 6.4.48):
        S_lm = N_lm sum_{t=0}^{(l-|m|)/2} sum_{u=0}^{t} sum_v C^lm_tuv x^(2t+|m|-2(u+v)) y^(2(u+v)) z^(l-2t-|m|),
        C^lm_tuv = (-1)^(t+v-v_m) (1/4)^t C(l,t) C(l-t,|m|+t) C(t,u) C(|m|,2v),
    v = v_m, v_m + 1, ..., up to floor(|m|/2 - v_m) + v_m, with v_m = 0 for m >= 0 and 1/2 for m < 0
    (cosine type for m >= 0, sine type for m < 0); the overall factor N_lm is replaced here by the
    normalization t^T D t = 1, which keeps the sign: the leading x^|m| term of S_l,+|m| is positive.
§2 ALGORITHM
    Shell keeps exponents, the contraction coefficients times g(alpha, l) (radial()), and the matrix
    angular (functions x Cartesian monomials) with normalized rows. overlap(shells, centres): monomial
    overlaps from the 1D formula for every pair of primitives, contracted and transformed with the
    angular matrices. on_grid: on an axis-aligned grid exp(-alpha r^2) x^a y^b z^c is a product of three
    vectors, so every primitive adds an outer product, restricted to the sub-box within
    sqrt(-2 ln CUTOFF / alpha) of its centre. overlap() packs all primitives of one angular momentum into
    arrays (overlap_by_pairs, shell pair by shell pair, is the slow cross-check).
§3 APPLICATIONS
    modules/spectrum/analysis/orbitals.py and orbital_files.py (orbitals of Molden, fchk and ORCA files).
§4 SPECIFICATION
    cartesian(l) -> tuple of (a, b, c) in the Molden order (xx, yy, zz, xy, xz, yz for d; see ORDER).
    solid_harmonic(l, m) -> {(a, b, c): coefficient}, unnormalized, by the formula of §1.
    pure_order(l) -> (0, 1, -1, 2, -2, ...): the Molden order of the 2l + 1 functions.
    Shell(centre: int, l: int, pure: bool, exponents, coefficients): coefficients multiply primitives that
        are normalized as functions (each Cartesian monomial on its own, each solid harmonic on its own).
        Shell.size: 2l + 1 or (l + 1)(l + 2)/2. Shell.angular: (size, ncart) array. Shell.radial(): d_i g_i.
        Shell.contraction_norm(): integral of phi^2 for the contraction as given.
    overlap(shells, centres (n, 3) bohr) -> (N, N) overlap matrix of the basis functions in shell order;
    overlap_by_pairs: the same, slowly. values_at(shells, centres, vector, points (m, 3)) -> (m).
    on_grid(shells, centres, vector (N), origin (3) bohr, step (3) bohr, shape (nx, ny, nz)) -> array of
        sum_k vector_k phi_k on the grid points origin + (i, j, k) * step.
    Units: bohr and atomic units throughout; l <= 5.
§5 PROCEDURES - below.
§6 NOTES
    The Molden format (theochem.ru.nl/molden/molden_format.html, read 2026-10-23) fixes the order of the
    Cartesian (6D, 10F, 15G) and spherical functions (D 0, D+1, D-1, D+2, D-2, ...) but not their
    normalization; orbitals.select decides it from the orthonormality of the orbitals.
    CUTOFF = 1e-10, a design choice: beyond sqrt(-2 ln CUTOFF / alpha) a primitive is below CUTOFF times the
    largest value of r^l exp(-alpha r^2 / 2) — far below what an isosurface (0.002..0.05 au) can show.
§7 TESTS
    tests/spectrum/test_orbitals.py: solid harmonics against their explicit forms, unit self-overlap of
    every normalized function, overlaps against Gauss-Hermite quadrature of values from on_grid.
§8' ROBUSTNESS
    l above 5 and empty shells raise ValueError; exponents must be positive and finite.
"""

from math import comb, pi, sqrt

import numpy as np

CUTOFF = 1e-10
MAX_L = 5


def cartesian(l):
    if l < 0 or l > MAX_L:
        raise ValueError(f'angular momentum {l} is not supported')
    if l == 4:  # Molden 15G: xxxx yyyy zzzz xxxy xxxz yyyx yyyz zzzx zzzy xxyy xxzz yyzz xxyz yyxz zzxy
        return (
            (4, 0, 0), (0, 4, 0), (0, 0, 4), (3, 1, 0), (3, 0, 1), (1, 3, 0), (0, 3, 1), (1, 0, 3),
            (0, 1, 3), (2, 2, 0), (2, 0, 2), (0, 2, 2), (2, 1, 1), (1, 2, 1), (1, 1, 2),
        )  # fmt: skip
    order = {
        0: ((0, 0, 0),),
        1: ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
        2: ((2, 0, 0), (0, 2, 0), (0, 0, 2), (1, 1, 0), (1, 0, 1), (0, 1, 1)),
        3: (
            (3, 0, 0), (0, 3, 0), (0, 0, 3), (1, 2, 0), (2, 1, 0), (2, 0, 1), (1, 0, 2), (0, 1, 2),
            (0, 2, 1), (1, 1, 1),
        ),
    }  # fmt: skip
    if l in order:
        return order[l]
    # l = 5: not in the Molden format; only needed as the monomials of pure h functions
    return tuple((a, b, l - a - b) for a in range(l, -1, -1) for b in range(l - a, -1, -1))


def pure_order(l):
    return (0,) + tuple(s * m for m in range(1, l + 1) for s in (1, -1))


def solid_harmonic(l, m):
    terms = {}
    am = abs(m)
    vm = 0.0 if m >= 0 else 0.5
    for t in range((l - am) // 2 + 1):
        for u in range(t + 1):
            v = vm
            while v <= (am / 2 - vm) // 1 + vm + 1e-9:
                two_v = int(round(2 * v))
                if two_v <= am:
                    c = (
                        (-1) ** int(round(t + v - vm))
                        * 0.25**t
                        * comb(l, t)
                        * comb(l - t, am + t)
                        * comb(t, u)
                        * comb(am, two_v)
                    )
                    key = (2 * t + am - 2 * u - two_v, 2 * u + two_v, l - 2 * t - am)
                    if c:
                        terms[key] = terms.get(key, 0.0) + c
                v += 1
    return {k: c for k, c in terms.items() if abs(c) > 1e-14}


def _double_factorial(n):
    return 1 if n <= 0 else n * _double_factorial(n - 2)


def _metric(monomials):
    """D(k, k'): the angular part of the one-centre, one-exponent overlap (see §1)."""
    size = len(monomials)
    d = np.zeros((size, size))
    for i, a in enumerate(monomials):
        for j, b in enumerate(monomials):
            s = [p + q for p, q in zip(a, b)]
            if all(x % 2 == 0 for x in s):
                d[i, j] = np.prod([_double_factorial(x - 1) for x in s])
    return d


_ANGULAR = {}


def angular(l, pure):
    key = (l, pure)
    if key not in _ANGULAR:
        monomials = cartesian(l)
        metric = _metric(monomials)
        if pure:
            rows = []
            for m in pure_order(l):
                terms = solid_harmonic(l, m)
                rows.append([terms.get(k, 0.0) for k in monomials])
            matrix = np.array(rows)
        else:
            if l == 5:
                raise ValueError('Cartesian h functions are not defined in the Molden format')
            matrix = np.eye(len(monomials))
        norms = np.sqrt(np.einsum('ik,kl,il->i', matrix, metric, matrix))
        _ANGULAR[key] = matrix / norms[:, None]
    return _ANGULAR[key]


def radial_norm(alpha, l):
    """g(alpha, l) of §1 (numpy arrays welcome)."""
    return np.sqrt((2 * alpha / pi) ** 1.5 * (4 * alpha) ** l)


class Shell:
    def __init__(self, centre, l, pure, exponents, coefficients):
        self.centre = int(centre)
        self.l = int(l)
        self.pure = bool(pure) and l >= 2  # s and p are the same either way
        self.exponents = np.asarray(exponents, dtype=float)
        self.coefficients = np.asarray(coefficients, dtype=float)
        if self.exponents.size == 0 or self.exponents.shape != self.coefficients.shape:
            raise ValueError('a shell needs as many coefficients as exponents')
        if not np.all(np.isfinite(self.exponents)) or np.any(self.exponents <= 0):
            raise ValueError('exponents must be positive')
        if not np.all(np.isfinite(self.coefficients)):
            raise ValueError('non-finite contraction coefficient')
        self.angular = angular(self.l, self.pure)
        self.monomials = cartesian(self.l)

    @property
    def size(self):
        return self.angular.shape[0]

    def radial(self):
        return self.coefficients * radial_norm(self.exponents, self.l)

    def contraction_norm(self):
        a = self.exponents
        pair = 2 * np.sqrt(np.outer(a, a)) / np.add.outer(a, a)
        return float(self.coefficients @ (pair ** (self.l + 1.5)) @ self.coefficients)

    def with_coefficients(self, coefficients):
        return Shell(self.centre, self.l, self.pure, self.exponents, coefficients)

    def __repr__(self):
        return f'Shell(centre={self.centre}, l={self.l}, pure={self.pure}, n={self.exponents.size})'


def _overlap_1d(i, j, pa, pb, p):
    """sum part of s_ij (without exp(-mu X^2) sqrt(pi/p)) for arrays pa, pb, p of one shape."""
    total = np.zeros_like(p)
    for ii in range(i + 1):
        for jj in range(j + 1):
            if (ii + jj) % 2:
                continue
            total = total + (
                comb(i, ii)
                * comb(j, jj)
                * pa ** (i - ii)
                * pb ** (j - jj)
                * _double_factorial(ii + jj - 1)
                / (2 * p) ** ((ii + jj) / 2)
            )
    return total


def _shell_pair(sa, sb, ra, rb):
    a = sa.exponents[:, None]
    b = sb.exponents[None, :]
    p = a + b
    mu = a * b / p
    diff = np.asarray(ra) - np.asarray(rb)
    pre = np.exp(-mu * float(diff @ diff)) * (pi / p) ** 1.5
    pref = np.outer(sa.radial(), sb.radial()) * pre
    tables = []
    for axis in range(3):
        P = (a * ra[axis] + b * rb[axis]) / p
        pa, pb = P - ra[axis], P - rb[axis]
        tables.append({(i, j): _overlap_1d(i, j, pa, pb, p) for i in range(sa.l + 1) for j in range(sb.l + 1)})
    mono = np.empty((len(sa.monomials), len(sb.monomials)))
    for ka, (xa, ya, za) in enumerate(sa.monomials):
        for kb, (xb, yb, zb) in enumerate(sb.monomials):
            mono[ka, kb] = np.sum(pref * tables[0][xa, xb] * tables[1][ya, yb] * tables[2][za, zb])
    return sa.angular @ mono @ sb.angular.T


def overlap_by_pairs(shells, centres):
    """The same matrix as overlap(), shell pair by shell pair (slow; a cross-check for the tests)."""
    centres = np.asarray(centres, dtype=float)
    offsets = np.cumsum([0] + [s.size for s in shells])
    result = np.zeros((offsets[-1], offsets[-1]))
    for i, sa in enumerate(shells):
        for j in range(i, len(shells)):
            sb = shells[j]
            block = _shell_pair(sa, sb, centres[sa.centre], centres[sb.centre])
            result[offsets[i] : offsets[i + 1], offsets[j] : offsets[j + 1]] = block
            result[offsets[j] : offsets[j + 1], offsets[i] : offsets[i + 1]] = block.T
    return result


def overlap(shells, centres):
    """All shells of one angular momentum at once: the primitive pairs of two classes form arrays."""
    centres = np.asarray(centres, dtype=float)
    offsets = np.cumsum([0] + [s.size for s in shells])
    result = np.zeros((offsets[-1], offsets[-1]))
    classes = {}
    for index, shell in enumerate(shells):
        classes.setdefault(shell.l, []).append(index)
    packed = {}
    for l, members in classes.items():
        alpha = np.concatenate([shells[i].exponents for i in members])
        weight = np.concatenate([shells[i].radial() for i in members])
        where = np.concatenate(
            [np.repeat(centres[shells[i].centre][None, :], shells[i].exponents.size, 0) for i in members]
        )
        owner = np.concatenate([[n] * shells[i].exponents.size for n, i in enumerate(members)])
        gather = np.zeros((alpha.size, len(members)))
        gather[np.arange(alpha.size), owner] = 1.0
        packed[l] = (members, alpha, weight, where, gather)
    for la, (ma, aa, wa, ra, ga) in packed.items():
        for lb, (mb, ab, wb, rb, gb) in packed.items():
            if lb < la:
                continue
            a = aa[:, None]
            b = ab[None, :]
            p = a + b
            mu = a * b / p
            diff = ra[:, None, :] - rb[None, :, :]
            pref = np.exp(-mu * np.einsum('ijk,ijk->ij', diff, diff)) * (pi / p) ** 1.5 * np.outer(wa, wb)
            tables = []
            for axis in range(3):
                P = (a * ra[:, axis][:, None] + b * rb[:, axis][None, :]) / p
                pa, pb = P - ra[:, axis][:, None], P - rb[:, axis][None, :]
                tables.append({(i, j): _overlap_1d(i, j, pa, pb, p) for i in range(la + 1) for j in range(lb + 1)})
            monomials_a, monomials_b = cartesian(la), cartesian(lb)
            mono = np.empty((len(ma), len(mb), len(monomials_a), len(monomials_b)))
            for ka, (xa, ya, za) in enumerate(monomials_a):
                for kb, (xb, yb, zb) in enumerate(monomials_b):
                    raw = pref * tables[0][xa, xb] * tables[1][ya, yb] * tables[2][za, zb]
                    mono[:, :, ka, kb] = ga.T @ raw @ gb
            for n, i in enumerate(ma):
                for q, j in enumerate(mb):
                    if la == lb and j < i:
                        continue
                    block = shells[i].angular @ mono[n, q] @ shells[j].angular.T
                    result[offsets[i] : offsets[i + 1], offsets[j] : offsets[j + 1]] = block
                    result[offsets[j] : offsets[j + 1], offsets[i] : offsets[i + 1]] = block.T
    return result


def on_grid(shells, centres, vector, origin, step, shape):
    centres = np.asarray(centres, dtype=float)
    vector = np.asarray(vector, dtype=float)
    origin = np.asarray(origin, dtype=float)
    step = np.asarray(step, dtype=float)
    axes = [origin[k] + step[k] * np.arange(shape[k]) for k in range(3)]
    field = np.zeros(shape)
    start = 0
    for shell in shells:
        weights = shell.angular.T @ vector[start : start + shell.size]  # per Cartesian monomial
        start += shell.size
        if not np.any(weights):
            continue
        centre = centres[shell.centre]
        radial = shell.radial()
        for alpha, d in zip(shell.exponents, radial):
            if d == 0:
                continue
            # beyond this distance exp(-alpha r^2 / 2) < CUTOFF, so r^l exp(-alpha r^2) is below CUTOFF times
            # the largest value of r^l exp(-alpha r^2 / 2): the dropped tail is negligible (§6)
            reach = sqrt(-2 * np.log(CUTOFF) / alpha)
            ranges = []
            for k in range(3):
                lo = int(np.searchsorted(axes[k], centre[k] - reach, 'left'))
                hi = int(np.searchsorted(axes[k], centre[k] + reach, 'right'))
                ranges.append((lo, hi))
            if any(hi <= lo for lo, hi in ranges):
                continue
            parts = []
            for k in range(3):
                lo, hi = ranges[k]
                x = axes[k][lo:hi] - centre[k]
                gauss = np.exp(-alpha * x * x)
                parts.append([gauss * x**n for n in range(shell.l + 1)])
            block = np.zeros([hi - lo for lo, hi in ranges])
            for w, (a, b, c) in zip(weights, shell.monomials):
                if w:
                    block += (d * w) * np.multiply.outer(np.multiply.outer(parts[0][a], parts[1][b]), parts[2][c])
            (x0, x1), (y0, y1), (z0, z1) = ranges
            field[x0:x1, y0:y1, z0:z1] += block
    return field


def values_at(shells, centres, vector, points):
    """sum_k vector_k phi_k at arbitrary points (m, 3) bohr; for tests and small samples."""
    centres = np.asarray(centres, dtype=float)
    points = np.atleast_2d(np.asarray(points, dtype=float))
    total = np.zeros(len(points))
    start = 0
    for shell in shells:
        weights = shell.angular.T @ np.asarray(vector, dtype=float)[start : start + shell.size]
        start += shell.size
        rel = points - centres[shell.centre]
        r2 = np.einsum('ij,ij->i', rel, rel)
        radial = np.exp(-np.multiply.outer(r2, shell.exponents)) @ shell.radial()
        poly = np.zeros(len(points))
        for w, (a, b, c) in zip(weights, shell.monomials):
            poly += w * rel[:, 0] ** a * rel[:, 1] ** b * rel[:, 2] ** c
        total += poly * radial
    return total


__all__ = [
    'CUTOFF',
    'MAX_L',
    'Shell',
    'angular',
    'cartesian',
    'on_grid',
    'overlap',
    'pure_order',
    'radial_norm',
    'solid_harmonic',
    'values_at',
]
