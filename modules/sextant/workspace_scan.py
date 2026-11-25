"""The scan of Sextant: the coordinates of the constraints of Compass offered, the second coordinate, the end of a
scan chosen. Methods of SextantWorkspace (self is the window), kept here to make workspace.py shorter.

Split off modules/sextant/workspace.py (0.222.30).
"""

from azimuth.i18n import tr


def update_scan_list(self):
    """The bonds, angles and dihedrals among the constraints of Compass, with their values now, in the list
    «Координата» of the scan; the one chosen stays chosen while it is there."""
    if not hasattr(self, 'scan_index'):
        return ()
    from azimuth.core import SCAN_UNITS, coordinate_value, scan_coordinates

    try:
        mol = self.calculation_molecule()
        coordinates = scan_coordinates(self.calculation_constraints())
    except ValueError:
        mol, coordinates = None, []
    rows = []
    for kind, atoms in coordinates:
        names = '–'.join(f'{mol.atoms[i].symbol}{i + 1}' for i in atoms)
        value = coordinate_value(mol, kind, atoms)
        sign = {'B': 'r', 'A': '∠', 'D': 'φ'}[kind]
        rows.append(f'{sign}({names}) = {value:.3f} {SCAN_UNITS[kind]}' if kind == 'B'
                    else f'{sign}({names}) = {value:.1f}{SCAN_UNITS[kind]}')
    shown = [self.scan_index.itemText(k) for k in range(self.scan_index.count())]
    if shown == rows and rows:
        if getattr(self, '_scan2_wanted', None) is not None or self.scan2_index.count() != len(rows) + 1:
            self.update_scan2_list(rows, coordinates)
        return coordinates
    wanted = getattr(self, '_scan_wanted', None)
    old = self.scan_index.currentData()
    keep = wanted if wanted is not None else max(0, old or 0)
    self._scan_wanted = None
    before = self._scan_shown[old] if old is not None and 0 <= old < len(self._scan_shown) else None
    self.scan_index.blockSignals(True)
    self.scan_index.clear()
    for k, text in enumerate(rows):
        self.scan_index.addItem(text, k)
    if not rows:
        self.scan_index.addItem(tr('Нет — задайте в Компасе ограничение длины или угла'), -1)
    self.scan_index.setCurrentIndex(min(max(0, keep), max(0, len(rows) - 1)))
    self.scan_index.blockSignals(False)
    self._scan_shown = tuple(coordinates)
    if rows:  # the units of the coordinate chosen
        kind = coordinates[self.scan_index.currentIndex()][0]
        value = self.scan_end.value()
        self.scan_end.blockSignals(True)
        self.scan_end.setDecimals(3 if kind == 'B' else 1)
        self.scan_end.setSuffix(' Å' if kind == 'B' else '°')
        self.scan_end.setValue(value)
        self.scan_end.blockSignals(False)
    if rows and wanted is None and before != coordinates[self.scan_index.currentIndex()]:
        self.scan_coordinate_chosen(quiet=True)  # another coordinate: its own end value (not for a project)
    self.update_scan2_list(rows, coordinates)
    return coordinates


def update_scan2_list(self, rows, coordinates):
    """«Вторая координата» — «Нет» and the same coordinates; the one chosen stays while it is there."""
    wanted = getattr(self, '_scan2_wanted', None)
    self._scan2_wanted = None
    old = self.scan2_index.currentData()
    keep = wanted if wanted is not None else (old if old is not None else -1)
    self.scan2_index.blockSignals(True)
    self.scan2_index.clear()
    self.scan2_index.addItem(tr('Нет — одномерный скан'), -1)
    for k, text in enumerate(rows):
        self.scan2_index.addItem(text, k)
    self.scan2_index.setCurrentIndex(max(0, self.scan2_index.findData(keep if keep < len(rows) else -1)))
    self.scan2_index.blockSignals(False)
    k = self.scan2_index.currentData()
    if k is not None and 0 <= k < len(coordinates):
        kind = coordinates[k][0]
        value = self.scan2_end.value()
        self.scan2_end.blockSignals(True)
        self.scan2_end.setDecimals(3 if kind == 'B' else 1)
        self.scan2_end.setSuffix(' Å' if kind == 'B' else '°')
        self.scan2_end.setValue(value)
        self.scan2_end.blockSignals(False)


def scan2_coordinate_chosen(self, *args):
    """The end of the second coordinate chosen — as for the first (+0.5 Å, +30°, a turn of 180°)."""
    from azimuth.core import SCAN_LIMITS, coordinate_value

    k = self.scan2_index.currentData()
    if k is not None and 0 <= k < len(self._scan_shown):
        kind, atoms = self._scan_shown[k]
        start = coordinate_value(self.calculation_molecule(), kind, atoms)
        low, high = SCAN_LIMITS[kind]
        end = {'B': start + 0.5, 'A': start + 30.0, 'D': start + 180.0 if start + 180.0 <= high else start - 180.0}[kind]
        self.scan2_end.blockSignals(True)
        self.scan2_end.setDecimals(3 if kind == 'B' else 1)
        self.scan2_end.setSuffix(' Å' if kind == 'B' else '°')
        self.scan2_end.setValue(min(high, max(low, end)))
        self.scan2_end.blockSignals(False)
    self.settings_changed()
    return self.scan2_end.value()


def scan_coordinate_chosen(self, *args, quiet=False):
    """The end of the scan for the coordinate chosen — +0.5 Å for a bond, +30° for an angle, a full turn
    for a dihedral — in its units."""
    from azimuth.core import SCAN_LIMITS, coordinate_value

    k = self.scan_index.currentData()
    if k is None or k < 0 or k >= len(self._scan_shown):
        return None
    kind, atoms = self._scan_shown[k]
    start = coordinate_value(self.calculation_molecule(), kind, atoms)
    low, high = SCAN_LIMITS[kind]
    end = {'B': start + 0.5, 'A': start + 30.0, 'D': start + 360.0 if start + 360.0 <= high else start - 360.0}[kind]
    self.scan_end.blockSignals(True)
    self.scan_end.setDecimals(3 if kind == 'B' else 1)
    self.scan_end.setSuffix(' Å' if kind == 'B' else '°')
    self.scan_end.setValue(min(high, max(low, end)))
    self.scan_end.blockSignals(False)
    if not quiet:
        self.settings_changed()
    return self.scan_end.value()
