"""The page «Орбитали» of the density panel of Compass: the table of the canonical orbitals or of the LMOs, their
localization, the composition by atoms. Methods of DensityDrawer (self is the panel), kept here to make
density_drawer.py shorter.

Split off modules/compass/panels/density_drawer.py (0.222.30).
"""

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QHeaderView, QPushButton, QTableWidget, QTableWidgetItem
from azimuth.i18n import tr


HARTREE_EV = 27.211386245988


class _ShiftRows(QObject):
    """Shift+click on a row of the table of the orbitals — callback(row); the choice of the table stays."""

    def __init__(self, table, callback):
        super().__init__(table)
        self.table, self.callback = table, callback
        table.viewport().installEventFilter(self)

    def eventFilter(self, watched, event):
        if (event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton
                and event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            try:
                index = self.table.indexAt(event.position().toPoint())
                if index.isValid():
                    self.callback(index.row())
            except RuntimeError:
                pass
            return True
        return False


# -- «Орбитали» -----------------------------------------------------------------------------------------------
def _orbitals_page(self, column):
    # the canonical orbitals or the localized ones (Multiwfn: Pipek–Mezey, Boys) in the same table
    from modules.spectrum.wavefunction.multiwfn_lmo import NAMES

    self.table_set = self.orbital_set
    kind = QComboBox()
    kind.addItem(tr('Канонические орбитали'), 'canonical')
    for key, name in NAMES.items():
        kind.addItem(tr('Локализованные · ') + tr(name), key)
    owner = self._owner()
    known = owner is not None and hasattr(owner, 'property_tool') and owner.property_tool.orbitals_file(self.orbital_set) is not None
    found = known and hasattr(owner, 'property_tool') and owner.property_tool.multiwfn_found() is not None
    kind.setEnabled(found)
    kind.setToolTip(tr('Локализованные орбитали — остовы, неподелённые пары (НП), связи. Пипек — Меззи быстрый; с '
                       'диффузными функциями базиса (aug-, -D) лучше «Беке» или Бойс') if found else
                    tr('Нужны файл этих орбиталей (Molden, fchk или .gbw ORCA) и программа Multiwfn'))
    kind.currentIndexChanged.connect(lambda *a: self.choose_orbitals(kind.currentData()))
    self.orbital_kind = kind
    column.addWidget(kind)
    table = QTableWidget(0, 5)  # «Состав» — the atoms of each orbital (Hirshfeld)
    table.setHorizontalHeaderLabels([tr('№'), tr('E, эВ'), tr('n'), '', tr('Состав')])
    header = table.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
    header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
    table.verticalHeader().hide()
    table.setShowGrid(False)
    table.setFrameShape(QFrame.Shape.NoFrame)
    table.setAlternatingRowColors(True)
    self.orbitals_table = table
    self._fill_table()
    table.cellDoubleClicked.connect(lambda *a: self.show_orbital(toggle=False))
    # Shift+click on a row puts that orbital over the one on the model (a second Shift+click takes it away)
    self._overlay = _ShiftRows(table, self.toggle_overlay)
    table.itemSelectionChanged.connect(self.refresh_lights)
    column.addWidget(table, 1)
    row = QHBoxLayout()
    row.setSpacing(6)
    self.orbital_button = QPushButton(tr('Орбиталь'))
    self.orbital_button.setToolTip(tr('Выбранная орбиталь на модели · двойной щелчок по строке; Shift+щелчок — '
                                      'наложить ещё одну'))
    self.orbital_button.clicked.connect(lambda: self.show_orbital(toggle=True))
    self.spin_button = QPushButton(tr('Спин'))
    self.spin_button.setToolTip(tr('Спиновая плотность'))
    self.spin_button.setVisible(self.orbital_set.unrestricted)
    self.spin_button.clicked.connect(lambda: self.show_density(True, toggle=True))
    owner = self._owner()
    known = owner is not None and hasattr(owner, 'property_tool') and owner.property_tool.orbitals_file(self.orbital_set) is not None
    self.composition_button = QPushButton(tr('Состав'))
    self.composition_button.setEnabled(known)
    self.composition_button.setToolTip(tr('Вклады атомов в каждую орбиталь (по Хиршфельду)') if known
                                       else tr('Нужен файл этих орбиталей (Molden, fchk или .gbw ORCA)'))
    self.composition_button.clicked.connect(self.show_composition)
    for b in (self.orbital_button, self.spin_button, self.composition_button):
        row.addWidget(b)
    row.addWidget(self._spinner('orbitals'))
    row.addStretch()
    column.addLayout(row)


def _fill_table(self, lmo=None):
    """The rows of the orbitals of self.table_set; lmo = ({number: kind}, {number: text}) for localized ones — their
    energy is «—» (the file keeps the canonical ones), the column of the marks gives the kind, «Состав» the atoms."""
    from modules.spectrum.views.orbitals_view import frontier_labels

    table, orbital_set = self.orbitals_table, self.table_set
    orbitals = orbital_set.orbitals
    labels = frontier_labels(orbital_set) if lmo is None else {}
    table.clearContents()
    table.setRowCount(len(orbitals))
    for k, o in enumerate(orbitals):
        spin = '' if not orbital_set.unrestricted else (' α' if o.spin == 'alpha' else ' β')
        key = (o.spin if orbital_set.unrestricted else 'alpha', o.number)
        localized = lmo is not None and key in lmo[0] and o.occupation > 0
        energy = '—' if localized else f'{o.energy * HARTREE_EV:.3f}'
        mark = tr(lmo[0][key]) if localized else labels.get(k, '')
        cells = [f'{o.number}{spin}', energy, f'{o.occupation:g}', mark, lmo[1].get(key, '') if localized else '']
        for c, value in enumerate(cells):
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)  # every value in the middle of its cell
            table.setItem(k, c, item)
    homo, _ = orbital_set.frontier('alpha')
    if homo is not None:
        table.selectRow(homo)
        table.scrollToItem(table.item(homo, 0), QTableWidget.ScrollHint.PositionAtCenter)


