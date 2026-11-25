"""Tables of an analysis written into the folder of the calculation: the extrema of a field on a grid, the
ESP on the molecular surface, the critical points of the density by their kinds.

§1 PURPOSE
    A surface on the model shows a field; the numbers behind it — where it is largest or smallest and how much — go to
    a CSV file next to the file of the orbitals, for a report or a spreadsheet: «<name>_<field>_extrema.csv»,
    «<name>_esp_extrema.csv» and «<name>_esp_summary.csv», «<name>_qtaim_nuclei.csv», «…_bonds.csv», «…_rings.csv»,
    «…_cages.csv».
§2 ALGORITHM
    grid_extrema: a grid node is a maximum when its value is not below any of its 26 neighbours and above FLOOR of the
    largest |value| (a minimum likewise); the edges of the grid are not extrema; the strongest LIMIT of each kind; for
    every one the nearest atom and the distance to it. CSV in UTF-8 with a BOM (so that spreadsheets read the Cyrillic
    headers); in the subfolder «Анализ», by default «;» and the decimal comma (style 'ru'), or «,» and the point
    ('intl') — the preference «Таблицы CSV» of the menu of the surfaces.
§4 SPECIFICATION
    grid_extrema(cube, mode='max' | 'min' | 'both', limit=LIMIT, floor=FLOOR, below=None) -> [dict kind ('max' | 'min'),
    value,
        position (Å), atom (0-based), distance (Å)]. write_csv(path, header, rows) -> Path; extrema_table(extrema,
    symbols, unit='') -> (header, rows); esp_tables(esp, symbols) -> {'extrema': (header, rows), 'summary': (header,
    rows)} (esp: multiwfn.run_esp); cp_tables(topology, symbols) -> {'nuclei' | 'bonds' | 'rings' | 'cages': (header,
    rows)} (density.Topology); write_tables(folder, base, tables: {suffix: (header, rows)}, chosen=None) -> [Path] (in
    folder/ANALYSIS); analysis_folder(folder) -> Path; save_output(wavefunction, name, text) -> Path | None;
    read_csv(path) -> (header, rows); style ∈ STYLES ('ru' | 'intl') or a code «<separator><decimal>» (';.', '\t,',
    '\t.'); style_parts(style) -> (separator, decimal); style_code(separator, decimal) -> style; valid_style(saved) ->
    style. map_extrema(values (n1, n2), points (n1, n2, 3), limit=20) -> [dict kind, value, position, ij]: not below
    (above)
        its eight neighbours; line_extrema(x, values, points) -> [dict kind, value, position, x]: not below (above)
        both neighbours.
    ESP_ROWS — the quantities of the summary (key, title, unit).
§7 TESTS
    tests/spectrum/test_field_tables.py.
"""

import csv
import re
from pathlib import Path

import numpy as np

from azimuth.i18n import tr

LIMIT = 30
FLOOR = 0.02
ESP_ROWS = (  # (key of multiwfn.parse_surface, title, unit)
    ('area', 'Площадь поверхности', 'Å²'),
    ('volume', 'Объём внутри неё', 'Å³'),
    ('minimum', 'Минимум ESP', 'ккал/моль'),
    ('maximum', 'Максимум ESP', 'ккал/моль'),
    ('average', 'Среднее ESP', 'ккал/моль'),
    ('positive_average', 'Среднее положительное V̄s⁺', 'ккал/моль'),
    ('negative_average', 'Среднее отрицательное V̄s⁻', 'ккал/моль'),
    ('positive_area', 'Площадь, где ESP > 0', 'Å²'),
    ('negative_area', 'Площадь, где ESP < 0', 'Å²'),
    ('variance', 'Дисперсия σ²tot', '(ккал/моль)²'),
    ('balance', 'Баланс зарядов ν (¼ — равновесие)', ''),
    ('product', 'σ²tot · ν', '(ккал/моль)²'),
    ('separation', 'Разделение зарядов Π', 'ккал/моль'),
    ('mpi', 'Индекс полярности MPI', 'ккал/моль'),
    ('polar_area', 'Полярная площадь (|ESP| > 10 ккал/моль)', 'Å²'),
    ('nonpolar_area', 'Неполярная площадь (|ESP| ≤ 10 ккал/моль)', 'Å²'),
)
CP_FILES = (('nucleus', 'nuclei'), ('bond', 'bonds'), ('ring', 'rings'), ('cage', 'cages'))
# the tables of one search of the points — written again in place; one the new search has not (no rings now, no weak
# interactions) is removed, not left from the search before
QTAIM_TABLES = tuple('qtaim_' + name for _, name in CP_FILES) + ('qtaim_contacts',)


