"""Natural transition orbitals of an ORCA TD-DFT calculation.

§1 THEORY
    The transition density of an excited state, written in occupied × virtual orbitals, is split by its singular value
    decomposition into pairs: a «hole» orbital (where the electron leaves) and a «particle» orbital (where it goes),
    with weights n that add up to about 1 (Martin, J. Chem. Phys. 118, 4775 (2003)). One pair with n ≈ 1 is the whole
    excitation in one picture — far easier to read than the list of canonical orbital pairs of TD-DFT.
§2 ALGORITHM
    ORCA computes them with «%tddft DoNTO true end» (all the states when NTOStates is empty) and prints, per state,
    «NATURAL TRANSITION ORBITALS FOR STATE n», the file «<name>.s<n>.nto», «E= … au … eV» and the pairs «4a -> 5a : n=
    0.998» (a — α, b — β; the numbers are ORCA's, from 0) of weight above NTOThresh. The pairs are read from the output;
    the orbitals from the .nto file: copied to «<name>_s<n>_nto.gbw» and turned into Molden by orca_2mkl (as every
    .gbw: modules/sextant/runner.molden_from_gbw), then read like the orbitals of a result. In that file the hole NTO
    of a pair stands at the number of its «from» and the particle at the number of its «to».
§3 APPLICATIONS
    modules/spectrum/views/spectra_view.UVVisPanel (the pairs of the chosen state, «NTO на модели»),
    modules/spectrum/workspace.py.
§4 SPECIFICATION
    NtoPair(hole: int, particle: int, spin 'a' | 'b', weight: float); NtoState(state: int, energy_ev: float | None,
    file: str, pairs: tuple of NtoPair, the heaviest first).
    read_ntos(text) -> {state: NtoState}; describe(state, count=2) -> str ('4a → 5a · 0.998; …');
    nto_gbw(output_path, entry) -> Path (the .nto next to the output); nto_orbitals(output_path, entry, orca=None) ->
    OrbitalSet; orbital_index(orbital_set, spin, number) -> int (the row of the orbital in the set).
§6 NOTES
    The format of the printout is that of real ORCA outputs (TD-DFT/TDA of an open-shell molecule, «322a -> 323a :
    n= 0.00291785», «Natural Transition Orbitals were saved in OrcaRun.s1.nto», zenodo.org/records/15488689) and of the
    ORCA 6.0 manual (DoNTO, NTOStates, NTOThresh; «TD-DFT-Example-6.s1.nto»). The .nto file is a .gbw with
    the NTOs in place of the orbitals: orca_2mkl reads it under a .gbw name (checked with ORCA 6.0.1,
    tools/check_programs.py --beta).
§7 TESTS
    tests/spectrum/test_nto.py.
"""

from dataclasses import dataclass
from pathlib import Path
import re
import shutil

from azimuth.i18n import tr

NUMBER = r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?'
HEAD = re.compile(r'NATURAL TRANSITION ORBITALS FOR STATE\s+(\d+)')
SAVED = re.compile(r'Natural Transition Orbitals were saved in\s+(\S+)')
ENERGY = re.compile(rf'^\s*E=\s*{NUMBER}\s*au\s+({NUMBER})\s*eV', re.M)
PAIR = re.compile(rf'^\s*(\d+)([ab])\s*->\s*(\d+)([ab])\s*:\s*n=\s*({NUMBER})\s*$', re.M)


@dataclass(frozen=True)
class NtoPair:
    hole: int
    particle: int
    spin: str
    weight: float


@dataclass(frozen=True)
class NtoState:
    state: int
    energy_ev: float | None
    file: str
    pairs: tuple


def read_ntos(text):
    """{state: NtoState} of the NTO blocks of an ORCA output ({} without them); the last block of a state wins."""
    found = {}
    heads = list(HEAD.finditer(text or ''))
    for k, head in enumerate(heads):
        end = heads[k + 1].start() if k + 1 < len(heads) else len(text)
        part = text[head.end():end]
        energy = ENERGY.search(part)
        saved = SAVED.search(part)
        pairs = _consecutive(part, energy.end()) if energy is not None else []
        state = int(head.group(1))
        found[state] = NtoState(state, float(energy.group(1)) if energy else None,
                                Path(saved.group(1)).name if saved else '',
                                tuple(sorted(pairs, key=lambda p: -p.weight)))
    return found


def _consecutive(part, start):
    """The pair lines right after the energy line (blank lines between them allowed)."""
    pairs = []
    newline = part.find('\n', start)  # the rest of the energy line («15304.8 cm**-1») is not a pair
    for line in part[newline + 1 if newline >= 0 else len(part):].splitlines():
        if not line.strip():
            if pairs:
                break
            continue
        m = PAIR.match(line)
        if m is None:
            break
        pairs.append(NtoPair(int(m.group(1)), int(m.group(3)), m.group(2), float(m.group(5))))
    return pairs


def describe(entry, count=2):
    """'4a → 5a · 0.998; 3a → 6a · 0.002' — the heaviest pairs of a state."""
    if entry is None or not entry.pairs:
        return ''
    return '; '.join(f'{p.hole}{p.spin} → {p.particle}{p.spin} · {p.weight:.3f}' for p in entry.pairs[:count])


def nto_gbw(output_path, entry):
    """The .nto file of the state next to the output: the name ORCA printed, else «<name>.s<n>.nto»."""
    output = Path(output_path)
    name = entry.file or f'{output.stem}.s{entry.state}.nto'
    return output.with_name(name)


def nto_orbitals(output_path, entry, orca=None):
    """The NTOs of the state as an OrbitalSet (orca_2mkl through a .gbw copy); ValueError with what is missing."""
    from modules.sextant.runner import molden_from_gbw
    from modules.spectrum.readers.orbital_files import read_orbitals

    source = nto_gbw(output_path, entry)
    if not source.is_file():
        raise ValueError(tr(f'Нет файла NTO {source.name} рядом с выводом — нужен расчёт TD-DFT с «NTO» (ORCA DoNTO).'))
    copy = source.with_name(f'{Path(output_path).stem}_s{entry.state}_nto.gbw')
    if not copy.is_file() or copy.stat().st_mtime < source.stat().st_mtime:
        shutil.copyfile(source, copy)
    molden = molden_from_gbw(copy, orca)
    return read_orbitals(molden.read_text(encoding='utf-8', errors='replace'))


def orbital_index(orbital_set, spin, number):
    """The row of ORCA's orbital «<number><spin>» in the set: α orbitals first, then β, each from 0."""
    wanted = 'alpha' if spin == 'a' else 'beta'
    rows = [k for k, o in enumerate(orbital_set.orbitals) if (o.spin or 'alpha') == wanted]
    if not 0 <= number < len(rows):
        name = f'{number}{spin}'
        raise ValueError(tr(f'В файле NTO нет орбитали {name}.'))
    return rows[number]
