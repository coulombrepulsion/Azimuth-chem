"""The steps of the optimization of a crystal: each step a crystal of its own, the start as a ghost, the
shift of the atoms and of the cell — as the steps of a molecule.

§1 THEORY
    A relax / vc-relax of Quantum ESPRESSO or a GEO_OPT / CELL_OPT of CP2K moves the atoms in the cell and (with the
    cell) the cell itself. Each step is the crystal of group P 1 of that step (its cell, its atoms in the order of the
    program). An atom that crossed a face of the cell is the same atom moved a little, not across the cell: the image
    of the starting atom nearest to it counts (minimum image, in the fractions of the step). The shift of an atom is the
    difference of the Cartesian positions (each in the cell of its own step — a cell that grew moves the atoms with it,
    as on the screen); the drift of the whole content (the origin of a periodic cell is free) is taken out by the mean
    shift. RMSD = √(mean |shift|²); the largest shift and its atom; the change of the cell — a, b, c (Å), α, β, γ (°),
    the volume (%).
§2 ALGORITHM
    make_steps(raw, title): raw — [(energy hartree | None, cell rows Å, ((symbol, fractions), …))] of the readers
    (qe.steps, cp2k.steps) → CrystalStep(cycle, energy, geometry — the atoms of the cell wrapped into it as Compass
    shows them, crystal). ghost(first, step) — the starting atoms at the images nearest to those of the step;
    difference(first, step) → Difference; describe(difference) — the line under the steps.
§4 SPECIFICATION
    CrystalStep(OptimizationStep) + crystal; crystal_of(cell_rows, atoms, title) -> cr.Crystal (P 1);
    Difference(rmsd, largest, atom, cell: (Δa, Δb, Δc, Δα, Δβ, Δγ), volume_percent); the atoms of two steps in the same
    order and number (else ValueError).
§7 TESTS tests/compass/test_crystal_steps.py — the steps of Si (pw.x 7.6 vc-relax, CP2K CELL_OPT), an atom across a
    face, a drift of the whole, a known shift.
"""

from dataclasses import dataclass
from math import acos, degrees, sqrt

from azimuth.core import Atom, Molecule
from modules.compass.chemistry import crystal as cr
from modules.spectrum.readers.results import OptimizationStep


@dataclass(frozen=True)
class CrystalStep(OptimizationStep):
    crystal: cr.Crystal | None = None  # the cell computed, group P 1 (a supercell, a primitive cell, as computed)
    adopted: cr.Crystal | None = None  # what «Взять» gives: the cell of the file, its group when the step keeps it
    note: str = ''  # why the group of the file is not kept (empty when it is)


@dataclass(frozen=True)
class Difference:
    rmsd: float
    largest: float
    atom: int  # index of the atom that moved most
    cell: tuple  # Δa, Δb, Δc (Å), Δα, Δβ, Δγ (°)
    volume_percent: float


def _length(v):
    return sqrt(sum(x * x for x in v))


def _angle(u, v):
    return degrees(acos(max(-1.0, min(1.0, sum(a * b for a, b in zip(u, v)) / (_length(u) * _length(v))))))


