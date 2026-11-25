"""The analyses of Multiwfn on the result shown in Compass: bond orders, spins, Hirshfeld, RESP, AIM, ADCH and CM5
charges onto the model, and finding the program and the file of the orbitals. Methods of PropertyTool (self is the
tool; the window only through its port self.w), kept here to make property_actions.py shorter.

Split off modules/compass/actions/property_actions.py (0.222.30).
"""

from azimuth.i18n import tr


BOND_SETS = (('mayer', 'Mayer'), ('wiberg', 'Wiberg-Löwdin'), ('fuzzy', 'Fuzzy'), ('laplacian', 'Laplacian'))


MULTIWFN_HINT = ('Multiwfn не найден: установите его (macOS: brew install multiwfn; Windows: архив с sobereva.com/multiwfn, '
                 'файл Multiwfn.exe) или укажите программу — «Поверхность на модели → Программа Multiwfn…»')


def multiwfn_bond_orders(self):
    """Mayer, Wiberg (Löwdin), fuzzy and Laplacian bond orders of the result; the Mayer ones shown on the model."""
    from dataclasses import replace
    from pathlib import Path

    from modules.spectrum.wavefunction import multiwfn
    from modules.spectrum.readers.orca_properties import Properties
    from azimuth.tasks import run_waiting

    source = self.multiwfn_source()
    if source is None:
        return False
    program, wavefunction, cores = source
    try:
        orders, text, _ = run_waiting(self.w.widget, tr('Порядки связей…'),
                                      lambda step: multiwfn.run_bond_orders(program, wavefunction, cores, step))
        props = self.w.result_properties
        if props is None:
            from modules.spectrum.readers.orbital_files import read_orbitals

            geometry = read_orbitals(Path(wavefunction).read_text(encoding='utf-8-sig', errors='replace')).molecule
            props = Properties(geometry=geometry)
        atoms = len(props.geometry.atoms)
        if any(max(i, j) >= atoms for kind in multiwfn.BOND_KINDS for i, j, _ in orders.get(kind, ())):
            raise ValueError(tr('Другое число атомов, чем у результата — порядки не взяты.'))
    except InterruptedError:  # «Отмена» — no message
        return False
    except (OSError, ValueError) as exc:
        self.w.error(exc)
        return False
    from modules.spectrum.wavefunction import field_tables

    field_tables.save_output(wavefunction, 'bond_orders', text)
    sets = dict(props.bond_sets)
    for key, kind in BOND_SETS:
        if key in orders:
            sets[kind] = tuple(orders[key])
    first = next(kind for _, kind in BOND_SETS if kind in sets)
    valence = props.mayer_valence or orders.get('valence')
    self.w.overlay_choice['bonds'] = True  # before: no hint about «±»
    self.set_result_properties(replace(props, bond_sets=sets, mayer_bonds=sets[first], bond_kind=first,
                                       mayer_valence=valence), self.w.result_source or Path(wavefunction).name)
    self.w.notify(tr('Порядки связей посчитаны — переключение между ними в «Связи».'), 10000)
    return True


# -- Multiwfn ---------------------------------------------------------------------------------------------
def has_wavefunction(self):
    """The shown result has a file with its orbitals (a Molden or fchk file, or an ORCA .gbw to convert)."""
    return getattr(self.w, 'sibling_molden', None) is not None or getattr(self.w, 'sibling_gbw', None) is not None


def multiwfn_ready(self, tip):
    """(enabled, tooltip) of an item that needs Multiwfn and the wavefunction of the result."""
    if not (self.has_wavefunction() and self.w.has('result_molden_path')):
        return False, tr('У результата нет файла с орбиталями (Molden, fchk или .gbw ORCA)')
    if self.multiwfn_found() is None:
        return False, tr(MULTIWFN_HINT)
    return True, tip


