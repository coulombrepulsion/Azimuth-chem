"""The ESP on the surface of the density and the real space functions of Multiwfn (ELF, LOL…) on the model of
Compass, the surfaces of an excitation. Methods of SurfaceTool (self is the tool; the window only through its port
self.w), kept here to make surface_actions.py shorter.

Split off modules/compass/actions/surface_actions.py (0.222.30).
"""

from azimuth.i18n import tr


MAPPED_TITLES = {  # the functions on the molecular surface ρ = 0.001
    'esp': ('ESP', 'ESP на молекулярной поверхности'),
    'alie': ('ALIE', 'ALIE — средняя локальная энергия ионизации'),
    'lea': ('LEA', 'LEA — локальное сродство к электрону'),
    'leae': ('LEAE', 'LEAE — локальная энергия присоединения электрона'),
}


# the other real space functions of Multiwfn as surfaces, kinds 'f-<name>':
# name: (title, levels, default, signed (± lobes), unit, extrema of the table, «below» for minima)
FUNCTION_INFO = {
    'rho': ('Электронная плотность ρ', (0.001, 0.002, 0.005, 0.01, 0.05, 0.1), 0.05, False, ' e/бор³', 'max', None),
    'gradient': ('Градиент плотности |∇ρ|', (0.01, 0.05, 0.1, 0.2, 0.5), 0.1, False, '', 'max', None),
    'laplacian': ('Лапласиан ∇²ρ: синее — ∇²ρ > 0, красное — < 0', (0.05, 0.1, 0.2, 0.5, 1.0), 0.2, True, ' e/бор⁵',
                  'both', None),
    'spin': ('Спиновая плотность', (0.001, 0.002, 0.005, 0.01, 0.02), 0.005, True, ' e/бор³', 'both', None),
    'g': ('Кинетическая энергия G(r)', (0.01, 0.05, 0.1, 0.5), 0.1, False, ' а. е.', 'max', None),
    'k': ('Кинетическая энергия K(r)', (0.01, 0.05, 0.1, 0.5), 0.1, True, ' а. е.', 'both', None),
    'entropy': ('Локальная информационная энтропия', (0.005, 0.01, 0.02, 0.05), 0.02, False, '', 'max', None),
    'esp': ('Электростатический потенциал (полный)', (0.01, 0.02, 0.05, 0.1), 0.05, True, ' а. е.', 'both', None),
    'alie': ('Средняя локальная энергия ионизации ALIE', (0.3, 0.4, 0.5, 0.6, 0.8), 0.5, False, ' а. е.', 'min', None),
    'rdg': ('Приведённый градиент плотности RDG', (0.3, 0.5, 0.7, 1.0), 0.5, False, '', 'min', 1.0),
}


def multiwfn_esp(self, path=None, mapped='esp'):
    """The ESP of the wavefunction on the surface ρ = 0.001 with its extrema, from Multiwfn; the extrema and
    the summary go to CSV files in the folder of the calculation (no window)."""
    from pathlib import Path
    from types import SimpleNamespace

    from modules.spectrum.wavefunction import multiwfn

    source = self.w.property_tool.multiwfn_source(path) if self.w.has('property_tool') else None
    if source is None:
        return False
    program, path, cores = source
    try:
        esp = self.wait_field(('surface', mapped, multiwfn._stamp(path)), tr(f'Расчёт {MAPPED_TITLES[mapped][0]} на поверхности…'),
                          lambda step: multiwfn.run_esp(program, path, cores, step, mapped=mapped))
    except InterruptedError:  # «Отмена» — no message
        return False
    except (OSError, ValueError, MemoryError) as exc:
        self.w.error(exc)
        return False
    cube = esp['density']
    base = Path(path)  # the extrema and the summary — CSV files next to the file of the orbitals
    title = None if mapped == 'esp' else tr(MAPPED_TITLES[mapped][1])
    if not self.show_surface(cube, 'esp-surface', SimpleNamespace(molecule=cube.molecule), esp=esp, title=title or '',
                             table=(base.parent, base.name.split('.')[0])):
        return False
    self.w.esp_result = esp
    from modules.spectrum.wavefunction import field_tables

    field_tables.save_output(path, mapped, esp['text'])
    return True


def add_function_menu(self, menu, wavefunction):
    """«Функции на сетке» — the real space functions of the wavefunction as surfaces; the grid is
    «Сетка расчёта» of the menu."""
    sub = menu.addMenu(tr('Функции на сетке'))
    entries = [('elf', tr('ELF — функция локализации электронов')), ('lol', tr('LOL — локатор локализованных орбиталей'))]
    entries += [(name, tr(info[0])) for name, info in FUNCTION_INFO.items()]
    for name, title in entries:
        item = sub.addAction(title)
        item.setEnabled(wavefunction)
        item.triggered.connect(lambda checked=False, n=name: self.multiwfn_function(n))
    return sub


def surface_choice(self, key, path=None):
    """A surface of the page «Поверхности» for the file of the orbitals path (by default that of the result)."""
    group, name = key
    if group == 'function':
        return self.multiwfn_function(name, path)
    if group == 'nci':
        return self.multiwfn_nci(name, path)
    return self.multiwfn_esp(path, mapped=name)


# -- Multiwfn: ELF and LOL ----------------------------------------------------------------------------------
def multiwfn_function(self, name, path=None):
    """A real space function of the wavefunction (ELF, LOL, any of multiwfn.FUNCTIONS) on the grid chosen
    for Multiwfn, as a surface on the model, with the table of its extrema in the folder of the calculation."""
    from pathlib import Path
    from types import SimpleNamespace

    from modules.spectrum.wavefunction import multiwfn

    source = self.w.property_tool.multiwfn_source(path) if self.w.has('property_tool') else None
    if source is None:
        return False
    program, path, cores = source
    grid = self.nci_grid()
    try:
        cube, text, number = self.wait_field(('function', name, multiwfn._stamp(path), grid),
                                             tr(f'Расчёт {name.upper()}…') if name in ('elf', 'lol') else
                                             tr(FUNCTION_INFO[name][0]) + '…',
                                             lambda step: multiwfn.run_function(program, path, name, grid, cores, step))
    except InterruptedError:  # «Отмена» — no message
        return False
    except (OSError, ValueError, MemoryError) as exc:
        self.w.error(exc)
        return False
    kind = name if name in ('elf', 'lol') else 'f-' + name
    base = Path(path)
    if not self.show_surface(cube, kind, SimpleNamespace(molecule=cube.molecule),
                             table=(base.parent, base.name.split('.')[0])):
        return False
    from modules.spectrum.wavefunction import field_tables

    field_tables.save_output(path, name, text)
    return True


# -- an excited state — the hole and the electron ----------------------------------------------------------
def show_excitation(self, hole, electron, title=''):
    from types import SimpleNamespace

    return self.show_surface(hole, 'excitation', SimpleNamespace(molecule=hole.molecule), title=title,
                             color_cube=electron)
