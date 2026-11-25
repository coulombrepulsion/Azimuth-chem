"""Multiwfn: the Hirshfeld charges and the charges and spin populations of the AIM basins.

§1 PURPOSE The beta of docs/plans/ROADMAP.md (items 2 and 3, «потом»): the charges of Bader's atoms in molecules (the
    basins of ρ) and the Hirshfeld charges for any file of orbitals — Gaussian (fchk), Molden of ORCA, xtb, other
    programs — not only for ORCA, which prints Hirshfeld itself; and for an open shell the spin populations of the AIM
    atoms.
§2 ALGORITHM Hirshfeld: main menu 7 → 1 (Hirshfeld atomic charge) → 1 (the built-in free-atom densities) → «n» (no .chg
    file); the charges of «Final atomic charges:» (normalized to the number of electrons by Multiwfn). AIM: 7 → 14 of
    Multiwfn 2026.7.15 only refers to the basin module (recorded), so: 17 (basin analysis) → 1 (generate the basins) → 1
    (of ρ) → 2 (the medium grid, 0.1 bohr) → 7 (integrate in the AIM basins with the mixed grids) → 2 (with the exact
    refinement of the boundary — the most exact) → 1 (ρ: the populations); for an open shell again 7 → 2 → 5 (the spin
    density: the spin populations); −10 back to the main menu (a «q» in the basin menu makes Multiwfn fall), «q». Each
    integration prints «Attractor N corresponds to atom M» and the «Total result:» table by basin; the basins are summed
    by atom (a non-nuclear attractor — one that corresponds to no atom — is left out and said). The charge of atom i is
    Z_eff,i + core_i − N_i: Z_eff the nuclear charge of the file (smaller with an ECP), core_i the core electrons
    Multiwfn puts back from its EDF library for such atoms («Core electrons: 28» of the output) — they are integrated
    with the rest (recorded: MoOCl4, Mo 28 and Cl 10 each). Recorded on Multiwfn 2026.7.15 (Homebrew, macOS):
    tests/data/multiwfn/pop_*.txt (tools/record_multiwfn_populations.py)
    — water of Gaussian 16 (MP2), the UKS cation of divinylbenzene (ORCA, Molden), MoOCl4 with an ECP.
§4 SPECIFICATION
    HIRSHFELD; HIRSHFELD_SPIN; parse_fuzzy(text) -> tuple | None; run_hirshfeld_spins(…) -> (spins, text);
    basin_answers(spin=False) -> tuple; parse_hirshfeld(text) -> tuple | None;
    core_electrons(text, count) -> np.ndarray; parse_basins(text, count) -> ([np.ndarray of count values per
    integration], left_out: [float per integration]);
    run_hirshfeld(program, path, cores=1, step=None, timeout=600) -> (charges, text);
    run_basins(program, path, nuclear, spin=False, cores=1, step=None, timeout=3600) -> (charges, spins | None, text).
§7 TESTS tests/spectrum/test_multiwfn_populations.py.
"""

import re

import numpy as np

from azimuth.i18n import tr
from modules.spectrum.wavefunction import multiwfn

HIRSHFELD = ('7', '1', '1', 'n', '0', 'q')
# the spin density integrated in the Hirshfeld atoms of the fuzzy space: 15 → −1 (partition) → 3 (Hirshfeld of
# the built-in atomic densities; 2 needs .wfn files of the atoms) → 1 (integrate a function) → 5 (the spin density)
HIRSHFELD_SPIN = ('15', '-1', '3', '1', '5', '0', 'q')
_SPACE_ROW = re.compile(r'^\s*(\d+)\(\s*[A-Za-z]{1,3}\s*\)\s+(-?\d+\.\d+)\s+-?\d+\.\d+\s+-?\d+\.\d+\s*$')
_ATTRACTOR = re.compile(r'Attractor\s+(\d+)\s+corresponds to atom\s+(\d+)')
_CORE = re.compile(r'^\s*[A-Za-z]{1,3}\(\s*(\d+)\)\s+Core electrons:\s*(\d+)', re.M)
_TOTAL_ROW = re.compile(r'^\s*(\d+)\s+(-?\d+\.\d+)\s+\d+\.\d+\s+\d+\.\d+\s*$')  # «basin integral volumes»
# the same table by atom («atom (C ) basin integral volumes»), as Multiwfn printed it for the spin density
_ATOM_ROW = re.compile(r'^\s*(\d+)\s*\(\s*[A-Za-z]{1,3}\s*\)\s+\d+\s+(-?\d+\.\d+)\s+\d+\.\d+\s+\d+\.\d+\s*$')