def add_multiwfn_item(self, menu):
    item = menu.addAction(tr('Заряды ADCH и CM5…'))
    enabled, tip = self.multiwfn_ready(tr('По волновой функции результата; они мало зависят от базиса, в отличие от Малликена'))
    item.setEnabled(enabled)
    item.setToolTip(tip)
    item.triggered.connect(self.multiwfn_charges)
    # RESP — fitted to the electrostatic potential, the charges of AMBER / GAFF
    resp = menu.addAction(tr('Заряды RESP…'))
    enabled, tip = self.multiwfn_ready(tr('Подогнаны под электростатический потенциал молекулы (двухстадийный RESP) — '
                                          'заряды силовых полей AMBER и GAFF для молекулярной динамики; файл .chg '
                                          'с координатами и зарядами — в «Анализ»'))
    resp.setEnabled(enabled)
    resp.setToolTip(tip)
    resp.triggered.connect(self.multiwfn_resp)
    # the Fukui functions of a result of the queue «Функции Фукуи» of Sextant
    fukui = menu.addAction(tr('Функции Фукуи…'))
    enabled, tip = self.multiwfn_ready(tr('Куда атакуют нуклеофил, электрофил и радикал: f⁺, f⁻, f⁰ и Δf по атомам '
                                          '(заряды Хиршфельда трёх расчётов) и глобальные индексы'))
    folder = self.fukui_folder()
    fukui.setEnabled(enabled and folder is not None)
    fukui.setToolTip(tip if folder is not None else tr('Сначала посчитайте в Секстанте задачу «Функции Фукуи (N, '
                                                       'N+1, N−1)» — три расчёта на одной геометрии'))
    fukui.triggered.connect(lambda *a: self.show_fukui(self.fukui_folder()))
    # Hirshfeld for any file of orbitals (ORCA prints its own), the charges and spins of the AIM basins
    props = getattr(self.w, 'result_properties', None)
    hirshfeld = menu.addAction(tr('Заряды Хиршфельда…'))
    # grey only when the program of the result printed them — not when Multiwfn computed them here
    known = props is not None and 'hirshfeld' in props.charges and \
        props.charges['hirshfeld'] != getattr(self, 'computed_hirshfeld', None)
    enabled, tip = self.multiwfn_ready(tr('По волновой функции результата (fchk, Molden) — для выводов, где их нет; у '
                                          'открытой оболочки — и спиновые заселённости'))
    hirshfeld.setEnabled(enabled and not known)
    hirshfeld.setToolTip(tr('Заряды Хиршфельда уже есть в выводе программы — они в «Атомы»') if known else tip)
    hirshfeld.triggered.connect(self.multiwfn_hirshfeld)
    aim = menu.addAction(tr('Заряды и спины AIM (бассейны Бейдера)…'))
    enabled, tip = self.multiwfn_ready(tr('Молекула делится на бассейны ρ (атомы в молекуле Бейдера); у открытой '
                                          'оболочки — и спиновые заселённости. От минуты до нескольких на средней сетке'))
    aim.setEnabled(enabled and self.w.has('load_result_orbitals'))
    aim.setToolTip(tip)
    aim.triggered.connect(self.multiwfn_aim)
    # the spin of an open shell on the atoms, from the orbitals of the result (no Multiwfn needed)
    spins = menu.addAction(tr('Спиновые заселённости по орбиталям (Малликен)'))
    closed = self.result_open_shell() is False  # grey for a closed shell — it had nothing to give
    spins.setEnabled(self.has_wavefunction() and self.w.has('load_result_orbitals') and not closed)
    spins.setToolTip(tr('Закрытая оболочка (мультиплетность 1): спиновая плотность всюду ноль') if closed else
                     tr('Где неспаренные электроны: доля спиновой плотности α − β на каждом атоме (открытая оболочка)'))
    spins.triggered.connect(self.orbital_spins)
    return item


def orbital_spins(self):
    """The Mulliken spin populations from the orbitals of the result onto the model (when the output has
    none — Gaussian without them, a Molden file of another program); True when they were added."""
    from dataclasses import replace

    from modules.spectrum.readers.orca_properties import Properties

    loaded = self.w.load_result_orbitals()
    if loaded is None:
        return False
    orbital_set, name = loaded
    if not orbital_set.unrestricted:
        self.w.notify(tr('Закрытая оболочка: спиновая плотность всюду ноль, спиновых заселённостей нет.'), 8000)
        return False
    spins = tuple(float(v) for v in orbital_set.mulliken_spins())
    props = self.w.result_properties or Properties(geometry=orbital_set.molecule)
    if len(spins) != len(props.geometry.atoms):
        self.w.error(ValueError(tr('Другое число атомов, чем у результата — спиновые заселённости не взяты.')))
        return False
    self.w.overlay_choice['atom'] = 'spin-mulliken'
    self.set_result_properties(replace(props, spins={**props.spins, 'mulliken': spins}), self.w.result_source or name)
    self.w.notify(tr(f'Спиновые заселённости по Малликену на модели: сумма {sum(spins):+.3f} = Nα − Nβ.'), 10000)
    return True


