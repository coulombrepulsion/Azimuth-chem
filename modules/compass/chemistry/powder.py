"""The powder X-ray diffraction pattern of a crystal.

§1 THEORY
    A reflection hkl of a crystal is at the Bragg angle λ = 2 d sin θ, 1/d = |h a* + k b* + l c*|. Its structure
    factor over the atoms j of the cell (fractional r_j, occupancy o_j, isotropic displacement U_j):
        F(hkl) = sum_j o_j f_j(s) exp(-8 π² U_j s²) exp(2πi (h x_j + k y_j + l z_j)), s = sin θ / λ = 1 / (2d),
    with the atomic scattering factor of the neutral atom f(s) = c + sum_i a_i exp(-b_i s²) (Waasmaier & Kirfel,
    Acta Cryst. A51, 416, 1995; data/xray_f0.json). The systematic absences of the space group come out of the sum as
    F = 0 (the cell content is built by the operations). In a powder every reflection with the same d falls on one
    line: its intensity is the sum of |F|² over them (the multiplicity is their number) times the Lorentz–polarization
    factor of an unpolarized beam without a monochromator, Lp = (1 + cos² 2θ) / (sin² θ cos θ) (Bragg–Brentano,
    a sample thick enough to absorb the beam: no absorption correction). The lines are scaled to 100 for the
    strongest. A profile: each line a pseudo-Voigt function of 2θ with the full width at half maximum FWHM and the
    share η of the Lorentzian.
    The Kα₂ line of the tube — each reflection again at λ(Kα₂) with I(Kα₂)/I(Kα₁) = 1/2 (the
    two levels 2p₃/₂ and 2p₁/₂ have 4 and 2 electrons) times the ratio of the Lp factors at the two angles; the
    preferred orientation of March–Dollase (W. A. Dollase, J. Appl. Cryst. 19, 267, 1986): a reflection whose vector
    makes the angle α with the axis H of the texture is weighted by P(α) = (r² cos² α + sin² α / r)^(−3/2) — r = 1 no
    texture, r < 1 plates lying on H (the reflections along H stronger), r > 1 needles; the average of P over the
    sphere is 1, so the total is kept. The widths of Caglioti, Paoletti & Ricci (Nucl. Instrum. 3, 223, 1958):
    FWHM² = U tan² θ + V tan θ + W, each line keeping its area (the height falls as the width grows).
§2 ALGORITHM
    pattern(crystal, wavelength, start, stop): the atoms of the cell (crystal.unit_cell) with the occupancy and U of
    their site (U_iso, else U_eq of the anisotropic tensor, else 0); every hkl with |h| <= |a| / d_min … (d_min =
    λ / (2 sin(stop / 2))), d in the range; F by numpy in chunks; |F|² below 1e-8 of the largest — absent; the
    reflections sorted by d and joined when d agrees within 1e-6 relative; the line's hkl — the largest of them in
    the order of tuples (200 rather than 0-20). profile(lines, start, stop, step, fwhm, eta) -> (2θ, I).
§3 APPLICATIONS
    modules/compass/actions/powder_window.py («Кристалл → Порошковая дифрактограмма…»).
§4 SPECIFICATION
    WAVELENGTHS: {name: λ in Å}; Line(two_theta, d, hkl, multiplicity, intensity in % of the strongest, f2 (sum of
    |F|²), alpha2=False); pattern(crystal, wavelength=CU, start=5.0, stop=90.0, least=0.01, texture=None,
    anomalous=False) -> tuple of Line by 2θ (texture: ((h, k, l), r) of March–Dollase; anomalous — f′ + i f″
    of the tube line added to f₀, ValueError for a wavelength of no tube); tube(λ) -> name | None; dispersion(symbol,
    λ) -> (f′, f″); profile(lines, start, stop, step=0.02, fwhm=0.1, eta=0.5,
    uvw=None) -> (list of 2θ, list of I) (uvw: (U, V, W) in degrees² — the widths of Caglioti instead of fwhm);
    KA2 {name of Kα₁: λ(Kα₂)}, KA2_RATIO = 0.5; alpha2(lines, wavelength, wavelength2, ratio=KA2_RATIO,
    start=None, stop=None) -> tuple of Line (alpha2=True); march(cos_alpha, r) -> P; caglioti(two_theta, U, V, W) ->
    FWHM; read_xy(text) -> (list of 2θ, list of I); write_xy(xs, ys) -> text.
§5 PROCEDURES - below.
§6 NOTES Neutral atoms (the charges of ions change f only at small s); no absorption or extinction; the anomalous
    dispersion only on request — f′, f″ of Henke, Gullikson & Davis, At. Data Nucl. Data Tables 54, 181 (1993)
    (data/xray_anomalous.json, data/LICENSE-henke.txt; near an absorption edge — Fe and Co with Co Kα — the free-atom
    values are less certain): the intensities are those of an ideal powder; measured patterns differ by some % (texture
    especially; March–Dollase is the usual single-axis correction). The Kα₁ and Kα₂ wavelengths are those of Hölzer et
    al., Phys. Rev. A 56, 4554 (1997), as listed by the International Tables vol. C, table 4.2.2.1. Unknown elements
    (dummy atoms 'X') scatter nothing.
§7 TESTS
    tests/compass/test_powder.py.
§8' ROBUSTNESS / ERRORS
    ValueError for a range outside 0 < start < stop < 180° or a wavelength <= 0, and when more than MAX_REFLECTIONS
    hkl would be needed (a huge cell with a short wavelength).
"""

