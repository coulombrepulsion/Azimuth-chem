"""Multiwfn: the charge transfer of an excited state between fragments (IFCT) and its transition matrix.

§1 PURPOSE The beta of docs/plans/ROADMAP.md, item 6: how much of the electron of an excitation moves from one part of
    the molecule to another — a local excitation or a charge transfer, between which fragments, and the atom / fragment
    transition matrix as a heat map (next to the hole and the electron of «Анализ возбуждений»).
§2 ALGORITHM IFCT: main menu 18 → 8 → 2 (the hole and the electron divided between the atoms by Hirshfeld — the Mulliken
    way is «incompatible with diffuse functions», as Multiwfn says) → the output with the excitations → the state → the
    number of fragments → the atoms of each («1,2,9», «3-8,10-14») → 0 (out of the function), 0, q. Printed: the shares
    of the fragments in the hole and the electron, the variation of their populations, the intrafragment redistribution,
    the electrons transferred between every pair and the net transfer, CT(%) and LE(%) intrinsic and apparent. The
    matrix: 18 → 2 → the output → the state → 0 (no symmetrization) → 1 (the atom matrix as the sum of the squares of
    the elements of the transition density matrix) → 4 (with the hydrogens) | −1, the fragments → 3 (to tmat.txt: «i j
    value») → 0, 0, q. Recorded on Multiwfn 2026.7.15 (tools/record_multiwfn_excitations.py, tests/data/multiwfn/exc_*):
    the TD-DFT of benzaldehyde of the user (ORCA 6, CAM-B3LYP/def2-SVPD), the fragments CHO (1, 2, 9) and the ring — S1
    (n→π*): the hole 85 % on CHO, CT 35 % intrinsic; S3 (π→π*): 0.32 e from the ring to CHO, CT 45 %.
§4 SPECIFICATION
    parse_atoms(text, count) -> [atom 1-based]; atoms_text(atoms) -> «1,2,9» with ranges; fragments(texts, count) ->
    [[atoms]] (one fragment: the rest is the second); ifct_answers(excited, state, fragments) -> tuple;
    matrix_answers(excited, state, fragments=None) -> tuple; parse_ifct(text) -> dict; read_tmat(text) -> np.ndarray;
    run_ifct(program, path, output, state, fragments, cores=1, step=None, timeout=1800) -> (dict, text);
    run_matrix(program, path, output, state, fragments=None, …) -> (np.ndarray, text).
§7 TESTS tests/spectrum/test_charge_transfer.py.
"""

import re

import numpy as np

from azimuth.i18n import tr
from modules.spectrum.wavefunction import multiwfn


def parse_atoms(text, count, symbols=None):
    """«1,2,9», «3-8, 10-14», «1 2 9» → the sorted atoms (1-based); also «O1, C2, H9», «C3–C8», «H» with the
    symbols of the molecule (azimuth/atom_labels.py); ValueError for a number outside 1…count or a wrong element."""
    from azimuth import atom_labels

    return atom_labels.parse(text, count, symbols)


def atoms_text(atoms):
    """[1, 2, 3, 5, 9, 10] → «1-3,5,9,10» (as Multiwfn reads it)."""
    atoms = sorted(set(atoms))
    parts, k = [], 0
    while k < len(atoms):
        j = k
        while j + 1 < len(atoms) and atoms[j + 1] == atoms[j] + 1:
            j += 1
        if j - k >= 2:  # a range from three atoms on («1,2,9» as recorded, «3-8»)
            parts.append(f'{atoms[k]}-{atoms[j]}')
        else:
            parts.extend(str(a) for a in atoms[k:j + 1])
        k = j + 1
    return ','.join(parts)


def fragments(texts, count, symbols=None):
    """The fragments typed (one per text); one fragment — the rest of the atoms is the second; overlaps refused."""
    found = [parse_atoms(t, count, symbols) for t in texts if t.strip()]
    if not found:
        raise ValueError(tr('Задайте хотя бы один фрагмент — номера его атомов.'))
    taken = [a for f in found for a in f]
    if len(taken) != len(set(taken)):
        raise ValueError(tr('Атом в двух фрагментах сразу — фрагменты не должны пересекаться.'))
    rest = [a for a in range(1, count + 1) if a not in set(taken)]
    if len(found) == 1:
        if not rest:
            raise ValueError(tr('Фрагмент — вся молекула: переносу заряда некуда идти.'))
        found.append(rest)
    return found