def _nearest(position, atoms):
    if not atoms:
        return None, None
    d = np.linalg.norm(np.asarray([a.position for a in atoms], float) - np.asarray(position, float), axis=1)
    k = int(np.argmin(d))
    return k, float(d[k])


def grid_extrema(cube, mode='max', limit=LIMIT, floor=FLOOR, below=None):
    """below: for minima only values under it (RDG of NCI: the weak-interaction dips, not its plateau of 100)."""
    values = np.asarray(cube.values[..., 0], float)
    if min(values.shape) < 3:
        return []
    inner = values[1:-1, 1:-1, 1:-1]
    top = float(np.max(np.abs(values))) or 1.0
    found = []
    for kind in (('max', 'min') if mode == 'both' else (mode,)):
        sign = 1.0 if kind == 'max' else -1.0
        if kind == 'max' or mode == 'both':
            mask = sign * inner > floor * top
        else:
            mask = np.ones_like(inner, bool)
        if kind == 'min' and below is not None:
            mask &= inner < below
        strict = np.zeros_like(inner, bool)  # a flat plateau is no extremum
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    if dx == dy == dz == 0:
                        continue
                    neighbour = values[1 + dx:values.shape[0] - 1 + dx, 1 + dy:values.shape[1] - 1 + dy,
                                       1 + dz:values.shape[2] - 1 + dz]
                    mask &= sign * inner >= sign * neighbour
                    strict |= sign * inner > sign * neighbour
        mask &= strict
        index = np.argwhere(mask) + 1
        chosen = sorted(index, key=lambda k: -sign * values[tuple(k)])[:limit]
        for k in chosen:
            position = np.asarray(cube.origin, float) + np.asarray(k, float) @ np.asarray(cube.axes, float)
            atom, distance = _nearest(position, cube.molecule.atoms)
            found.append({'kind': kind, 'value': float(values[tuple(k)]), 'position': position, 'atom': atom,
                          'distance': distance})
    return found


def _atom(k, symbols):
    return '' if k is None or not 0 <= k < len(symbols) else f'{symbols[k]}{k + 1}'


def extrema_table(extrema, symbols, unit='', extra=None):
    """extra: (title, values) — one more column (sign(λ₂)ρ at the dips of RDG)."""
    header = [tr('№'), tr('Экстремум'), tr('Значение') + (f', {tr(unit)}' if unit else ''), 'x, Å', 'y, Å', 'z, Å',
              tr('Ближайший атом'), tr('Расстояние, Å')] + ([extra[0]] if extra else [])
    rows = []
    for n, e in enumerate(extrema, 1):
        rows.append([n, tr('максимум') if e['kind'] == 'max' else tr('минимум'), f"{e['value']:.6g}",
                     *(f'{c:.4f}' for c in e['position']), _atom(e['atom'], symbols),
                     '' if e['distance'] is None else f"{e['distance']:.3f}"]
                    + ([f'{extra[1][n - 1]:.6g}'] if extra else []))
    return header, rows


MAPPED_ROWS = (  # the summary of ALIE, LEA, LEAE on the surface (Multiwfn prints them in eV)
    ('area', 'Площадь поверхности', 'Å²'),
    ('volume', 'Объём внутри неё', 'Å³'),
    ('minimum', 'Минимум', 'эВ'),
    ('maximum', 'Максимум', 'эВ'),
    ('average_ev', 'Среднее', 'эВ'),
    ('variance_ev', 'Дисперсия', 'эВ²'),
    ('positive_area', 'Площадь, где функция > 0', 'Å²'),
    ('negative_area', 'Площадь, где функция < 0', 'Å²'),
)


def esp_tables(esp, symbols, atoms=()):
    """The extrema (a.u., eV, kcal/mol) and the summary of a function on the molecular surface (multiwfn.run_esp);
    of ESP, ALIE, LEA or LEAE (esp['mapped'])."""
    mapped = esp.get('mapped', 'esp')
    header = [tr('№'), tr('Экстремум'), tr('а. е.'), tr('эВ'), tr('ккал/моль'), 'x, Å', 'y, Å', 'z, Å', tr('Глобальный'),
              tr('Ближайший атом'), tr('Расстояние, Å')]
    rows = []
    items = []
    for name, title in (('minima', tr('минимум')), ('maxima', tr('максимум'))):
        units = esp.get(name + '_units') or [(float('nan'), float('nan'))] * len(esp.get(name, ()))
        items += [(title, *item, *unit) for item, unit in zip(esp.get(name, ()), units)]
    for n, (kind, kcal, xyz, top, au, ev) in enumerate(items, 1):
        atom, distance = _nearest(xyz, atoms)
        rows.append([n, kind, f'{au:.6f}', f'{ev:.4f}', f'{kcal:.4f}', *(f'{c:.4f}' for c in xyz), tr('да') if top else '',
                     _atom(atom, symbols), '' if distance is None else f'{distance:.3f}'])
    summary = esp.get('summary', {})
    chosen = ESP_ROWS if mapped == 'esp' else MAPPED_ROWS
    totals = [[tr(title), f'{summary[key]:.6g}', tr(unit)] for key, title, unit in chosen if key in summary]
    return {f'{mapped}_extrema': (header, rows), f'{mapped}_summary': ([tr('Величина'), tr('Значение'), tr('Единицы')], totals)}


