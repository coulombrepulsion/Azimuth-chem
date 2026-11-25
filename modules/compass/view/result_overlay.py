"""What Compass draws over the model from a calculation result: atom values, Mayer bond orders, the
dipole and the forces, in the frame of the structure on screen.

§1 PURPOSE
    A result (modules/spectrum/readers/orca_properties.Properties) belongs to one geometry. The structure in
    Compass may be that geometry turned (best view does not change coordinates, but «standard
    orientation» and moving the molecule do), or a different structure (edited, another optimization
    step). Values are shown only for the same structure, and vectors are turned with it.
§2 ALGORITHM
    match: same elements in the same order, then the proper rotation R (Kabsch: SVD of the centred
    coordinates, det R = +1) that takes the result geometry onto the structure; the structure matches
    if the RMS deviation after it is below MATCH_RMSD. A mirror image does not match (vectors would be
    wrong). Vectors v of the result become v @ R.
    mayer_structure: the bonds of the structure from the Mayer orders: a bond where B >= BOND_MIN;
    aromatic (1.5) when AROMATIC_LOW <= B < AROMATIC_HIGH and the bond lies in a six-membered ring of
    such bonds' graph (benzene 1.36-1.47, the cation's quinoid ring 1.26/1.55 in the test data); else
    the nearest of 1, 2, 3 (1 below 1.5, 2 below 2.5): C=O 1.93, vinyl C=C 1.90, the C=C of the
    pyrrole ring of indole 1.69 -> 2 (Trp, ORCA 6.0.1, cclib data).
§3 APPLICATIONS
    modules/compass/actions/property_actions.py (menu, state), viewer.draw_overlay (drawing).
§4 SPECIFICATION
    ATOM_VALUES: {key: (source in Properties, field key, Russian title)} for the atom labels.
    match(props, molecule) -> rotation (3x3 numpy array) or None.
    overlay(props, molecule, choice) -> dict | None; choice = {'atom': key | None, 'bonds': bool,
        'dipole': bool, 'forces': bool}. The dict: 'atom': (key, values) | None; 'bonds': [(i, j, order)];
        'dipole': (vector in a.u. in the frame of the structure, Debye) | None; 'forces': [force vectors
        (minus gradient), hartree/bohr] | None. None when the structure does not match.
    mayer_structure(props, molecule) -> Molecule with bonds (molecule must match).
    MATCH_RMSD = 0.01 A: a design choice, not a physical limit. ORCA prints coordinates to 1e-6 A;
        symmetrization in Compass moves atoms by up to ~1e-3 A; a hand-moved atom (>0.01 A) is another
        structure. BOND_MIN = half a bond; Mayer orders of hydrogen bonds and long contacts are
        typically 0.05-0.3, of covalent bonds 0.8 and more (ASSUMPTION: textbook ranges, not checked
        against a source).
§5 PROCEDURES - below.
§6 NOTES
    NumPy, no Qt.
§7 TESTS
    tests/compass/test_orca_properties.py (match after a rotation, a mirror image, a moved atom; turned vectors;
    Mayer bonds of divinylbenzene).
§8' ROBUSTNESS
    Any mismatch gives None, never values on the wrong atoms.
"""

import numpy as np

from azimuth.core import Molecule
from modules.compass.chemistry.editing import _rings6

MATCH_RMSD = 0.01
BOND_MIN = 0.5
AROMATIC_LOW, AROMATIC_HIGH = 1.25, 1.75  # design choice: around 1.5, ranges in §2
# the labels of the structure of a crystal (crystal_energetics.model_labels) — their legends
CRYSTAL_LABELS = {'oxidation': 'Степени окисления (формальные)', 'bvs': 'Суммы валентностей связей, в.е.',
                  'fractional': 'Дробные координаты x y z', 'site': 'Позиция: метка · кратность · симметрия'}