def crystal_of(rows, atoms, title='шаг'):
    a, b, c = (_length(v) for v in rows)
    cell = cr.Cell(a, b, c, _angle(rows[1], rows[2]), _angle(rows[0], rows[2]), _angle(rows[0], rows[1]))
    sites = tuple(cr.Site(f'{s}{k + 1}', s, *(x - int(x // 1) if abs(x - round(x)) > 1e-9 else 0.0 for x in f))
                  for k, (s, f) in enumerate(atoms))
    return cr.Crystal(title, cell, sites, (cr.operation('x, y, z'),), 'P 1')


def _content(crystal):
    """The atoms of the cell where Compass shows them: the sites wrapped into [0, 1), in their order."""
    return Molecule(crystal.title, tuple(Atom(s.symbol, *crystal.cell.cartesian((s.x, s.y, s.z)))
                                         for s in crystal.sites))


def make_steps(raw, title='кристалл', original=None, repeat=(1, 1, 1), primitive=False):
    """The steps; with original (the crystal of the file), repeat (the supercell computed) and primitive (the primitive
    cell computed) each step also gets what «Взять» makes of it: the supercell folded back into one cell, then the group
    of the file when its operations still hold (adopted; note — why not)."""
    found = []
    for k, (energy, rows, atoms) in enumerate(raw):
        crystal = crystal_of(rows, atoms, f'{title} · шаг {k}')
        adopted, note = (crystal, '') if original is None else back_to_the_file(crystal, original, repeat, primitive)
        found.append(CrystalStep(k, energy, _content(crystal), crystal=crystal, adopted=adopted, note=note))
    return tuple(found)


def _near(f, g, tol):
    return all(abs((f[i] - g[i]) - round(f[i] - g[i])) < tol for i in range(3))


def fold(crystal, n, tol=2e-3):
    """A supercell n1 × n2 × n3 (group P 1) back into one cell: the edges divided by n, the atoms of the first sub-cell
    (each atom of the supercell at n·f mod 1 must find its copies — the translation kept), else None."""
    n = tuple(int(k) for k in n)
    if n == (1, 1, 1):
        return crystal
    cell = crystal.cell
    small = cr.Cell(cell.a / n[0], cell.b / n[1], cell.c / n[2], cell.alpha, cell.beta, cell.gamma)
    folded = [(s.symbol, tuple((v * k) % 1.0 for v, k in zip((s.x, s.y, s.z), n))) for s in crystal.sites]
    kept = []
    for symbol, f in folded:
        if not any(symbol == t and _near(f, g, tol) for t, g in kept):
            kept.append((symbol, f))
    if len(kept) * n[0] * n[1] * n[2] != len(folded):
        return None
    return cr.Crystal(crystal.title, small, tuple(cr.Site(f'{t}{k + 1}', t, *g) for k, (t, g) in enumerate(kept)),
                      (cr.operation('x, y, z'),), 'P 1')


def _metric(cell):
    v = cell.vectors()
    return [[sum(v[i][k] * v[j][k] for k in range(3)) for j in range(3)] for i in range(3)]


def symmetrize(crystal, original, tol=2e-3):
    """The crystal of one cell of the file (group P 1, its atoms) in the group of the file — when every operation of the
    file maps the lattice (its metric) and the atoms onto themselves (within tol of the fractions); the asymmetric unit:
    for each site of the file the atom of its element nearest to it, its label, occupancy and the rest kept. None when
    an operation no longer holds."""
    from dataclasses import replace

    atoms = [(s.symbol, (s.x, s.y, s.z)) for s in crystal.sites]
    if len(atoms) != len(cr.unit_cell(original)):
        return None
    g = _metric(crystal.cell)
    scale = max(abs(x) for row in g for x in row)
    for rows, shifts in original.operations:
        turned = [[sum(rows[k][i] * g[k][l] * rows[l][j] for k in range(3) for l in range(3)) for j in range(3)]
                  for i in range(3)]
        if any(abs(turned[i][j] - g[i][j]) > 1e-3 * scale for i in range(3) for j in range(3)):
            return None
        for symbol, f in atoms:
            image = cr._apply((rows, shifts), f)
            if not any(symbol == t and _near(image, h, tol) for t, h in atoms):
                return None
    sites = []
    for site in original.sites:
        own = [h for t, h in atoms if t == site.symbol]
        if not own:
            return None
        best = min(own, key=lambda h: sum(((h[i] - v) - round(h[i] - v)) ** 2
                                          for i, v in enumerate((site.x, site.y, site.z))))
        start = (site.x, site.y, site.z)
        sites.append(replace(site, **{k: start[i] + ((best[i] - start[i]) - round(best[i] - start[i]))
                                      for i, k in enumerate('xyz')}))
    return replace(original, cell=crystal.cell, sites=tuple(sites))


def back_to_the_file(crystal, original, repeat=(1, 1, 1), primitive=False):
    """(the crystal «Взять» gives, why its group is P 1 — '' when the group of the file is kept)."""
    from azimuth.i18n import tr

    if primitive:
        return crystal, tr('считалась примитивная ячейка — шаг берётся в группе P 1')
    one = fold(crystal, repeat)
    if one is None:
        return crystal, tr('атомы суперячейки сдвинулись неодинаково — шаг берётся суперячейкой в группе P 1')
    kept = symmetrize(one, original)
    if kept is None:
        return one, tr('симметрия файла при оптимизации нарушилась — шаг берётся в группе P 1')
    return kept, ''


def _images(first, step):
    """For each atom: the fractions of the starting atom at the image nearest to the atom of the step."""
    if [s.symbol for s in first.sites] != [s.symbol for s in step.sites]:
        raise ValueError('the steps have other atoms')
    out = []
    for a, b in zip(first.sites, step.sites):
        f = (a.x, a.y, a.z)
        g = (b.x, b.y, b.z)
        out.append(tuple(f[i] + round(g[i] - f[i]) for i in range(3)))
    return out


def ghost(first, step):
    """The starting atoms (in the cell of the start) at the images nearest to the atoms of the step."""
    return Molecule('', tuple(Atom(s.symbol, *first.cell.cartesian(f))
                              for s, f in zip(first.sites, _images(first, step))))


def difference(first, step):
    starts = [first.cell.cartesian(f) for f in _images(first, step)]
    ends = [step.cell.cartesian((s.x, s.y, s.z)) for s in step.sites]
    shifts = [tuple(e[i] - s[i] for i in range(3)) for s, e in zip(starts, ends)]
    n = len(shifts)
    mean = tuple(sum(v[i] for v in shifts) / n for i in range(3)) if n else (0.0, 0.0, 0.0)
    sizes = [_length(tuple(v[i] - mean[i] for i in range(3))) for v in shifts]
    k = max(range(n), key=sizes.__getitem__) if n else 0
    one, two = first.cell, step.cell
    cell = (two.a - one.a, two.b - one.b, two.c - one.c, two.alpha - one.alpha, two.beta - one.beta,
            two.gamma - one.gamma)
    volume = 100.0 * (two.volume() / one.volume() - 1.0)
    return Difference(sqrt(sum(x * x for x in sizes) / n) if n else 0.0, sizes[k] if n else 0.0, k, cell, volume)


def describe(d, step):
    """The line under the steps: the shift of the atoms, and of the cell when it changed."""
    from azimuth.i18n import tr

    atom = step.sites[d.atom].label if step.sites else ''
    text = tr('От начальной: RMSD {} Å · наибольший сдвиг {} Å ({})').format(f'{d.rmsd:.3f}', f'{d.largest:.3f}', atom)
    if max(abs(x) for x in d.cell) > 1e-4 or abs(d.volume_percent) > 1e-3:
        text += ' · ' + tr('ячейка: Δa {}, Δb {}, Δc {} Å, ΔV {} %').format(
            *(f'{x:+.3f}' for x in d.cell[:3]), f'{d.volume_percent:+.2f}')
        if max(abs(x) for x in d.cell[3:]) > 0.01:
            text += ' · ' + tr('Δα {}, Δβ {}, Δγ {}°').format(*(f'{x:+.2f}' for x in d.cell[3:]))
    return text


# -- the steps of a run kept in the project of a crystal -----------------------------------------------------
# The runs of a crystal project are read back when the project opens. A run records its folder, its program and its task
# in the project (crystal_projects.record_run); its supercell and
# its cell (primitive or of the file) are not recorded, so they are read back from its first step: each edge of the
# cell computed is a whole number of edges of the cell of the file (or of its primitive cell).
def guess_computed(original, rows, tol=0.02):
    """(repeat, primitive) of a run whose start had the cell rows (Å), or None when no cell of the file fits."""
    import numpy as np

    lengths = [float(np.linalg.norm(v)) for v in rows]
    for primitive in (False, True):
        cell = (cr.primitive(original) if primitive else original).cell
        repeat = []
        for length, edge in zip(lengths, (cell.a, cell.b, cell.c)):
            n = round(length / edge)
            if n < 1 or abs(length - n * edge) > tol * length:
                break
            repeat.append(int(n))
        else:
            return tuple(repeat), primitive
    return None


def run_steps(folder, program, original, title):
    """The steps of the optimization of a run in folder (CP2K: its files; Quantum ESPRESSO: pw.out), () without them."""
    from pathlib import Path

    from modules.spectrum.readers import cp2k, qe

    folder = Path(folder)
    if program == 'cp2k':
        raw = cp2k.steps(folder)
    else:
        output = folder / 'pw.out'
        if not output.is_file():
            return ()
        text = output.read_text(encoding='utf-8', errors='replace')
        raw = qe.steps((qe.runs(text) or [text])[0])
    if len(raw) < 2:
        return ()
    computed = guess_computed(original, raw[0][1]) if original is not None else None
    if computed is None:
        return make_steps(raw, title)
    return make_steps(raw, title, original, *computed)


def project_steps(manifest, original, title):
    """(steps, the folder of the run) of the last run of the project of a crystal that has steps; ((), None) else."""
    from pathlib import Path

    from azimuth import crystal_projects

    manifest = Path(manifest)
    for run in reversed(crystal_projects.info(manifest).get('runs') or []):
        folder = manifest.parent / str(run.get('folder', ''))
        if not folder.is_dir():
            continue
        try:
            steps = run_steps(folder, run.get('program', 'qe'), original, title)
        except (OSError, ValueError, IndexError):
            continue
        if steps:
            return steps, folder
    return (), None
