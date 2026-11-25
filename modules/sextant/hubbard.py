"""DFT+U of a crystal: the Hubbard U of the d or f shell of an element, for Quantum ESPRESSO and CP2K.

§1 THEORY
    The semilocal functionals (PBE …) spread the electrons of a partly filled localized shell (3d of Fe, Ni, Co, Mn in
    oxides, 4f of Ce, 5f of U) too much: the gap of NiO, MnO, FeO comes out near zero, the magnetic moments small.
    DFT+U (Dudarev et al., Phys. Rev. B 57 (1998) 1505 — the simplified rotationally invariant form) adds to the energy
    (U/2) Σ_σ Tr[n^σ (1 − n^σ)] over the occupation matrix n^σ of the shell projected on its atomic orbitals: a penalty
    for fractional occupations, which opens the gap. U (eV) is an effective parameter: it depends on the projectors
    and the pseudopotentials, so values are taken from a calculation of the same kind (linear response — hp.x of QE)
    or from the literature for the same code; the U of one code is not that of another.
§2 ALGORITHM
    parse(text): «Fe 5.3, Ni 6.2» (or «Fe=5.3; Ni-3d 6.2») -> ((element, manifold, U), …); the manifold — that of
    MANIFOLDS when not written (3d for Sc–Zn, 4d for Y–Cd, 5d for La, Hf–Hg, 4f for Ce–Lu, 5f for Th–Lr).
    Quantum ESPRESSO 7.1 and later (INPUT_PW, read 2026-11-15): the card «HUBBARD (ortho-atomic)» with lines
    «U Fe-3d 5.3» — Löwdin-orthogonalized atomic orbitals of the pseudopotential (the projectors the documentation
    recommends; forces and stress work with them). CP2K (src/input_cp2k_subsys.F and input_cp2k_dft.F, read 2026-11-15):
    PLUS_U_METHOD MULLIKEN in &DFT and in &KIND «&DFT_PLUS_U T», L (2 — d, 3 — f), U_MINUS_J [eV].
§4 SPECIFICATION
    MANIFOLDS {element: manifold}; L_OF {'d': 2, 'f': 3}; parse(text) -> tuple; candidates(elements) -> [element];
    qe_card(hubbard) -> [line]; cp2k_kind(hubbard, element) -> [line]; ValueError — a word not understood, an element
    without a d or f shell here, a U below 0 or above 15 eV, an element twice.
§7 TESTS
    tests/sextant/test_hubbard.py.
"""

import re

from azimuth.i18n import tr

_3D = 'Sc Ti V Cr Mn Fe Co Ni Cu Zn'.split()
_4D = 'Y Zr Nb Mo Tc Ru Rh Pd Ag Cd'.split()
_5D = 'La Hf Ta W Re Os Ir Pt Au Hg'.split()
_4F = 'Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu'.split()
_5F = 'Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr'.split()
MANIFOLDS = {**{e: '3d' for e in _3D}, **{e: '4d' for e in _4D}, **{e: '5d' for e in _5D}, **{e: '4f' for e in _4F},
             **{e: '5f' for e in _5F}}
L_OF = {'d': 2, 'f': 3}
U_MAX = 15.0
_ITEM = re.compile(r'^([A-Z][a-z]?)(?:-(\d[df]))?\s*(?:=|:|\s)\s*([0-9]+(?:[.,][0-9]+)?)$')


def parse(text):
    out, seen = [], set()
    for chunk in re.split(r'[;,]\s+|;|\n', (text or '').strip()):
        chunk = chunk.strip()
        if not chunk:
            continue
        m = _ITEM.match(chunk)
        if not m:
            raise ValueError(tr('DFT+U: не понимаю «{}» — пишите «Fe 5.3, Ni 6.2» (эВ).').format(chunk))
        element, manifold, value = m.group(1), m.group(2), float(m.group(3).replace(',', '.'))
        if element not in MANIFOLDS:
            raise ValueError(tr('DFT+U: у {} нет d- или f-оболочки, к которой обычно ставят U.').format(element))
        if not 0 <= value <= U_MAX:
            raise ValueError(tr('DFT+U: U = {:g} эВ для {} — вне 0…{:g} эВ.').format(value, element, U_MAX))
        if element in seen:
            raise ValueError(tr('DFT+U: {} задан дважды.').format(element))
        seen.add(element)
        out.append((element, manifold or MANIFOLDS[element], value))
    return tuple(out)


def candidates(elements):
    return [e for e in dict.fromkeys(elements) if e in MANIFOLDS]


def qe_card(hubbard):
    if not hubbard:
        return []
    return ['HUBBARD (ortho-atomic)'] + [f'  U {e}-{m} {u:g}' for e, m, u in hubbard]


def cp2k_kind(hubbard, element):
    for e, m, u in hubbard or ():
        if e == element:
            return ['      &DFT_PLUS_U T', f'        L {L_OF[m[-1]]}', f'        U_MINUS_J [eV] {u:g}', '      &END DFT_PLUS_U']
    return []
