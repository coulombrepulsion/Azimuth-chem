"""CoordinateTool (window.coordinate_tool, a part of the window; was the mixin CoordinateActions of
CompassWorkspace, split from it on 2026-11-08): the table «Координаты» of Compass — drawing it, its units and
format, editing a cell back into the structure, copying and saving the coordinates."""

from dataclasses import replace

from PySide6.QtWidgets import QApplication

from azimuth.core import Molecule, read_xyz
from modules.compass.chemistry.geometry_tools import BOHR, coordinate_text
from azimuth.i18n import tr


class CoordinateTool:
    """Was the mixin CoordinateActions of the window; a part of its own — it reaches the window only through
    the names of PORT (azimuth/window_port.WindowPort)."""

    PORT = (
        'FILE_FORMATS',
        'LINE_FORMATS',
        '_coordinate_bohr',
        '_loading',
        'charge',
        'coord_format',
        'coord_note',
        'coord_text',
        'coord_units',
        'compass_mode',
        'crystal',
        'dirty',
        'error',
        'geometry_error',
        'input_tool',
        'molecule',
        'molecule_info',
        'molecule_summary',
        'naming_tool',
        'preview',
        'push_history',
        'retitled',
        'save_text',
        'site_table',
        'slab',
        'spin',
        'symmetry_timer',
        'table',
        'update_history_buttons',
        'update_measurements',
        'update_side_quill',
        'viewer',
    )

    def __init__(self, window):
        from azimuth.window_port import WindowPort

        self.w = WindowPort(window, self.PORT)


    def render_coordinate_table(self):
        self.w.table.blockSignals(True)
        factor = BOHR if self.w._coordinate_bohr else 1
        for i, atom in enumerate(self.w.molecule.atoms):
            for j, value in enumerate(atom.position, 1):
                self.w.table.item(i, j).setText(f'{value / factor:.10f}')
        self.w.table.setHorizontalHeaderLabels(
            [tr('Атом')] + [f'{a}, ' + ('a₀' if self.w._coordinate_bohr else 'Å') for a in 'XYZ']
        )
        self.w.table.blockSignals(False)

    def coordinate_units_changed(self, *args):
        try:
            self.table_molecule()
        except ValueError as exc:
            self.w.coord_units.blockSignals(True)
            self.w.coord_units.setCurrentIndex(int(self.w._coordinate_bohr))
            self.w.coord_units.blockSignals(False)
            self.w.error(exc)
            return
        self.w._coordinate_bohr = self.w.coord_units.currentIndex() == 1
        self.render_coordinate_table()
        self.refresh_coordinates()

    FRACTIONAL = 'fractional'  # the data of the item «Дробные (CIF)» of «Формат», shown in «Компас · Кристалл»

    def shown_crystal(self):
        """The crystal of the model of a crystal tab (the slab when one is shown), or None."""
        if getattr(self.w, 'compass_mode', 'molecule') != 'crystal':
            return None
        slab = getattr(self.w, 'slab', None)
        if slab is not None:
            return slab
        crystal = getattr(self.w, 'crystal', None)
        return crystal[0] if crystal else None

    # the formats of a crystal (the data of their items of
    # «Формат», shown in «Компас · Кристалл» only) and those of a calculation of one molecule, grey there
    CRYSTAL_FORMATS = ('sites', 'cif', 'poscar', 'extxyz', FRACTIONAL)
    MOLECULAR_FORMATS = ('ORCA', 'Gaussian', 'NWChem', 'Z-matrix', 'SMILES', 'InChI')

    def show_fractional_format(self, crystal_mode):
        """«Дробные (CIF)» among the formats only in «Компас · Кристалл»; leaving it, back to the table.
        All the formats of a crystal (CRYSTAL_FORMATS) the same way; the inputs of a molecule
        (MOLECULAR_FORMATS) grey in a crystal; coming into a crystal from the table — its independent atoms shown."""
        from PySide6.QtCore import Qt

        box = self.w.coord_format
        model = box.model()
        for index in range(box.count()):
            if box.itemData(index) in self.CRYSTAL_FORMATS:
                box.view().setRowHidden(index, not crystal_mode)
            elif box.itemText(index) in self.MOLECULAR_FORMATS and hasattr(model, 'item'):
                item = model.item(index)
                if item is not None:
                    item.setEnabled(not crystal_mode)
                    item.setData(tr('Для кристалла нет: выделите молекулу и перенесите её во вкладку молекулы.')
                                 if crystal_mode else '', Qt.ItemDataRole.ToolTipRole)
        current = box.currentData()
        entered = crystal_mode and not getattr(self, '_crystal_formats', False)
        self._crystal_formats = bool(crystal_mode)
        if not crystal_mode and current in self.CRYSTAL_FORMATS:
            box.setCurrentIndex(0)
        elif crystal_mode and (box.currentText() in self.MOLECULAR_FORMATS or entered and box.currentIndex() == 0):
            box.setCurrentIndex(box.findData('sites'))
        elif crystal_mode and current in self.CRYSTAL_FORMATS:
            self.refresh_coordinates()

    def site_rows(self, data):
        """[(label, symbol, x, y, z, occupancy, U_iso)] — the independent atoms of the crystal."""
        return [(s.label, s.symbol, s.x, s.y, s.z, s.occupancy, s.u_iso) for s in data.sites]

    def sites_note(self, data):
        """The cell and the group over the table of the independent atoms."""
        from modules.compass.chemistry import crystal as cr

        c = data.cell
        group = data.space_group or 'P 1'
        if data.number:
            group += f' (№ {data.number})'
        try:
            in_cell = len(cr.unit_cell(data))
        except ValueError:
            in_cell = 0
        return (tr('{}: a = {:.4f}, b = {:.4f}, c = {:.4f} Å; α = {:.3f}, β = {:.3f}, γ = {:.3f}°; V = {:.2f} Å³.').format(
                    group, c.a, c.b, c.c, c.alpha, c.beta, c.gamma, c.volume())
                + ' ' + tr('Независимых атомов: {}, в ячейке: {}. Строка таблицы выделяет копии атома на модели.').format(
                    len(data.sites), in_cell))

    def fill_site_table(self, data):
        from PySide6.QtWidgets import QTableWidgetItem

        table = self.w.site_table
        rows = self.site_rows(data)
        table.blockSignals(True)
        table.setRowCount(len(rows))
        table.setHorizontalHeaderLabels([tr('Метка'), tr('Атом'), 'x', 'y', 'z', tr('Заселённость'), 'U, Å²'])
        for i, row in enumerate(rows):
            texts = [row[0], row[1]] + [f'{v:.6f}' for v in row[2:5]] + [f'{row[5]:g}', f'{row[6]:.4f}' if row[6] else '']
            for j, text in enumerate(texts):
                table.setItem(i, j, QTableWidgetItem(text))
        table.blockSignals(False)
        return '\n'.join('\t'.join([row[0], row[1]] + [f'{v:.6f}' for v in row[2:5]] + [f'{row[5]:g}']) for row in rows)

    def site_selection_changed(self):
        """The rows chosen in the table of the independent atoms — their copies selected on the model."""
        from modules.compass.chemistry import crystal as cr

        data = self.shown_crystal()
        if data is None:
            return
        chosen = {self.w.site_table.item(i.row(), 0).text() for i in self.w.site_table.selectedIndexes()
                  if self.w.site_table.item(i.row(), 0) is not None}
        try:
            labels = cr.model_sites(data, self.w.molecule)
        except (ValueError, ArithmeticError):
            return
        self.w.viewer.set_selection([k for k, (label, _) in enumerate(labels) if label in chosen])

    def crystal_text(self, kind):
        """The text of a format of a crystal: its CIF (the group and the independent atoms), its cell as
        POSCAR or as the extended XYZ."""
        from modules.compass.chemistry import crystal_export
        from modules.compass.chemistry import surface

        data = self.shown_crystal()
        if data is None:
            raise ValueError(tr('Дробные координаты — у кристалла: откройте CIF во вкладке «Компас · Кристалл».'))
        if kind == 'sites':
            return self.fill_site_table(data)
        if kind == 'cif':
            return surface.write_cif(data)
        try:
            return crystal_export.poscar(data) if kind == 'poscar' else crystal_export.extended_xyz(data)
        except ValueError:
            raise ValueError(tr('В ячейке нет атомов.')) from None

    def fractional_text(self):
        from modules.compass.chemistry import crystal as cr
        from modules.compass.chemistry import surface

        data = self.shown_crystal()
        if data is None:
            raise ValueError(tr('Дробные координаты — у кристалла: откройте CIF во вкладке «Компас · Кристалл».'))
        return surface.write_cif(cr.block_crystal(data, self.w.molecule))

    def coordinate_format_changed(self, *args):
        angstrom = (self.w.coord_format.currentText() in ('XYZ', 'Z-matrix') + self.w.FILE_FORMATS + self.w.LINE_FORMATS
                    or self.w.coord_format.currentData() in self.CRYSTAL_FORMATS)
        if self.w.coord_format.currentText() == 'InChI' and self.w.has('naming_tool'):
            self.w.naming_tool.forget_failed_inchi()  # chosen again: a failed request is repeated
        if angstrom:
            self.w.coord_units.setCurrentIndex(0)
        self.w.coord_units.setEnabled(not angstrom)
        self.w.table.setVisible(self.w.coord_format.currentIndex() == 0)
        sites = self.w.coord_format.currentData() == 'sites'
        self.w.coord_text.setVisible(self.w.coord_format.currentIndex() != 0 and not sites)
        if self.w.has('site_table'):  # the independent atoms of a crystal
            self.w.site_table.setVisible(sites)
        self.refresh_coordinates()

    def refresh_coordinates(self):
        fmt = self.w.coord_format.currentText()
        try:
            mol = self.table_molecule()
            charge = self.w.charge.value() if self.w.has('charge') else 0
            spin = self.w.spin.value() if self.w.has('spin') else 1
            kind = self.w.coord_format.currentData()
            if kind == self.FRACTIONAL:
                self.w.coord_text.setPlainText(self.fractional_text())
            elif kind in self.CRYSTAL_FORMATS:
                self.w.coord_text.setPlainText(self.crystal_text(kind))
            elif fmt == 'Z-matrix':
                from modules.compass.chemistry import zmatrix

                rows = zmatrix.build(mol)
                self.w.coord_text.setPlainText(zmatrix.text(rows) if mol.atoms else '')
            elif fmt in self.w.FILE_FORMATS:
                from modules.compass.chemistry import formats
                from modules.compass.chemistry.editing import perceived_orders

                bonds = formats.kekule(len(mol.atoms), perceived_orders(mol))
                writer = {
                    'MOL': formats.write_mol,
                    'SDF': formats.write_sdf,
                    'MOL2': formats.write_mol2,
                    'PDB': formats.write_pdb,
                }[fmt]
                self.w.coord_text.setPlainText(writer(mol, bonds))
            elif fmt == 'SMILES':
                from modules.compass.chemistry import pubchem

                self.w.coord_text.setPlainText(pubchem.to_smiles(mol))
            elif fmt == 'InChI':
                self.w.coord_text.setPlainText(self.w.naming_tool.inchi_text(mol))
            else:
                self.w.coord_text.setPlainText(coordinate_text(mol, fmt, self.w._coordinate_bohr, charge, spin))
            if kind == 'sites':
                note = self.sites_note(self.shown_crystal())
            elif kind == 'cif':
                note = tr('CIF кристалла: группа симметрии, ячейка и независимые атомы — как в файле (одна часть '
                          'разупорядочения, если выбрана); атомы, добавленные на модели, сюда не входят.')
            elif kind == 'poscar':
                note = tr('POSCAR (VASP 5): векторы ячейки в Å и все атомы одной ячейки в долях (Direct), по элементам.')
            elif kind == 'extxyz':
                note = tr('Расширенный XYZ (ASE, OVITO): все атомы одной ячейки в Å и её векторы в строке Lattice.')
            elif kind == self.FRACTIONAL:
                note = tr('Атомы модели в долях ячейки (за пределами первой ячейки — больше 1), с метками и заселённостями '
                          'из файла; весь текст — CIF этого блока в группе P 1.')
            elif fmt == 'Gaussian':
                note = (
                    tr('Блок геометрии Gaussian. В маршрут расчёта добавьте Units=')
                    + ('Bohr' if self.w._coordinate_bohr else 'Angstrom')
                    + tr('. Метод и базис задаются отдельно.')
                )
            elif fmt in ('ORCA', 'NWChem'):
                note = tr('Блок геометрии, не полный входной файл. Метод и базис задаются отдельно.')
            elif fmt == 'XYZ':
                note = tr('Стандартный XYZ: координаты всегда в ангстремах.')
            elif fmt == 'Z-matrix':
                note = tr(
                    'Z-матрица: атом, номер атома и расстояние (Å), номер и угол (°), номер и двугранный угол (°). Gaussian — после строки заряда и мультиплетности; ORCA — между «* gzmt заряд мульт» и «*».'
                )
                rows = zmatrix.build(mol)
                if any(r[4] is not None and r[6] is not None and not 5 < r[4] < 175 for r in rows[3:]):
                    note += tr(
                        ' Есть линейный фрагмент: двугранный угол там не определён, может понадобиться фиктивный атом.'
                    )
            elif fmt in self.w.FILE_FORMATS:
                note = tr(
                    'Файл со связями (порядки — из структуры, ароматика — в форме Кекуле); координаты в ангстремах.'
                )
                if fmt in ('MOL', 'SDF') and len(mol.atoms) > 999:
                    note += tr(' Атомов больше 999 — молфайл версии V3000.')
            elif fmt == 'SMILES':
                note = tr(
                    'SMILES по связям структуры (порядки — как в Компасе, ароматика — в форме Кекуле), без стереохимии. Построить молекулу по SMILES — «Файл → Молекула по SMILES…».'
                )
            elif fmt == 'InChI':
                note = tr('InChI и InChIKey даёт PubChem по SMILES структуры (нужен интернет): сама программа InChI не считает.')
            else:
                note = tr('Редактируйте таблицу. Переключение единиц меняет представление, а не размер молекулы.')
            self.w.coord_note.setText(note)
        except ValueError as exc:
            self.w.coord_text.clear()
            if self.w.has('site_table'):
                self.w.site_table.setRowCount(0)
            self.w.coord_note.setText(str(exc))

    def copy_coordinates(self):
        self.refresh_coordinates()
        if self.w.coord_text.toPlainText():
            QApplication.clipboard().setText(self.w.coord_text.toPlainText())
            from azimuth.ui import copied

            fmt = self.w.coord_format.currentText() if hasattr(self.w.coord_format, 'currentText') else ''
            copied(self.w.coord_text, tr('координаты') + (f' ({fmt})' if fmt else ''))

    def save_coordinates(self):
        self.refresh_coordinates()
        text = self.w.coord_text.toPlainText()
        if not text:
            self.w.error(ValueError(tr('Исправьте координаты перед сохранением')))
            return
        fmt = self.w.coord_format.currentText()
        # Gaussian block needs a separate route option, so keep its units explicit in the file name.
        suffix = 'bohr' if self.w._coordinate_bohr else 'angstrom'
        kind = self.w.coord_format.currentData()
        if kind in (self.FRACTIONAL, 'cif'):
            fmt = 'CIF'
        elif kind == 'poscar':  # VASP reads the file named POSCAR
            self.w.save_text(tr('Сохранить блок координат'), tr('POSCAR VASP (POSCAR *.vasp)'), text, 'POSCAR')
            return
        elif kind == 'extxyz':
            fmt = 'XYZ'
        elif kind == 'sites':
            fmt = 'TSV'
        extension = {'TSV': 'tsv', 'CIF': 'cif', 'XYZ': 'xyz', 'MOL': 'mol', 'SDF': 'sdf', 'MOL2': 'mol2', 'PDB': 'pdb', 'Z-matrix': 'gzmt', 'SMILES': 'smi'}.get(
            fmt, 'txt'
        )
        self.w.save_text(
            tr('Сохранить блок координат'),
            tr('Текст (*.') + extension + ')',
            text,
            'geometry-' + suffix + '.' + extension,
        )

    def table_molecule(self):
        if self.w.table.rowCount() == 0:
            return Molecule(self.w.molecule.title, (), ())
        rows = []
        for i in range(self.w.table.rowCount()):
            cells = [self.w.table.item(i, j).text().strip() if self.w.table.item(i, j) else '' for j in range(4)]
            if self.w._coordinate_bohr:
                cells[1:] = [str(float(v) * BOHR) for v in cells[1:]]
            rows.append(' '.join(cells))
        text = f'{len(rows)}\n{self.w.molecule.title}\n' + '\n'.join(rows)
        # 0.108.67 (the measurement of a project of 44 molecules: 16 calls for each choice of a molecule, each one
        # reading and checking the whole table again): the same text of the table is read once
        last = getattr(self, '_last_table', None)
        if last is not None and last[0] == text:
            molecule = last[1]
        else:
            molecule = read_xyz(text)
            self._last_table = (text, molecule)
        return replace(molecule, title=self.w.molecule.title, bonds=self.w.molecule.bonds)

    def table_changed(self, *args):
        self.w.dirty = True
        try:
            molecule = self.table_molecule()
            if not self.w._loading:
                molecule = self.w.retitled(molecule)
            if not self.w._loading and molecule != self.w.molecule:
                self.w.push_history()
            self.w.molecule = molecule
            self.w.viewer.set_molecule(molecule)
            self.w.molecule_info.setText(self.w.molecule_summary(molecule))
            self.w.update_side_quill()
            if self.w.has('symmetry_timer'):
                self.w.symmetry_timer.start()
            self.w.geometry_error.hide()
            self.w.update_history_buttons()
            self.w.update_measurements(self.w.viewer.selected)
        except ValueError as exc:
            self.w.geometry_error.setText(str(exc))
            self.w.geometry_error.show()
            self.w.molecule_info.setText(
                tr('Исправьте координаты. Построение временно заблокировано; показана последняя корректная структура.')
            )
        if self.w.has('preview'):
            self.w.input_tool.refresh_input()
        if self.w.has('coord_text'):
            self.refresh_coordinates()

    def table_selection_changed(self):
        chosen = {item.row() for item in self.w.table.selectedIndexes()}
        indices = [i for i in self.w.viewer.selected if i in chosen] + sorted(chosen - set(self.w.viewer.selected))
        self.w.viewer.set_selection(indices)
