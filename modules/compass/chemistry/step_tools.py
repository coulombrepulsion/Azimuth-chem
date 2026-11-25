"""The steps of a calculation and its normal modes as data — «Job tools» of Chemcraft for Compass.

§1 PURPOSE
    The menu «Расчёт» of Compass: the steps of an optimization, a scan or an IRC as one XYZ file
    and as a table of coordinates; a distance, an angle, a dihedral — or the angle between two vectors or planes of
    «Векторы и плоскости» — followed along the steps; the normal modes in which the selected atoms move most.
§2 ALGORITHM
    steps_xyz: one frame a step with a geometry, the comment «шаг n · E = … Eh». coordinate_rows: a row an atom of a
    step (step, atom, symbol, x, y, z). parameter_series: core.coordinate_value of the atoms (2 — a bond, 3 — an angle,
    4 — a dihedral) at every step with a geometry. guide_series: guides.angle of two guides at every step (the guides
    are made of atoms: they follow them). involvement(modes, atoms): the share of the selected atoms in the motion of
    a mode, Σ_sel |d_i|² / Σ_all |d_i|² of its Cartesian displacements (the vectors as printed by the program: for a
    light atom the shares are the larger, as one sees on the screen), the modes in descending order of the share.
§4 SPECIFICATION
    KINDS {2: 'B', 3: 'A', 4: 'D'}; steps_xyz(steps) -> str; coordinate_rows(steps) -> [(n, i, symbol, x, y, z)];
    parameter_series(steps, atoms) -> [(n, value, energy | None)]; guide_series(steps, a, b) -> [(n, angle, energy)];
    involvement(modes, atoms) -> [(index, frequency, share)]. Steps: objects with .cycle, .energy, .geometry; modes:
    with .index, .frequency, .vectors. ValueError for a wrong number of atoms or no steps with a geometry.
§7 TESTS
    tests/compass/test_step_tools.py.
"""

from azimuth.core import coordinate_value

KINDS = {2: 'B', 3: 'A', 4: 'D'}


def _with_geometry(steps):
    found = [s for s in steps if getattr(s, 'geometry', None) is not None and s.geometry.atoms]
    if not found:
        raise ValueError('В шагах нет геометрий.')
    return found


def steps_xyz(steps):
    frames = []
    for s in _with_geometry(steps):
        energy = '' if s.energy is None else f' · E = {s.energy:.10f} Eh'
        body = s.geometry.xyz().split('\n', 2)[2] if s.geometry.xyz().count('\n') >= 2 else ''
        frames.append(f'{len(s.geometry.atoms)}\nшаг {s.cycle}{energy}\n{body.rstrip()}\n')
    return ''.join(frames)


def coordinate_rows(steps):
    return [(s.cycle, i + 1, a.symbol, *a.position) for s in _with_geometry(steps) for i, a in enumerate(s.geometry.atoms)]


def parameter_series(steps, atoms):
    atoms = tuple(atoms)
    if len(atoms) not in KINDS or len(set(atoms)) != len(atoms):
        raise ValueError('Выделите 2, 3 или 4 разных атома: длина, угол или двугранный угол.')
    out = []
    for s in _with_geometry(steps):
        if max(atoms) >= len(s.geometry.atoms):
            raise ValueError('В шагах меньше атомов, чем номер выделенного.')
        out.append((s.cycle, coordinate_value(s.geometry, KINDS[len(atoms)], atoms), s.energy))
    return out


def guide_series(steps, first, second):
    from modules.compass.chemistry import guides

    return [(s.cycle, guides.angle(first, second, s.geometry), s.energy) for s in _with_geometry(steps)]


def involvement(modes, atoms):
    chosen = set(atoms)
    if not chosen:
        raise ValueError('Выделите атомы.')
    out = []
    for m in modes:
        vectors = getattr(m, 'vectors', ()) or ()
        squares = [sum(c * c for c in v) for v in vectors]
        total = sum(squares)
        if not total or max(chosen) >= len(squares):
            continue
        out.append((m.index, m.frequency, sum(squares[i] for i in chosen) / total))
    return sorted(out, key=lambda row: -row[2])