def basin_answers(spin=False):
    answers = ['17', '1', '1', '2', '7', '2', '1']
    if spin:
        answers += ['7', '2', '5']
    return tuple(answers + ['-10', 'q'])


def parse_hirshfeld(text):
    """The Hirshfeld charges of «Final atomic charges:» after the citation of the method; None when there are none."""
    lines = text.replace('\r', '').split('\n')
    start = next((k for k, line in enumerate(lines) if 'Citation of Hirshfeld method' in line), None)
    if start is None:
        return None
    values, _ = multiwfn._final(lines, start)
    return values or None


def parse_fuzzy(text):
    """The values of the table «Atomic space  Value  % of sum …» of the integral of a function in the fuzzy atomic
    spaces (the last one in text); None when there is none."""
    lines = text.replace('\r', '').split('\n')
    starts = [k for k, line in enumerate(lines) if line.strip().startswith('Atomic space') and 'Value' in line]
    if not starts:
        return None
    values = []
    for line in lines[starts[-1] + 1:]:
        row = _SPACE_ROW.match(line)
        if not row:
            break
        values.append(float(row.group(2)))
    return tuple(values) or None


def run_hirshfeld_spins(program, path, cores=1, step=None, timeout=600):
    text, _ = multiwfn._run(program, path, HIRSHFELD_SPIN, cores, step, timeout)
    spins = parse_fuzzy(text)
    if not spins:
        raise ValueError(tr('Multiwfn не проинтегрировал спиновую плотность. Конец его вывода:') + '\n'
                         + multiwfn._tail(text))
    return spins, text


def parse_basins(text, count):
    """For every integration of the AIM basins in text (in their order): the integral by atom (count values), and the
    part of it in the basins of no atom (non-nuclear attractors)."""
    lines = text.replace('\r', '').split('\n')
    results, left_out = [], []
    owner = {}
    k = 0
    while k < len(lines):
        found = _ATTRACTOR.search(lines[k])
        if found:
            owner[int(found.group(1))] = int(found.group(2))
        if lines[k].strip().startswith('Total result:'):
            values, other = np.zeros(count), 0.0
            j = k + 1
            while j < len(lines) and not (_TOTAL_ROW.match(lines[j]) or _ATOM_ROW.match(lines[j])):
                j += 1  # the head of the table
            by_atom = j < len(lines) and bool(_ATOM_ROW.match(lines[j]))
            while j < len(lines):
                row = (_ATOM_ROW if by_atom else _TOTAL_ROW).match(lines[j])
                if not row:
                    break
                atom = int(row.group(1)) if by_atom else owner.get(int(row.group(1)))
                if atom is not None and 1 <= atom <= count:
                    values[atom - 1] += float(row.group(2))
                else:
                    other += float(row.group(2))
                j += 1
            results.append(values)
            left_out.append(other)
            k = j  # the next integration may not print the attractors again: they keep their atoms
            continue
        k += 1
    return results, left_out


def core_electrons(text, count):
    """The core electrons Multiwfn put back as the EDF densities of its library for the atoms with an ECP («Mo(    1)
    Core electrons: 28»): they are in the basin populations, so the charge is (Z_eff + core) − N."""
    core = np.zeros(count)
    for atom, number in _CORE.findall(text):
        if 1 <= int(atom) <= count:
            core[int(atom) - 1] = float(number)
    return core


def run_hirshfeld(program, path, cores=1, step=None, timeout=600):
    text, _ = multiwfn._run(program, path, HIRSHFELD, cores, step, timeout)
    charges = parse_hirshfeld(text)
    if not charges:
        raise ValueError(tr('Multiwfn не напечатал зарядов Хиршфельда. Конец его вывода:') + '\n' + multiwfn._tail(text))
    return charges, text


def run_basins(program, path, nuclear, spin=False, cores=1, step=None, timeout=3600):
    """The AIM charges (Z_eff − N by atom) and, for spin=True, the spin populations of the basins."""
    nuclear = np.asarray(nuclear, dtype=float)
    text, _ = multiwfn._run(program, path, basin_answers(spin), cores, step, timeout)
    results, left_out = parse_basins(text, len(nuclear))
    if not results or (spin and len(results) < 2):
        raise ValueError(tr('Multiwfn не проинтегрировал бассейны AIM. Конец его вывода:') + '\n' + multiwfn._tail(text))
    if abs(left_out[0]) > 0.01:
        raise ValueError(tr(f'В бассейнах без ядра (ненуклеарные аттракторы) {left_out[0]:.3f} e — заряды атомов AIM '
                            'не определены однозначно.'))
    charges = tuple(float(v) for v in nuclear + core_electrons(text, len(nuclear)) - results[0])
    spins = tuple(float(v) for v in results[1]) if spin else None
    return charges, spins, text
