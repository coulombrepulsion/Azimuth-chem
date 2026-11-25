"""The course of a geometry optimization: energy and gradient step by step, the convergence criteria.

§1 THEORY
    An optimization stops when the forces on the nuclei (minus the gradient of the energy) and the last step
    are small. ORCA tests the energy change, the RMS and the largest component of the gradient and of the
    step, Gaussian the largest and RMS force and displacement, xtb the energy change and the gradient
    norm. Each program prints the value and its threshold; a plot of log10(value) per step shows how the
    criteria fall and which one holds the run back. The energy relative to the last step, in kcal/mol, shows
    how much the geometry still changes the energy.
§2 ALGORITHM
    Energies: the steps of the output (Output.steps). ORCA: the text between two «GEOMETRY OPTIMIZATION
    CYCLE n» headers; «RMS gradient ... v» and «MAX gradient ... v» after the Cartesian gradient, and the
    table «Geometry convergence» (rows «name value tolerance YES|NO»: Energy change, RMS gradient, MAX
    gradient, RMS step, MAX step). Gaussian: the table «Item Value Threshold Converged?» of every step (rows
    Maximum Force, RMS Force, Maximum Displacement, RMS Displacement). xtb: «gnorm:» of every frame of
    xtbopt.log next to the output. Rows of a table are kept per step; a criterion missing in a step is None.
§3 APPLICATIONS
    modules/spectrum/views/convergence_view.py (the «Сходимость» tab of Spectrum).
§4 SPECIFICATION
    history(output, text, path=None) -> History | None (None without at least two steps or criteria)
    History: program, energies ((step, hartree) ...), criteria {name: [value | None per step]},
    thresholds {name: value}, converged {name: bool of the last step}, steps (count)
    relative_kcal(history) -> ((step, kcal/mol relative to the last energy) ...)
§5 PROCEDURES - below.
§6 NOTES
    ORCA prints two gradients per cycle: the Cartesian one («RMS gradient ... v» after the gradient) and the one
    in the internal coordinates of the optimizer (the table «Geometry convergence»); the tolerances are for the
    second, so the table is taken, the summary only for a cycle without it. Verified on the ORCA 6.0.1 optimization
    of water (tests/data/orca601/h2o_opt.out: every value of the four tables), on the ORCA 6.0 optimization of the
    cclib test data (gradient summaries, tests/data/orca_cclib/dvb_gopt_orca6.0.out) and on xtbopt.log of xtb 6.6.1
    (tests/data/xtb/dvb_opt). ASSUMPTION: the table of Gaussian «Converged?» follows the layout of Gaussian 16 as
    remembered (no Gaussian optimization with it in the test data); its test uses hand-written rows.
§7 TESTS
    tests/spectrum/test_convergence.py.
§8' ROBUSTNESS
    Non-finite numbers are skipped; nothing found gives None.
"""

from dataclasses import dataclass, field
from math import isfinite
from pathlib import Path
import re

from modules.spectrum.readers.results import NUMBER

HARTREE_KCAL = 627.5094740631
ORCA_ROWS = ('Energy change', 'RMS gradient', 'MAX gradient', 'RMS step', 'MAX step')
GAUSSIAN_ROWS = ('Maximum Force', 'RMS Force', 'Maximum Displacement', 'RMS Displacement')
TITLES = {
    'Energy change': 'Изменение энергии',
    'RMS gradient': 'Градиент (RMS)',
    'MAX gradient': 'Градиент (наибольший)',
    'RMS step': 'Шаг (RMS)',
    'MAX step': 'Шаг (наибольший)',
    'Maximum Force': 'Сила (наибольшая)',
    'RMS Force': 'Сила (RMS)',
    'Maximum Displacement': 'Смещение (наибольшее)',
    'RMS Displacement': 'Смещение (RMS)',
    'gnorm': 'Норма градиента',
}


def _number(text):
    value = float(text.replace('D', 'E').replace('d', 'e'))
    return value if isfinite(value) else None


