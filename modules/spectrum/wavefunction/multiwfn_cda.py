"""Multiwfn: the charge decomposition analysis CDA of Dapprich and Frenking.

§1 PURPOSE
    The beta of docs/plans/ROADMAP.md, item 9: how a donor–acceptor bond is made — the electrons donated from fragment 1
    (the donor, a ligand) to fragment 2 (the acceptor, a metal fragment) d, the electrons back donated b, the
    repulsive polarization r (< 0: the electrons pushed out of the region between the fragments) and d − b, by complex
    orbital and in all; with the extended CDA (ECDA) of Multiwfn — the net charge fragment 2 gets.
§2 ALGORITHM
    Three wavefunctions at one geometry (Sextant, the queue «CDA»): the complex — its atoms those of fragment 1, then
    those of fragment 2 — and each fragment alone, in the same basis. Multiwfn reads the complex, then main menu 16 →
    «2» (two fragments) → the file of fragment 1 → the file of fragment 2; it prints the result at once (the orbital
    composition by Mulliken, «iCDAcomp» of settings.ini), then its menu: «-1» back to the main menu, «q».
    Recorded on Multiwfn 2026.7.15 with ORCA 6 B3LYP/def2-SVP (tools/record_multiwfn_cda.py, tests/data/multiwfn/cda_*):
    H3N→BH3 d 0.268, b 0.015, r −0.257; OC→BH3 d 0.348, b 0.156 (the back donation of CO), r −0.263.
    The table: «Orb. Occ. d b d - b r», rows «7 2.000000 0.166697 0.046277 0.120421 -0.498620», «Sum: 18.000000 …»;
    ECDA: «PL( 1) + CT( 1-> 2) = 0.4816 …», «The net electrons obtained by frag. 2 = CT( 1-> 2) - CT( 2-> 1) = 0.4532».
    References: S. Dapprich, G. Frenking, J. Phys. Chem. 99, 9352 (1995); M. Xiao, T. Lu, J. Adv. Phys. Chem. 4, 111
    (2015) — the generalized CDA of Multiwfn.
§4 SPECIFICATION
    answers(name1, name2) -> tuple; parse_cda(text) -> {'orbitals': [(n, occ, d, b, d_b, r)], 'sum': {'occ', 'd', 'b',
    'd_b', 'r'}, 'net': float | None, 'ecda': {'pl1_ct12', 'pl1_ct21', 'pl2_ct12', 'pl2_ct21'}} | None;
    run_cda(program, complex_path, fragment_paths (2), cores=1, step=None, timeout=1800) -> (result, output text);
    table(result) -> (header, rows); main_orbitals(result, count=5) -> [rows] by |d| + |b| + |r|.
    plan(molecule, calc) -> {'fragments': (atoms 1, atoms 2) 0-based in the order of the molecule, 'order': atoms 1 +
    atoms 2, 'parts': [(key, Molecule, charge, multiplicity)] for 'complex', 'frag1', 'frag2'} — the three calculations
    of the queue (calc.cda_atoms, cda_charge, cda_mult1, cda_mult2); ValueError with what to change.
§7 TESTS tests/spectrum/test_multiwfn_cda.py.
"""

import re
import shutil
from pathlib import Path

from azimuth.i18n import tr
from modules.spectrum.wavefunction import multiwfn

_NUMBER = r'(-?\d+\.\d+)'
_ROW = re.compile(r'^\s*(\d+)\s+' + r'\s+'.join([_NUMBER] * 5) + r'\s*$')
_SUM = re.compile(r'^\s*Sum:\s+' + r'\s+'.join([_NUMBER] * 5) + r'\s*$')
_HEAD = re.compile(r'^\s*Orb\.\s+Occ\.\s+d\s+b\s+d\s*-\s*b\s+r\s*$')
_NET = re.compile(r'net electrons obtained by frag\.\s*2\s*=.*=\s*' + _NUMBER)
_PL = re.compile(r'PL\(\s*(\d)\)\s*\+\s*CT\(\s*1->\s*2\)\s*=\s*' + _NUMBER + r'\s+PL\(\s*\d\)\s*\+\s*CT\(\s*2->\s*1\)\s*=\s*'
                 + _NUMBER)


def answers(name1, name2):
    return ('16', '2', name1, name2, '-1', 'q')


def parse_cda(text):
    """The last table of CDA in the output (Multiwfn prints it again for «0» of its menu) and the ECDA after it."""
    lines = text.replace('\r', '').split('\n')
    heads = [k for k, line in enumerate(lines) if _HEAD.match(line)]
    if not heads:
        return None
    orbitals, total, k = [], None, heads[-1] + 1
    for k in range(heads[-1] + 1, len(lines)):
        row = _ROW.match(lines[k])
        if row:
            orbitals.append((int(row.group(1)), *(float(row.group(i)) for i in range(2, 7))))
            continue
        found = _SUM.match(lines[k])
        if found:
            total = dict(zip(('occ', 'd', 'b', 'd_b', 'r'), (float(found.group(i)) for i in range(1, 6))))
            break
    if total is None:
        return None
    ecda, net = {}, None
    for line in lines[k:k + 40]:
        pl = _PL.search(line)
        if pl:
            ecda[f'pl{pl.group(1)}_ct12'], ecda[f'pl{pl.group(1)}_ct21'] = float(pl.group(2)), float(pl.group(3))
        found = _NET.search(line)
        if found:
            net = float(found.group(1))
            break
    return {'orbitals': orbitals, 'sum': total, 'net': net, 'ecda': ecda}