from dataclasses import dataclass
from functools import lru_cache
import json
from math import asin, cos, degrees, pi, radians, sin, sqrt
from pathlib import Path

from azimuth.i18n import tr
from modules.compass.chemistry import crystal as cr

TABLE = Path(__file__).with_name('data') / 'xray_f0.json'
ANOMALOUS = TABLE.with_name('xray_anomalous.json')  # f′, f″ of Henke et al. at the Kα₁ of each tube
WAVELENGTHS = {
    'Cu Kα₁': 1.5405929,
    'Mo Kα₁': 0.7093171,
    'Co Kα₁': 1.7889961,
    'Fe Kα₁': 1.9360410,
    'Cr Kα₁': 2.2897260,
    'Ag Kα₁': 0.5594218,
}
CU = WAVELENGTHS['Cu Kα₁']
KA2 = {  # the Kα₂ line of each tube (Hölzer et al. 1997; International Tables C, 4.2.2.1)
    'Cu Kα₁': 1.5444274,
    'Mo Kα₁': 0.7136043,
    'Co Kα₁': 1.7928350,
    'Fe Kα₁': 1.9399730,
    'Cr Kα₁': 2.2936510,
    'Ag Kα₁': 0.5638131,
}
KA2_RATIO = 0.5
MAX_REFLECTIONS = 3_000_000
CHUNK = 20_000


@dataclass(frozen=True)
class Line:
    two_theta: float
    d: float
    hkl: tuple
    multiplicity: int
    intensity: float
    f2: float
    alpha2: bool = False  # a line of Kα₂


@lru_cache(maxsize=1)
def _f0():
    return json.loads(TABLE.read_text(encoding='utf-8'))['ions']


@lru_cache(maxsize=1)
def _anomalous():
    return json.loads(ANOMALOUS.read_text(encoding='utf-8'))['lines']


def tube(wavelength):
    """The name of the tube line of this wavelength (Kα₁ or Kα₂ of WAVELENGTHS, KA2), or None."""
    for name, value in WAVELENGTHS.items():
        if abs(value - wavelength) < 1e-5 or abs(KA2[name] - wavelength) < 1e-5:
            return name
    return None


def dispersion(symbol, wavelength):
    """(f′, f″) of the neutral atom at the line of a tube; ValueError for another wavelength."""
    name = tube(wavelength)
    if name is None:
        raise ValueError(tr('Аномальное рассеяние известно для линий трубок (Cu, Mo, Co, Fe, Cr, Ag), не для '
                            'произвольной длины волны.'))
    entry = _anomalous().get('H' if symbol == 'D' else symbol)
    return (0.0, 0.0) if entry is None else tuple(entry[name])


def f0(symbol, s):
    """The scattering factor of the neutral atom at s = sin θ / λ (1/Å); 0 for an unknown symbol."""
    entry = _f0().get('H' if symbol == 'D' else symbol)
    if entry is None:
        return 0.0
    from math import exp

    _, c, a, b = entry
    return c + sum(ai * exp(-bi * s * s) for ai, bi in zip(a, b))


def _site_u(site, cell):
    if site.u_iso > 0:
        return site.u_iso
    if site.u:
        from modules.compass.chemistry import crystal_adp as adp

        return adp.u_eq(adp.u_cart(cell, site.u))
    return 0.0