ATOM_VALUES = {
    'mulliken': ('charges', 'mulliken', 'Заряды Малликена'),
    'loewdin': ('charges', 'loewdin', 'Заряды Лёвдина'),
    'hirshfeld': ('charges', 'hirshfeld', 'Заряды Хиршфельда'),
    'spin-mulliken': ('spins', 'mulliken', 'Спиновая заселённость (Малликен)'),
    'spin-loewdin': ('spins', 'loewdin', 'Спиновая заселённость (Лёвдин)'),
    'spin-hirshfeld': ('spins', 'hirshfeld', 'Спиновая заселённость (Хиршфельд)'),
    'cm5': ('charges', 'cm5', 'Заряды CM5'),
    'adch': ('charges', 'adch', 'Заряды ADCH'),
    'resp': ('charges', 'resp', 'Заряды RESP'),  # Multiwfn
    # the condensed Fukui functions of the queue «Функции Фукуи» (modules/spectrum/analysis/fukui.py)
    'fukui-plus': ('charges', 'fukui+', 'Фукуи f⁺ (атака нуклеофила)'),
    'fukui-minus': ('charges', 'fukui-', 'Фукуи f⁻ (атака электрофила)'),
    'fukui-zero': ('charges', 'fukui0', 'Фукуи f⁰ (атака радикала)'),
    'fukui-dual': ('charges', 'dual', 'Дескриптор двойственности Δf'),
    'aim': ('charges', 'aim', 'Заряды AIM (бассейны Бейдера)'),  # Multiwfn
    'spin-aim': ('spins', 'aim', 'Спиновая заселённость (бассейны AIM)'),
    'apt': ('charges', 'apt', 'Заряды APT'),
    'xtb': ('charges', 'xtb', 'Заряды xtb (GFN)'),
    'mopac': ('charges', 'mopac', 'Заряды MOPAC'),
    'mayer-valence': (None, None, 'Валентность Майера'),
}


def available(props):
    """Keys of ATOM_VALUES present in props, in menu order."""
    if props is None:
        return []
    keys = []
    for key, (source, name, _) in ATOM_VALUES.items():
        if source is None:
            if props.mayer_valence:
                keys.append(key)
        elif name in getattr(props, source):
            keys.append(key)
    return keys


def atom_values(props, key):
    source, name, _ = ATOM_VALUES[key]
    return props.mayer_valence if source is None else getattr(props, source)[name]


def match(props, molecule):
    if props is None or molecule is None or not molecule.atoms:
        return None
    if [a.symbol for a in props.geometry.atoms] != [a.symbol for a in molecule.atoms]:
        return None
    x = np.array([a.position for a in props.geometry.atoms], float)
    y = np.array([a.position for a in molecule.atoms], float)
    xc, yc = x - x.mean(axis=0), y - y.mean(axis=0)
    if len(x) == 1:
        rotation = np.eye(3)
    else:
        u, _, vt = np.linalg.svd(xc.T @ yc)
        correction = np.eye(3)
        correction[2, 2] = 1.0 if np.linalg.det(u @ vt) >= 0 else -1.0
        rotation = u @ correction @ vt
    rmsd = float(np.sqrt(np.mean(np.sum((xc @ rotation - yc) ** 2, axis=1))))
    return rotation if rmsd < MATCH_RMSD else None


def overlay(props, molecule, choice):
    rotation = match(props, molecule)
    if rotation is None:
        return None
    key = choice.get('atom')
    turn = lambda v: tuple(float(c) for c in np.asarray(v, float) @ rotation)
    return {
        'atom': (key, atom_values(props, key)) if key in available(props) else None,
        'bonds': list(props.mayer_bonds) if choice.get('bonds') else [],
        'bond_kind': getattr(props, 'bond_kind', 'Mayer'),
        'dipole': (turn(props.dipole), props.dipole_debye) if choice.get('dipole') and props.dipole else None,
        'forces': [turn([-g for g in row]) for row in props.gradient]
        if choice.get('forces') and props.gradient
        else None,
    }


def mayer_structure(props, molecule):
    if match(props, molecule) is None:
        raise ValueError('the structure is not the geometry of the result')
    from azimuth import defaults

    least = defaults.get('bond_order_min')  # «Настройки → Связи»; BOND_MIN is its default
    kept = [(i, j, order) for i, j, order in props.mayer_bonds if order >= least]
    neighbours = [[] for _ in molecule.atoms]
    for i, j, _ in kept:
        neighbours[i].append(j)
        neighbours[j].append(i)
    in_ring6 = set()
    for ring in _rings6(neighbours):
        for a, b in zip(ring, ring[1:] + ring[:1]):
            in_ring6.add((min(a, b), max(a, b)))
    bonds = []
    for i, j, order in kept:
        if AROMATIC_LOW <= order < AROMATIC_HIGH and (min(i, j), max(i, j)) in in_ring6:
            bonds.append((i, j, 1.5))
        else:
            bonds.append((i, j, 1 if order < 1.5 else (2 if order < 2.5 else 3)))
    return Molecule(molecule.title, molecule.atoms, tuple(bonds))