def _population_target(self, wavefunction):
    """The Properties of the shown result (or of the geometry of the wavefunction alone)."""
    from pathlib import Path

    from modules.spectrum.readers.orca_properties import Properties

    props = self.w.result_properties
    if props is None:
        from modules.spectrum.readers.orbital_files import read_orbitals

        geometry = read_orbitals(Path(wavefunction).read_text(encoding='utf-8-sig', errors='replace')).molecule
        props = Properties(geometry=geometry)
    return props


def multiwfn_hirshfeld(self):
    """The Hirshfeld charges of Multiwfn onto the model (for Gaussian, Molden — ORCA prints its own)."""
    from dataclasses import replace
    from pathlib import Path

    from azimuth.tasks import run_waiting
    from modules.spectrum.wavefunction import field_tables, multiwfn_populations

    program = self.multiwfn_program()
    wavefunction = self.w.result_molden_path() if program is not None else None
    if wavefunction is None:
        return False
    cores = self.w.cores.value() if self.w.has('cores') else 1
    try:
        charges, text = run_waiting(self.w.widget, tr('Заряды Хиршфельда…'),
                                    lambda step: multiwfn_populations.run_hirshfeld(program, wavefunction, cores, step))
        props = self._population_target(wavefunction)
        if len(charges) != len(props.geometry.atoms):
            raise ValueError(tr('Другое число атомов, чем у результата — заряды не взяты.'))
    except InterruptedError:
        return False
    except (OSError, ValueError) as exc:
        self.w.error(exc)
        return False
    field_tables.save_output(wavefunction, 'hirshfeld', text)
    new = replace(props, charges={**props.charges, 'hirshfeld': tuple(charges)})
    self.computed_hirshfeld = tuple(charges)  # of Multiwfn — the item stays to be computed again
    spins = None
    loaded = self.w.load_result_orbitals() if self.w.has('load_result_orbitals') else None
    if loaded is not None and getattr(loaded[0], 'unrestricted', False):  # an open shell — and the spins
        try:
            spins, spin_text = run_waiting(self.w.widget, tr('Спиновые заселённости Хиршфельда…'),
                                           lambda step: multiwfn_populations.run_hirshfeld_spins(
                                               program, wavefunction, cores, step))
            if len(spins) != len(props.geometry.atoms):
                raise ValueError(tr('Другое число атомов, чем у результата — спиновые заселённости не взяты.'))
            field_tables.save_output(wavefunction, 'hirshfeld_spins', spin_text)
            new = replace(new, spins={**props.spins, 'hirshfeld': tuple(spins)})
        except InterruptedError:
            spins = None
        except (OSError, ValueError) as exc:
            spins = None
            self.w.error(exc)
    self.w.overlay_choice['atom'] = 'hirshfeld'
    self.set_result_properties(new, self.w.result_source or Path(wavefunction).name)
    self.w.notify(tr(f'Заряды Хиршфельда на модели: сумма {sum(charges):+.3f}.')
                + (tr(f' Спиновые заселённости Хиршфельда — в «Атомы» (сумма {sum(spins):+.3f}).') if spins else ''), 10000)
    return True