def march(cos_alpha, r):
    """The March–Dollase weight of a reflection at the angle α to the axis of the texture."""
    c2 = cos_alpha * cos_alpha
    return (r * r * c2 + (1 - c2) / r) ** -1.5


def caglioti(two_theta, u, v, w):
    """The width (FWHM, °) at 2θ: √(U tan² θ + V tan θ + W); never below 0.001°."""
    from math import tan

    t = tan(radians(two_theta) / 2)
    return sqrt(max(u * t * t + v * t + w, 1e-6))


def _lp(theta):
    return (1 + cos(2 * theta) ** 2) / (sin(theta) ** 2 * cos(theta))


def pattern(crystal, wavelength=CU, start=5.0, stop=90.0, least=0.01, texture=None, anomalous=False):
    import numpy as np

    if not (wavelength > 0 and 0 < start < stop < 180):
        raise ValueError(tr('Порошковая дифрактограмма: нужен интервал 0 < 2θ₁ < 2θ₂ < 180° и длина волны больше нуля.'))
    sites = {s.label: s for s in crystal.sites}
    atoms = cr.unit_cell(crystal)
    symbols = sorted({a[0] for a in atoms})
    index = np.array([symbols.index(a[0]) for a in atoms])
    frac = np.array([a[1:4] for a in atoms], dtype=float)
    occ = np.array([sites[a[4]].occupancy if a[4] in sites else 1.0 for a in atoms])
    u = np.array([_site_u(sites[a[4]], crystal.cell) if a[4] in sites else 0.0 for a in atoms])
    rows = np.array(crystal.cell.vectors(), dtype=float)
    star = np.linalg.inv(rows).T  # rows a*, b*, c* (no 2π)
    d_min = wavelength / (2 * sin(radians(stop) / 2))
    d_max = wavelength / (2 * sin(radians(start) / 2))
    limits = [int(np.linalg.norm(v) / d_min) + 1 for v in rows]
    if np.prod([2 * n + 1 for n in limits]) > MAX_REFLECTIONS:
        raise ValueError(tr('Порошковая дифрактограмма: слишком много отражений — уменьшите 2θ₂ или возьмите более длинную волну.'))
    grid = np.stack(np.meshgrid(*[np.arange(-n, n + 1) for n in limits], indexing='ij'), -1).reshape(-1, 3)
    inverse_d = np.linalg.norm(grid @ star, axis=1)
    keep = (inverse_d > 0) & (inverse_d <= 1 / d_min + 1e-12) & (inverse_d >= 1 / d_max - 1e-12)
    hkl, inverse_d = grid[keep], inverse_d[keep]
    s = inverse_d / 2
    # f = f₀(s) + f′ + i f″ at the line of the tube (Henke et al. 1993); the Kα₂ lines keep those of Kα₁
    extra = np.array([complex(*dispersion(sym, wavelength)) for sym in symbols]) if anomalous else np.zeros(len(symbols))
    f2 = np.empty(len(hkl))
    for lo in range(0, len(hkl), CHUNK):
        part, sp = hkl[lo:lo + CHUNK], s[lo:lo + CHUNK]
        table = np.array([[f0(sym, x) for sym in symbols] for x in sp]) if len(sp) < 64 else _f0_grid(symbols, sp)
        table = table + extra[None, :]
        weight = table[:, index] * occ[None, :] * np.exp(-8 * pi * pi * u[None, :] * sp[:, None] ** 2)
        phase = np.exp(2j * pi * (part @ frac.T))
        f = (weight * phase).sum(axis=1)
        f2[lo:lo + CHUNK] = (f * f.conj()).real
    if not len(f2) or f2.max() <= 0:
        return ()
    present = f2 > 1e-8 * f2.max()
    hkl, inverse_d, f2 = hkl[present], inverse_d[present], f2[present]
    weight = np.ones(len(f2))
    if texture is not None:  # March–Dollase about the reciprocal vector of the plane H
        axis, r = texture
        h_vec = np.array(axis, dtype=float) @ star
        if not np.linalg.norm(h_vec) or r <= 0:
            raise ValueError(tr('Преимущественная ориентация: нужна плоскость hkl, не 0 0 0, и r больше нуля.'))
        cos_alpha = (hkl @ star) @ (h_vec / np.linalg.norm(h_vec)) / inverse_d
        weight = march(np.clip(cos_alpha, -1.0, 1.0), float(r))
    order = np.argsort(inverse_d, kind='stable')
    hkl, inverse_d, f2, weight = hkl[order], inverse_d[order], f2[order], weight[order]
    groups, begin = [], 0
    for k in range(1, len(order) + 1):
        if k == len(order) or inverse_d[k] - inverse_d[begin] > 1e-6 * inverse_d[begin]:
            groups.append((begin, k))
            begin = k
    raw = []
    for lo, hi in groups:
        d = float(1 / inverse_d[lo:hi].mean())
        theta = asin(min(1.0, wavelength / (2 * d)))
        lp = _lp(theta)
        total = float(f2[lo:hi].sum())
        best = max(tuple(int(x) for x in h) for h in hkl[lo:hi])
        raw.append((degrees(2 * theta), d, best, hi - lo, float((f2[lo:hi] * weight[lo:hi]).sum()) * lp, total))
    top = max(r[4] for r in raw)
    lines = [Line(t, d, h, m, 100 * i / top, f) for t, d, h, m, i, f in raw if 100 * i / top >= least]
    return tuple(sorted(lines, key=lambda line: line.two_theta))