@dataclass(frozen=True)
class History:
    program: str
    energies: tuple
    criteria: dict = field(default_factory=dict)
    thresholds: dict = field(default_factory=dict)
    converged: dict = field(default_factory=dict)

    @property
    def steps(self):
        lengths = [len(v) for v in self.criteria.values()] + [len(self.energies)]
        return max(lengths)


def _tables(blocks, names):
    """Per block: {name: (value, threshold, yes)} from rows «name value threshold YES|NO»."""
    pattern = re.compile(
        r'^\s*(' + '|'.join(n.replace(' ', r'\s+') for n in names) + r')\s+(' + NUMBER + r')\s+(' + NUMBER + r')\s+(YES|NO)\b',
        re.M,
    )
    found = []
    for block in blocks:
        rows = {}
        for m in pattern.finditer(block):
            name = re.sub(r'\s+', ' ', m[1])
            value, threshold = _number(m[2]), _number(m[3])
            if value is not None:
                rows[name] = (value, threshold, m[4] == 'YES')
        found.append(rows)
    return found


def _orca(text):
    headers = list(re.finditer(r'GEOMETRY OPTIMIZATION CYCLE\s+(\d+)', text))
    blocks = [text[h.end(): headers[i + 1].start() if i + 1 < len(headers) else len(text)] for i, h in enumerate(headers)]
    criteria = {}
    tables = _tables(blocks, ORCA_ROWS)
    for k, block in enumerate(blocks):
        # the table gives the gradient in the internal coordinates of the optimizer — the one its tolerances are for;
        # the summary «RMS gradient ... v» after the Cartesian gradient is used only for a cycle without the table
        for name, (value, _, _) in tables[k].items():
            criteria.setdefault(name, [None] * len(blocks))[k] = abs(value)
        for name in ('RMS gradient', 'MAX gradient'):
            values = re.findall(name + r'\s+\.\.\.\s+(' + NUMBER + ')', block)
            if values and name not in tables[k]:
                criteria.setdefault(name, [None] * len(blocks))[k] = _number(values[-1])
    return criteria, tables


def _gaussian(text):
    starts = [m.start() for m in re.finditer(r'Item\s+Value\s+Threshold\s+Converged\?', text)]
    blocks = [text[s: starts[i + 1] if i + 1 < len(starts) else len(text)] for i, s in enumerate(starts)]
    tables = _tables(blocks, GAUSSIAN_ROWS)
    criteria = {}
    for k, rows in enumerate(tables):
        for name, (value, _, _) in rows.items():
            criteria.setdefault(name, [None] * len(blocks))[k] = abs(value)
    return criteria, tables


def _xtb(path):
    if path is None:
        return {}
    log = Path(path).with_name('xtbopt.log')
    try:
        text = log.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return {}
    values = [_number(v) for v in re.findall(r'gnorm:\s*(' + NUMBER + ')', text)]
    return {'gnorm': values} if values else {}


def history(output, text, path=None):
    program = getattr(output, 'program', 'ORCA') or 'ORCA'
    energies = tuple((s.cycle, s.energy) for s in getattr(output, 'steps', ()) if s.energy is not None)
    tables = []
    if program.startswith('Gaussian'):
        criteria, tables = _gaussian(text)
    elif program.startswith('xtb'):
        criteria = _xtb(path)
    elif program.startswith(('Psi4', 'NWChem', 'Q-Chem', 'GAMESS', 'Firefly')):  # the energies of the steps only
        criteria = {}
    else:
        criteria, tables = _orca(text)
    criteria = {k: v for k, v in criteria.items() if any(x is not None for x in v)}
    if len(energies) < 2 and not criteria:
        return None
    last = next((rows for rows in reversed(tables) if rows), {})
    thresholds = {name: t for name, (_, t, _) in last.items() if t is not None}
    converged = {name: yes for name, (_, _, yes) in last.items()}
    return History(program, energies, criteria, thresholds, converged)


def relative_kcal(h):
    if not h.energies:
        return ()
    final = h.energies[-1][1]
    return tuple((step, (e - final) * HARTREE_KCAL) for step, e in h.energies)