def choose_orbitals(self, key):
    """The table of the canonical orbitals or of the LMOs of a method (computed once by Multiwfn; the file of
    the LMOs is kept in «Анализ» next to the file of the orbitals, and the surfaces of an LMO are built from it)."""
    if self.panel is None:
        return False
    if key in (None, 'canonical'):
        self.table_set = self.orbital_set
        self._fill_table()
    else:
        if key not in self.lmos and not self._localize(key):
            self.orbital_kind.blockSignals(True)  # back to what the table shows
            self.orbital_kind.setCurrentIndex(max(0, self.orbital_kind.findData(
                next((k for k, v in self.lmos.items() if v[0] is self.table_set), 'canonical'))))
            self.orbital_kind.blockSignals(False)
            return False
        lmo_set, named, texts = self.lmos[key]
        self.table_set = lmo_set
        self._fill_table((named, texts))
        counts = {name: sum(1 for v in named.values() if v == name) for name in ('остов', 'НП', 'связь', 'делок.')}
        self.panel.status.setText(tr(f'Локализованные орбитали: остовов {counts["остов"]}, НП {counts["НП"]}, связей '
                                     f'{counts["связь"]}, делокализованных {counts["делок."]}.'))
    self.refresh_lights()
    return True


def _localize(self, key):
    from pathlib import Path

    from modules.spectrum.wavefunction import field_tables, multiwfn_lmo
    from modules.spectrum.readers.orbital_files import read_orbitals

    owner = self._owner()
    source = owner.property_tool.multiwfn_for(self.orbital_set) if owner is not None and hasattr(owner, 'property_tool') else None
    if source is None:
        return False
    program, path, cores = source
    open_shell = bool(getattr(self.orbital_set, 'unrestricted', False))
    found = self._quiet('orbitals', lambda step: multiwfn_lmo.run_lmo(program, path, key, cores, step,
                                                                      open_shell=open_shell),
                        tr('Локализация орбиталей…'))
    if found is None:
        return False
    fch, summary, text = found
    try:
        lmo_set = read_orbitals(fch)
        if len(lmo_set.molecule.atoms) != len(self.orbital_set.molecule.atoms):
            raise ValueError(tr('Другое число атомов в файле локализованных орбиталей.'))
    except ValueError as exc:
        self.panel.status.setText(str(exc))
        return False
    base = Path(path)
    try:  # the surfaces of an LMO are Multiwfn's grids of this file
        saved = field_tables.analysis_folder(base.parent) / f'{base.name.split(".")[0]}_lmo_{key}.fch'
        saved.write_text(fch, encoding='utf-8')
    except OSError:
        import tempfile

        saved = Path(tempfile.mkdtemp(prefix='azimuth-lmo-')) / f'lmo_{key}.fch'
        saved.write_text(fch, encoding='utf-8')
    field_tables.save_output(path, f'lmo_{key}', text)
    if hasattr(owner, 'property_tool'):
        owner.property_tool.remember_orbitals_file(lmo_set, saved)
    named = multiwfn_lmo.kinds(summary, lmo_set)
    texts = {n: multiwfn_lmo.describe(shares) for n, (_, shares) in summary.items()}
    self.lmos[key] = (lmo_set, named, texts)
    return True


def _quiet(self, name, work, title=''):
    """work(step) with the turning ring of the page (no waiting window); None after an error (said) or when busy."""
    if self.panel is None or self.busy:
        return None
    self.busy = True
    self.panel.spinner, saved = self.spinners.get(name), self.panel.spinner
    try:
        return self.panel._run(work, title)
    finally:
        self.panel.spinner = saved
        self.busy = False


def show_composition(self):
    """The Hirshfeld shares of the atoms in every orbital in the column «Состав» (the largest three)."""
    from modules.spectrum.wavefunction import multiwfn

    owner = self._owner()
    if self.panel is None or owner is None or not hasattr(owner, 'property_tool'):
        return None
    source = owner.property_tool.multiwfn_for(self.table_set)
    if source is None:
        return None
    program, path, cores = source
    count = len(self.table_set.orbitals)
    found = self._quiet('orbitals', lambda step: multiwfn.run_composition(program, path, count, cores, step),
                        tr('Состав орбиталей…'))
    if found is None:
        return None
    shares = multiwfn.composition_of(self.table_set, found[0])
    symbols = [a.symbol for a in self.table_set.molecule.atoms]
    for k, atoms in shares.items():
        ranked = sorted(atoms.items(), key=lambda item: -item[1])
        text = ' · '.join(f'{symbols[a]}{a + 1} {p:.0f} %' for a, p in ranked[:3] if p >= 1.0)
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setToolTip('\n'.join(f'{symbols[a]}{a + 1}: {p:.1f} %' for a, p in ranked))
        self.orbitals_table.setItem(k, 4, item)
    self.composition = shares
    self.refresh_lights()
    self.panel.status.setText(tr(f'Состав посчитан для {len(shares)} орбиталей из {count}.'))
    return shares