def _f0_grid(symbols, sp):
    import numpy as np

    table = _f0()
    out = np.zeros((len(sp), len(symbols)))
    s2 = sp ** 2
    for k, sym in enumerate(symbols):
        entry = table.get('H' if sym == 'D' else sym)
        if entry is None:
            continue
        _, c, a, b = entry
        out[:, k] = c + sum(ai * np.exp(-bi * s2) for ai, bi in zip(a, b))
    return out


def alpha2(lines, wavelength, wavelength2, ratio=KA2_RATIO, start=None, stop=None):
    """The lines of Kα₂ — each line of Kα₁ again at λ₂ (the same d), its intensity × ratio × Lp(θ₂)/Lp(θ₁),
    in % of the strongest line of Kα₁ as the lines given; those beyond 180° or outside start…stop left out."""
    out = []
    for line in lines:
        q = wavelength2 / (2 * line.d)
        if q >= 1:
            continue
        t1, t2 = radians(line.two_theta) / 2, asin(q)
        two = degrees(2 * t2)
        if (start is not None and two < start) or (stop is not None and two > stop):
            continue
        out.append(Line(two, line.d, line.hkl, line.multiplicity, line.intensity * ratio * _lp(t2) / _lp(t1), line.f2,
                        True))
    return tuple(out)


def curve(x, centres, intensities, widths, eta=0.5):
    """The sum of pseudo-Voigt lines at the centres; widths — the FWHM of each. A line of the width w has the height
    intensity × w₀ / w (w₀ the first width): the areas follow the intensities, and lines of one width have the
    heights of their intensities."""
    import numpy as np

    x = np.asarray(x, dtype=float)
    y = np.zeros_like(x)
    if not len(widths):
        return y
    reference = float(widths[0])
    for centre, intensity, width in zip(centres, intensities, widths):
        t = (x - centre) / (width / 2)
        y += intensity * reference / width * ((1 - eta) * np.exp(-np.log(2) * t * t) + eta / (1 + t * t))
    return y


def profile(lines, start, stop, step=0.02, fwhm=0.1, eta=0.5, uvw=None):
    """The pattern as a curve: a pseudo-Voigt line (FWHM in degrees, Lorentzian share eta) at each line;
    uvw = (U, V, W) — the width of each line by Caglioti instead of one FWHM."""
    import numpy as np

    x = np.arange(start, stop + step / 2, step)
    widths = [caglioti(line.two_theta, *uvw) if uvw else fwhm for line in lines]
    y = curve(x, [line.two_theta for line in lines], [line.intensity for line in lines], widths, eta)
    if len(y) and y.max() > 0:
        y *= 100 / y.max()
    return x.tolist(), y.tolist()


def read_xy(text):
    """Two columns (2θ, intensity) of a measured pattern; comments (#, !, ;) and other lines are skipped."""
    xs, ys = [], []
    for line in text.splitlines():
        words = line.replace(',', ' ').split()
        if len(words) < 2 or words[0][0] in '#!;':
            continue
        try:
            x, y = float(words[0]), float(words[1])
        except ValueError:
            continue
        xs.append(x)
        ys.append(y)
    if len(xs) < 2:
        raise ValueError(tr('В файле нет двух столбцов чисел (2θ и интенсивность).'))
    return xs, ys


def write_xy(xs, ys):
    return ''.join(f'{x:.4f} {y:.4f}\n' for x, y in zip(xs, ys))