def cp_tables(topology, symbols):
    header = [tr('№'), tr('Атомы'), 'x, Å', 'y, Å', 'z, Å', 'ρ', '∇²ρ', 'ε', 'G', 'V', 'H', '|V|/G', 'λ1', 'λ2', 'λ3']
    everything = list(getattr(topology, 'nuclei', ())) + list(topology.points)
    tables = {}
    for kind, name in CP_FILES:
        rows = []
        for n, p in enumerate((p for p in everything if p.kind == kind), 1):
            ratio = abs(p.potential) / p.kinetic if p.kinetic and p.kinetic > 1e-12 else float('nan')
            rows.append([n, '–'.join(_atom(k, symbols) for k in p.atoms), *(f'{c:.4f}' for c in p.position),
                         f'{p.rho:.6f}', f'{p.laplacian:+.6f}', '' if p.ellipticity is None else f'{p.ellipticity:.4f}',
                         f'{p.kinetic:.6f}', f'{p.potential:+.6f}', f'{p.energy:+.6f}', f'{ratio:.3f}',
                         *(f'{v:+.6f}' for v in p.eigenvalues)])
        if rows:
            tables['qtaim_' + name] = (header, rows)
    return tables


# the tables and the outputs of Multiwfn go to the subfolder «Анализ» of the folder of the calculation (the
# folder itself had dozens of files after a few surfaces); the CSV style: 'ru' — «;» between the columns and the
# decimal comma, as Excel and Numbers with a Russian locale open it by a double click; 'intl' — «,» and the point
ANALYSIS = 'Анализ'
STYLES = ('ru', 'intl')
style = 'ru'
# «Файл → Настройки…» chooses the separator and the decimal sign apart; any other style is the code
# «<separator><decimal>» (';.', '\t,', '\t.'); 'ru' is ';,' and 'intl' is ',.'
SEPARATORS = ((';', 'Точка с запятой «;»'), (',', 'Запятая «,»'), ('\t', 'Табуляция'))
DECIMALS = ((',', 'Запятая «,»'), ('.', 'Точка «.»'))
_NAMED = {'ru': (';', ','), 'intl': (',', '.')}


def style_parts(chosen=None):
    """(separator, decimal) of a style; an unknown one is 'ru'."""
    chosen = style if chosen is None else chosen
    if chosen in _NAMED:
        return _NAMED[chosen]
    if (isinstance(chosen, str) and len(chosen) == 2 and chosen[0] in dict(SEPARATORS) and chosen[1] in dict(DECIMALS)
            and chosen != ',,'):
        return chosen[0], chosen[1]
    return _NAMED['ru']


def style_code(separator, decimal):
    """The style of a separator and a decimal sign ('ru', 'intl' or the code); «,» with the decimal comma
    would mix the columns with the numbers — then the point."""
    separator = separator if separator in dict(SEPARATORS) else ';'
    decimal = decimal if decimal in dict(DECIMALS) else ','
    if separator == ',':
        decimal = '.'
    code = separator + decimal
    return next((k for k, v in _NAMED.items() if v == (separator, decimal)), code)


def valid_style(chosen):
    """A style kept in the settings, or 'ru'."""
    return style_code(*style_parts(chosen))
_NUMBER = re.compile(r'^[+\-−]?(\d+\.?\d*|\.\d+)([eE][+\-]?\d+)?$')


def analysis_folder(folder):
    """folder/«Анализ», made when missing."""
    target = Path(folder) / ANALYSIS
    target.mkdir(parents=True, exist_ok=True)
    return target


def save_output(wavefunction, name, text):
    """The output of Multiwfn «<name of the file>_multiwfn_<name>.txt» in «Анализ» next to the file; the path or None."""
    try:
        base = Path(wavefunction)
        path = analysis_folder(base.parent) / f'{base.name.split(".")[0]}_multiwfn_{name}.txt'
        path.write_text(text, encoding='utf-8')
        from azimuth.runtime.provenance import write_source

        write_source(path, base, analysis=name)  # which file (its SHA-256) the output was made from
        return path
    except OSError:
        return None