def ifct_answers(excited, state, parts):
    return ('18', '8', '2', excited, str(int(state)), str(len(parts)), *(atoms_text(p) for p in parts), '0', '0', 'q')


def matrix_answers(excited, state, parts=None):
    if parts:
        return ('18', '2', excited, str(int(state)), '0', '1', '-1', str(len(parts)), *(atoms_text(p) for p in parts),
                '3', '0', '0', 'q')
    return ('18', '2', excited, str(int(state)), '0', '1', '4', '3', '0', '0', 'q')


_SHARES = re.compile(r'^\s*(\d+)\s+Hole:\s*(-?\d+\.\d+)\s*%\s+Electron:\s*(-?\d+\.\d+)\s*%', re.M)
_VARIATION = re.compile(r'Variation of population number of fragment\s+(\d+):\s*(-?\d+\.\d+)')
_REDISTRIBUTION = re.compile(r'Intrafragment electron redistribution of fragment\s+(\d+):\s*(-?\d+\.\d+)')
_TRANSFER = re.compile(r'(\d+)\s*->\s*(\d+):\s*(-?\d+\.\d+)\s+(\d+)\s*<-\s*(\d+):\s*(-?\d+\.\d+)\s+Net\s+(\d+)\s*->\s*(\d+):'
                       r'\s*(-?\d+\.\d+)')
_PERCENT = {'ct': 'Intrinsic charge transfer percentage', 'le': 'Intrinsic local excitation percentage',
            'ct_apparent': 'Apparent charge transfer percentage', 'le_apparent': 'Apparent local excitation percentage'}


def parse_ifct(text):
    """{'hole': [%], 'electron': [%], 'variation': [e], 'redistribution': [e], 'transfer': {(i, j): e} (from i to j,
    1-based), 'net': {(i, j): e}, 'ct', 'le', 'ct_apparent', 'le_apparent' (%)} of the last IFCT printed; {} if none."""
    start = text.rfind('Contribution of each fragment to hole and electron')
    if start < 0:
        return {}
    part = text[start:]
    shares = _SHARES.findall(part)
    found = {'hole': [float(h) for _, h, _ in shares], 'electron': [float(e) for _, _, e in shares],
             'variation': [float(v) for _, v in _VARIATION.findall(part)],
             'redistribution': [float(v) for _, v in _REDISTRIBUTION.findall(part)], 'transfer': {}, 'net': {}}
    for i, j, there, i2, j2, back, ni, nj, net in _TRANSFER.findall(part):
        found['transfer'][(int(i), int(j))] = float(there)
        found['transfer'][(int(j2), int(i2))] = float(back)  # «i <- j»: from j to i
        found['net'][(int(ni), int(nj))] = float(net)
    for key, head in _PERCENT.items():
        match = re.search(re.escape(head) + r'[^:]*:\s*(-?\d+\.\d+)\s*%', part)
        if match:
            found[key] = float(match.group(1))
    return found


def read_tmat(text):
    """The matrix of tmat.txt («i j value» per line, 1-based) as an n × n array."""
    rows = [line.split() for line in text.splitlines() if len(line.split()) == 3]
    entries = [(int(i), int(j), float(v)) for i, j, v in rows]
    if not entries:
        raise ValueError(tr('Матрица перехода пуста.'))
    n = max(max(i, j) for i, j, _ in entries)
    matrix = np.zeros((n, n))
    for i, j, v in entries:
        matrix[i - 1, j - 1] = v
    return matrix


def run_ifct(program, path, output, state, parts, cores=1, step=None, timeout=1800):
    write, excited = multiwfn._with_output(path, output)
    text, _ = multiwfn._run(program, write, ifct_answers(excited, state, parts), cores, step, timeout)
    found = parse_ifct(text)
    if not found.get('hole'):
        raise ValueError(tr('Multiwfn не напечатал перенос заряда (IFCT). Конец его вывода:') + '\n' + multiwfn._tail(text))
    return found, text


def run_matrix(program, path, output, state, parts=None, cores=1, step=None, timeout=1800):
    write, excited = multiwfn._with_output(path, output)
    text, kept = multiwfn._run(program, write, matrix_answers(excited, state, parts), cores, step, timeout,
                               keep=('tmat.txt',))
    if 'tmat.txt' not in kept:
        raise ValueError(tr('Multiwfn не выгрузил матрицу перехода. Конец его вывода:') + '\n' + multiwfn._tail(text))
    return read_tmat(kept['tmat.txt']), text