def multiwfn_resp(self):
    """The RESP charges of Multiwfn onto the model; the output and «<name>_resp.chg» in «Анализ»."""
    from dataclasses import replace
    from pathlib import Path

    from azimuth.tasks import run_waiting
    from modules.spectrum.wavefunction import field_tables, multiwfn_resp

    program = self.multiwfn_program()
    wavefunction = self.w.result_molden_path() if program is not None else None
    if wavefunction is None:
        return False
    cores = self.w.cores.value() if self.w.has('cores') else 1
    try:
        charges, rmse, rrmse, chg, text = run_waiting(
            self.w.widget, tr('Заряды RESP…'), lambda step: multiwfn_resp.run_resp(program, wavefunction, cores, step))
        props = self._population_target(wavefunction)
        if len(charges) != len(props.geometry.atoms):
            raise ValueError(tr('Другое число атомов, чем у результата — заряды не взяты.'))
    except InterruptedError:
        return False
    except (OSError, ValueError) as exc:
        self.w.error(exc)
        return False
    field_tables.save_output(wavefunction, 'resp', text)
    if chg:
        base = Path(wavefunction)
        try:
            (field_tables.analysis_folder(base.parent) / f'{base.name.split(".")[0]}_resp.chg').write_text(
                chg, encoding='utf-8')
        except OSError:
            pass
    self.w.overlay_choice['atom'] = 'resp'
    self.set_result_properties(replace(props, charges={**props.charges, 'resp': tuple(charges)}),
                               self.w.result_source or Path(wavefunction).name)
    quality = tr(f' Отклонение от потенциала RRMSE {rrmse:.3f}.') if rrmse is not None else ''
    self.w.notify(tr(f'Заряды RESP на модели: сумма {sum(charges):+.3f}.') + quality, 10000)
    return True


def multiwfn_aim(self):
    """The charges of the AIM basins (and the spin populations of an open shell) onto the model."""
    from dataclasses import replace
    from pathlib import Path

    from azimuth.tasks import run_waiting
    from modules.spectrum.wavefunction import field_tables, multiwfn_populations

    program = self.multiwfn_program()
    if program is None:
        return False
    loaded = self.w.load_result_orbitals()  # the nuclear charges (with an ECP — effective) and the kind of shell
    wavefunction = self.w.result_molden_path() if loaded is not None else None
    if wavefunction is None:
        return False
    orbital_set, _ = loaded
    spin = bool(getattr(orbital_set, 'unrestricted', False))
    cores = self.w.cores.value() if self.w.has('cores') else 1
    try:
        charges, spins, text = run_waiting(
            self.w.widget, tr('Бассейны AIM…'),
            lambda step: multiwfn_populations.run_basins(program, wavefunction, orbital_set.charges, spin, cores, step))
        props = self._population_target(wavefunction)
        if len(charges) != len(props.geometry.atoms):
            raise ValueError(tr('Другое число атомов, чем у результата — заряды не взяты.'))
    except InterruptedError:
        return False
    except (OSError, ValueError) as exc:
        self.w.error(exc)
        return False
    field_tables.save_output(wavefunction, 'aim', text)
    # the output of the basins gives
    # populations, the charges need the nuclear charges of the orbitals — the values themselves are kept beside it
    import json

    field_tables.save_output(wavefunction, 'aim_values', json.dumps(
        {'charges': list(charges), 'spins': list(spins) if spins is not None else None}))
    new = replace(props, charges={**props.charges, 'aim': tuple(charges)})
    if spins is not None:
        new = replace(new, spins={**props.spins, 'aim': tuple(spins)})
    self.w.overlay_choice['atom'] = 'aim'
    self.set_result_properties(new, self.w.result_source or Path(wavefunction).name)
    self.w.notify(tr(f'Заряды AIM на модели: сумма {sum(charges):+.3f}.')
                + (tr(f' Спиновые заселённости бассейнов — в «Атомы» (сумма {sum(spins):+.3f}).') if spins else ''), 10000)
    return True


def multiwfn_found(self):
    """Multiwfn of the settings or found — without asking (None: not installed)."""
    from modules.spectrum.wavefunction import multiwfn

    settings = getattr(self.w, 'preferences', None)
    configured = settings.value('multiwfn_program', '') if settings is not None else ''
    return multiwfn.find(configured or None)


def multiwfn_program(self):
    """Multiwfn of the settings or found; no file dialog — when it is not there, a notice how to get it
    (the items that need it are off, «Программа Multiwfn…» chooses the file)."""
    program = self.multiwfn_found()
    if program is None:
        self.w.notify(tr(MULTIWFN_HINT), 12000)
    return program


def choose_multiwfn_program(self):
    """«Программа Multiwfn…»: the file of the program, kept in the settings; None when not chosen."""
    from pathlib import Path

    from PySide6.QtWidgets import QFileDialog

    found = self.multiwfn_found()
    start = str(found.parent) if found is not None else (
        '/opt/homebrew/bin' if Path('/opt/homebrew/bin').is_dir() else str(Path.home()))
    path, _ = QFileDialog.getOpenFileName(self.w.widget, tr('Программа Multiwfn'), start)
    if not path:
        return None
    settings = getattr(self.w, 'preferences', None)
    if settings is not None:
        settings.setValue('multiwfn_program', path)
    from modules.spectrum.wavefunction import multiwfn

    multiwfn.clear_cache()
    if self.w.has('density_tool'):
        self.w.density_tool.update_surfaces_page()
    return Path(path)