class _Files:
    """The complex and its two fragments copied into the folder of the run under ASCII names (the paths of the user
    may have spaces and Cyrillic letters, which the Fortran input of Multiwfn does not take); key — for the cache."""

    def __init__(self, complex_path, fragment_paths):
        self.paths = [Path(complex_path), *map(Path, fragment_paths)]
        stamps = [multiwfn._stamp(p) for p in self.paths]
        self.key = None if None in stamps else tuple(stamps)
        self.names = [name.replace('input', part) for name, part in
                      zip(map(multiwfn.wavefunction_name, self.paths), ('complex', 'frag1', 'frag2'))]

    def __call__(self, folder):
        for path, name in zip(self.paths, self.names):
            if not path.is_file():
                raise ValueError(tr('Файл волновой функции не найден: ') + str(path))
            shutil.copyfile(path, Path(folder) / name)
        return self.names[0]


def run_cda(program, complex_path, fragment_paths, cores=1, step=None, timeout=1800):
    if len(fragment_paths) != 2:
        raise ValueError(tr('CDA здесь — для двух фрагментов.'))
    files = _Files(complex_path, fragment_paths)
    text, _ = multiwfn._run(program, files, answers(*files.names[1:]), cores, step, timeout)
    found = parse_cda(text)
    if not found:
        raise ValueError(tr('Multiwfn не напечатал результат CDA. Конец его вывода:') + '\n' + multiwfn._tail(text))
    return found, text


def table(result):
    header = [tr('Орбиталь'), tr('Заселённость'), 'd', 'b', 'd − b', 'r']
    rows = [[str(n), f'{occ:.4f}', f'{d:.6f}', f'{b:.6f}', f'{d_b:.6f}', f'{r:.6f}'] for n, occ, d, b, d_b, r
            in result['orbitals']]
    s = result['sum']
    rows.append([tr('Сумма'), f'{s["occ"]:.4f}', f'{s["d"]:.6f}', f'{s["b"]:.6f}', f'{s["d_b"]:.6f}', f'{s["r"]:.6f}'])
    return header, rows


def main_orbitals(result, count=5):
    """The complex orbitals that carry most of the bond: by |d| + |b| + |r|, the largest first."""
    return sorted(result['orbitals'], key=lambda row: -(abs(row[2]) + abs(row[3]) + abs(row[5])))[:count]


PARTS = ('complex', 'frag1', 'frag2')


def plan(molecule, calc):
    """The three calculations of CDA: the complex with its atoms reordered — fragment 1 first, then fragment 2, the
    order of the record (Multiwfn takes the basis functions of the complex as those of fragment 1, then of fragment 2)
    —, and each fragment alone at the same positions."""
    from azimuth.core import Molecule
    from modules.spectrum.analysis.charge_transfer import parse_atoms

    n = len(molecule.atoms)
    if not calc.cda_atoms.strip():
        raise ValueError(tr('CDA: укажите атомы фрагмента 1 — донора (например, лиганда): номера через запятую, '
                            'диапазоны через дефис, или «Из выделения» в Компасе.'))
    first = [k - 1 for k in parse_atoms(calc.cda_atoms, n, [a.symbol for a in molecule.atoms])]  # «N1, H2–H4»
    second = [k for k in range(n) if k not in set(first)]
    if not first or not second:
        raise ValueError(tr('CDA: во фрагменте 2 нет атомов — фрагмент 1 не должен занимать всю молекулу.'))
    order = first + second
    title = molecule.title or molecule.formula
    complex_ = Molecule(title, tuple(molecule.atoms[k] for k in order))
    frag1 = Molecule(title + ' · 1', tuple(molecule.atoms[k] for k in first))
    frag2 = Molecule(title + ' · 2', tuple(molecule.atoms[k] for k in second))
    charge2 = calc.charge - calc.cda_charge
    for part, charge, mult, name in ((frag1, calc.cda_charge, calc.cda_mult1, '1'), (frag2, charge2, calc.cda_mult2, '2')):
        try:
            part.validate_state(charge, mult)
        except ValueError as exc:
            raise ValueError(tr(f'CDA, фрагмент {name} ({part.formula}, заряд {charge:+d}, мультиплетность {mult}): ')
                             + str(exc)) from None
    molecule.validate_state(calc.charge, calc.multiplicity)
    return {'fragments': (tuple(first), tuple(second)), 'order': tuple(order),
            'parts': [('complex', complex_, calc.charge, calc.multiplicity), ('frag1', frag1, calc.cda_charge, calc.cda_mult1),
                      ('frag2', frag2, charge2, calc.cda_mult2)]}