# -- the critical points kept, shown again when the result is opened again ---------------------------------
# What was computed is not computed again when the project is opened again. The topology of a search (the points, the
# nuclei, the bond paths) is written as
# «<stem>_qtaim_saved.json» in «Анализ» with the record of its source (azimuth.runtime.provenance: the name, SHA-256
# and size of the file of orbitals Multiwfn read); it is read back only while that file is the same.
SAVED_TOPOLOGY = 'qtaim_saved'


def _stem(wavefunction):
    return Path(wavefunction).name.split('.')[0]


def kept_for(target, folder):
    """Is the file of orbitals that target (a result kept in «Анализ») was made from still the same — cheaply, without
    reading it: its size as recorded and no change after the record was made (its SHA-256 is not computed again: a
    Molden of hundreds of MB would take seconds). False without a record."""
    import json
    from datetime import datetime

    try:
        record = json.loads(Path(str(target) + '.source.json').read_text(encoding='utf-8'))
        source = Path(folder) / str(record.get('source') or '')
        info = source.stat()
        made = datetime.fromisoformat(record['made']).timestamp()
    except (OSError, ValueError, KeyError, TypeError):
        return False
    return record.get('size') == info.st_size and info.st_mtime <= made + 2.0


def saved_output(wavefunction, name):
    """The output of Multiwfn kept by save_output for these orbitals (any file of the result: the .gbw or
    its Molden), when they are still the same (kept_for); else None. Small files: read at once."""
    try:
        base = Path(wavefunction)
        target = base.parent / ANALYSIS / f'{_stem(base)}_multiwfn_{name}.txt'
        if not target.is_file() or not kept_for(target, base.parent):
            return None
        return target.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return None


def save_topology(wavefunction, topology):
    """The topology of a search of the points of these orbitals kept; the path or None."""
    import json

    def point(p):
        return {'kind': p.kind, 'position': [float(c) for c in p.position], 'rho': float(p.rho),
                'laplacian': float(p.laplacian), 'eigenvalues': [float(v) for v in p.eigenvalues],
                'ellipticity': None if p.ellipticity is None else float(p.ellipticity), 'kinetic': float(p.kinetic),
                'potential': float(p.potential), 'energy': float(p.energy), 'atoms': [int(k) for k in p.atoms]}

    try:
        base = Path(wavefunction)
        target = analysis_folder(base.parent) / f'{_stem(base)}_{SAVED_TOPOLOGY}.json'
        data = {'version': 1, 'points': [point(p) for p in topology.points],
                'nuclei': [point(p) for p in getattr(topology, 'nuclei', ())],
                'paths': [np.asarray(path, float).round(5).tolist() for path in topology.paths],
                'counts': dict(topology.counts), 'poincare_hopf': int(topology.poincare_hopf),
                'notes': list(topology.notes)}
        target.write_text(json.dumps(data), encoding='utf-8')
        from azimuth.runtime.provenance import write_source

        write_source(target, base, analysis='topology')
        return target
    except (OSError, TypeError, ValueError):
        return None


def load_topology(wavefunction):
    """The topology kept for the file of orbitals of this name (any file of the result: the .gbw or its Molden), when
    the file it was found in is still the same; else None."""
    import json

    from modules.spectrum.analysis.density import CriticalPoint, Topology

    try:
        base = Path(wavefunction)
        target = base.parent / ANALYSIS / f'{_stem(base)}_{SAVED_TOPOLOGY}.json'
        if not target.is_file():
            return None
        if not kept_for(target, base.parent):
            return None  # the orbitals were computed again: the points are of another file
        data = json.loads(target.read_text(encoding='utf-8'))

        def point(d):
            return CriticalPoint(d['kind'], np.array(d['position'], float), d['rho'], d['laplacian'],
                                 np.array(d['eigenvalues'], float), d['ellipticity'], d['kinetic'], d['potential'],
                                 d['energy'], tuple(d['atoms']))

        return Topology(tuple(point(d) for d in data['points']), tuple(np.array(p, float) for p in data['paths']),
                        dict(data['counts']), int(data['poincare_hopf']), tuple(data.get('notes', ())),
                        tuple(point(d) for d in data.get('nuclei', ())))
    except (OSError, ValueError, KeyError, TypeError):
        return None