def multiwfn_source(self, path=None):
    """(Multiwfn, the wavefunction file — path or that of the result —, cores) or None (not found, no
    file)."""
    if path is None:
        path = self.w.result_molden_path() if self.w.has('result_molden_path') else None
    if path is None:
        return None
    program = self.multiwfn_program()
    if program is None:
        return None
    return program, path, self.w.cores.value() if self.w.has('cores') else 1


# which file every set of orbitals was read from — ESP and QTAIM are Multiwfn's, it reads that file
def remember_orbitals_file(self, orbital_set, path):
    files = getattr(self.w, 'orbital_files', None)
    if files is None:
        files = self.w.orbital_files = {}
    files[id(orbital_set)] = (orbital_set, path)


def orbitals_file(self, orbital_set):
    found = getattr(self.w, 'orbital_files', {}).get(id(orbital_set))
    return found[1] if found is not None and found[0] is orbital_set else None


def multiwfn_quiet(self, orbital_set):
    """(Multiwfn, the file of these orbitals, cores) when both are there — found without asking; for the
    grids of orbitals and density, which fall back on our own code."""
    from modules.spectrum.wavefunction import multiwfn

    path = self.orbitals_file(orbital_set)
    if path is None:
        return None
    try:
        multiwfn.wavefunction_name(path)
    except ValueError:
        return None
    settings = getattr(self.w, 'preferences', None)
    program = multiwfn.find((settings.value('multiwfn_program', '') if settings is not None else '') or None)
    return (program, path, self.w.cores.value() if self.w.has('cores') else 1) if program is not None else None


def multiwfn_for(self, orbital_set):
    """(Multiwfn, the file of these orbitals, cores) or None."""
    path = self.orbitals_file(orbital_set)
    return self.multiwfn_source(path) if path is not None else None


def multiwfn_charges(self):
    """ADCH and CM5 of the shown result from Multiwfn, onto the model (ADCH chosen); the output of Multiwfn is kept
    next to the wavefunction file. Returns True when the charges were added."""
    from dataclasses import replace
    from pathlib import Path

    from modules.spectrum.wavefunction import multiwfn
    from modules.spectrum.readers.orca_properties import Properties
    from azimuth.tasks import run_waiting

    program = self.multiwfn_program()
    if program is None:
        return False
    wavefunction = self.w.result_molden_path()  # an ORCA .gbw becomes Molden here
    if wavefunction is None:
        return False
    cores = self.w.cores.value() if self.w.has('cores') else 1
    try:
        charges, text, number = run_waiting(
            self.w.widget, tr('Заряды ADCH и CM5…'),
            lambda step: multiwfn.run_charges(program, wavefunction, cores, step),
        )
        props = self.w.result_properties
        if props is None:  # only the orbitals: the geometry of the wavefunction
            from modules.spectrum.readers.orbital_files import read_orbitals

            geometry = read_orbitals(Path(wavefunction).read_text(encoding='utf-8-sig', errors='replace')).molecule
            props = Properties(geometry=geometry)
        if any(len(values) != len(props.geometry.atoms) for values in charges.values()):
            raise ValueError(tr('Другое число атомов, чем у результата — заряды не взяты.'))
    except InterruptedError:  # «Отмена» — no message
        return False
    except (OSError, ValueError) as exc:
        self.w.error(exc)
        return False
    from modules.spectrum.wavefunction import field_tables

    field_tables.save_output(wavefunction, 'charges', text)  # for the student, in «Анализ»
    self.w.overlay_choice['atom'] = 'adch' if 'adch' in charges else 'cm5'  # before: no hint about «±»
    self.set_result_properties(replace(props, charges={**props.charges, **charges}),
                               self.w.result_source or Path(wavefunction).name)
    self.w.notify(tr('Заряды ADCH и CM5 посчитаны — на модели ADCH, CM5 в «Атомы».'), 10000)
    return True