def save_field(wavefunction, kind, data, name, atoms):
    """The last map ('map': u, v, values, points) or profile ('line': x, values, points) built for these
    orbitals, kept as «<stem>_field_<kind>.npz» in «Анализ» with the record of its source (read back fast — not the
    CSV of tens of thousands of rows); the path or None."""
    try:
        base = Path(wavefunction)
        target = analysis_folder(base.parent) / f'{_stem(base)}_field_{kind}.npz'
        arrays = {key: np.asarray(data[key], float) for key in ('u', 'v', 'x', 'values', 'points') if key in data}
        with open(target, 'wb') as out:
            np.savez_compressed(out, name=np.array(str(name)), atoms=np.array([int(a) for a in atoms]), **arrays)
        from azimuth.runtime.provenance import write_source

        write_source(target, base, analysis=f'field_{kind}', function=str(name), atoms=[int(a) + 1 for a in atoms])
        return target
    except (OSError, TypeError, ValueError, KeyError):
        return None


def load_field(wavefunction, kind):
    """(data, name, atoms) of the last map or profile kept for these orbitals while they are the same; else None."""
    try:
        base = Path(wavefunction)
        target = base.parent / ANALYSIS / f'{_stem(base)}_field_{kind}.npz'
        if not target.is_file() or not kept_for(target, base.parent):
            return None
        with np.load(target, allow_pickle=False) as kept:
            data = {key: kept[key] for key in ('u', 'v', 'x', 'values', 'points') if key in kept.files}
            return data, str(kept['name']), tuple(int(a) for a in kept['atoms'])
    except (OSError, ValueError, KeyError):
        return None


def _cell(value, chosen):
    text = str(value)
    if style_parts(chosen)[1] == ',' and _NUMBER.match(text):
        return text.replace('.', ',')
    return value


def write_csv(path, header, rows, chosen=None):
    chosen = chosen or style
    path = Path(path)
    with open(path, 'w', encoding='utf-8-sig', newline='') as out:
        writer = csv.writer(out, delimiter=style_parts(chosen)[0])
        writer.writerow(header)
        writer.writerows([_cell(v, chosen) for v in row] for row in rows)
    return path


def write_tables(folder, base, tables, chosen=None, family=()):
    """The tables as «<base>_<suffix>.csv» in folder/«Анализ»; family — the suffixes of one
    analysis (QTAIM_TABLES): a table of it that is not among these is removed (it was of the run before)."""
    target = analysis_folder(folder)
    for suffix in family:
        old = target / f'{base}_{suffix}.csv'
        if suffix not in tables and old.is_file():
            try:
                old.unlink()
            except OSError:
                pass
    return [write_csv(target / f'{base}_{suffix}.csv', header, rows, chosen) for suffix, (header, rows) in tables.items()]


def read_csv(path):
    """(header, rows) of a table written here, in either style (for the tests and the panels)."""
    text = Path(path).read_text(encoding='utf-8-sig')
    first = text.split('\n', 1)[0]
    delimiter = max(('\t', ';', ','), key=first.count) if any(c in first for c in '\t;,') else ','
    rows = list(csv.reader(text.splitlines(), delimiter=delimiter))
    return rows[0], rows[1:]


# -- the extrema of a map in a plane and of a profile along a line ----------------------------------------
def map_extrema(values, points, limit=20):
    v = np.asarray(values, float)
    found = []
    inner = v[1:-1, 1:-1]
    for kind, sign in (('max', 1.0), ('min', -1.0)):
        mask = np.ones_like(inner, bool)
        strict = np.zeros_like(inner, bool)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == dy == 0:
                    continue
                other = v[1 + dx:v.shape[0] - 1 + dx, 1 + dy:v.shape[1] - 1 + dy]
                mask &= sign * inner >= sign * other
                strict |= sign * inner > sign * other
        index = np.argwhere(mask & strict) + 1
        for i, j in sorted(index, key=lambda k: -sign * v[tuple(k)])[:limit]:
            found.append({'kind': kind, 'value': float(v[i, j]), 'position': np.asarray(points[i, j], float), 'ij': (i, j)})
    return found


def line_extrema(x, values, points):
    v = np.asarray(values, float)
    found = []
    for k in range(1, len(v) - 1):
        for kind, sign in (('max', 1.0), ('min', -1.0)):
            if sign * v[k] >= sign * v[k - 1] and sign * v[k] >= sign * v[k + 1] and (sign * v[k] > sign * v[k - 1] or
                                                                                       sign * v[k] > sign * v[k + 1]):
                found.append({'kind': kind, 'value': float(v[k]), 'position': np.asarray(points[k], float),
                              'x': float(x[k])})
    return found
