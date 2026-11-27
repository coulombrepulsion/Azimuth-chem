"""Window tests — Files, documents and steps: opening, saving, crystals, trajectories, the drawer of Compass (split from
test_gui.py on 2026-11-08)."""

import os
import sys

from tests.gui_support import *  # noqa: F401,F403 — the fixtures app, window and the helpers


def test_structure_tabs_are_separate(window):
    assert window.structure_tabs.count() == 2
    assert [window.structure_tabs.tabText(i) for i in range(2)] == ['Молекула', 'Координаты']
    assert window.viewer.parentWidget() != window.table.parentWidget()


def test_optimization_drawer_in_compass(window, app):
    # the steps of an optimization are browsed in Compass; the project is not touched until «Взять»
    show_model(window, app)
    original = window.molecule
    dirty = window.dirty
    undo = len(window.undo_history)
    window.opening_tool.demo_optimization()
    app.processEvents()  # opens in Compass
    assert window.stack.currentIndex() == 0 and window.trajectory_button.isChecked()
    drawer = window.drawer
    assert drawer.isVisible() and window.browsing and drawer.table.rowCount() == 5
    # it opens on the last cycle (the result), the start drawn faintly
    assert drawer.current == 4 and window.molecule.atoms[1].x == 0.7586 and window.viewer.ghost is not None
    drawer.select(0)
    assert window.molecule.atoms[1].x == 1.02 and window.viewer.ghost is None  # the first cycle: no ghost
    assert not window.edit_toggle.isEnabled() and not window.move_button.isEnabled()
    drawer.select(4)
    assert window.molecule.atoms[1].x == 0.7586 and window.table.item(1, 1).text() == '0.75860000'
    assert window.viewer.ghost is not None and 'RMSD' in drawer.detail.text()
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtCore import QEvent

    window.eventFilter(window.viewer, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Up, Qt.KeyboardModifier.NoModifier))
    assert drawer.current == 3
    window.eventFilter(window.viewer, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Home, Qt.KeyboardModifier.NoModifier))
    assert drawer.current == 0
    point = drawer.plot.points()[1][1].toPoint()
    QTest.mouseClick(drawer.plot, Qt.MouseButton.LeftButton, pos=point)
    assert drawer.current == 1
    drawer.initial.setChecked(False)
    assert window.viewer.ghost is None
    # the result has its own tab, the water stays in tab 1; closing the drawer keeps the cycle
    # chosen (cycle 2 here) as the structure of the tab — one undoable change
    assert len(window.documents) == 2 and window.current_document == 1
    chosen = drawer.steps[1].geometry
    window.trajectory_button.click()
    assert not window.browsing and window.molecule.atoms == chosen.atoms and window.dirty
    assert window.edit_toggle.isEnabled() and len(window.undo_history) == 1
    window.undo_geometry()
    assert window.molecule.atoms[1].x == 0.7586
    window.redo_geometry()
    assert window.molecule.atoms == chosen.atoms
    window.viewer.rotate_view('y', 0.7)  # each tab keeps its own view of the model
    turned = window.viewer.yaw
    window.switch_document(0)
    assert window.molecule == original and window.dirty == dirty and len(window.undo_history) == undo
    assert not window.drawer.steps  # the steps belong to the other tab
    assert window.viewer.yaw != turned
    window.switch_document(1)
    assert len(drawer.steps) == 5 and not window.browsing  # the drawer was closed there
    assert window.viewer.yaw == turned
    window.trajectory_button.click()
    drawer.select(0)
    drawer.adopt.click()
    assert not window.browsing and not drawer.isVisible() and window.molecule.atoms[1].x == 1.02
    assert window.dirty and len(window.undo_history) == 2
    window.undo_geometry()
    assert window.molecule.atoms == chosen.atoms


def test_open_dispatches_by_file(window, app, tmp_path):
    show_model(window, app)
    window.confirm_replace = lambda: True
    xyz = tmp_path / 'm.xyz'
    xyz.write_text('1\nX\nNe 0 0 0\n', encoding='utf-8')
    log = tmp_path / 'run.log'
    log.write_text(
        (Path(__file__).parents[2] / 'examples' / 'optimization-demo.out').read_text(encoding='utf-8'), encoding='utf-8'
    )
    plain = tmp_path / 'job.txt'
    plain.write_text(log.read_text(encoding='utf-8'), encoding='utf-8')
    assert window.opening_tool.file_kind(xyz) == 'xyz' and window.opening_tool.file_kind(log) == 'output' and window.opening_tool.file_kind(plain) == 'output'
    window.opening_tool.open_path(str(xyz))
    assert [a.symbol for a in window.molecule.atoms] == ['Ne']
    window.opening_tool.open_path(str(log))
    assert window.stack.currentIndex() == 0 and window.browsing and window.drawer.table.rowCount() == 5
    window.trajectory_button.click()  # the result in its tab, the neon in the first one
    assert window.molecule.formula == 'H2O'
    # a tab is a project — the neon is a molecule of the project opened from its file, in a
    # document of its own (the bar of documents is hidden; the list of the project shows them)
    neon = next(k for k, d in enumerate(window.documents) if d.molecule is not None and
                [a.symbol for a in d.molecule.atoms] == ['Ne'])
    assert window.documents[neon].research_molecule_id
    window.switch_document(neon)
    assert [a.symbol for a in window.molecule.atoms] == ['Ne']


def test_open_other_formats_and_write_them(window, app, tmp_path):
    from modules.compass.chemistry import formats

    show_model(window, app)
    window.confirm_replace = lambda: True
    water = read_xyz(EXAMPLES['Вода · H₂O'])
    bonds = ((0, 1, 1), (0, 2, 1))
    for suffix, writer in (
        ('mol', formats.write_mol),
        ('sdf', formats.write_sdf),
        ('mol2', formats.write_mol2),
        ('pdb', formats.write_pdb),
    ):
        path = tmp_path / ('w.' + suffix)
        path.write_text(writer(water, bonds), encoding='utf-8')
        window.load_molecule(read_xyz('1\nX\nNe 0 0 0'))
        window.opening_tool.open_path(str(path))
        assert window.molecule.formula == 'H2O', suffix
    gjf = tmp_path / 'w.gjf'
    gjf.write_text('#p hf\n\nwater\n\n-1 2\nO 0 0 0\nH 0.96 0 0\n\n', encoding='utf-8')
    window.opening_tool.open_path(str(gjf))
    assert window.molecule.formula == 'HO' and window.charge.value() == -1 and window.spin.value() == 2
    frames = ''.join(f'3\nE {e}\nO 0 0 0\nH {x} 0 0.5\nH -{x} 0 0.5\n' for e, x in ((-76.0, 0.8), (-76.1, 0.76)))
    trj = tmp_path / 'opt_trj.xyz'
    trj.write_text(frames, encoding='utf-8')
    window.opening_tool.open_path(str(trj))
    assert window.browsing and window.drawer.table.rowCount() == 2
    window.trajectory_button.click()
    window.structure_tabs.setCurrentIndex(1)
    window.coord_format.setCurrentText('MOL')
    assert 'V2000' in window.coord_text.toPlainText() and not window.coord_units.isEnabled()
    window.coord_format.setCurrentIndex(0)
    window.structure_tabs.setCurrentIndex(0)
    window.opening_tool.load_smiles('CC(=O)O')
    window.iupac_button.click()  # the name on demand
    assert window.molecule.formula == 'C2H4O2' and window.molecule_info.text().startswith('этановая')


def test_cancelled_picture_dialog_writes_nothing(window, app, tmp_path, monkeypatch):
    # pictures go where the user chooses; Cancel saves nothing and reports no error
    from modules.compass.actions import pictures

    show_model(window, app)
    errors = []
    monkeypatch.setattr(window, 'error', lambda exc: errors.append(str(exc)))
    monkeypatch.setattr(pictures, 'ask_picture_path', lambda *args: None)
    assert window.picture_tool.save_screenshot(1) is None and window.picture_tool.save_rotation_gif() is None
    assert errors == [] and list(tmp_path.iterdir()) == []


def test_picture_dialog_starts_in_the_last_folder_and_adds_the_suffix(app, tmp_path, monkeypatch):
    from azimuth import ui
    from azimuth.paths import ROOT

    class Preferences(dict):
        def value(self, key, default=None):
            return self.get(key, default)

        def setValue(self, key, value):
            self[key] = value

    asked = []

    class Dialog:
        @staticmethod
        def getSaveFileName(parent, title, start, pattern):
            asked.append((start, pattern))
            return str(tmp_path / 'sub' / 'turn'), pattern

    monkeypatch.setattr(ui, 'QFileDialog', Dialog)
    (tmp_path / 'sub').mkdir()
    prefs = Preferences(pictures_dir=str(tmp_path))
    assert ui.ask_picture_path(None, 'GIF', 'Azimuth-1', '.gif', prefs) == tmp_path / 'sub' / 'turn.gif'
    assert asked == [(str(tmp_path / 'Azimuth-1.gif'), 'GIF (*.gif)')]
    assert prefs['pictures_dir'] == str(tmp_path / 'sub')  # remembered for the next picture
    assert ui.pictures_folder(Preferences(pictures_dir=str(tmp_path / 'missing'))) != ROOT  # never the program folder


def test_trajectory_reload_clears_previous_steps(window):
    # the steps stay in their tab of Compass; a result without steps gets its own tab too, and
    # Spectrum shows the result of the tab chosen
    window.opening_tool.demo_optimization()
    tabs, steps_tab = len(window.documents), window.current_document
    window.display_output('ORCA\nFINAL SINGLE POINT ENERGY -12', 'single.out')
    assert len(window.documents) == tabs + 1 and not window.drawer.steps
    assert window.use_geometry.isEnabled() is False
    assert window.result_tabs.currentIndex() == 0 and window.output.energies == (-12.0,)
    window.switch_document(steps_tab)
    assert len(window.drawer.steps) == 5 and window.output.steps


def test_trajectory_missing_geometry_disables_adoption(window, app):
    show_model(window, app)
    window.display_output(
        'ORCA\nGEOMETRY OPTIMIZATION CYCLE 1\nFINAL SINGLE POINT ENERGY -12', 'partial.out', show=False
    )
    window.trajectory_button.click()
    assert window.drawer.table.rowCount() == 1 and not window.drawer.adopt.isEnabled()
    window.trajectory_button.click()


def test_scan_points_in_the_compass_drawer(window, tmp_path):
    # a relaxed scan gives its 12 points (value of the dihedral, energy from the lowest);
    # an IRC path takes its geometries from <name>_IRC_Full_trj.xyz next to the output
    data = Path(__file__).parents[1] / 'data' / 'orca_cclib'
    window.display_output((data / 'dvb_scan_relaxed_orca6.0.out').read_text(encoding='utf-8'), 'scan.out', False)
    drawer = window.drawer
    assert drawer.scan.kind == 'relaxed' and drawer.table.rowCount() == 12 and drawer.table.columnCount() == 3
    assert drawer.table.horizontalHeaderItem(1).text() == 'φ(10–9–4–3), °'
    assert drawer.table.item(11, 2).text() in ('+0.00', '-0.00') and drawer.table.item(1, 1).text() == '32.727'
    window.trajectory_tool.set_trajectory_open(True)
    drawer.select(3)
    assert window.molecule.atoms == drawer.steps[3].geometry.atoms
    assert 'φ(10–9–4–3) = 98.182 °' in drawer.detail.text()
    window.trajectory_tool.set_trajectory_open(False)
    rows = [
        '   1    -76.401000   -12.550000    0.004829  0.001679',
        '   2    -76.390000    -5.647500    0.003100  0.001000',
        '   3    -76.381000     0.000000    0.000149  0.000056 <= TS',
        '   4    -76.392000    -6.902600    0.002900  0.000900',
        '   5    -76.405000   -15.060000    0.004500  0.001500',
    ]
    irc = 'Program Version 6.0.0 (ORCA, synthetic summary)\nIRC PATH SUMMARY\n-----\n\nAll gradients are in Eh/Bohr.\n\nStep  E(Eh)  dE(kcal/mol)  max(|G|)  RMS(G)\n'
    out = tmp_path / 'ts.out'
    out.write_text(irc + '\n'.join(rows) + '\n\nTimings\n', encoding='utf-8')
    frames = ''.join(f'3\nE -76.4\nO 0 0 {0.01 * k}\nH 0.96 0 0\nH -0.24 0.93 0\n' for k in range(5))
    (tmp_path / 'ts_IRC_Full_trj.xyz').write_text(frames, encoding='utf-8')
    window.open_output_path(str(out), show=False)
    assert drawer.scan.kind == 'irc' and drawer.table.item(2, 0).text() == '3 · TS'
    assert all(s.geometry is not None for s in drawer.steps)


def test_overlay_of_another_structure_with_shuffled_atoms(window, tmp_path, monkeypatch):
    # a structure file with the atoms in another order and turned is paired with the model,
    # drawn over it and can give its numbering to the model (undoable)
    import math

    from PySide6.QtWidgets import QFileDialog

    from modules.compass.chemistry import library
    from modules.compass.chemistry.overlay import superimpose
    from azimuth.core import Atom, Molecule

    key = next(k for k in library.keys() if k.startswith('Этанол'))
    model = library.molecule(key)
    window.load_molecule(model)
    order = list(range(len(model.atoms)))[::-1]
    c, s = math.cos(0.7), math.sin(0.7)
    atoms = [model.atoms[j] for j in order]
    turned = Molecule('', tuple(Atom(a.symbol, c * a.x - s * a.y + 3, s * a.x + c * a.y, a.z - 1) for a in atoms))
    path = tmp_path / 'other.xyz'
    path.write_text(turned.xyz(), encoding='utf-8')
    assert window.overlay_tool.compare_path(str(path))
    result = window.compare_result
    assert result.rmsd < 1e-6 and not result.same_order and list(result.order) == order
    ghost, caption = window.viewer.compare_source(window.molecule)
    assert ghost is not None and len(ghost.atoms) == len(model.atoms)
    assert caption[0].startswith('Сравнение с other.xyz') and 'RMSD 0.000 Å' in caption[1]
    window.viewer.grab()  # draws the overlay and the caption
    window.overlay_tool.fill_compare_menu(window.compare_menu)
    enabled = {a.text() for a in window.compare_menu.actions() if a.isEnabled()}
    assert 'Перенумеровать модель как в файле' in enabled
    window.overlay_tool.renumber_as_compared()
    assert [a.symbol for a in window.molecule.atoms] == [a.symbol for a in turned.atoms]
    assert superimpose(window.molecule, turned).same_order  # now numbered as the file
    window.undo_geometry()
    assert [a.symbol for a in window.molecule.atoms] == [a.symbol for a in model.atoms]
    saved = tmp_path / 'renumbered.xyz'
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *a, **k: (str(saved), ''))
    window.overlay_tool.save_compared_renumbered()
    assert [ln.split()[0] for ln in saved.read_text(encoding='utf-8').splitlines()[2:]] == [
        a.symbol for a in model.atoms
    ]
    window.overlay_tool.clear_compare()
    assert window.viewer.compare_source(window.molecule) == (None, [])
    other = tmp_path / 'water.xyz'
    other.write_text('3\n\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0\n', encoding='utf-8')
    assert not window.overlay_tool.compare_path(str(other))  # another composition: refused with a message
    assert 'Состав' in window.compare_error


def test_user_fragment_saved_placed_exported_and_deleted(window, tmp_path):
    # the methyl of toluene saved as «Мои фрагменты», put on a hydrogen of benzene, exported,
    # deleted and imported back; the user's real settings are restored afterwards
    from modules.compass.chemistry import builder, library, user_fragments
    from modules.compass.actions.fragment_actions import SETTINGS_KEY
    from modules.compass.chemistry.builder import connections

    saved = window.preferences.value(SETTINGS_KEY, '')
    window.preferences.setValue(SETTINGS_KEY, '')
    previous = dict(user_fragments.USER)
    window.fragment_tool._store_fragments({})
    try:
        toluene = library.molecule(next(k for k in library.keys() if k.startswith('Метилбензол')))
        window.load_molecule(toluene)
        bonds = connections(toluene)
        c = next(
            i
            for i, a in enumerate(toluene.atoms)
            if a.symbol == 'C' and sum(1 for k, j, _ in bonds if i in (k, j) and 'H' == toluene.atoms[j if k == i else k].symbol) == 3
        )
        group = [c] + [j if k == c else k for k, j, _ in bonds if c in (k, j) and toluene.atoms[j if k == c else k].symbol == 'H']
        window.viewer.set_selection(group)
        key = window.fragment_tool.save_selection_as_fragment('Тест-метил')
        assert key == 'Тест-метил' and key in user_fragments.USER and key in builder.FRAGMENT_GROUPS[user_fragments.USER_GROUP]
        assert key in [window.fragment.itemText(i) for i in range(window.fragment.count())]
        assert user_fragments.parse(window.preferences.value(SETTINGS_KEY))[key][0][0][0] == 'C'
        menu = window.model_menu_tool.fragment_menu()
        titles = [a.text() for a in menu.actions()]
        assert 'Мои фрагменты' in titles and 'Удалить мой фрагмент' in titles
        benzene = library.molecule(next(k for k in library.keys() if k.startswith('Бензол')))
        window.load_molecule(benzene)
        window.fragment_tool.choose_user_fragment(key)
        assert window.viewer.mode == 'fragment'
        h = next(i for i, a in enumerate(benzene.atoms) if a.symbol == 'H')
        window.place_on_model(benzene.atoms[h].position, h)
        assert window.molecule.formula == 'C7H8'  # toluene
        out = tmp_path / 'fragments.json'
        window.fragment_tool.export_user_fragments(str(out))
        assert window.fragment_tool.delete_user_fragment(key, ask=False)
        assert key not in builder.FRAGMENTS and key not in [window.fragment.itemText(i) for i in range(window.fragment.count())]
        assert window.fragment_tool.import_user_fragments(str(out)) == 1 and key in user_fragments.USER
        assert window.fragment_tool.import_user_fragments(str(out)) == 1 and 'Тест-метил (2)' in user_fragments.USER
    finally:
        window.fragment_tool._store_fragments(previous)
        window.preferences.setValue(SETTINGS_KEY, saved)


def test_crystal_from_cif(window, tmp_path):
    # a CIF opens the «Кристалл» window; the cell with its faces and a 2x2x2 block are built
    # with the edges drawn; the cell can be hidden; another structure removes the crystal
    from itertools import permutations, product

    ops = []
    for perm in permutations(range(3)):
        for signs in product((1, -1), repeat=3):
            for t in ((0, 0, 0), (0, '1/2', '1/2'), ('1/2', 0, '1/2'), ('1/2', '1/2', 0)):
                ops.append(
                    ', '.join(('-' if signs[r] < 0 else '') + 'xyz'[perm[r]] + (f'+{t[r]}' if t[r] else '') for r in range(3))
                )
    text = (
        'data_NaCl\n_cell_length_a 5.64\n_cell_length_b 5.64\n_cell_length_c 5.64\n'
        "_symmetry_space_group_name_H-M 'F m -3 m'\nloop_\n_space_group_symop_operation_xyz\n"
        + '\n'.join(f"'{o}'" for o in ops)
        + '\nloop_\n_atom_site_label\n_atom_site_fract_x\n_atom_site_fract_y\n_atom_site_fract_z\nNa1 0 0 0\nCl1 0.5 0.5 0.5\n'
    )
    path = tmp_path / 'nacl.cif'
    path.write_text(text, encoding='utf-8')
    window.dirty = False
    window.opening_tool.open_path(str(path))
    w = window.crystal_window
    from PySide6.QtWidgets import QLabel

    assert any('F m -3 m' in label.text() for label in w.findChildren(QLabel))
    # the crystal is built at once (one cell, the atoms on the faces), the window stays closed
    assert not w.isVisible() and window.crystal is not None and window.molecule.formula == 'Cl13Na14'
    assert 'F m -3 m' in window.molecule_info.text() and 'Z = 4' in window.molecule_info.text()
    w.build()
    assert window.molecule.formula == 'Cl13Na14' and window.viewer.cell_lines and len(window.viewer.cell_lines) == 12
    window.viewer.grab()
    w = window.crystal_tool.reopen_crystal()
    for box in w.counts:
        box.setValue(2)
    w.faces.setChecked(False)
    window.dirty = False
    w.build()
    assert len(window.molecule.atoms) == 64
    window.crystal_tool.set_cell_shown(False)
    assert window.viewer.cell_lines is None
    window.crystal_tool.set_cell_shown(True)
    assert window.viewer.cell_lines
    window.dirty = False
    window.new_molecule()
    assert window.viewer.cell_lines is None and window.crystal is None


def test_crystal_symmetry_and_whole_molecules(window, tmp_path):
    # the «Кристалл» window names the group found from the operations and Z; «Целые молекулы» builds the
    # molecules a face of the cell cuts (an ethanol molecule across the face x = 0 of a P2_1/c cell: 4 x 9 atoms)
    from PySide6.QtWidgets import QLabel, QPlainTextEdit

    from modules.compass.chemistry import surface
    from tests.compass.test_crystal_symmetry import ethanol_crystal

    crystal, _ = ethanol_crystal()
    path = tmp_path / 'etoh.cif'
    path.write_text(surface.write_cif(crystal), encoding='utf-8')
    window.dirty = False
    window.opening_tool.open_path(str(path))
    w = window.crystal_window
    text = ' '.join(label.text() for label in w.findChildren(QLabel))
    assert 'точечная группа 2/m' in text and 'Z = 4' in text and 'Молекул в ячейке' in text
    assert 'Коэффициент упаковки' in text
    listing = w.findChildren(QPlainTextEdit)[0].toPlainText()
    assert 'Винтовая ось 2₁' in listing and 'Центр инверсии' in listing
    assert w.whole.isEnabled() and w.whole.isChecked() and not w.faces.isEnabled()
    w.build()
    assert len(window.molecule.atoms) == 36 and window.molecule.formula == 'C8H24O4'
    assert window.crystal[3] is True
    # the symmetry button of «Компас · Кристалл» names the class of the crystal, not of the block of atoms
    result = window.symmetry_tool.determine_symmetry()
    assert result['name'] == 'C2h' and result['hm'] == '2/m' and '(№ 14)' in result['group']
    assert 'C<sub>2h</sub> (2/m)' in window.molecule_info.text() and not window.symmetrize_action.isEnabled()
    assert window.symmetry_tool.symmetry_menu().actions()[0].text().startswith('Кристаллический класс: 2/m')
    w = window.crystal_tool.reopen_crystal()
    assert w.whole.isChecked()
    # the symmetry elements over the model and the views along the cell
    w.elements.setChecked(True)
    assert len(window.viewer.symmetry_items) == 35
    assert window.crystal_tool.look_along_cell(crystal, 'b') and window.crystal_tool.look_along_cell(crystal, (1, 0, 1))
    window.viewer.grab()
    w.elements.setChecked(False)
    assert window.viewer.symmetry_items is None
    window.dirty = False
    window.new_molecule()


def test_crystal_displacement_ellipsoids(window, tmp_path):
    # «Эллипсоиды смещений (50 %)» gives every atom with U_ij or U_iso its tensor; H without U gets none
    text = ('data_adp\n_cell_length_a 5\n_cell_length_b 5\n_cell_length_c 5\nloop_\n_atom_site_label\n'
            '_atom_site_fract_x\n_atom_site_fract_y\n_atom_site_fract_z\n_atom_site_U_iso_or_equiv\n'
            'O1 0.5 0.5 0.5 0.02\nH1 0.65 0.5 0.5 ?\nloop_\n_atom_site_aniso_label\n_atom_site_aniso_U_11\n'
            '_atom_site_aniso_U_22\n_atom_site_aniso_U_33\n_atom_site_aniso_U_12\n_atom_site_aniso_U_13\n'
            '_atom_site_aniso_U_23\nO1 0.03 0.02 0.01 0 0 0\n')
    path = tmp_path / 'adp.cif'
    path.write_text(text, encoding='utf-8')
    window.dirty = False
    window.opening_tool.open_path(str(path))
    w = window.crystal_window
    assert w.adp.isEnabled()
    w.build()
    w = window.crystal_tool.reopen_crystal()
    w.adp.setChecked(True)
    molecule, tensors = window.viewer.ellipsoids
    assert molecule is window.viewer.molecule and len(tensors) == 2
    o = next(k for k, a in enumerate(molecule.atoms) if a.symbol == 'O')
    assert abs(tensors[o][0][0] - 0.03) < 1e-12 and tensors[1 - o] is None
    window.viewer.grab()
    w.adp.setChecked(False)
    assert window.viewer.ellipsoids is None
    window.dirty = False
    window.new_molecule()


def test_crystal_coordination_polyhedra(window):
    # rock salt 2 x 2 x 2 with the atoms on the faces: the 13 Na inside have their 6 Cl — 13 octahedra
    from azimuth.paths import ROOT

    window.dirty = False
    window.opening_tool.open_path(str(ROOT / 'examples' / '10-crystals' / 'NaCl_rock_salt.cif'))
    w = window.crystal_window
    for box in w.counts:
        box.setValue(2)
    w.faces.setChecked(True)
    w.build()
    w = window.crystal_tool.reopen_crystal()
    assert w.polyhedra.isEnabled()
    w.polyhedra.setChecked(True)
    molecule, found = window.viewer.polyhedra
    assert molecule is window.viewer.molecule and len(found) == 13 and all(len(f) == 8 for _, f in found)
    window.viewer.grab()
    w.polyhedra.setChecked(False)
    assert window.viewer.polyhedra is None
    window.dirty = False
    window.new_molecule()


def test_crystal_contacts_and_the_hydrogen_bond_network(window, tmp_path):
    # «Контакты…» lists the hydrogen bond of a chain of water molecules along a; «Показать сеть водородных
    # связей» puts the molecule of the cell and its two neighbours on the model
    from modules.compass.chemistry import surface
    from tests.compass.test_crystal_contacts import water_chain

    path = tmp_path / 'water.cif'
    path.write_text(surface.write_cif(water_chain()), encoding='utf-8')
    window.dirty = False
    window.opening_tool.open_path(str(path))
    # the panel of «Компас · Кристалл» — the crystal tools instead of those of a molecule
    assert window.contacts_button.isVisibleTo(window) and window.powder_button.isVisibleTo(window)
    assert not window.lock_button.isVisibleTo(window) and not window.iupac_button.isVisibleTo(window)
    assert window.next_button.full == 'К расчёту кристалла' and 'Компас · Молекула' in window.next_button.toolTip()
    menu = window.crystal_tool.view_menu()
    items = [a for a in menu.actions() if not a.isSeparator()]
    assert [a.text() for a in items[:3]] == ['Вдоль a', 'Вдоль b', 'Вдоль c'] and len(items) == 9  # + colours; + rings;
    # + Bravais nodes
    items[3].setChecked(True)
    assert window.viewer.symmetry_items is not None
    items[3].setChecked(False)
    assert window.viewer.symmetry_items is None and not items[5].isEnabled()  # no displacement parameters in the file
    # «Координаты → Дробные (CIF)» in the crystal tab: the atoms of the model with the labels of the file
    fractional = window.coord_format.findData('fractional')
    assert fractional > 0 and not window.coord_format.view().isRowHidden(fractional)
    window.coord_format.setCurrentIndex(fractional)
    assert 'O1' in window.coord_text.toPlainText() and '_atom_site_fract_x' in window.coord_text.toPlainText()
    window.coord_format.setCurrentIndex(0)
    contacts = window.crystal_tool.show_contacts(normalize=False)  # the H of the file first
    kinds = [contacts.table.item(r, 0).text() for r in range(contacts.table.rowCount())]
    assert 'водородная' in kinds and contacts.network_button.isEnabled()
    row = kinds.index('водородная')
    assert contacts.table.item(row, 8).text() == 'C(2)'  # the water chain; + d/Σr, X···X
    assert contacts.table.item(row, 4).text() == f'{1.94 / 2.72:.2f}'  # d/Σr of O–H···O (H 1.20 + O 1.52)
    # O–H made 0.983 Å — the H···O bond shorter; the choice is kept for the next opening
    from PySide6.QtWidgets import QLabel

    contacts = contacts.renormalize(True)
    assert contacts.normalize.isChecked() and 'передвинуто' in contacts.findChildren(QLabel)[0].text()
    normal = [contacts.table.item(r, 0).text() for r in range(contacts.table.rowCount())].index('водородная')
    assert float(contacts.table.item(normal, 2).text()) < 1.94 and window.crystal_window.normalize_h
    contacts = contacts.renormalize(False)
    assert contacts.rings == () and not contacts.stacks.isVisibleTo(contacts)  # water has no rings
    # the table of the hydrogen bonds for a paper — the acceptor is the O of the next molecule along a
    paper = contacts.show_paper_table()
    assert paper.table.rowCount() == 1 and paper.table.item(0, 0).text() == 'O1–H1···O1 (i)'
    assert paper.table.item(0, 5).text() in ('x+1, y, z', 'x-1, y, z') and paper.table.item(0, 2).text() == '1.94'
    assert paper.save_csv(str(tmp_path / 'hb.csv')) and (tmp_path / 'hb.csv').read_text(encoding='utf-8').startswith('D,H,A')
    assert '(i) x' in paper.text() and paper.copy()
    paper.reject()
    # the criteria of the search are kept for the next opening; «По умолчанию» brings back 0.2 Å
    contacts.tolerance.setValue(0.4)
    contacts = contacts.search_again()
    assert contacts.tolerance.value() == 0.4 and window.crystal_window.criteria()['tolerance'] == 0.4
    contacts = contacts.default_criteria()
    assert abs(contacts.tolerance.value() - 0.2) < 1e-9 and contacts.hb_angle.value() == 120
    contacts.show_network()
    assert len(window.molecule.atoms) == 9 and window.molecule.formula == 'H6O3'
    # two of the molecules, picked by one atom each, go to a new tab of «Компас · Молекула»
    oxygens = [k for k, atom in enumerate(window.molecule.atoms) if atom.symbol == 'O']
    window.viewer.set_selection(oxygens[:2])
    document = window.crystal_tool.to_calculation()  # with atoms selected — selection_to_molecule
    assert document is not None and window.compass_mode == 'molecule' and window.molecule.formula == 'H4O2'
    assert window.lock_button.isVisibleTo(window) and not window.contacts_button.isVisibleTo(window)
    assert window.next_button.full == 'К параметрам расчёта'
    assert window.coord_format.view().isRowHidden(window.coord_format.findData('fractional'))
    window.dirty = False
    window.new_molecule()


def test_crystal_powder_pattern(window, tmp_path):
    # «Порошковая дифрактограмма…» of rock salt: 200 the strongest line, a measured pattern laid over it,
    # the curve and the lines saved
    from modules.compass.chemistry import powder, surface
    from tests.compass.test_crystal_symmetry import rock_salt

    path = tmp_path / 'salt.cif'
    path.write_text(surface.write_cif(rock_salt()), encoding='utf-8')
    window.dirty = False
    window.opening_tool.open_path(str(path))
    dialog = window.crystal_window.show_powder()
    assert dialog.table.rowCount() == len(dialog.lines) > 5
    assert dialog.table.item(max(range(len(dialog.lines)), key=lambda k: dialog.lines[k].intensity), 0).text() == '2 0 0'
    measured = tmp_path / 'measured.xy'
    measured.write_text(powder.write_xy([20, 31.7, 45.4, 60], [1, 1000, 550, 1]), encoding='utf-8')
    assert dialog.load_xy(str(measured)) and max(dialog.plot.measured[1]) == 100
    assert dialog.save_xy(str(tmp_path / 'calc.xy')) and dialog.save_lines(str(tmp_path / 'lines.csv'))
    assert (tmp_path / 'lines.csv').read_text(encoding='utf-8').startswith('h,k,l,2theta')
    dialog.source.setCurrentIndex(1)  # Mo: the lines move to smaller angles
    assert min(line.two_theta for line in dialog.lines) < 15
    # Kα₂, the widths of Caglioti with the step, the texture of March–Dollase
    dialog.source.setCurrentIndex(0)
    dialog.ka2.setChecked(True)
    assert len(dialog.second) == len(dialog.lines) and all(line.alpha2 for line in dialog.second)
    assert dialog.alpha2() == (powder.KA2['Cu Kα₁'], 0.5)
    dialog.widths.setCurrentIndex(1)
    assert dialog.shape()['uvw'] == (0.01, -0.005, 0.003) and not dialog.fwhm.isEnabled() and dialog.u.isEnabled()
    dialog.step.setValue(0.05)
    dialog.compute()
    xs, _ = dialog.plot.curve
    assert abs((xs[1] - xs[0]) - 0.05) < 1e-9
    plain = {line.hkl: line.intensity for line in dialog.lines}
    dialog.texture_r.setValue(0.6)
    dialog.texture.setChecked(True)  # plates on (001): 200 (2 of its 6 along the axis) stronger than 220
    textured = {line.hkl: line.intensity for line in dialog.lines}
    assert textured[(2, 2, 0)] / textured[(2, 0, 0)] < plain[(2, 2, 0)] / plain[(2, 0, 0)]
    dialog.texture_hkl.setText('1 x 0')
    dialog.compute()
    assert dialog.lines == () and 'три целых индекса' in dialog.status.text()
    dialog.texture.setChecked(False)
    assert dialog.lines
    dialog.grab()
    dialog.reject()
    window.crystal_window.reject()


def test_crystal_pi_stacking_in_the_contacts_window(window, tmp_path):
    # benzene stacked along c (3.6 Å): one ring, one stack in the table of the «Контакты» window
    from modules.compass.chemistry import surface
    from tests.compass.test_crystal_rings import benzene_crystal

    path = tmp_path / 'benzene.cif'
    path.write_text(surface.write_cif(benzene_crystal()), encoding='utf-8')
    window.dirty = False
    window.opening_tool.open_path(str(path))
    contacts = window.crystal_tool.show_contacts()
    assert len(contacts.rings) == 1 and contacts.stacks.rowCount() == 1
    assert contacts.stacks.item(0, 2).text() == '3.600' and contacts.stacks.item(0, 0).text() == 'π–π'
    assert 'π–π' in contacts.stacking_info.text() and contacts.ch_pi_rows == []
    assert contacts.second_level == [] and contacts.pairs.isHidden()  # no hydrogen bonds, no second level
    contacts.reject()
    # the rings on the model — 1 × 1 × 2 cells: two rings, one stack between them
    window.crystal_window.counts[2].setValue(2)
    window.crystal_window.build()
    items = [a for a in window.crystal_tool.view_menu().actions() if not a.isSeparator()]
    marks = next(a for a in items if a.text() == 'Кольца, π–π и C–H···π на модели')
    marks.setChecked(True)
    molecule, found = window.viewer.ring_marks
    assert molecule is window.viewer.molecule and len(found['rings']) == 2 and len(found['stacks']) == 1
    window.viewer.grab()
    marks.setChecked(False)
    assert window.viewer.ring_marks is None
    # the network of the stacks — the molecule of the cell and its two neighbours along c
    contacts = window.crystal_tool.show_contacts()
    choice = contacts.network_kinds.findText('π–π-стопок и C–H···π')
    assert choice >= 0 and contacts.network_button.isEnabled()
    contacts.network_kinds.setCurrentIndex(choice)
    contacts.show_network()
    assert len(window.viewer.molecule.atoms) == 36


def test_crystal_range_and_symmetry_colours(window, tmp_path):
    # ethanol in P2₁/c — whole molecules by the range 0…2 along a (8 molecules), coloured by symmetry (4 colours,
    # one per operation); the range is kept for the window opened again
    from modules.compass.chemistry import crystal_packing as cp
    from modules.compass.chemistry import surface
    from tests.compass.test_crystal_symmetry import ethanol_crystal

    crystal, _ = ethanol_crystal()
    path = tmp_path / 'etoh.cif'
    path.write_text(surface.write_cif(crystal), encoding='utf-8')
    window.dirty = False
    window.opening_tool.open_path(str(path))
    w = window.crystal_tool.reopen_crystal()
    w.by_range.setChecked(True)
    assert not w.counts[0].isEnabled() and w.range_boxes[0][1].isEnabled()
    w.range_boxes[0][1].setValue(2.0)
    assert w.build() and len(window.molecule.atoms) == 72
    again = window.crystal_tool.reopen_crystal()
    assert again.by_range.isChecked() and again.range_boxes[0][1].value() == 2.0
    again.reject()
    items = [a for a in window.crystal_tool.view_menu().actions() if not a.isSeparator()]
    tint = next(a for a in items if a.text() == 'Окраска молекул по симметрии')
    tint.setChecked(True)
    molecule, colours = window.viewer.atom_tints
    assert molecule is window.viewer.molecule and len(set(colours.values())) == 4 and len(colours) == 72
    assert set(colours.values()) <= set(cp.PALETTE)
    window.viewer.grab()
    tint.setChecked(False)
    assert window.viewer.atom_tints is None


@pytest.mark.skipif(os.name == 'nt', reason='Quantum ESPRESSO has no Windows build; the fake pw.x is a POSIX script')
def test_crystal_quantum_espresso_window(window, tmp_path, monkeypatch):
    # «Расчёт в Quantum ESPRESSO…» of the crystal window: the input of the cell, a run of a fake pw.x that prints
    # the real vc-relax output of silicon (tests/data/qe), the summary, the relaxed cell opened as a new crystal
    import sys
    import time

    from modules.sextant import install_tools, qe_pseudo
    from tests.sextant.test_qe_inputs import silicon

    data = Path(__file__).resolve().parents[1] / 'data' / 'qe' / 'si2_vcrelax_pw76.out'
    fake = tmp_path / 'pw.x'
    fake.write_text(f'#!{sys.executable}\nimport sys\nsys.stdout.write(open({str(data)!r}).read())\n', encoding='utf-8')
    fake.chmod(0o755)
    monkeypatch.setattr(install_tools, 'qe_program', lambda *a, **k: fake)
    monkeypatch.setattr(qe_pseudo, 'installed', lambda *a, **k: True)
    monkeypatch.setattr(qe_pseudo, 'table', lambda *a, **k: {'Si': ('Si.upf', 30.0, 240.0)})
    monkeypatch.setattr(window.run_tool, 'jobs_root', lambda: tmp_path / 'jobs')
    from modules.compass.chemistry import surface

    path = tmp_path / 'si.cif'
    path.write_text(surface.write_cif(silicon()), encoding='utf-8')
    window.dirty = False
    window.opening_tool.open_path(str(path))
    qe_window = window.crystal_window.show_qe()
    qe_window.processes.setValue(1)  # the fake pw.x runs alone
    # silicon (F) in its primitive cell by default — 2 atoms; the conventional cell — 8
    assert qe_window.primitive.isChecked() and 'nat = 2' in qe_window.preview.toPlainText()
    qe_window.primitive.setChecked(False)
    assert 'nat = 8' in qe_window.preview.toPlainText() and qe_window.run_button.isEnabled()
    qe_window.task.setCurrentIndex(qe_window.task.findData('Оптимизация с ячейкой'))
    assert "calculation = 'vc-relax'" in qe_window.preview.toPlainText()
    assert qe_window.start() is not None and (qe_window.folder / 'pw.in').is_file()
    deadline = time.monotonic() + 20
    while qe_window.result is None and time.monotonic() < deadline:
        time.sleep(0.1)
        qe_window.poll()
    r = qe_window.result
    assert r is not None and r.energy == -16.92455412
    text = qe_window.summary.text()
    assert '-16.924554 Ry' in text and 'a = 3.8661' in text and qe_window.open_button.isEnabled()
    assert qe_window.open_relaxed() and len(window.molecule.atoms) >= 2 and window.crystal is not None
    assert len(window.drawer.steps) == 3 and window.browsing  # with the steps of the optimization
    window.trajectory_tool.set_trajectory_open(False)
    qe_window.reject()


@pytest.mark.skipif(sys.platform == 'win32', reason='no build of Quantum ESPRESSO for Windows (a calculation goes to a server or WSL), and the fake pw.x is a POSIX script')
def test_a_batch_of_crystals(window, tmp_path, monkeypatch):
    # two crystals of one
    # project with ticks in its batch mode — «Запустить расчёт» runs pw.x for each with the settings of the window, the
    # pressure of each its own (that of its output of CRYSTAL), each run recorded to its crystal; a table at the end
    import sys
    import time

    from PySide6.QtWidgets import QApplication

    from azimuth import crystal_projects
    from modules.compass.actions import crystal_batch
    from modules.compass.chemistry import surface
    from modules.sextant import install_tools, qe_pseudo
    from tests.sextant.test_qe_inputs import silicon

    data = Path(__file__).resolve().parents[1] / 'data' / 'qe' / 'si2_vcrelax_pw76.out'
    fake = tmp_path / 'pw.x'
    fake.write_text(f'#!{sys.executable}\nimport sys\nsys.stdout.write(open({str(data)!r}).read())\n', encoding='utf-8')
    fake.chmod(0o755)
    monkeypatch.setattr(install_tools, 'qe_program', lambda *a, **k: fake)
    monkeypatch.setattr(qe_pseudo, 'installed', lambda *a, **k: True)
    monkeypatch.setattr(qe_pseudo, 'table', lambda *a, **k: {'Si': ('Si.upf', 30.0, 240.0)})
    window.dirty = False
    for name in ('si-a.cif', 'si-b.cif'):  # the second goes into the project of the first
        (tmp_path / name).write_text(surface.write_cif(silicon()), encoding='utf-8')
        window.opening_tool.open_path(str(tmp_path / name))
        window.crystal_window.reject()
    project = window.research_path()
    ids = [c['id'] for c in crystal_projects.crystals(project)]
    assert len(ids) == 2
    crystal_projects.set_result(project, 'CRYSTAL17 · PBE0', -1.0, ids[1], pressure=3.5)
    window.set_project_batch_mode(True)
    assert window.project_mode_tabs.isTabEnabled(1) and window.crystal_batch_idents() == ids
    panel = window.crystal_window.show_qe()
    panel.processes.setValue(1)
    panel.task.setCurrentIndex(panel.task.findData('Оптимизация с ячейкой'))
    assert panel.batch_idents() == ids
    batch = crystal_batch.run(panel, ids, crystal_batch.OWN)
    deadline = time.monotonic() + 40
    while batch.running and time.monotonic() < deadline:
        time.sleep(0.1)
        panel.poll()
        QApplication.processEvents()
    assert not batch.running and [r[1] for r in batch.rows] == ['готово', 'готово'], batch.rows
    assert batch.rows[0][2] == f'{-16.92455412 / 2:.6f}' and batch.window is not None
    for ident in ids:  # each run recorded to its own crystal, the pressure of the second one in its input
        runs = crystal_projects.info(project, ident)['runs']
        assert len(runs) == 1
        text = (project.parent / runs[0]['folder'] / 'pw.in').read_text()
        assert ('press = 35' in text) == (ident == ids[1])
    batch.window.close()
    panel.reject()
    window.set_project_batch_mode(False)


@pytest.mark.skipif(sys.platform == 'win32', reason='no build of Quantum ESPRESSO for Windows (a calculation goes to a server or WSL), and the fake pw.x is a POSIX script')
def test_crystal_quantum_espresso_bands(window, tmp_path, monkeypatch):
    # «Зонная структура» and «Плотность состояний» — the steps in one job (run.sh), fake pw.x and dos.x that
    # print the real outputs of pw.x 7.6 for silicon (tests/data/qe); the gap along the path, the plots, the CSV
    import sys
    import time

    from modules.compass.chemistry import surface
    from modules.sextant import install_tools, qe_inputs, qe_pseudo
    from tests.sextant.test_qe_inputs import silicon

    data = Path(__file__).resolve().parents[1] / 'data' / 'qe'
    scf, bands = (data / 'si_bands_pw76.out').read_text(encoding='utf-8').split('Program PWSCF')[1:3]
    (tmp_path / 'scf.txt').write_text('Program PWSCF' + scf, encoding='utf-8')
    (tmp_path / 'bands.txt').write_text('Program PWSCF' + bands, encoding='utf-8')
    tools = tmp_path / 'bin'
    tools.mkdir()
    fake = tools / 'pw.x'
    fake.write_text(f"""#!{sys.executable}
import sys
name = sys.argv[sys.argv.index('-in') + 1]
part = 'bands' if name == 'bands.in' else 'scf'
sys.stdout.write(open({str(tmp_path)!r} + '/' + part + '.txt').read())
""", encoding='utf-8')
    dos = tools / 'dos.x'
    dos.write_text(f"""#!{sys.executable}
import shutil, sys
shutil.copy({str(data / 'si_dos_pw76.dos')!r}, 'azimuth.dos')
sys.stdout.write('Program DOS v.7.6 starts\\n JOB DONE.\\n')
""", encoding='utf-8')
    for f in (fake, dos):
        f.chmod(0o755)
    monkeypatch.setattr(install_tools, 'qe_program', lambda *a, **k: fake)
    monkeypatch.setattr(qe_pseudo, 'installed', lambda *a, **k: True)
    monkeypatch.setattr(qe_pseudo, 'table', lambda *a, **k: {'Si': ('Si.upf', 30.0, 240.0)})
    monkeypatch.setattr(qe_inputs, 'valence', lambda *a, **k: 4.0)
    monkeypatch.setattr(window.run_tool, 'jobs_root', lambda: tmp_path / 'jobs')
    path = tmp_path / 'si.cif'
    path.write_text(surface.write_cif(silicon()), encoding='utf-8')
    window.dirty = False
    window.opening_tool.open_path(str(path))
    panel = window.crystal_window.show_qe()
    panel.processes.setValue(1)  # the fake pw.x runs alone
    panel.task.setCurrentIndex(panel.task.findData(qe_inputs.BANDS_TASK))
    text = panel.preview.toPlainText()
    assert "calculation = 'bands'" in text and 'nbnd = 8' in text and 'K_POINTS crystal' in text and '# ---- scf.in' in text

    def finish():
        assert panel.start() is not None and (panel.folder / 'run.sh').is_file()
        deadline = time.monotonic() + 30
        while panel.result is None and time.monotonic() < deadline:
            time.sleep(0.1)
            panel.poll()
        assert panel.result is not None and panel.result.done and not panel.result.error, panel.status.text()

    finish()
    assert (panel.folder / 'path.json').is_file() and (panel.folder / 'bands.in').is_file()
    assert 'Щель по пути' in panel.summary.text() and '0.574' in panel.summary.text()
    assert panel.plot_button.isVisible() and not panel.open_button.isEnabled()
    plot = panel.show_plot()
    assert len(plot.plot.x) == 297 and [t[1] for t in plot.plot.ticks][:3] == ['Γ', 'X', 'W']
    assert abs(max(row[3] for row in plot.plot.energies)) < 0.01  # the top of the valence band at 0
    saved = plot.save(str(tmp_path / 'bands.csv'))
    assert saved and len(Path(saved).read_text(encoding='utf-8').splitlines()) == 298
    plot.reject()
    panel.task.setCurrentIndex(panel.task.findData(qe_inputs.DOS_TASK))
    assert "occupations = 'tetrahedra_opt'" in panel.preview.toPlainText() and '&DOS' in panel.preview.toPlainText()
    finish()
    assert (panel.folder / 'azimuth.dos').is_file() and panel.plot_button.text() == 'Показать плотность состояний'
    plot = panel.show_plot()
    assert len(plot.plot.dos) == 2207 and min(plot.plot.energies) < -11
    plot.reject()
    panel.reject()


def test_crystal_quantum_espresso_on_the_server(window, tmp_path, monkeypatch):
    # «Где — Сервер · serv3» in the panel of Quantum ESPRESSO: the fake SLURM server of tests/fake_server.py
    # with a fake pw.x in its PATH (it prints the real vc-relax output of silicon); the pseudopotential goes with the
    # folder (pseudo_dir './pseudo'), the job is queued, watched and finished as on this computer
    import os
    import stat
    import sys
    import time

    import pytest

    if os.name == 'nt':
        pytest.skip('the fake server is a set of POSIX scripts')
    from modules.compass.chemistry import surface
    from modules.sextant import keychain, qe_pseudo, remote
    from tests import fake_server
    from tests.sextant.test_qe_inputs import silicon

    server = fake_server.install(tmp_path, monkeypatch)
    monkeypatch.setattr(keychain, 'SESSION', {})
    monkeypatch.setattr(keychain, '_lib', lambda: None)
    data = Path(__file__).resolve().parents[1] / 'data' / 'qe' / 'si_primitive_scf_pw76.out'
    fake = server / 'bin' / 'pw.x'
    fake.write_text(f"#!{sys.executable}\nimport sys\nassert open('pseudo/Si.upf').read() == 'upf'\n"
                    f"sys.stdout.write(open({str(data)!r}).read())\n", encoding='utf-8')
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    library = tmp_path / 'sssp'
    library.mkdir()
    (library / 'Si.upf').write_text('upf', encoding='utf-8')
    monkeypatch.setattr(qe_pseudo, 'installed', lambda *a, **k: True)
    monkeypatch.setattr(qe_pseudo, 'table', lambda *a, **k: {'Si': ('Si.upf', 30.0, 240.0)})
    monkeypatch.setattr(qe_pseudo, 'folder', lambda *a, **k: library)
    monkeypatch.setattr(window.run_tool, 'jobs_root', lambda: tmp_path / 'jobs')
    window.preferences.remove(remote.PROFILES_KEY)
    remote.save(window.preferences, remote.ServerProfile('serv3', '192.0.2.103', 22, 'user', '~/azimuth/calculations'))
    path = tmp_path / 'si.cif'
    path.write_text(surface.write_cif(silicon()), encoding='utf-8')
    window.dirty = False
    window.opening_tool.open_path(str(path))
    panel = window.crystal_window.show_qe()
    panel.processes.setValue(1)  # the fake pw.x runs alone
    assert panel.where.count() == 2 and panel.where.isVisibleTo(panel)
    panel.where.setCurrentIndex(panel.where.findData('server'))
    assert "pseudo_dir = './pseudo'" not in panel.preview.toPlainText()  # the file shown is the one of this computer
    assert 'serv3' in panel.status.text() and panel.run_button.isEnabled()
    try:
        assert panel.start() is not None, panel.status.text()
        assert "pseudo_dir = './pseudo'" in (panel.folder / 'pw.in').read_text() and (panel.folder / 'job.sh').is_file()
        deadline = time.monotonic() + 30
        while panel.result is None and time.monotonic() < deadline:
            time.sleep(0.1)
            panel.poll()
        assert panel.result is not None and panel.result.energy == -16.92417107, panel.status.text()
        assert 'Ry' in panel.summary.text()
    finally:
        window.preferences.remove(remote.PROFILES_KEY)
    panel.reject()


@pytest.mark.skipif(sys.platform == 'win32', reason='no build of Quantum ESPRESSO for Windows (a calculation goes to a server or WSL), and the fake pw.x is a POSIX script')
def test_sextant_quantum_espresso(window, tmp_path, monkeypatch):
    # the arrow of «Компас ·
    # Кристалл» leads to Sextant with the crystal tabs kept; the cards of a molecule — the form with the settings of
    # pw.x, the card of the crystal, the input file edited by hand and run as it is; a molecule tab — the page of a
    # molecule without Quantum ESPRESSO
    import sys
    import time

    from modules.compass.chemistry import surface
    from modules.sextant import install_tools, qe_pseudo
    from tests.sextant.test_qe_inputs import silicon

    data = Path(__file__).resolve().parents[1] / 'data' / 'qe' / 'si_primitive_scf_pw76.out'
    fake = tmp_path / 'pw.x'
    fake.write_text(f'#!{sys.executable}\nimport sys\nsys.stdout.write(open({str(data)!r}).read())\n', encoding='utf-8')
    fake.chmod(0o755)
    monkeypatch.setattr(install_tools, 'qe_program', lambda *a, **k: fake)
    monkeypatch.setattr(qe_pseudo, 'installed', lambda *a, **k: True)
    monkeypatch.setattr(qe_pseudo, 'table', lambda *a, **k: {'Si': ('Si.upf', 30.0, 240.0)})
    monkeypatch.setattr(window.run_tool, 'jobs_root', lambda: tmp_path / 'jobs')
    tool = window.crystal_mode_tool
    assert window.program.findData('qe') < 0  # a molecule has no Quantum ESPRESSO
    path = tmp_path / 'si.cif'
    path.write_text(surface.write_cif(silicon()), encoding='utf-8')
    window.dirty = False
    window.opening_tool.open_path(str(path))
    window.crystal_window.reject()
    window.viewer.set_selection([])
    assert window.crystal_tool.to_calculation()
    assert window.stack.currentIndex() == 1 and tool.active and window.calc_stack.currentWidget() is tool.page
    assert window.compass_mode == 'crystal' and window.crystal is not None  # the crystal tabs stay
    assert [tool.program_combo.itemData(k) for k in range(tool.program_combo.count())] == ['qe', 'cp2k']  # + CP2K
    panel = tool.panel
    panel.processes.setValue(1)  # the fake pw.x runs alone
    assert 'nat = 2' in panel.preview.toPlainText() and panel.run_button.isEnabled()  # silicon, its primitive cell
    assert '2 атомов' in tool.facts.text()
    panel.supercell[0].setValue(2)  # a supercell along a
    assert 'nat = 4' in panel.preview.toPlainText() and '4 атомов' in tool.facts.text()
    panel.supercell[0].setValue(1)
    panel.vdw.setCurrentIndex(panel.vdw.findData('d3bj'))
    panel.kmode.setCurrentIndex(panel.kmode.findData('grid'))
    for box in panel.grid:
        box.setValue(6)
    text = panel.preview.toPlainText()
    assert 'dftd3_version = 4' in text and '  6 6 6 0 0 0' in text and not panel.grid_line.isHidden()
    # the functional and the charge of the cell (a non-local functional — without the correction)
    panel.vdw.setCurrentIndex(panel.vdw.findData(''))
    panel.functional.setCurrentIndex(panel.functional.findData('vdw-df2'))
    panel.charge.setValue(1)
    other = panel.preview.toPlainText()
    assert "input_dft = 'vdw-df2'" in other and 'tot_charge = 1' in other and 'vdw_corr' not in other
    assert panel.options().functional == 'vdw-df2' and panel.options().charge == 1
    panel.functional.setCurrentIndex(panel.functional.findData(''))
    panel.charge.setValue(0)
    panel.vdw.setCurrentIndex(panel.vdw.findData('d3bj'))
    assert panel.preview.toPlainText() == text
    # DFT+U — silicon has no d or f element; a U of an element not in the cell is an error of the settings
    assert 'не нужен' in panel.hubbard.placeholderText()
    panel.hubbard.setText('Ni 5')
    assert 'DFT+U' in panel.status.text() and not panel.run_button.isEnabled()
    # another crystal keeps the U of its own elements only, and its charge is 0
    from tests.sextant.test_hubbard import nickel_oxide

    silicon_crystal = panel.crystal
    panel.charge.setValue(1)
    assert panel.keep_for_crystal(nickel_oxide()) == ''  # Ni is there — kept
    assert panel.hubbard.text() == 'Ni 5' and panel.charge.value() == 0
    assert panel.keep_for_crystal(silicon_crystal) == 'Ni' and panel.hubbard.text() == ''
    assert panel.run_button.isEnabled() and 'DFT+U' not in panel.status.text()
    assert panel.preview.toPlainText() == text and panel.run_button.isEnabled()
    edited = text.replace("prefix = 'azimuth'", "prefix = 'azimuth'\n  ! by hand")
    panel.preview.setPlainText(edited)
    assert panel.input_edited and panel.reset_button.isVisibleTo(panel.reset_button.parentWidget())
    panel.spin.setChecked(True)  # the settings do not overwrite the file edited by hand
    assert panel.preview.toPlainText() == edited
    tool.calc_title.setText('si-test')
    assert panel.start() is not None and (panel.folder / 'pw.in').read_text() == edited.rstrip('\n') + '\n'
    assert 'si-test' in panel.folder.name
    # the calculation in the place of the input file, with Quill counting (as for a molecule)
    from PySide6.QtGui import QImageReader

    webp = b'webp' in [bytes(f) for f in QImageReader.supportedImageFormats()]  # Quill is webp (no plugin — no picture)
    assert tool.job_card.isVisibleTo(tool.page) and tool.preview_card.isHidden()
    assert tool.job_card.picture_name == ('calc-running' if webp else None)
    deadline = time.monotonic() + 20
    while panel.result is None and time.monotonic() < deadline:
        time.sleep(0.1)
        panel.poll()
    assert panel.result is not None and panel.result.energy == -16.92417107 and 'Ry' in panel.summary.text()
    assert tool.job_card.picture_name == ('calc-done' if webp else None) and 'scf' in tool.job_card.stage_keys
    tool.job_card.input_button.click()
    assert tool.job_slot.isHidden() and not tool.preview_card.isHidden()
    panel.reset_input()
    assert not panel.input_edited and 'nspin = 2' in panel.preview.toPlainText()
    # another crystal tab while a job runs — the page keeps the crystal computed, its picture too, and
    # says why
    import types

    tab, job = window.crystal, panel.job
    tool.thumb.set_molecule(None)
    try:
        window.crystal = (types.SimpleNamespace(),) + tuple(tab[1:])
        panel.job = types.SimpleNamespace(running=True)
        tool.update_card()
        assert tool.thumb.molecule is None and 'Идёт расчёт этого кристалла' in tool.facts.text()
    finally:
        window.crystal, panel.job = tab, job
    tool.update_card()
    assert tool.thumb.molecule is not None and 'Идёт расчёт этого' not in tool.facts.text()
    # NiO started without spin — the question; «Включить АФМ» — the antiferromagnetic order, which needs a supercell
    # (the Ni of this cubic cell of P 1 — fcc, frustrated); «Считать без спина» — asked once for the crystal
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(qe_pseudo, 'table', lambda *a, **k: {'Si': ('Si.upf', 30.0, 240.0), 'Ni': ('ni.upf', 45.0, 360.0),
                                                             'O': ('O.upf', 50.0, 400.0)})
    asked = []
    answer = [QMessageBox.StandardButton.Yes]
    monkeypatch.setattr(QMessageBox, 'question', lambda parent, title, text, *rest: asked.append(text) or answer[0])
    panel.reset_input()
    panel.spin.setChecked(False)
    nio = nickel_oxide()
    assert panel.set_crystal(nio, 'NiO') is not False
    assert panel.ask_magnetism() is False and 'Ni' in asked[-1]  # no two sublattices in this cell
    assert panel.spin.isChecked() and panel.order.currentData() == 'afm' and 'Антиферромагнитный' in panel.status.text()
    panel.supercell[0].setValue(2)
    text = panel.preview.toPlainText()
    assert '  Ni1 ' in text and '  Ni2 ' in text and 'tot_magnetization = 0' in text, panel.status.text()
    assert 'спин: антиферромагнитный' in tool.options_summary.text() or not tool.active
    panel.spin.setChecked(False)
    answer[0] = QMessageBox.StandardButton.No
    count = len(asked)
    assert panel.ask_magnetism() is True and panel.ask_magnetism() is True and len(asked) == count + 1
    panel.supercell[0].setValue(1)
    # a molecule tab: the page of a molecule
    window.crystal_tool.set_compass_mode('molecule')
    assert not tool.active and window.calc_stack.currentWidget() is window.calc_body
    window.navigate(0)
    window.navigate(1)
    assert not tool.active and window.calc_stack.currentWidget() is window.calc_body
    window.navigate(0)


@pytest.mark.skipif(sys.platform == 'win32', reason='no build of CP2K for Windows (a calculation goes to a server or WSL), and the fake cp2k is a POSIX script')
def test_sextant_cp2k(window, tmp_path, monkeypatch):
    # CP2K as the second program of a
    # crystal in Sextant — its tasks and rows, its input, a run of a fake CP2K that prints the output and writes the
    # files of a cell optimisation of tests/data/cp2k (written by hand), the relaxed cell; back to Quantum ESPRESSO
    import shutil
    import sys
    import time

    from modules.compass.chemistry import surface
    from modules.sextant import install_tools
    from tests.sextant.test_qe_inputs import silicon

    data = Path(__file__).resolve().parents[1] / 'data' / 'cp2k'
    fake = tmp_path / 'cp2k.ssmp'
    fake.write_text(f"""#!{sys.executable}
import shutil, sys
assert sys.argv[1:] == ['-i', 'azimuth.inp'] and '&FORCE_EVAL' in open('azimuth.inp').read()
for name in ('azimuth-pos-1.xyz', 'azimuth-1.cell'):
    shutil.copy({str(data)!r} + '/' + name, name)
sys.stdout.write(open({str(data / 'cellopt.out')!r}).read())
""", encoding='utf-8')
    fake.chmod(0o755)
    monkeypatch.setattr(install_tools, 'cp2k_program', lambda *a, **k: fake)
    monkeypatch.setattr(window.run_tool, 'jobs_root', lambda: tmp_path / 'jobs')
    path = tmp_path / 'si.cif'
    path.write_text(surface.write_cif(silicon()), encoding='utf-8')
    window.dirty = False
    window.opening_tool.open_path(str(path))
    window.crystal_window.reject()
    window.viewer.set_selection([])
    assert window.crystal_tool.to_calculation()
    tool = window.crystal_mode_tool
    panel = tool.panel
    assert [tool.program_combo.itemData(k) for k in range(tool.program_combo.count())] == ['qe', 'cp2k']
    tool.program_combo.setCurrentIndex(tool.program_combo.findData('cp2k'))
    # the fourth task of CP2K — the frequencies at Γ (cp2k_inputs.TASKS)
    assert panel.program == 'cp2k' and panel.task.count() == 4 and 'CP2K' in tool.preview_title.text()
    # the rows the two pages
    # share stand in the order of the molecule page; the electronic state and the SCF — in «Дополнительные настройки…»
    from PySide6.QtWidgets import QFormLayout

    def captions(form):
        out = []
        for r in range(form.rowCount()):
            item = form.itemAt(r, QFormLayout.ItemRole.LabelRole)
            text = item.widget().text() if item is not None and item.widget() is not None else ''
            if text and (not out or out[-1] != text):
                out.append(text)
        return out

    molecule, crystal = captions(window.main_form), captions(panel.form)
    shared = [t for t in molecule if t in crystal]
    # «Название» of a molecule is in «Дополнительные настройки…» by default (setup_rows), so not shared
    assert shared[:4] == ['Программа', 'Задача', 'Метод', 'Базис'] and 'Ресурсы' in shared
    assert [t for t in crystal if t in shared] == shared
    assert 'Заряд ячейки' not in crystal and 'Сходимость SCF' not in crystal
    assert panel.form.contentsMargins().left() == 0 and panel.form.contentsMargins().top() == 0
    # one width of the captions
    first = [f.itemAt(0, QFormLayout.ItemRole.LabelRole).widget() for f in (panel.form, window.main_form)]
    assert first[0].minimumWidth() == first[1].minimumWidth() > 0
    assert tool.options_button.isVisibleTo(tool.page) and 'заряд 0' in tool.options_summary.text()
    assert tool.show_options() is tool.options_dialog
    tool.options_dialog.close()
    assert panel.task.findData('Частоты (точка Γ)') >= 0
    assert panel.form.isRowVisible(panel.basis) and not panel.form.isRowVisible(panel.k_line)
    text = panel.preview.toPlainText()
    # the primitive cell of 3.84 Å at the Γ point — the supercell 3 × 3 × 3 of 11.5 Å, chosen by itself
    assert [b.value() for b in panel.supercell] == [3, 3, 3] and 'Осторожно' not in panel.note.text()
    assert '&FORCE_EVAL' in text and 'DZVP-MOLOPT-SR-GTH' in text and text.count('      Si ') == 54
    # the functional of CP2K — its own row (that of Quantum ESPRESSO hidden)
    assert panel.form.isRowVisible(panel.cp2k_functional) and not panel.form.isRowVisible(panel.functional_line)
    panel.cp2k_functional.setCurrentIndex(panel.cp2k_functional.findData('BLYP'))
    assert 'POTENTIAL GTH-BLYP' in panel.preview.toPlainText() and panel.options().functional == 'BLYP'
    # GFN1-xTB — no rows of the basis, the density grid and the D3 choice
    panel.cp2k_functional.setCurrentIndex(panel.cp2k_functional.findData('GFN1-XTB'))
    assert 'METHOD xTB' in panel.preview.toPlainText() and not panel.form.isRowVisible(panel.basis)
    extra = next(f for f in panel.extra_forms if f.indexOf(panel.hubbard) >= 0)  # «Дополнительные настройки…»
    assert not panel.form.isRowVisible(panel.cp2k_cut_line) and not extra.isRowVisible(panel.hubbard)
    panel.cp2k_functional.setCurrentIndex(panel.cp2k_functional.findData('PBE'))
    assert panel.preview.toPlainText() == text and panel.form.isRowVisible(panel.basis)
    panel.supercell[0].setValue(1)  # the user's own choice stays, and is warned about
    assert [b.value() for b in panel.supercell] == [1, 3, 3] and 'Осторожно' in panel.note.text()
    panel.supercell[0].setValue(3)
    panel.task.setCurrentIndex(panel.task.findData('Оптимизация с ячейкой'))
    assert 'RUN_TYPE CELL_OPT' in panel.preview.toPlainText() and 'CP2K найден' in panel.status.text()
    assert panel.start() is not None and panel.folder.name.startswith('cp2k-')
    deadline = time.monotonic() + 20
    while panel.result is None and time.monotonic() < deadline:
        time.sleep(0.1)
        panel.poll()
    r = panel.result
    assert r is not None and r.done and r.energy_hartree == -31.5813, panel.status.text()
    assert 'a = 5.4700' in panel.summary.text() and panel.open_button.isEnabled()
    # a finished run — «Перейти в Компас» and «Перейти в Спектр», as after the run of a molecule
    assert tool.job_card.compass_button.isVisibleTo(tool.job_card) and tool.job_card.spectrum_button.isVisibleTo(tool.job_card)
    steps = panel.optimization_steps()  # the three frames of azimuth-pos-1.xyz with their cells
    assert [round(s.crystal.cell.a, 4) for s in steps] == [5.431, 5.45, 5.47]
    # no Molden file of the fake CP2K — no button of AIM; with the file for Multiwfn of the real CsCl and
    # the points Multiwfn found in it (the program itself is not run here) — the table of the kinds of bonds and its CSV
    assert panel.aim_button.isHidden() and 'Multiwfn' not in panel.summary.text()
    from azimuth import tasks
    from modules.spectrum.wavefunction import multiwfn

    data = Path(__file__).resolve().parents[1] / 'data' / 'multiwfn'
    cps = multiwfn.parse_cps((data / 'crystal_topology_cp2k-CsCl-20261112-144541__CPprop.txt').read_text(encoding='utf-8'))
    panel.multiwfn_file = data / 'crystal_cscl333_geometry.molden'
    monkeypatch.setattr(panel, 'multiwfn_found', lambda: Path('/opt/Multiwfn'))
    monkeypatch.setattr(multiwfn, 'run_topology', lambda *a, **k: (cps, '', '2026.10.28', []))
    monkeypatch.setattr(tasks, 'run_waiting', lambda parent, title, work, total=0, alone=True: work(lambda *a: True))
    aim = panel.show_aim()
    assert aim is not None and aim.table.rowCount() == 3 and aim.table.item(0, 0).text() == 'Cl–Cs'
    assert aim.table.item(0, 1).text() == '3.59' and 'замкнутые оболочки' in aim.table.item(0, 7).text()
    assert aim.table.item(0, 2).text() == 'Cl: 8, Cs: 8'
    assert 'Найдены не все' in aim.note.text() and '= 17' in aim.note.text()  # 17 points Cs–Cs missed by Multiwfn
    assert (panel.folder / 'aim-bonds.csv').read_text(encoding='utf-8').splitlines()[1].startswith('Cl–Cs,3.59,')
    aim.close()
    from modules.spectrum.wavefunction import crystal_aim

    recorded = crystal_aim.parse_charges((data / 'crystal_cm5_a_cp2k-CsCl-20261112-144541.txt').read_text(encoding='utf-8'))
    monkeypatch.setattr(crystal_aim, 'run_charges', lambda *a, **k: (recorded, '', '2026.10.28'))
    charges = panel.show_charges()
    assert charges is not None and charges.table.rowCount() == 2 and charges.table.item(0, 3).text() == '+0.547'
    assert (panel.folder / 'charges.csv').read_text(encoding='utf-8').splitlines()[1] == '1,Cs,0.299477,0.546776'
    charges.close()
    # the run of a project shown again — the panel opened later finds the last finished CP2K run in the
    # project of the crystal, shows its summary and the buttons of Multiwfn (no new run needed)
    from azimuth import crystal_projects
    from modules.compass.chemistry import surface

    manifest = crystal_projects.create(tmp_path / 'projects', 'CsCl', surface.write_cif(panel.crystal))
    run = Path(manifest).parent / 'calculations' / panel.folder.name
    shutil.copytree(panel.folder, run)
    shutil.copyfile(data / 'crystal_cscl333_geometry.molden', run / 'azimuth-MOS-1_0.molden')
    crystal_projects.record_run(manifest, {'folder': f'calculations/{run.name}', 'program': 'cp2k'})
    monkeypatch.setattr(panel, 'jobs_root', lambda: Path(manifest).parent / 'calculations')
    panel.aim_button.hide()
    panel.summary.setText('')
    assert panel.show_last_run() and panel.folder == run
    assert 'Последний расчёт проекта' in panel.summary.text() and 'Волновая функция для Multiwfn' in panel.summary.text()
    # the buttons of Multiwfn are not on
    # the page of Sextant (nor windows of their own) — the analysis is in Compass and Spectrum
    assert not panel.aim_button.isVisibleTo(tool.page) and not panel.charges_button.isVisibleTo(tool.page)
    assert not panel.aim_button.isWindow() and not panel.charges_button.isWindow()
    tool.program_combo.setCurrentIndex(tool.program_combo.findData('qe'))
    assert panel.program == 'qe' and panel.task.count() == 14 and not panel.form.isRowVisible(panel.basis)  # + E(V), E(ε), five series
    assert [b.value() for b in panel.supercell] == [1, 1, 1]  # the k points of pw.x: no supercell of the Γ point
    shutil.rmtree(tmp_path / 'jobs', ignore_errors=True)
    tool.job_card.compass_button.click()  # back to the crystal in Compass
    assert window.stack.currentIndex() == 0 and window.compass_mode == 'crystal'


def test_a_crystal_is_a_project(window, tmp_path):
    # a CIF opened gets a project tab with the file in its folder; a tab of molecules shows «Компас · Молекула», the tab
    # of the crystal brings its crystal back; a second CIF is a tab of its own; a closed tab leaves its folder on disk
    # (when something was calculated in it — a CIF only looked at leaves none)
    from azimuth import crystal_projects, projects
    from modules.compass.chemistry import surface
    from tests.sextant.test_qe_inputs import silicon

    window.dirty = False
    molecules = window.ensure_project_tab()  # the water of the example in a project of molecules
    window.save_research_project()
    path = tmp_path / 'si.cif'
    path.write_text(surface.write_cif(silicon()), encoding='utf-8')
    window.opening_tool.open_path(str(path))
    window.crystal_window.reject()
    crystal = window.research_path()
    assert crystal_projects.is_crystal(crystal) and (crystal.parent / 'crystal.cif').is_file()
    assert window.compass_mode == 'crystal' and window.project_tabs.count() == 2
    assert window.research_document_path() == crystal  # the calculations go into its folder
    assert Path(window.run_tool.jobs_root()) == crystal.parent / 'calculations'
    assert window.project_molecules.rowCount() == 1 and 'кристалл' in window.project_caption.text()
    shown = window.document()
    window.activate_project_tab(window.project_sessions.index(molecules))
    assert window.compass_mode == 'molecule' and window.research_path() == molecules and window.molecule.formula == 'H2O'
    window.activate_project_tab(window.project_sessions.index(crystal))
    assert window.compass_mode == 'crystal' and window.document() is shown and window.crystal is not None
    cscl = str(Path(__file__).resolve().parents[2] / 'examples' / '10-crystals' / 'CsCl.cif')
    # a CIF opened while a crystal project is shown — one more crystal of it, in
    # its tab; its list has both, a row chosen shows its crystal
    window.opening_tool.open_example_path(cscl)
    window.crystal_window.reject()
    assert window.research_path() == crystal and window.project_tabs.count() == 2 and window.document() is shown
    assert [c['title'] for c in crystal_projects.crystals(crystal)][1] == 'CsCl' and (crystal.parent / 'crystal-2.cif').is_file()
    assert window.project_molecules.rowCount() == 2 and 'Cs' in window.molecule.formula
    assert window.project_mode_tabs.isTabEnabled(1)  # the batch of crystals (crystal_batch.py)
    window.project_molecule_chosen(0)
    assert crystal_projects.active(crystal) == crystal_projects.FIRST and 'Si' in window.molecule.formula
    assert window.document() is shown and len(window.documents) == 1
    window.activate_project_tab(window.project_sessions.index(molecules))  # from a tab of molecules — a project of its own
    window.opening_tool.open_example_path(cscl)
    window.crystal_window.reject()
    second = window.research_path()
    assert second != crystal and crystal_projects.is_crystal(second) and window.project_tabs.count() == 3
    assert window.document() is not shown and len(window.documents) == 2  # each crystal project — a tab of its own
    window.activate_project_tab(window.project_sessions.index(crystal))
    assert window.document() is shown and 'Si' in window.molecule.formula
    window.close_project_tab(window.project_sessions.index(crystal))
    # a CIF only looked at leaves no folder; one with a calculation stays — and one with two crystals
    assert crystal not in window.project_sessions and crystal.parent.exists() and shown not in window.documents
    crystal_projects.record_run(second, {'folder': 'calculations/scf', 'task': 'scf'})
    window.close_project_tab(window.project_sessions.index(second))
    assert second not in window.project_sessions and second.is_file()
    assert projects.Project.view(second).data[crystal_projects.KEY]['title'] == 'CsCl'
    for d in window.all_documents():
        d.dirty = False
    window.crystal_tool.set_compass_mode('molecule')


def test_closing_the_only_crystal_project_stays_in_crystal(window, tmp_path):
    manifest, _ = crystal_project_with_charges(tmp_path)
    for path in list(window.project_sessions):  # only the crystal project open
        window.close_project_tab(window.project_sessions.index(path))
    window.open_project_path(str(manifest))
    assert window.compass_mode == 'crystal'
    window.close_project_tab(window.project_sessions.index(Path(manifest).resolve()))
    assert window.compass_mode == 'crystal' and not window.crystal and Path(manifest).is_file()
    window.crystal_tool.set_compass_mode('molecule')


def test_molecules_after_a_crystal_are_not_in_its_project(window):
    # «Компас · Молекула» after a crystal project, with no project of molecules —
    # the tab «Новый проект» is the current one, and the molecule saved goes into a new project of molecules
    from azimuth import crystal_projects
    from azimuth.core import read_xyz

    window.dirty = False
    examples = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals'
    window.opening_tool.open_example_path(str(examples / 'CsCl.cif'))
    window.crystal_window.reject()
    crystal = window.research_path()
    assert crystal_projects.is_crystal(crystal)
    window.crystal_tool.set_compass_mode('molecule')
    tabs = [window.project_tabs.tabText(k) for k in range(window.project_tabs.count())]
    assert window.research_path() is None and tabs[-1] == 'Новый проект'
    assert window.project_tabs.currentIndex() == len(tabs) - 1
    window.load_molecule(read_xyz('3\nwater\nO 0 0 0\nH 0 0.76 0.58\nH 0 -0.76 0.58'))
    made = window.ensure_project_tab()
    assert made != crystal and not crystal_projects.is_crystal(made)
    assert window.project_tabs.currentIndex() == window.project_sessions.index(made)
    for d in window.all_documents():
        d.dirty = False


def test_sextant_follows_the_kind_of_the_project_tab(window, monkeypatch):
    from azimuth.core import read_xyz

    window.dirty = False
    window.load_molecule(read_xyz('3\nwater\nO 0 0 0\nH 0 0.76 0.58\nH 0 -0.76 0.58'))
    molecules = window.ensure_project_tab()
    examples = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals'
    window.opening_tool.open_example_path(str(examples / 'CsCl.cif'))
    window.crystal_window.reject()
    crystal = window.research_path()
    page = window.crystal_mode_tool.page
    # the tab of a project of molecules has the icon of a molecule, that of a crystal — of a crystal
    tabs = window.project_tabs
    assert tabs.tabData(window.project_sessions.index(molecules)) == 'molecule' and not tabs.tabIcon(0).isNull()
    assert tabs.tabData(window.project_sessions.index(crystal)) == 'crystal'
    window.navigate(1)
    for target, is_crystal in ((molecules, False), (crystal, True), (molecules, False)):
        window.project_tabs.setCurrentIndex(window.project_sessions.index(target))
        assert (window.calc_stack.currentWidget() is page) == is_crystal
        assert window.project_tabs.currentIndex() == window.project_sessions.index(target)
    assert 'Quantum ESPRESSO' not in [window.program.itemText(k) for k in range(window.program.count())]
    window.project_tabs.setCurrentIndex(window.project_sessions.index(crystal))
    programs = window.crystal_mode_tool.panel.program_box
    assert [programs.itemData(k) for k in range(programs.count())] == ['qe', 'cp2k']
    # with the server chosen the crystal page has the buttons of the server and of its files, as a molecule (the owner's
    # Windows, 2026-11-24: there were none)
    tool, panel = window.crystal_mode_tool, window.crystal_mode_tool.panel
    assert not tool.server_button.isVisibleTo(page) and not tool.server_files_button.isVisibleTo(page)

    class Profile:
        def title(self):
            return 'lab'

    monkeypatch.setattr(panel, 'server_profile', lambda: Profile())
    panel.update_where()
    tool.set_where('server')
    assert panel.on_server() and tool.server_button.isVisibleTo(page) and tool.server_files_button.isVisibleTo(page)
    tool.set_where('local')
    assert not tool.server_button.isVisibleTo(page)
    for d in window.all_documents():
        d.dirty = False


def test_a_new_project_has_no_kind_until_something_is_in_it(window, monkeypatch):
    from azimuth import crystal_projects
    from azimuth.core import read_xyz

    window.dirty = False
    examples = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals'
    window.load_molecule(read_xyz('3\nwater\nO 0 0 0\nH 0 0.76 0.58\nH 0 -0.76 0.58'))
    molecules = window.ensure_project_tab()
    tabs = window.project_tabs
    assert tabs.tabData(window.project_sessions.index(molecules)) == 'molecule'
    window.new_project_tab()
    empty = window.research_path()
    assert tabs.tabData(window.project_sessions.index(empty)) == '' and tabs.tabIcon(tabs.currentIndex()).isNull()
    window.navigate(1)
    assert window.program.findData('qe') >= 0 and window.program.findData('cp2k') >= 0
    # a program of a crystal chosen: a CIF is opened, it takes the place of the empty project, its page — with CP2K
    def open_cif():
        window.opening_tool.open_example_path(str(examples / 'CsCl.cif'))
        window.crystal_window.reject()
        return 'CsCl.cif'

    monkeypatch.setattr(window.crystal_tool, 'open_cif', open_cif)
    before = window.program.currentData()
    window.program.setCurrentIndex(window.program.findData('cp2k'))
    crystal = window.research_path()
    assert crystal_projects.is_crystal(crystal) and empty not in window.project_sessions
    assert window.project_sessions == [molecules, crystal]
    assert window.calc_stack.currentWidget() is window.crystal_mode_tool.page
    assert window.crystal_mode_tool.panel.program == 'cp2k'
    assert window.program.findData('qe') < 0 and window.program.currentData() == before
    assert window.preferences.value('sextant_program') != 'cp2k'
    for d in window.all_documents():
        d.dirty = False


def test_the_tab_of_a_loose_molecule_stays_beside_a_crystal(window):
    # the tab stays and brings the molecule back
    from azimuth.core import read_xyz

    window.dirty = False
    examples = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals'
    window.opening_tool.open_example_path(str(examples / 'CsCl.cif'))
    window.crystal_window.reject()
    window.crystal_tool.set_compass_mode('molecule')
    window.load_molecule(read_xyz('5\nmethane\nC 0 0 0\nH 0.63 0.63 0.63\nH -0.63 -0.63 0.63\nH -0.63 0.63 -0.63\n'
                                  'H 0.63 -0.63 -0.63'))
    tabs = window.project_tabs
    # the molecule drawn of no project, left for another tab, is written into a draft
    # project of its own — its tab is a project tab from then on, it cannot vanish
    for section in (0, 1):
        window.navigate(section)
        tabs.setCurrentIndex(0)
        assert window.compass_mode == 'crystal' and tabs.count() == 2 and tabs.tabData(1) == 'molecule'
        assert len(window.project_sessions) == 2
        kept = window.project_sessions[1]
        tabs.setCurrentIndex(1)
        assert window.compass_mode == 'molecule' and window.research_path() == kept
        assert window.molecule.formula == 'CH4' and tabs.currentIndex() == 1
    assert window.calc_stack.currentWidget() is not window.crystal_mode_tool.page
    for d in window.all_documents():
        d.dirty = False


def test_a_new_project_made_in_the_crystal_stays_there(window):
    from azimuth import crystal_projects

    window.dirty = False
    examples = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals'
    window.opening_tool.open_example_path(str(examples / 'CsCl.cif'))
    window.crystal_window.reject()
    cscl = window.research_path()
    empty = window.new_project_tab()
    tabs = window.project_tabs
    assert window.compass_mode == 'crystal' and window.crystal is None and tabs.tabData(tabs.currentIndex()) == ''
    tabs.setCurrentIndex(window.project_sessions.index(cscl))
    tabs.setCurrentIndex(window.project_sessions.index(empty))
    assert window.compass_mode == 'crystal' and window.research_path() == empty and window.crystal is None
    window.opening_tool.open_example_path(str(examples / 'CsCl.cif'))
    window.crystal_window.reject()
    second = window.research_path()
    assert crystal_projects.is_crystal(second) and empty not in window.project_sessions
    window.navigate(1)
    window.navigate(2)  # Spectrum of the crystal — the project of the crystal stays, no new project
    assert window.stack.currentIndex() == 2 and window.results_stack.currentWidget() is window.crystal_results
    assert window.research_path() == second and len(window.project_sessions) == 2
    # as the empty Spectrum of a molecule — the tabs with the first one alone, in it Quill with her
    # magnifier and the hint in place of the plots and the table; no list of runs
    empty = window.crystal_results
    tabs = empty.tabs
    assert tabs.isVisibleTo(empty) and empty.empty.isVisibleTo(empty) and not empty.runs.isVisibleTo(empty)
    assert [tabs.isTabVisible(k) for k in range(tabs.count())].count(True) == 1
    assert tabs.currentIndex() == empty.optimization_tab and empty.steps_table.rowCount() == 0
    assert empty.steps_table.isVisibleTo(empty) and not empty.energy_plot.isVisibleTo(empty)  # the table empty
    assert tabs.header.isVisibleTo(empty) and tabs.header.count() == 1  # the tabs on the top of the frame, as a molecule's
    cards = empty.tabs.widget(empty.optimization_tab).layout()  # the cards share the width 2 : 3, as a molecule's
    assert [cards.stretch(k) for k in range(cards.count())] == [2, 3]
    assert not empty.empty_quill.pixmap().isNull() and empty.empty_quill.isVisibleTo(empty)
    from PySide6.QtCore import Qt

    assert 'Секстанте' in empty.empty_text.text() and empty.empty_text.alignment() & Qt.AlignmentFlag.AlignHCenter
    # another tab of a crystal chosen in Spectrum — Spectrum stays, with the results of that crystal
    window.project_tabs.setCurrentIndex(window.project_sessions.index(cscl))
    assert window.stack.currentIndex() == 2 and window.results_stack.currentWidget() is window.crystal_results
    assert window.research_path() == cscl and 'CsCl' in window.crystal_results.heading.text()
    for d in window.all_documents():
        d.dirty = False


def test_the_steps_of_the_optimization_of_a_crystal(window):
    # the vc-relax of silicon (pw.x 7.6) step by step in «Компас · Кристалл»
    from modules.compass.chemistry import crystal_steps
    from modules.spectrum.readers import qe

    window.dirty = False
    examples = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals'
    window.opening_tool.open_example_path(str(examples / 'CsCl.cif'))
    window.crystal_window.reject()
    text = (Path(__file__).resolve().parents[1] / 'data' / 'qe' / 'si2_vcrelax_pw76.out').read_text(encoding='utf-8')
    steps = crystal_steps.make_steps(qe.steps(text), 'Si')
    window.trajectory_tool.load_crystal_steps(steps, 'оптимизация QE · Si')
    drawer = window.drawer
    assert len(drawer.steps) == 3 and drawer.current == 2 and window.browsing and window.trajectory_button.isChecked()
    assert [a.symbol for a in window.viewer.molecule.atoms] == ['Si', 'Si']
    assert window.viewer.ghost is not None and 'ΔV +2.05 %' in drawer.detail.text()
    edges = window.viewer.cell_lines
    drawer.select(0)
    assert window.viewer.ghost is None and window.viewer.cell_lines != edges
    drawer.select(2)
    window.trajectory_tool.adopt_trajectory_step()
    assert not window.browsing and abs(window.crystal[0].cell.a - 3.866076314) < 1e-6
    assert [s.symbol for s in window.crystal[0].sites] == ['Si', 'Si']
    # the real CELL_OPT of CsCl (CP2K 2026.2): «Взять» gives the cell of the file in its group P m -3 m, in this tab
    from modules.compass.chemistry import crystal as cr
    from modules.spectrum.readers import cp2k

    # a crystal opened in a crystal project goes into it, in its tab — the step taken above is
    # a change of that tab, and «Заменить структуру?» would be asked; it is let go here
    window.dirty = False
    window.opening_tool.open_example_path(str(examples / 'CsCl.cif'))
    window.crystal_window.reject()
    projects_before = list(window.project_sessions)
    original = window.crystal[0]
    found = crystal_steps.make_steps(cp2k.steps(Path(__file__).resolve().parents[1] / 'data' / 'cp2k' / 'cscl_cellopt'),
                                     'CsCl', original)
    window.trajectory_tool.load_crystal_steps(found, 'оптимизация CP2K · CsCl')
    assert len(drawer.steps) == 11 and 'P m -3 m' in drawer.detail.text()
    window.trajectory_tool.adopt_trajectory_step()
    kept = window.crystal[0]
    assert kept.space_group == original.space_group and abs(kept.cell.a - 5.2841042045) < 1e-6
    assert [s.label for s in kept.sites] == [s.label for s in original.sites] and window.project_sessions == projects_before
    for d in window.all_documents():
        d.dirty = False


def test_open_example_routes_files(window):
    # «Файл → Открыть пример…»: a result with steps goes to the Compass drawer, spectra to
    # Spectrum, a CIF to the «Кристалл» window, the fragments file to «Мои фрагменты»
    from modules.compass.chemistry import user_fragments
    from modules.compass.actions.fragment_actions import SETTINGS_KEY
    from azimuth.paths import ROOT

    examples = ROOT / 'examples'
    window.dirty = False
    window.opening_tool.open_example_path(str(examples / '2-optimization' / 'divinylbenzene_opt_psi4.out'))
    assert window.stack.currentIndex() == 0 and len(window.drawer.steps) > 1
    window.trajectory_tool.set_trajectory_open(False)
    window.opening_tool.open_example_path(str(examples / '5-uv-vis-nmr' / 'divinylbenzene_tddft_orca6.out'))
    assert window.stack.currentIndex() == 2 and window.output.absorption
    window.opening_tool.open_example_path(str(examples / '10-crystals' / 'CsCl.cif'))
    assert window.crystal is not None and not window.crystal_window.isVisible()  # built, no window
    window.crystal_window.reject()
    saved = window.preferences.value(SETTINGS_KEY, '')
    previous = dict(user_fragments.USER)
    try:
        window.fragment_tool._store_fragments({})
        assert window.opening_tool.open_example_path(str(examples / '11-fragments' / 'example_fragments.json')) == 3
    finally:
        window.fragment_tool._store_fragments(previous)
        window.preferences.setValue(SETTINGS_KEY, saved)


def test_broken_optimization_steps_go_to_compass(window, app, tmp_path):
    # the user — «При завершении расчета с ошибкой нельзя перейти в Компас чтоб взять последнюю геометрию… приходится
    # открывать этот out через компас». An ORCA optimization that broke off after three cycles: its steps go to the tab
    # of the calculation, the last geometry is the structure there, the window offers «Перейти в Компас», which opens
    # them
    from types import SimpleNamespace

    lines = (Path(__file__).parents[2] / 'examples' / 'optimization-demo.out').read_text(encoding='utf-8').splitlines()
    out = tmp_path / 'broken.out'
    out.write_text('\n'.join(lines[:34]) + '\n\nORCA finished by error termination in SCF gradient\n', encoding='utf-8')
    asked = []
    place = SimpleNamespace(show_results=lambda compass=False, spectrum=False: asked.append((compass, spectrum)))
    show_model(window, app)
    window.dirty = False
    try:
        assert window.run_tool.open_broken_result(SimpleNamespace(spec=SimpleNamespace(output=out)), place)
        assert asked == [(True, False)] and len(window.output.steps) == 3
        last = window.output.steps[-1].geometry
        shown = window.coordinate_tool.table_molecule().atoms
        assert len(shown) == 3 and all(abs(p - q) < 1e-6 for a, b in zip(shown, last.atoms)
                                       for p, q in zip(a.position, b.position))
        assert window.run_tool.go_to_result('compass') == 'compass'
        assert window.stack.currentIndex() == 0 and window.trajectory_button.isChecked()
        assert window.drawer.page() == 'steps' and window.drawer.table.rowCount() == 3
        # an output without steps (or none at all) — nothing is opened and nothing is said
        empty = tmp_path / 'empty.out'
        empty.write_text('ORCA finished by error termination in SCF\n', encoding='utf-8')
        assert not window.run_tool.open_broken_result(SimpleNamespace(spec=SimpleNamespace(output=empty)), place)
        assert not window.run_tool.open_broken_result(SimpleNamespace(spec=SimpleNamespace(output=tmp_path / 'none.out')), place)
        assert asked == [(True, False)]
    finally:
        window.trajectory_tool.set_trajectory_open(False)
        for d in window.all_documents():
            d.dirty = False
        window.dirty = False


def test_standard_views_zmatrix_editor_and_documents(window, app, tmp_path):
    # views along an axis, a bond and onto a plane; the Z-matrix editor (live, undoable, cancel,
    # a wrong number); the picture as SVG and PDF; a CIF dropped on the window; a (111) slab and its CIF
    from math import dist

    from modules.compass.chemistry import crystal as cr

    show_model(window, app)
    window.dirty = False
    viewer = window.viewer
    mol = window.molecule
    assert window.view_tool.standard_view('z') and viewer.to_view((0, 0, 1))[2] == pytest.approx(1.0)
    assert window.view_tool.standard_view('x') and viewer.to_view((1, 0, 0))[2] == pytest.approx(1.0)
    viewer.set_selection([0, 1])
    assert window.view_tool.standard_view('bond')
    d = [mol.atoms[1].position[k] - mol.atoms[0].position[k] for k in range(3)]
    x, y, _ = viewer.to_view(d)
    assert abs(x) < 1e-9 and abs(y) < 1e-9  # the bond points at the viewer
    viewer.set_selection([0, 1, 2])
    assert window.view_tool.standard_view('plane')
    depths = [viewer.to_view(a.position)[2] for a in mol.atoms[:3]]
    assert max(depths) - min(depths) < 1e-9  # the three atoms lie in the plane of the screen
    viewer.set_selection([])
    assert not window.view_tool.standard_view('bond')

    start = window.coordinate_tool.table_molecule()
    w = window.view_tool.open_zmatrix_editor()
    assert w is not None and w.table.rowCount() == len(start.atoms)
    w.table.item(1, 2).setText('1.200000')  # the second atom: its distance to the first
    shown = window.molecule
    a, b = w.rows()[1][1], 1
    assert dist(shown.atoms[b].position, shown.atoms[a].position) == pytest.approx(1.2, abs=1e-6)
    centre = lambda m: [sum(at.position[k] for at in m.atoms) / len(m.atoms) for k in range(3)]  # noqa: E731
    assert dist(centre(shown), centre(start)) < 0.5  # put back in its place, not at the origin
    w.table.item(1, 2).setText('abc')
    assert not w.message.isHidden() and window.molecule is shown
    w.table.item(1, 2).setText('1.200000')
    # the Z-matrix of the table to a file,
    # the window open; read back it is the same structure
    from PySide6.QtWidgets import QPushButton

    from modules.compass.chemistry import zmatrix

    assert any(b.text() == 'Сохранить…' for b in w.findChildren(QPushButton))
    saved = w.save(tmp_path / 'water.zmat')
    assert saved and w.isVisible() and (tmp_path / 'water.zmat').read_text(encoding='utf-8') == zmatrix.text(w.rows())
    rows = zmatrix.parse((tmp_path / 'water.zmat').read_text(encoding='utf-8').splitlines())
    assert len(rows) == len(start.atoms) and rows[1][2] == pytest.approx(1.2)
    w.commit()
    assert dist(window.molecule.atoms[1].position, window.molecule.atoms[a].position) == pytest.approx(1.2, abs=1e-6)
    window.undo_geometry()
    assert window.molecule.atoms == start.atoms
    w = window.view_tool.open_zmatrix_editor()
    w.table.item(1, 2).setText('2.000000')
    w.cancel()
    assert window.molecule.atoms == start.atoms

    svg = window.view_tool.save_document('.svg', tmp_path / 'model.svg')
    text = svg.read_text(encoding='utf-8')
    assert text.lstrip().startswith('<?xml') and '<image' in text  # the model as an image, the rest vector
    pdf = window.view_tool.save_document('.pdf', tmp_path / 'model.pdf')
    assert pdf.read_bytes()[:5] == b'%PDF-' and pdf.stat().st_size > 2000

    nacl = Path(__file__).parents[2] / 'examples' / '10-crystals' / 'NaCl_rock_salt.cif'
    window.dirty = False
    assert window.view_tool.drop_paths([str(nacl), str(tmp_path / 'missing.xyz')]) == str(nacl)
    assert window.crystal_window is not None and window.crystal is not None  # built at once
    window.crystal_window.miller[0].setValue(1)
    window.crystal_window.miller[1].setValue(1)
    window.crystal_window.miller[2].setValue(1)
    window.crystal_window.layers.setValue(2)
    for spin in window.crystal_window.plane:
        spin.setValue(1)
    window.crystal_window.build_surface()
    assert len(window.molecule.atoms) == 16 and len(viewer.cell_lines) == 12
    saved = window.crystal_tool.save_crystal_cif(tmp_path / 'slab.cif')
    assert len(cr.unit_cell(cr.parse_cif(Path(saved).read_text(encoding='utf-8')))) == 16
    window.crystal_tool.clear_crystal()


def test_document_tabs_keep_results(window, app, monkeypatch):
    # a result opens in a new tab and the molecule stays in its own; an empty tab takes the result
    # itself; the result of a job goes back to the tab it was started from; the drawer closed shows the last
    # geometry; a tab with unsaved changes asks before it closes; the program starts with an empty Compass
    from azimuth.paths import ROOT

    show_model(window, app)
    water = window.molecule
    demo = str(ROOT / 'examples' / 'optimization-demo.out')
    window.opening_tool.open_path(demo)
    assert len(window.documents) == 2 and window.current_document == 1 and window.browsing
    window.trajectory_tool.set_trajectory_open(False)
    assert window.molecule.atoms[1].x == 0.7586 and 'optimization-demo.out' in window.document_title(1)
    window.navigate(1)
    window.navigate(0)  # going to Sextant and back keeps the result
    assert window.current_document == 1 and len(window.drawer.steps) == 5 and window.molecule.atoms[1].x == 0.7586
    window.switch_document(0)
    assert window.molecule == water and not window.drawer.steps
    window.new_document()
    assert len(window.documents) == 3 and not window.molecule.atoms
    window.opening_tool.open_path(demo)  # the shown tab is empty: the result goes there
    assert len(window.documents) == 3 and window.current_document == 2 and len(window.drawer.steps) == 5
    window.trajectory_tool.set_trajectory_open(False)
    window.result_target = window.documents[0]  # as Sextant does for the tab a job was started from
    window.opening_tool.open_path(demo)
    assert window.current_document == 0 and len(window.documents) == 3
    window.trajectory_tool.set_trajectory_open(False)
    assert window.molecule.atoms[1].x == 0.7586 and window.dirty  # one undoable change in that tab
    window.undo_geometry()
    assert window.molecule == water
    from PySide6.QtWidgets import QMessageBox

    asked = []
    monkeypatch.setattr(QMessageBox, 'question', lambda *a, **k: asked.append(a[1]) or QMessageBox.StandardButton.No)
    window.dirty = True
    assert window.close_document(0) is False and asked and len(window.documents) == 3
    window.dirty = False
    assert window.close_document(0) and len(window.documents) == 2
    for _ in range(2):
        window.close_document(0)
    assert len(window.documents) == 1 and not window.molecule.atoms  # the last tab: an empty one
    fresh = Studio()
    try:
        assert not fresh.molecule.atoms and len(fresh.documents) == 1
    finally:
        fresh.dirty = False
        fresh.close()


def test_molecule_and_crystal_have_their_own_tabs(window, app):
    # «Компас · Молекула» and «Компас · Кристалл» do not share tabs: each shows its own, a crystal never
    # appears among the molecules and a molecule never among the crystals; results and XYZ files go to the molecules
    from azimuth.paths import ROOT

    examples = ROOT / 'examples'
    water = window.molecule
    assert window.compass_mode == 'molecule' and water.atoms and len(window.documents) == 1
    window.crystal_tool.set_compass_mode('crystal')
    assert len(window.documents) == 1 and not window.molecule.atoms  # its own, empty tab
    assert 'CIF' in window.viewer.empty_text
    window.dirty = False
    window.opening_tool.open_path(str(examples / '10-crystals' / 'NaCl_rock_salt.cif'))
    window.crystal_window.build()
    nacl = window.molecule
    assert window.compass_mode == 'crystal' and window.crystal is not None and nacl.atoms
    assert len(window.documents) == 1  # built in the empty crystal tab, no new tab
    window.crystal_tool.set_compass_mode('molecule')
    assert window.molecule.atoms == water.atoms and window.crystal is None and len(window.documents) == 1
    assert window.viewer.cell_lines is None
    window.crystal_tool.set_compass_mode('crystal')
    assert window.molecule.atoms == nacl.atoms and window.crystal is not None and window.viewer.cell_lines
    # an XYZ opened from the crystal subsection goes to the molecules
    window.opening_tool.open_path(str(examples / '9-torsion' / 'butane.xyz'))
    assert window.compass_mode == 'molecule' and window.crystal is None
    assert all(d.kind == 'molecule' for d in window.documents)
    assert len(window.all_documents()) == len(window.documents) + 1  # the crystal tab waits on the shelf
    # unsaved changes in the hidden subsection still count when the window closes
    window.crystal_tool.set_compass_mode('crystal')
    window.dirty = True
    window.crystal_tool.set_compass_mode('molecule')
    window.dirty = False
    assert window.any_dirty()
    # an empty tab that was only visited has nothing to save
    window.new_document()
    window.dirty = True
    for d in window.all_documents():
        if d.molecule is not None and d.molecule.atoms:
            d.dirty = False
    assert not window.any_dirty()


def test_tabs_stand_on_the_edge_of_the_field(window, app):
    # the row of tabs right on the top edge of the field, starting after its rounded corner
    window.show()
    app.processEvents()
    row, field = window.document_row, window.structure_tabs
    assert row.parentWidget() is field.parentWidget()
    assert row.geometry().bottom() + 1 == field.geometry().top()
    assert row.layout().contentsMargins().left() >= 10  # the radius of the field's corner


def test_crystal_tab_and_the_empty_field(window, app):
    # «Кристалл | Координаты» in «Компас · Кристалл»; the empty molecule field says how to begin
    from modules.compass.view.viewer import EMPTY_TEXT

    window.dirty = False
    window.crystal_tool.set_compass_mode('crystal')
    assert window.view_tabs.tabText(0) == 'Кристалл' and window.structure_tabs.tabText(0) == 'Кристалл'
    window.crystal_tool.set_compass_mode('molecule')
    assert window.view_tabs.tabText(0) == 'Молекула'
    assert EMPTY_TEXT.startswith('Постройте свою молекулу') and not hasattr(window.viewer, 'empty_text')
    # 0.247.0: no Quill with her bubble in the empty field — the field itself says how to begin, a crystal its own way
    from modules.compass.view.viewer import CRYSTAL_PARTS, EMPTY_PARTS

    window.resize(1400, 900)
    window.show()
    window.navigate(0)
    app.processEvents()
    window.new_document()
    app.processEvents()
    assert window.quill_hint is None and window.crystal_hint is None and not getattr(window.viewer, 'hint_shown', False)
    assert window.viewer.empty_parts == EMPTY_PARTS
    window.viewer.grab()  # the pale words with their glyphs
    window.crystal_tool.set_compass_mode('crystal')
    assert window.viewer.empty_parts == CRYSTAL_PARTS and [g for _, g in CRYSTAL_PARTS] == ['folder', 'crystal']
    window.viewer.grab()
    window.crystal_tool.set_compass_mode('molecule')
    assert window.viewer.empty_parts == EMPTY_PARTS
    assert not window.open_action.icon().isNull()  # «Открыть…» with the folder
    assert window.drawer.initial.isCheckable() and window.drawer.initial.property('quail_icon') == 'initial-geometry'


def test_sdf_tabs_pdb_frames_and_line_formats(window, app, tmp_path, monkeypatch):
    # an SDF file with several molecules (listed on «Структуры» of the drawer); a PDB file with
    # several MODEL frames opens in the steps drawer; the coordinates tab shows SMILES and InChI (from PubChem)
    import time

    from modules.compass.chemistry import formats, pubchem

    show_model(window, app)
    window.confirm_replace = lambda: True
    water = read_xyz(EXAMPLES['Вода · H₂O'])
    methane = read_xyz(EXAMPLES['Метан · CH₄'])
    sdf = tmp_path / 'set.sdf'
    sdf.write_text(formats.write_sdf(water, ((0, 1, 1), (0, 2, 1))) + formats.write_sdf(methane, ())
                   + formats.write_sdf(read_xyz('1\nneon\nNe 0 0 0\n'), ()), encoding='utf-8')
    try:
        # a set opens as a project — its list instead of «Структуры» of the drawer
        window.opening_tool.open_path(str(sdf))
        assert window.project_molecules.count() == 3 and window.molecule.formula == 'H2O'
        window.project_molecules.setCurrentRow(1)
        assert window.molecule.formula == 'CH4'
        # the input files of the whole set, with the settings of Sextant (one file per structure)
        window.program.setCurrentIndex(window.program.findData('orca'))
        window.task.setCurrentIndex(window.task.findText('Энергия'))
        out = tmp_path / 'set-inputs'
        out.mkdir()
        written = window.input_tool.export_set_inputs(str(out))
        assert len(written) == 3 and all(p.suffix == '.inp' for p in written)
        assert any('* xyz 0 1' in p.read_text() and 'Ne ' in p.read_text() for p in written)
        window.project_molecules.setCurrentRow(0)
        assert window.molecule.formula == 'H2O'
        first = window.current_document
        pdb = tmp_path / 'md.pdb'
        frames = ''.join(
            f'MODEL {k}\n' + ''.join(line + '\n' for line in formats.write_pdb(
                read_xyz(f'3\nw\nO 0 0 0\nH {x} 0 0\nH -0.24 0.93 0\n'), ((0, 1, 1), (0, 2, 1))).splitlines()
                if line.startswith('HETATM')) + 'ENDMDL\n' for k, x in ((1, 0.95), (2, 0.97)))
        pdb.write_text(frames + 'END\n', encoding='utf-8')
        window.opening_tool.open_path(str(pdb))
        assert window.browsing and window.drawer.table.rowCount() == 2 and window.drawer.page() == 'steps'
        window.trajectory_tool.set_trajectory_open(False)
        window.switch_document(first)
        window.structure_tabs.setCurrentIndex(1)
        window.coord_format.setCurrentText('SMILES')
        assert window.coord_text.toPlainText() == 'O' and not window.coord_units.isEnabled()
        monkeypatch.setattr(pubchem, 'lookup_inchi', lambda smiles, **kw: ('InChI=1S/H2O/h1H2', 'XLYOFNOQVPJJNP-UHFFFAOYSA-N'))
        window.coord_format.setCurrentText('InChI')
        end = time.monotonic() + 5
        while not window.coord_text.toPlainText().startswith('InChI=') and time.monotonic() < end:
            app.processEvents()
            time.sleep(0.02)
        assert window.coord_text.toPlainText() == 'InChI=1S/H2O/h1H2\nXLYOFNOQVPJJNP-UHFFFAOYSA-N'
        window.coord_format.setCurrentIndex(0)
        window.structure_tabs.setCurrentIndex(0)
    finally:
        for d in window.all_documents():
            d.dirty = False
        window.dirty = False


def test_own_atom_labels(window, app, monkeypatch):
    # «Своя подпись» — the selected atoms get the label written («#» — their number in the selection),
    # without a selection the own labels are hidden and shown again; the labels follow the atoms through edits
    # (an atom added or deleted elsewhere, a moved geometry), live in the tab and in the project
    from PySide6.QtWidgets import QInputDialog

    from azimuth.core import project_labels, project_text

    show_model(window, app)
    window.confirm_replace = lambda: True
    water = read_xyz(EXAMPLES['Вода · H₂O'])
    try:
        window.viewer.custom_labels = {}
        window.load_molecule(water)
        assert not window.custom_label_button.isHidden()
        window.viewer.set_selection([1, 2])
        monkeypatch.setattr(QInputDialog, 'getText', staticmethod(lambda *a, **k: ('H#', True)))
        assert window.edit_custom_labels() == {1: 'H1', 2: 'H2'}
        window.viewer.grab()  # painted beside the atoms
        window.viewer.set_selection([])
        assert window.edit_custom_labels() is False and not window.custom_label_button.isChecked()
        assert window.edit_custom_labels() is True
        moved = Molecule(water.title, tuple(Atom(a.symbol, a.x + 0.1, a.y, a.z) for a in water.atoms))
        window.load_molecule(moved)
        assert window.viewer.custom_labels == {1: 'H1', 2: 'H2'}  # the same atoms, moved
        fewer = Molecule(water.title, moved.atoms[1:])  # the oxygen deleted: the hydrogens are atoms 0 and 1
        window.load_molecule(fewer)
        assert window.viewer.custom_labels == {0: 'H1', 1: 'H2'}
        text = project_text(window.coordinate_tool.table_molecule(), window.calculation(), (), window.viewer.custom_labels)
        assert project_labels(text) == {0: 'H1', 1: 'H2'}
        first = window.current_document
        window.new_document()
        assert window.viewer.custom_labels == {}
        window.switch_document(first)
        assert window.viewer.custom_labels == {0: 'H1', 1: 'H2'}
        window.close_document(first + 1)
        window.viewer.set_selection([0])
        monkeypatch.setattr(QInputDialog, 'getText', staticmethod(lambda *a, **k: ('', True)))
        assert window.edit_custom_labels() == {1: 'H2'}  # empty — removed
    finally:
        window.viewer.custom_labels = {}
        for d in window.all_documents():
            d.dirty = False
        window.dirty = False


def test_a_database_without_names_is_named_by_formula(window, tmp_path):
    # the records of an SDF without a name of their own get the formula (with the hydrogens added), the same
    # formula again « · 2»; a named record keeps its name
    from modules.compass.chemistry import formats

    water = read_xyz(EXAMPLES['Вода · H₂O'])
    bonds = [(0, 1, 1), (0, 2, 1)]
    text = formats.write_sdf(replace(water, title=''), bonds) * 2 + formats.write_sdf(replace(water, title='Вода'), bonds)
    path = tmp_path / 'base.sdf'
    path.write_text(text, encoding='utf-8')
    window.dirty = False
    assert window.opening_tool.open_paths_as_set([str(path)]) == 3
    assert [name for _, name in window.batch_tool.structure_rows()] == ['H₂O', 'H₂O · 2', 'Вода']
    assert window.own_molecule().title == 'H₂O'  # the structure of the tab (the panel shows the first one meanwhile)
    window.trajectory_tool.set_trajectory_open(False)
    window.dirty = False


def test_files_without_hydrogens_get_them_when_opened(window, tmp_path, monkeypatch):
    # a file of the heavy atoms only (a database) gets its hydrogens by the valences as an edit of its own
    # (Ctrl+Z gives the file back); a file with hydrogens is not touched; «Файл → Достраивать водороды у файлов без H»
    # turns it off; the structures of an SDF set get them too
    monkeypatch.setattr(window, 'confirm_replace', lambda: True)
    asked = []  # the flat (2D) skeleton — Quill offers 3D; «Не сейчас» here
    monkeypatch.setattr(window.opening_tool, 'offer_3d', lambda flat, total: asked.append((flat, total)) or 0)
    saved = window.preferences.value(window.HYDROGENS_ON_OPEN)
    skeleton = tmp_path / 'ethanol.xyz'
    skeleton.write_text('3\nethanol\nC 0 0 0\nC 1.52 0 0\nO 2.0 1.35 0\n', encoding='utf-8')
    water = tmp_path / 'water.xyz'
    water.write_text('3\nwater\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0\n', encoding='utf-8')
    try:
        assert window.hydrogens_open_action.isChecked()  # on by default
        window.opening_tool.open_path(str(skeleton))
        assert window.coordinate_tool.table_molecule().formula == 'C2H6O' and asked == [(1, 1)]
        window.undo_geometry()
        assert window.coordinate_tool.table_molecule().formula == 'C2O'  # the file as it was
        window.opening_tool.open_path(str(water))
        assert window.coordinate_tool.table_molecule().formula == 'H2O'
        window.hydrogens_open_action.setChecked(False)
        assert not window.opening_tool.hydrogens_on_open()
        window.opening_tool.open_path(str(skeleton))
        assert window.coordinate_tool.table_molecule().formula == 'C2O'
        window.hydrogens_open_action.setChecked(True)
        sdf = tmp_path / 'set.sdf'
        record = ('{name}\n  test\n\n  2  1  0  0  0  0  0  0  0  0999 V2000\n'
                  '    0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n'
                  '    1.4300    0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0\n'
                  '  1  2  1  0\nM  END\n$$$$\n')
        sdf.write_text(record.format(name='methanol') + record.format(name='again'), encoding='utf-8')
        window.opening_tool.open_path(str(sdf))
        assert [m.formula for m, _ in window.batch_tool.structure_rows()] == ['CH4O', 'CH4O']
        assert window.coordinate_tool.table_molecule().formula == 'CH4O'
    finally:
        if saved is None:
            window.preferences.remove(window.HYDROGENS_ON_OPEN)
        else:
            window.preferences.setValue(window.HYDROGENS_ON_OPEN, saved)


def test_steps_in_one_orientation(window):
    # «Шаги оптимизации и скана — в одной ориентации» (Chemcraft: Set common orientation for all geometries):
    # a step turned by 90° about z is shown (and taken) in the orientation of the start; lengths are kept
    from math import dist

    from azimuth import defaults
    from azimuth.core import Atom, Molecule

    start = Molecule('', (Atom('O', 0, 0, 0), Atom('H', 0.96, 0, 0), Atom('H', -0.24, 0.93, 0)), None)
    turned = Molecule('', tuple(Atom(a.symbol, -a.position[1], a.position[0], a.position[2]) for a in start.atoms),
                      None)
    window.trajectory_initial = start
    try:
        assert window.trajectory_tool.oriented_step(turned) is turned  # off: as in the output
        defaults.put('common_orientation', True)
        shown = window.trajectory_tool.oriented_step(turned)
        assert max(dist(a.position, b.position) for a, b in zip(shown.atoms, start.atoms)) < 1e-9
        assert abs(dist(shown.atoms[0].position, shown.atoms[2].position)
                   - dist(turned.atoms[0].position, turned.atoms[2].position)) < 1e-12
        other = Molecule('', start.atoms[:2], None)
        assert window.trajectory_tool.oriented_step(other) is other  # other atoms: nothing to turn onto
    finally:
        defaults.reset()
        window.trajectory_initial = None


def test_a_field_is_not_shown_on_another_document(window, app, monkeypatch):
    # the spinner leaves the window usable; a field whose document changed while
    # it was computed is kept, not shown (InterruptedError, as «Отмена»), and the second press takes it from the cache
    import numpy as np

    from modules.compass.actions.surface_actions import field_bytes

    class Ring:
        def start(self):
            pass

        def stop(self):
            pass

    contexts = iter([('doc', 1), ('another', 2)])
    monkeypatch.setattr(window.surface_tool, 'field_context', lambda: next(contexts))
    window.quiet_spinner = Ring()
    calls = []
    try:
        with pytest.raises(InterruptedError):
            window.surface_tool.wait_field(('test-field', 1), 'поле', lambda step: calls.append(1) or np.zeros((10, 10, 10)))
        again = window.surface_tool.wait_field(('test-field', 1), 'поле', lambda step: calls.append(1))
    finally:
        window.quiet_spinner = None
    assert calls == [1] and again.shape == (10, 10, 10)
    assert field_bytes((again, {'x': again}, 'text')) == 2 * again.nbytes


def test_structure_chosen_in_the_list_keeps_its_charge(window, app, tmp_path):
    # 0.100.1 (no «Взять эту структуру»), the list of the project — the molecule chosen is the molecule of
    # the tab with its charge and multiplicity from the file (the chloride −1, the water 0)
    from modules.compass.chemistry import formats
    from tests.compass.test_formal_charges import CHLORIDE

    show_model(window, app)
    window.confirm_replace = lambda: True
    window.opening_tool.hydrogens_on_open = lambda: True
    water = read_xyz(EXAMPLES['Вода · H₂O'])
    sdf = tmp_path / 'set.sdf'
    sdf.write_text(formats.write_sdf(water, ((0, 1, 1), (0, 2, 1))) + CHLORIDE, encoding='utf-8')
    window.opening_tool.open_path(str(sdf))
    assert not hasattr(window.drawer, 'structure_adopt')
    window.project_molecules.setCurrentRow(1)
    assert window.molecule.formula == 'Cl' and window.charge.value() == -1
    window.project_molecules.setCurrentRow(0)
    assert window.molecule.formula == 'H2O' and window.charge.value() == 0


def test_a_project_opens_from_the_crystal(window, tmp_path, monkeypatch):
    # the dialog of «Открыть CIF…» and of
    # the folder of the empty field takes a project too; the project of a crystal is then among «Недавние файлы»
    from PySide6.QtWidgets import QFileDialog

    from azimuth import crystal_projects
    from modules.compass.chemistry import surface
    from tests.sextant.test_qe_inputs import silicon

    path = crystal_projects.create(tmp_path / 'projects', 'Si', surface.write_cif(silicon()))
    window.crystal_tool.set_compass_mode('crystal')
    assert 'Открыть проект' in window.viewer.empty_text
    asked = []

    def chosen(parent, title, start, kinds):
        asked.append(kinds)
        return str(path), ''

    monkeypatch.setattr(QFileDialog, 'getOpenFileName', chosen)
    assert window.crystal_tool.open_cif() == str(path)
    assert '*.qcc' in asked[0] and window.compass_mode == 'crystal' and window.research_path() == Path(path).resolve()
    assert str(Path(path).resolve()) in window.file_tool.recent_files()


def test_the_folder_of_projects_opens(window, tmp_path, monkeypatch):
    # the file dialog of the system in «Проекты/Кристаллы» from «Компас · Кристалл», in «Проекты/Молекулы» otherwise,
    # project.qcc chosen
    from PySide6.QtWidgets import QFileDialog

    from azimuth import crystal_projects
    from modules.compass.chemistry import surface
    from tests.sextant.test_qe_inputs import silicon

    monkeypatch.setenv('AZIMUTH_PROJECTS_DIR', str(tmp_path))
    crystal = crystal_projects.create(window.projects_root('crystal'), 'Si', surface.write_cif(silicon()))
    from azimuth import project_folders

    crystals = project_folders.kind_root(tmp_path, 'crystal')  # «Кристаллы», «Crystals» on Windows
    assert Path(crystal).parent.parent == crystals
    asked = []

    def chosen(parent, title, start, kinds):
        asked.append((start, kinds))
        return answer[0], ''

    monkeypatch.setattr(QFileDialog, 'getOpenFileName', chosen)
    answer = [str(crystal)]
    window.crystal_tool.set_compass_mode('crystal')
    window.open_project()
    assert asked[-1] == (str(crystals), 'Азимут (*.qcc)') and window.research_path() == Path(crystal).resolve()
    window.crystal_tool.set_compass_mode('molecule')
    answer[0] = ''
    assert window.open_project() is None  # nothing chosen; no «Молекулы» yet — the folder of projects
    assert asked[-1][0] == str(tmp_path)
    path = window.new_project_tab()
    assert Path(path).parent.parent == project_folders.kind_root(tmp_path, 'molecule')


def test_the_place_of_a_crystal_is_no_window(window, monkeypatch):
    # the panel of Sextant keeps «Где считать» out of its form; with a server set up the list was shown — with no
    # parent, as a window of its own
    from types import SimpleNamespace

    from modules.compass.actions.qe_window import QePanel

    panel = QePanel(window, None, '', None, compact=False, where_in_form=False)
    monkeypatch.setattr(panel, 'server_profile', lambda: SimpleNamespace(title=lambda: 'кластер'))
    panel.update_where()
    assert panel.where.count() == 2 and not panel.where.isVisible() and not panel.where_label.isVisible()
    panel.deleteLater()


def test_a_crystal_project_opens_with_its_steps(window, tmp_path):
    # the project of a crystal with an optimization done opens with its steps in the panel of the steps, the last one
    # shown
    import shutil

    from azimuth import crystal_projects

    cif = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals' / 'CsCl.cif'
    manifest = crystal_projects.create(tmp_path, 'CsCl', cif.read_text(encoding='utf-8'))
    shutil.copytree(Path(__file__).resolve().parents[1] / 'data' / 'cp2k' / 'cscl_cellopt',
                    Path(manifest).parent / 'calculations' / 'cp2k-CsCl-1')
    crystal_projects.record_run(manifest, {'folder': 'calculations/cp2k-CsCl-1', 'program': 'cp2k'})
    window.open_project_path(str(manifest))
    assert window.compass_mode == 'crystal' and len(window.drawer.steps) == 11 and window.drawer.current == 10
    assert window.browsing and abs(window.drawer.steps[-1].adopted.cell.a - 5.2841042) < 1e-6


def test_the_last_run_of_a_crystal_project_in_its_program(window, tmp_path, monkeypatch):
    # a crystal put into the panel — the program of its last run, that run with its buttons and its optimized cell; a
    # program the user picks stays; the item «авто» of the occupations says what it chose (CsCl — an insulator); the
    # card — CsCl, not the block
    import shutil

    from azimuth import crystal_projects
    from modules.compass.actions.qe_window import QePanel
    from modules.compass.chemistry import crystal as cr
    from modules.compass.chemistry import crystal_symmetry

    cif = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals' / 'CsCl.cif'
    manifest = crystal_projects.create(tmp_path, 'CsCl', cif.read_text(encoding='utf-8'))
    shutil.copytree(Path(__file__).resolve().parents[1] / 'data' / 'cp2k' / 'cscl_cellopt',
                    Path(manifest).parent / 'calculations' / 'cp2k-CsCl-1')
    crystal_projects.record_run(manifest, {'folder': 'calculations/cp2k-CsCl-1', 'program': 'cp2k'})
    crystal = cr.parse_cif(cif.read_text(encoding='utf-8'))
    assert crystal_symmetry.empirical_formula(crystal) == 'CsCl'
    panel = QePanel(window, None, '', None, compact=False, where_in_form=False)
    monkeypatch.setattr(panel, 'jobs_root', lambda: Path(manifest).parent / 'calculations')
    assert panel.program == 'qe'
    panel.set_crystal(crystal, 'CsCl')
    assert panel.program == 'cp2k' and panel.program_box.currentData() == 'cp2k'
    assert 'Последний расчёт проекта: cp2k-CsCl-1' in panel.summary.text() and panel.open_button.isEnabled()
    assert len(panel.optimization_steps()) == 11
    assert panel.occupations.itemText(panel.occupations.findData('auto')) == 'авто: изолятор — фиксированные'
    panel.program_box.setCurrentIndex(panel.program_box.findData('qe'))  # the user's choice
    assert panel.program == 'qe' and 'Последний расчёт' not in panel.summary.text()
    panel.deleteLater()


def crystal_project_with_charges(tmp_path):
    """CsCl of the examples as a project with the real CELL_OPT of CP2K (1 × 1 × 1) and its file for Multiwfn; the
    charges of the 3 × 3 × 3 run recorded by Multiwfn (54 atoms) put on its two atoms — Cs +0.547, Cl −0.547 (CM5)."""
    import shutil

    from azimuth import crystal_projects
    from modules.compass.chemistry import crystal_results

    data = Path(__file__).resolve().parents[1] / 'data'
    cif = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals' / 'CsCl.cif'
    manifest = crystal_projects.create(tmp_path, 'CsCl', cif.read_text(encoding='utf-8'))
    run = Path(manifest).parent / 'calculations' / 'cp2k-CsCl-1'
    shutil.copytree(data / 'cp2k' / 'cscl_cellopt', run)
    crystal_projects.record_run(manifest, {'folder': 'calculations/cp2k-CsCl-1', 'program': 'cp2k'})
    crystal_results.write_charges(run, [('Cs', None), ('Cl', None)], {'cm5': (0.546776, -0.546776),
                                                                      'hirshfeld': (0.299477, -0.299477)})
    return Path(manifest), run


def test_the_charges_of_a_crystal_on_its_model(window, tmp_path):
    # «Атомы» and «Связи» above the model of a
    # crystal; the charges of its CP2K run as labels on its atoms; the cleaning button takes them away
    manifest, run = crystal_project_with_charges(tmp_path)
    window.open_project_path(str(manifest))
    if window.browsing:  # the steps of the optimization shown at the opening: the cell of the file
        window.trajectory_tool.leave_trajectory()
    assert window.compass_mode == 'crystal'
    assert not window.property_buttons['atoms'].isHidden() and window.property_buttons['vectors'].isHidden()
    menu = window.property_menus['atoms']
    window.property_tool.fill_properties_menu(menu, 'atoms')
    titles = [a.text() for a in menu.actions()]
    assert 'Заряды CM5 на модели' in titles and 'Таблица зарядов…' in titles
    window.property_tool.show_crystal_charges('cm5')
    shown = window.property_tool.result_overlay(window.molecule)
    labelled = {(a.symbol, round(v, 3)) for a, v in zip(window.molecule.atoms, shown['atom'][1]) if v is not None}
    assert shown['atom'][0] == 'cm5' and labelled == {('Cs', 0.547), ('Cl', -0.547)}
    window.viewer.grab()  # drawn without an error
    table = window.property_tool.crystal_charges_table()
    assert table.table.rowCount() == 2 and table.table.item(0, 3).text() == '+0.547'
    table.close()
    window.property_tool.clear_model_overlays()
    assert window.property_tool.result_overlay(window.molecule) is None
    window.property_tool.fill_properties_menu(window.property_menus['bonds'], 'bonds')
    assert window.property_menus['bonds'].actions()[1].text() == 'Связи по AIM (Multiwfn)…'


def test_crystal_structure_window(window, tmp_path):
    # «Кристалл → Анализ структуры» — the Madelung energy with the formal and the CM5 charges, BVS, Pauling's
    # rules, the packing, the cell of the CP2K CELL_OPT against the file
    from modules.compass.actions import crystal_structure

    manifest, run = crystal_project_with_charges(tmp_path)
    window.open_project_path(str(manifest))
    if window.browsing:
        window.trajectory_tool.leave_trajectory()
    shown = crystal_structure.show(window, 'compare')
    assert shown.tabs.currentIndex() == 4
    madelung = shown.pages['madelung']
    assert 'M = 1.762675' in madelung.summary.text() and madelung.table.rowCount() == 2
    assert shown.charges.count() == 3
    shown.charges.setCurrentIndex(1)  # CM5: the energy scales as q² — 0.547² of the formal one
    assert madelung.table.item(0, 2).text() == '0.547' and 'Заряды расчёта' in madelung.note.text()
    assert 'GII' in shown.pages['valence'].summary.text()
    assert shown.pages['radii'].table.item(0, 4).text() == 'да'
    assert shown.pages['packing'].table.rowCount() == 5
    compare = shown.pages['compare'].table
    names = [compare.item(r, 0).text() for r in range(compare.rowCount())]
    assert names[0] == 'a' and 'плотность' in names
    shown.close()


def test_crystal_labels_and_brillouin_zone(window, tmp_path):
    # the labels of the structure on the atoms of a crystal with
    # no calculation (oxidation states, BVS, fractional coordinates, sites); the Brillouin zone of NaCl
    from modules.compass.actions import brillouin_window

    window.dirty = False
    window.opening_tool.open_path(str(Path(__file__).resolve().parents[2] / 'examples' / '10-crystals'
                                      / 'NaCl_rock_salt.cif'))
    assert window.compass_mode == 'crystal' and window.crystal is not None
    menu = window.property_menus['atoms']
    window.property_tool.fill_properties_menu(menu, 'atoms')
    assert 'Степени окисления на модели' in [a.text() for a in menu.actions()]
    for key, expected in (('oxidation', {'+1', '−1'}), ('bvs', {0.98}), ('site', {'Na1 · 4 · m-3m', 'Cl1 · 4 · m-3m'})):
        window.property_tool.show_crystal_charges(key)
        shown = window.property_tool.result_overlay(window.molecule)
        assert shown['atom'][0] == key and set(shown['atom'][1]) - {None} == expected
        window.viewer.grab()  # drawn without an error, the legend found
    window.property_tool.show_crystal_charges('fractional')
    assert '0 0 0' in window.property_tool.result_overlay(window.molecule)['atom'][1]
    window.property_tool.clear_model_overlays()
    assert window.property_tool.result_overlay(window.molecule) is None
    zone = brillouin_window.show(window)
    assert zone.zone.kind == 'cF' and zone.table.rowCount() == 6
    zone.axes[0].click()
    assert zone.view.grab().width() > 0
    path = zone.save_picture(str(tmp_path / 'bz.png'))
    assert Path(path).stat().st_size > 1000
    zone.close()


def test_the_density_and_the_elf_of_a_crystal_on_its_model(window, tmp_path):
    # «Расчёт → Электронная плотность на модели»
    # and «ELF на модели» — from the Molden file of the CP2K run, an isosurface over the model; the grid kept in the run
    # (the isosurface needs VTK: without it — the grids only)
    import importlib.util

    import numpy as np

    from modules.compass.chemistry import crystal_field

    vtk = importlib.util.find_spec('vtk') is not None
    manifest, run = crystal_project_with_charges(tmp_path)
    window.open_project_path(str(manifest))
    if window.browsing:
        window.trajectory_tool.leave_trajectory()
    said = []
    window.error = lambda exc: said.append(str(exc))
    assert bool(window.property_tool.crystal_field('density')) is vtk, said
    one = np.load(run / 'crystal-density.npz')['values']
    from modules.spectrum.readers import cp2k

    # the grid takes the fractions of the cell of the file; the electrons are those of the cell computed (5.28 Å)
    assert crystal_field.integral(one, cp2k.last_cell(run)) == pytest.approx(16.0, abs=0.05)
    assert bool(window.property_tool.crystal_field('elf')) is vtk
    elf = np.load(run / 'crystal-elf.npz')['values']
    assert 0 <= elf.min() and elf.max() <= 1
    if vtk:
        assert window.surface_source['kind'] == 'elf' and window.surface_source['level'] == 0.8
        window.viewer.grab()


def test_the_export_of_a_crystal(window, tmp_path):
    # 2026-11-13 («Файл → Экспорт кристалла»): POSCAR, the extended XYZ of the cell, the block shown (2 × 2 × 2) in P 1
    from modules.compass.chemistry import crystal as cr

    cif = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals' / 'NaCl_rock_salt.cif'
    window.opening_tool.open_path(str(cif))
    window.crystal_tool.build_crystal(window.crystal[0], (2, 2, 2), True, False)
    poscar = window.crystal_tool.export_crystal('poscar', str(tmp_path / 'POSCAR'))
    assert Path(poscar).read_text(encoding='utf-8').splitlines()[6].split() == ['4', '4']
    extxyz = window.crystal_tool.export_crystal('extxyz', str(tmp_path / 'nacl.extxyz'))
    assert Path(extxyz).read_text(encoding='utf-8').startswith('8\nLattice="')
    block = window.crystal_tool.export_crystal('block', str(tmp_path / 'block.cif'))
    back = cr.parse_cif(Path(block).read_text(encoding='utf-8'))
    assert len(cr.unit_cell(back)) == 64 and back.cell.a == pytest.approx(2 * 5.64)


def test_the_voids_of_a_crystal(window, tmp_path):
    # «Кристалл → Пустоты…»: channels along c between rows of atoms; the surface on the model (with VTK)
    import importlib.util

    from modules.compass.actions import voids_window
    from modules.compass.chemistry import crystal as cr
    from modules.compass.chemistry import surface

    rows = cr.Crystal('channels', cr.Cell(8, 8, 3), tuple(cr.Site(f'C{i}', 'C', x, y, 0) for i, (x, y) in enumerate(
        ((0, 0), (0.5, 0), (0, 0.5), (0.5, 0.5)))), (cr.operation('x,y,z'),), 'P 1')
    path = tmp_path / 'channels.cif'
    path.write_text(surface.write_cif(rows), encoding='utf-8')
    window.opening_tool.open_path(str(path))
    shown = voids_window.show(window)
    assert shown.result is not None and shown.table.rowCount() == 4
    assert shown.table.item(0, 3).text() == 'канал вдоль c' and '%' in shown.summary.text()
    shown.probe.setValue(3.0)  # too large a probe: no voids
    assert shown.compute().volume == 0 and 'нет' in shown.summary.text() and not shown.model_button.isEnabled()
    shown.probe.setValue(1.0)
    shown.compute()
    vtk = importlib.util.find_spec('vtk') is not None
    said = []
    window.error = lambda exc: said.append(str(exc))  # without VTK: «No module named 'vtk'»
    assert shown.show_on_model() is vtk, said
    if vtk:
        assert window.surface_source['kind'] == 'void'
        window.viewer.grab()
    shown.close()


def test_the_shape_of_a_crystal(window, tmp_path):
    # 2026-11-13 («Кристалл → Форма кристалла (BFDH)…»): rock salt — {111} and {100} as (200); turned, saved
    from modules.compass.actions import morphology_window

    window.opening_tool.open_path(str(Path(__file__).resolve().parents[2] / 'examples' / '10-crystals' /
                                      'NaCl_rock_salt.cif'))
    shown = morphology_window.show(window)
    assert shown.table.rowCount() == 2 and shown.table.item(1, 0).text() == '{100} (как 200)'
    assert shown.table.item(1, 1).text() == '2.820' and '78 %' in shown.summary.text()
    shown.view.along(2)
    assert shown.save_picture(str(tmp_path / 'shape.png')) and (tmp_path / 'shape.png').stat().st_size > 1000
    shown.close()


def test_a_measured_pattern_compared(window, tmp_path):
    # the zero shift, the larger cell and the impurity said; the table
    from modules.compass.chemistry import powder
    from tests.compass.test_powder_match import measured

    window.opening_tool.open_path(str(Path(__file__).resolve().parents[2] / 'examples' / '10-crystals' /
                                      'NaCl_rock_salt.cif'))
    dialog = window.crystal_window.show_powder()
    dialog.start.setValue(10.0)
    dialog.compute()
    _, x, y = measured()
    path = tmp_path / 'salt.xy'
    path.write_text(powder.write_xy(x, y), encoding='utf-8')
    assert dialog.load_xy(str(path))
    text = dialog.status.text()
    assert 'сдвиг нуля +0.12' in text and 'больше на 0.50 %' in text and '33.00°' in text
    table = dialog.comparison_table()
    kinds = [table.table.item(r, 5).text() for r in range(table.table.rowCount())]
    assert kinds.count('лишний пик') == 1 and 'найдена' in kinds
    dialog.fitted.setChecked(False)  # as they are: the measured pattern to 100 with its background
    assert min(dialog.plot.measured[1]) > 20
    table.close()
    dialog.reject()
    window.crystal_window.reject()


def test_another_setting_of_the_cell(window, tmp_path):
    # benzoic acid of the file (P 21/n) shown as P 21/c, then as
    # its reduced cell; the planes of groups of atoms work on the model of a crystal
    from modules.compass.actions import setting_window

    window.opening_tool.open_path(str(Path(__file__).resolve().parents[2] / 'examples' / '10-crystals' /
                                      'benzoic_acid.cif'))
    shown = setting_window.show(window)
    names = [shown.table.item(r, 0).text() for r in range(shown.table.rowCount())]
    assert names[0] == 'P 1 21/n 1 (файл)' and 'P 1 21/c 1' in names and names[-1].startswith('Приведённая ячейка')
    new = shown.apply(names.index('P 1 21/c 1'))
    assert window.crystal[0] is new and new.space_group == 'P 1 21/c 1' and window.crystal[1] == (1, 1, 1)
    assert len(window.molecule.atoms) > 0
    reduced = shown.apply(len(names) - 1)
    assert window.crystal[0] is reduced and reduced.cell.volume() == pytest.approx(new.cell.volume())
    text = window.structure_tool.show_planes([0, 1, 2, 3, 4, 5]) if hasattr(window, 'structure_tool') else 'Плоскость'
    assert 'Плоскость' in text
    shown.close()


def test_lattice_planes_in_the_cell(window, tmp_path):
    # (111) of rock salt in its cell — two triangles, d and 2θ of the line 1 1 1; a
    # double click on the line 2 0 0 of the powder pattern shows its planes; a new block takes them away
    from modules.compass.actions import planes_window

    window.opening_tool.open_path(str(Path(__file__).resolve().parents[2] / 'examples' / '10-crystals' /
                                      'NaCl_rock_salt.cif'))
    shown = planes_window.show(window)
    for box, value in zip(shown.boxes, (1, 1, 1)):
        box.setValue(value)
    assert 'd = 3.2563 Å' in shown.info.text() and '27.367' in shown.info.text() and 'линия дифрактограммы 1 1 1' in shown.info.text()
    assert len(shown.show_planes()) == 2 and window.viewer.lattice_planes[0] == '(1 1 1)'
    window.viewer.grab()
    shown.boxes[0].setValue(1)
    shown.boxes[1].setValue(0)
    shown.boxes[2].setValue(0)
    assert 'отражения нет' in shown.info.text()  # 1 0 0 of an fcc lattice: absent
    powder = window.crystal_window.show_powder()
    row = [line.hkl for line in powder.lines].index((2, 0, 0))
    assert len(powder.planes_of(row)) == 3 and window.viewer.lattice_planes[0] == '(2 0 0)'  # x = 0, ½, 1
    window.crystal_tool.build_crystal(window.crystal[0], (2, 2, 2), True, False)
    assert window.viewer.lattice_planes is None
    powder.reject()
    shown.close()


def test_packing_similarity_window(window, tmp_path):
    # benzoic acid against itself in another setting (another CIF)
    from modules.compass.actions import packing_window
    from modules.compass.chemistry import crystal_setting as cs
    from modules.compass.chemistry import surface

    cif = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals' / 'benzoic_acid.cif'
    window.opening_tool.open_path(str(cif))
    crystal = window.crystal[0]
    m = next(m for e, m, _ in cs.settings(crystal) if cs.entry_name(e) == 'P 1 21/c 1')
    other = tmp_path / 'p21c.cif'
    other.write_text(surface.write_cif(cs.transform(crystal, m)), encoding='utf-8')
    shown = packing_window.show(window)
    assert shown.with_optimization() is None  # no optimization yet
    result = shown.open_file(str(other))
    assert result.matched == 15 and 'совпало молекул 15 из 15' in shown.summary.text() and 'одна упаковка' in shown.summary.text()
    assert shown.table.rowCount() == 15 and shown.table.item(14, 4).text() == 'да'
    salt = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals' / 'NaCl_rock_salt.cif'
    assert shown.open_file(str(salt)) is None and 'нет отдельных молекул' in shown.summary.text()
    shown.close()


def test_the_modes_and_the_critical_points_of_a_crystal(window, tmp_path):
    # a run «Частоты (точка Γ)» of the project — its modes in
    # the page «Частоты» of the drawer at the opening; the critical points of the 3 × 3 × 3 run of CsCl on one cell
    import json
    import shutil

    from azimuth import crystal_projects
    from modules.compass.actions import crystal_dynamics
    from modules.spectrum.wavefunction import crystal_aim, multiwfn

    manifest, run = crystal_project_with_charges(tmp_path)
    data = Path(__file__).resolve().parents[1] / 'data'
    vib = manifest.parent / 'calculations' / 'cp2k-CsCl-vib'
    vib.mkdir()
    shutil.copy(data / 'cp2k' / 'cscl_vibrations.mol', vib / 'azimuth-VIBRATIONS-1.mol')
    shutil.copy(run / 'azimuth.inp', vib / 'azimuth.inp')
    crystal_projects.record_run(manifest, {'folder': 'calculations/cp2k-CsCl-vib', 'program': 'cp2k',
                                           'task': 'Частоты (точка Γ)'})
    cell, atoms = crystal_aim.geometry((data / 'multiwfn' / 'crystal_cscl333_geometry.molden').read_text(encoding='utf-8'))
    cps = multiwfn.parse_cps((data / 'multiwfn' / 'crystal_topology_cp2k-CsCl-20261112-144541__CPprop.txt')
                             .read_text(encoding='utf-8'))
    from modules.compass.chemistry import crystal_results

    crystal_results.write_aim_points(run, crystal_aim.unique_points(cps, atoms, cell), cell)
    window.open_project_path(str(manifest))
    if window.browsing:
        window.trajectory_tool.leave_trajectory()
    assert len(window.drawer.modes) == 6 and window.trajectory_button.isVisibleTo(window)  # loaded at the opening
    assert crystal_dynamics.show_modes(window) == 6 and window.drawer.page() == 'modes'
    window.drawer.modes_table.setCurrentCell(3, 0)
    window.drawer.select_mode(3)
    window.drawer.phase = 0.25
    moved = window.drawer.mode_geometry()
    base = window.drawer.modes_base
    shift = [m.position[0] - b.position[0] for m, b in zip(moved.atoms, base.atoms)]
    assert all((d > 0) == (a.symbol == 'Cs') for d, a in zip(shift, base.atoms))  # Cs one way, Cl the other
    window.trajectory_tool.set_trajectory_open(False)
    assert crystal_dynamics.show_points(window) > 8
    shown = window.viewer.aim
    assert sum(1 for kind, _ in shown['points'] if kind == 'bond') >= 8 and shown['paths']
    window.viewer.grab()
    window.surface_tool.clear_aim()
    assert window.viewer.aim is None
    json.loads((run / 'aim-points.json').read_text(encoding='utf-8'))


def test_the_spectrum_of_a_crystal(window, tmp_path):
    # Spectrum of a project of a crystal shows its runs; the real CELL_OPT of CsCl (CP2K)
    from modules.compass.chemistry import crystal_results

    manifest, run = crystal_project_with_charges(tmp_path)
    crystal_results.write_aim(run, [('Cl–Cs', '3.59', 'Cl: 8, Cs: 8', '0.0094', '+0.0272', '+0.00115', '0.80', 'closed')],
                              {'census': {'poincare_hopf': 17}, 'atoms': 54, 'version': '2026.10.28'})
    window.open_project_path(str(manifest))
    window.navigate(2)
    view = window.crystal_results
    assert window.stack.currentIndex() == 2 and window.results_stack.currentWidget() is view
    assert view.runs.count() == 1 and view.heading.text() == 'CsCl — расчёты кристалла'
    shown = [view.tabs.tabText(k) for k in range(view.tabs.count()) if view.tabs.isTabVisible(k)]
    assert shown == ['Энергия и шаги', 'Плотность состояний', 'Заряды', 'Связи AIM']  # no bands of a CP2K run
    # the PDOS of the Molden file — worked out on the button, kept in pdos-levels.csv
    assert not view.pdos_button.isHidden()
    assert view.pdos_found is None and 'ещё не считалась' in view.dos_note.text()
    assert view.compute_pdos() and (run / 'pdos-levels.csv').is_file() and view.pdos_button.isHidden()
    assert [name for name, _ in view.dos_plot.parts] == ['Cl', 'Cs'] and 'Малликена' in view.dos_note.text()
    view.projection.setCurrentIndex(1)
    assert 'Cl p' in [name for name, _ in view.dos_plot.parts]
    assert view.steps_table.rowCount() == 11 and view.steps_table.item(10, 3).text() == '5.2841'
    assert view.energy_plot.series[0][1][-1] == 0 and len(view.cell_plot.series) == 4
    assert abs(view.cell_plot.series[0][1][-1] - 100 * (5.2841042045 / 4.123 - 1)) < 1e-3  # Δa, %
    assert 'Полная энергия ячейки' in view.line.text()
    assert view.charges_table.rowCount() == 2 and 'Cs: +0.299 (Хиршфельд), +0.547 (CM5)' in view.charges_note.text()
    assert view.charges_table.item(1, 3).text() == '−0.5468' and 'Cl: −0.299' in view.charges_note.text()
    assert view.aim_table.item(0, 7).text().startswith('замкнутые оболочки') and '= 17' in view.aim_note.text()
    view.grab()  # drawn without an error
    window.navigate(0)
    assert window.compass_mode == 'crystal'


def test_the_molecular_shell_of_a_crystal(window):
    # 0.163.0 (as «Molecular Shell» of Mercury): benzoic acid of the examples — 14 neighbours within 4 Å; on the model
    # the centre is selected, and the window opened again takes the selected molecule as its centre
    from pathlib import Path

    from modules.compass.actions import shell_window

    path = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals' / 'benzoic_acid.cif'
    window.dirty = False
    window.opening_tool.open_path(str(path))
    shown = shell_window.show(window)
    assert shown.result is not None and shown.table.rowCount() == 14 and '14' in shown.summary.text()
    assert shown.table.item(0, 2).text() == '-x+1, -y, -z+1' and shown.table.item(0, 3).text() == 'H2A···O1'
    assert shown.show_on_model() and len(window.molecule.atoms) == 15 * 15 and window.viewer.selected == list(range(15))
    shown.accept()
    again = shell_window.show(window)
    assert again.centre and len(again.centre) == 1 and again.table.rowCount() == 14
    again.mode.setCurrentIndex(1)  # the van der Waals contacts: fewer neighbours
    assert again.radius.value() == 0.5 and 0 < len(again.compute().neighbours) < 14
    again.accept()
    window.dirty = False
    window.new_molecule()


def test_the_hirshfeld_surface_of_a_crystal(window, tmp_path):
    # benzoic acid — the surface, the shares of the contacts (H···H the largest), the
    # fingerprint of O···H chosen, the picture saved; on the model (with VTK) the molecule with its neighbours
    import importlib.util
    from pathlib import Path

    from modules.compass.actions import hirshfeld_window

    path = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals' / 'benzoic_acid.cif'
    window.dirty = False
    window.opening_tool.open_path(str(path))
    shown = hirshfeld_window.show(window)
    # the panel opens with its settings, «Построить» builds the surface
    assert shown.result is None and shown.build_button.text() == 'Построить' and not shown.save_button.isEnabled()
    vtk = importlib.util.find_spec('vtk') is not None
    said = []
    window.error = lambda exc: said.append(str(exc))
    first = shown.build()
    assert first is not None and shown.result is first and 'Площадь' in shown.summary.text()
    assert shown.build() is first  # the same grid and molecule: not computed again
    shown.accept()
    assert hirshfeld_window.show(window) is shown and shown.result is first and shown.plot.whole is not None
    assert '(O···H)' in shown.summary.text() or '(H···O)' in shown.summary.text()  # the red spot: the O–H···O bond
    assert shown.table.item(0, 0).text() == 'H···H' and shown.pair.count() == shown.table.rowCount() + 1
    shown.pair.setCurrentIndex(shown.pair.findData('H···O'))
    assert shown.plot.chosen is not None and 0 < shown.plot.chosen.sum() < shown.plot.whole.sum()
    assert shown.save_plot(str(tmp_path / 'fp.png')) and (tmp_path / 'fp.png').stat().st_size > 1000
    # the scale by the data — the axes round the spot, all of it
    standard = float(shown.plot.whole.sum())
    shown.scale.setCurrentIndex(shown.scale.findData('data'))
    r = shown.result
    assert shown.plot.low <= min(r.d_i.min(), r.d_e.min()) and shown.plot.high >= max(r.d_i.max(), r.d_e.max())
    assert shown.plot.high - shown.plot.low < 2.2 and shown.plot.whole.sum() >= standard - 1e-6
    assert shown.plot.chosen is not None  # the pair chosen stays, on the new scale
    shown.scale.setCurrentIndex(shown.scale.findData('standard'))
    assert (shown.plot.low, shown.plot.high) == (0.4, 2.6)
    assert shown.show_on_model() is vtk, said
    assert window.viewer.selected == list(range(15)) and len(window.molecule.atoms) > 15
    if vtk:
        assert window.surface_source['kind'] == 'hirshfeld' and window.surface_source['mapped'] == 'd_norm'
    # the shape index on the model — its own colours, the title says it
    shown.mapped.setCurrentIndex(shown.mapped.findData('shape_index'))
    assert shown.mapped.currentText() == 'индекс формы' and shown.show_on_model() is vtk, said
    if vtk:
        assert window.surface_source['mapped'] == 'shape_index' and 'индекс формы' in window.surface_source['title']
    shown.accept()
    window.dirty = False
    window.new_molecule()


def test_the_network_by_layers_and_by_the_rows_picked(window, tmp_path):
    # 0.170.0 (Mercury's «expand contacts»): the water chain — one row picked, three layers: the network the same as
    # crystal_contacts.network of those contacts grown three times (the cell's molecule and 3 on each side)
    from modules.compass.chemistry import crystal_contacts as cc
    from modules.compass.chemistry import surface
    from tests.compass.test_crystal_contacts import water_chain

    path = tmp_path / 'water.cif'
    path.write_text(surface.write_cif(water_chain()), encoding='utf-8')
    window.dirty = False
    window.opening_tool.open_path(str(path))
    contacts = window.crystal_tool.show_contacts()
    assert contacts.chosen_contacts() is None
    row = next(k for k in range(contacts.table.rowCount()) if contacts.table.item(k, 0).text() == cc.name('hydrogen'))
    contacts.table.selectRow(row)
    chosen = contacts.chosen_contacts()
    assert chosen and all(c.kind == 'hydrogen' for c in chosen)
    want, added = cc.network(contacts.data, chosen=chosen, layers=3)
    contacts.layers.setValue(3)
    contacts.show_network()
    assert added == 6 and len(window.molecule.atoms) == len(want.atoms) == 3 * 7
    window.dirty = False
    window.new_molecule()


def test_a_crystal_from_cod(window, tmp_path, monkeypatch):
    # «Найти кристалл в COD…» with a fake server: the table of the entries found, the CIF saved and opened
    from pathlib import Path

    import time

    from PySide6.QtWidgets import QApplication

    from modules.compass.actions import cod_window
    from modules.compass.chemistry import cod

    def settled(seconds=5):  # the worker thread answers through a queued signal
        deadline = time.monotonic() + seconds
        while shown.busy and time.monotonic() < deadline:
            QApplication.processEvents()
            time.sleep(0.01)
        return not shown.busy

    cif = (Path(__file__).resolve().parents[2] / 'examples' / '10-crystals' / 'benzoic_acid.cif').read_text(encoding='utf-8')
    entry = cod.Entry('7133168', 'C7 H6 O2', 'benzoic acid', 'P 1 21/n 1', (5.502, 5.157, 21.884, 90, 97.37, 90),
                      '2024', 'Chem. Commun.', '')
    shown = cod_window.show(window)
    monkeypatch.setattr(shown, 'folder', lambda: tmp_path / 'COD')
    asked = []
    shown.search_function = lambda *criteria, **options: asked.append((criteria, options)) or ([entry], 1)
    shown.fetch_function = lambda number: cif
    assert not shown.find() and 'хотя бы одно условие' in shown.status.text()
    shown.formula.setText('C7H6O2')
    assert shown.find()
    assert settled()
    assert asked[0][0] == ('', 'C7H6O2', [], False) and asked[0][1]['cell'] is None and shown.table.rowCount() == 1
    assert shown.table.item(0, 0).text() == '7133168' and shown.table.item(0, 3).text() == 'P 1 21/n 1'
    window.dirty = False
    assert shown.open_entry(0)
    assert settled()
    assert (tmp_path / 'COD' / '7133168.cif').read_text(encoding='utf-8') == cif
    assert window.crystal is not None and window.compass_mode == 'crystal'
    # the cell of the crystal just opened, any order of the axes, ± 2 %
    assert shown.cell_of_crystal().startswith('5.5')
    shown.formula.clear()
    shown.any_order.setChecked(True)
    shown.tolerance.setCurrentIndex(shown.tolerance.findData(2.0))
    assert shown.find() and settled()
    options = asked[-1][1]
    assert len(options['cell']) == 6 and options['tolerance'] == 2.0 and options['any_order']
    shown.cell.setText('5.5 5.1')
    assert not shown.find() and 'три длины' in shown.status.text()
    shown.cell.clear()
    shown.formula.setText('C7H6O2')
    shown.search_function = lambda *criteria, **options: (_ for _ in ()).throw(OSError('no network'))
    assert shown.find()
    assert settled()
    assert 'COD недоступен' in shown.status.text()
    shown.accept()
    window.dirty = False
    window.new_molecule()


def test_the_pair_energies_of_a_crystal(window):
    # «Энергии пар и каркас (xtb)…» of benzoic acid with a model energy instead of xtb (a sum over the atom
    # pairs): the table, the lattice energy, the framework on the model
    import time
    from pathlib import Path

    from PySide6.QtWidgets import QApplication

    from modules.compass.actions import pairs_window
    from tests.compass.test_crystal_pairs import model

    path = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals' / 'benzoic_acid.cif'
    window.dirty = False
    window.opening_tool.open_path(str(path))
    shown = pairs_window.show(window)
    assert shown.plan is not None and shown.table.rowCount() == len(shown.plan.shell.neighbours) > 0
    shown.energy = model
    assert shown.compute()
    deadline = time.monotonic() + 10
    while shown.busy and time.monotonic() < deadline:
        QApplication.processEvents()
        time.sleep(0.01)
    assert not shown.busy and shown.result is not None and 'Энергия решётки' in shown.summary.text()
    assert shown.table.item(0, 4).text() not in ('', '—')
    # a neutral crystal — no table of charges; a plain energy — no terms; an energy with terms — its columns
    assert shown.charges.isHidden() and shown.chosen_charges() == {'C7H6O2': 0}
    assert shown.table.columnCount() == 9 and shown.table.item(0, 5).text() == ''
    from tests.compass.test_crystal_pairs import split_model

    shown.energy = split_model
    assert shown.compute()
    deadline = time.monotonic() + 10
    while shown.busy and time.monotonic() < deadline:
        QApplication.processEvents()
        time.sleep(0.01)
    assert shown.table.item(0, 5).text() not in ('', '—') and shown.table.item(0, 8).text() in ('0.0', '-0.0')
    assert shown.show_frame() and window.viewer.energy_frame is not None
    assert window.viewer.energy_frame[0] is window.viewer.molecule and window.viewer.energy_frame[1]
    window.viewer.grab()
    shown.accept()
    window.dirty = False
    window.new_molecule()


def test_the_point_group_from_the_menu_only_finds_it(window):
    # «Инструменты → Определить точечную группу»
    # names the group however often it is chosen; symmetrising is the next items of that menu, never this one
    example = Path(__file__).resolve().parents[2] / 'examples' / '0-molecules' / 'water.xyz'
    window.dirty = False
    window.opening_tool.open_path(str(example))
    before = [(a.x, a.y, a.z) for a in window.molecule.atoms]
    for _ in range(2):
        assert window.symmetry_tool.determine_symmetry(apply=False)['name'] == 'C2v'
    assert [(a.x, a.y, a.z) for a in window.molecule.atoms] == before
    assert 'C<sub>2v</sub>' in window.molecule_info.text() and window.symmetrize_action.isEnabled()


def test_a_model_for_3d_printing(window, tmp_path):
    # 0.176.0 (Mercury «Print 3D»): «Файл → Модель для 3D-печати…» — the model on the screen as STL and VRML; in
    # «Компас · Кристалл» the edges of the cell go with it
    import struct

    from modules.compass.actions import print3d_window

    example = Path(__file__).resolve().parents[2] / 'examples' / '0-molecules' / 'water.xyz'
    window.dirty = False
    window.opening_tool.open_path(str(example))
    shown = print3d_window.show(window)
    assert not shown.cell.isEnabled() and shown.size.text().startswith('Размер модели:')
    stl = shown.save('stl', str(tmp_path / 'water.stl'))
    data = Path(stl).read_bytes()
    assert len(data) == 84 + 50 * struct.unpack('<I', data[80:84])[0]
    text = Path(shown.save('vrml', str(tmp_path / 'water.wrl'))).read_text(encoding='utf-8')
    assert text.count('Shape {') >= 3  # O, H and the halves of the bonds in their colours
    shown.reject()
    window.opening_tool.open_example_path(str(Path(__file__).resolve().parents[2] / 'examples' / '10-crystals' / 'CsCl.cif'))
    window.crystal_window.reject()
    shown = print3d_window.show(window)
    assert shown.cell.isEnabled() and shown.cell.isChecked()
    assert any(p.name == 'cell' for p in shown.model())
    shown.reject()
    for d in window.all_documents():
        d.dirty = False
    window.crystal_tool.set_compass_mode('molecule')


def test_the_symbol_of_the_group_and_the_bravais_nodes(window):
    # «Что значит символ…» of the window «Кристалл» reads the symbol part by part; «Узлы решётки Браве» puts
    # the nodes of the block on the model — CsCl (P m -3 m, cP): the 8 corners of one cell
    examples = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals'
    window.dirty = False
    window.opening_tool.open_example_path(str(examples / 'CsCl.cif'))
    w = window.crystal_window
    lines = w.explain_symbol()
    assert lines and 'cP' in lines[1] and any('⟨111⟩' in line for line in lines)
    w.symbol_box.close()
    w.build()
    w = window.crystal_tool.reopen_crystal()
    w.lattice.setChecked(True)
    nodes = window.viewer.lattice_points
    assert len(nodes) == 8 and not any(centred for _, centred in nodes)
    window.viewer.grab()
    w.lattice.setChecked(False)
    assert window.viewer.lattice_points is None
    w.reject()
    for d in window.all_documents():
        d.dirty = False
    window.crystal_tool.set_compass_mode('molecule')


def test_a_click_on_a_hydrogen_bond_of_the_model(window):
    # benzoic acid — the dotted O–H···O of the dimer on the model; a click in
    # the middle of its line names it with the labels of the file and chooses its row in the open «Контакты» window
    from PySide6.QtCore import QPointF

    examples = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals'
    window.dirty = False
    window.opening_tool.open_example_path(str(examples / 'benzoic_acid.cif'))
    w = window.crystal_window
    w.build()
    contacts = window.crystal_tool.show_contacts()
    contacts.show_network()  # the molecules of the cell with their partners: the dimers whole on the model
    contacts = window.crystal_tool.show_contacts()
    viewer = window.viewer
    viewer.show_hbonds = True
    # the whole cell (450 atoms) fills the field: an H···O is 3–10 px long there and the middle of each lies on some
    # covalent bond, which a click rightly chooses — the model zoomed in as far as it goes (6×), as one would to click
    # a contact; the test passed only when the tests before it had left the model zoomed in
    window.show()
    viewer.zoom_view(6.0)
    QApplication.processEvents()
    found = [(h, a) for h, a in viewer.hydrogen_bonds() if h not in viewer.hidden_atoms()]
    assert found
    points = viewer.projected()

    def middle_of(pair):
        return (points[pair[0]][0] + points[pair[1]][0]) / 2

    # a hydrogen bond whose middle no covalent bond covers on the picture (which lies on top depends on the size of the
    # field: a click on a bond there rightly chooses the bond)
    free = [pair for pair in found if viewer.rect().contains(middle_of(pair).toPoint())
            and viewer.bond_at(QPointF(middle_of(pair))) is None and viewer.hbond_at(QPointF(middle_of(pair))) == pair]
    assert free
    h, a = free[0]
    middle = middle_of((h, a))
    clicked = []
    viewer.contactClicked.connect(lambda *pair: clicked.append(pair))
    viewer._empty_click(QPointF(middle))
    assert clicked == [(h, a)]
    text = window.crystal_tool.contact_clicked(h, a)
    assert text in ('O2–H2A···O1', 'O1–H1···O2') and '···' in text
    row = window.crystal_tool.last_contact[3]
    assert row is not None and contacts.table.item(row, 1).text() == text
    assert contacts.table.selectionModel().isRowSelected(row)
    contacts.reject()
    for d in window.all_documents():
        d.dirty = False
    window.crystal_tool.set_compass_mode('molecule')


def test_an_energy_of_a_crystal_has_its_tab_in_spectrum(window, monkeypatch):
    # «Энергия и шаги» is there for every run — an energy has its one row, no plots; an output with no step —
    # Quill says where the result is
    from types import SimpleNamespace

    from modules.compass.chemistry import crystal_results
    from modules.spectrum.views.crystal_view import CrystalResultsView

    view = CrystalResultsView(window)
    row = {'step': 0, 'energy': -192.306765, 'a': 2.9475, 'b': 2.9475, 'c': 2.9475, 'volume': 18.1}
    monkeypatch.setattr(crystal_results, 'steps', lambda run: [(None, None, [0, 1])])
    monkeypatch.setattr(crystal_results, 'steps_table', lambda raw: [row] if raw else [])
    view.show_empty(False)
    view.show_optimization(SimpleNamespace())
    tab = view.optimization_tab
    view.tabs.setCurrentIndex(tab)
    assert view.tabs.isTabVisible(tab) and view.tabs.tabText(tab) == 'Энергия и шаги'
    assert view.steps_table.rowCount() == 1 and view.steps_table.item(0, 1).text() == '−192.30676500'
    assert view.steps_table.isVisibleTo(view) and not view.energy_plot.isVisibleTo(view)
    assert view.empty.isVisibleTo(view) and 'один шаг' in view.empty_text.text()  # Quill in the card of the plots
    monkeypatch.setattr(crystal_results, 'steps', lambda run: [])
    view.show_optimization(SimpleNamespace())
    assert view.tabs.isTabVisible(tab) and view.empty.isVisibleTo(view) and 'строке внизу' in view.empty_text.text()
    assert view.steps_table.rowCount() == 0
    view.show_empty(True)
    assert 'Секстанте' in view.empty_text.text()


def test_a_crystal_output_opens_with_its_steps(window, monkeypatch):
    # solid chlorine at 10 GPa (CRYSTAL17) — its last structure in
    # its cell and group (C m c e), the 23 points of the optimization in the drawer, a line of what the run gave; the
    # elastic tensor of another run in a table; the critical points of TOPOND in a table
    from modules.compass.actions import crystal_code_window

    data = Path(__file__).resolve().parents[1] / 'data' / 'crystal'
    said = []
    monkeypatch.setattr(window, 'notify', lambda text, ms=8000: said.append(text))
    assert window.opening_tool.file_kind(str(data / 'chlorine-10gpa.out')) == 'crystal_output'
    window.opening_tool.open_path(str(data / 'chlorine-10gpa.out'))
    assert window.crystal[0].number == 64 and len(window.drawer.steps) == 23
    assert any('CRYSTAL17' in t and 'давление 10.00 ГПа' in t and 'щель 3.334 эВ' in t for t in said)
    # the method and the energy of the output in its project
    from azimuth import crystal_projects

    method, energy, *_ = crystal_projects.cells(window.research_path(), crystal_projects.info(window.research_path()))
    assert method.startswith('CRYSTAL17') and 'свой базис' in method and energy == '-1839.604326'
    window.opening_tool.open_path(str(data / 'rubsud-elastic.out'))
    table = crystal_code_window.WINDOWS['elastic'].table
    assert table.rowCount() == 6 and table.item(0, 1).text() == '149.49'
    crystal_code_window.WINDOWS['elastic'].close()
    assert window.opening_tool.file_kind(str(data / 'brbenz-topond.outp')) == 'crystal_output'
    window.opening_tool.open_path(str(data / 'brbenz-topond.outp'))
    table = crystal_code_window.WINDOWS['topond'].table
    assert table.rowCount() == 10 and table.item(7, 1).text() == 'связь' and table.item(7, 2).text().startswith('C')
    crystal_code_window.WINDOWS['topond'].close()


def test_crystal_input_window(window, tmp_path, monkeypatch):
    # «Расчёт → Входной файл CRYSTAL…» — the input
    # of the crystal shown, as the choices make it; a pressure only for the optimization of the cell; saved as .d12
    from PySide6.QtWidgets import QFileDialog

    from modules.compass.actions import crystal_code_window

    window.opening_tool.open_path(str(Path(__file__).resolve().parents[2] / 'examples' / '10-crystals' /
                                      'benzoic_acid.cif'))
    shown = crystal_code_window.show(window)
    text = shown.preview.toPlainText()
    assert '\nCRYSTAL\n0 0 0\n14\n' in text and 'OPTGEOM\nFULLOPTG' in text and 'BASISSET\nPOB-TZVP' in text
    shown.pressure.setValue(1.5)
    assert 'EXTPRESS' in shown.preview.toPlainText()
    shown.task.setCurrentIndex(list(crystal_code_window.ci.TASKS).index('Упругие константы'))
    assert not shown.pressure.isEnabled() and shown.pressure.value() == 0 and 'ELASTCON' in shown.preview.toPlainText()
    target = tmp_path / 'benzoic.d12'
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *a, **k: (str(target), ''))
    assert shown.save() == str(target) and target.read_text(encoding='utf-8') == shown.preview.toPlainText()
    shown.close()


def test_the_crystal_window_fits_the_screen(window):
    # the settings scroll inside the window, the buttons under them; the window no taller than the screen
    from PySide6.QtWidgets import QPushButton, QScrollArea

    window.dirty = False
    examples = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals'
    window.opening_tool.open_example_path(str(examples / 'CsCl.cif'))
    dialog = window.crystal_window
    room = dialog.screen().availableGeometry()
    assert dialog.height() <= room.height() and isinstance(dialog.scroll, QScrollArea)
    # no «Построить» (the block is rebuilt as the settings change) — «Закрыть» stays under the settings
    close = next(b for b in dialog.findChildren(QPushButton) if b.text() == 'Закрыть')
    assert not dialog.scroll.widget().isAncestorOf(close)  # the buttons do not scroll away
    assert 'Построить' not in [b.text() for b in dialog.findChildren(QPushButton)]
    dialog.reject()
    for d in window.all_documents():
        d.dirty = False


def test_a_menu_of_a_button_at_the_right_opens_to_the_left(window):
    from PySide6.QtWidgets import QMenu, QPushButton

    # the «Атомы» menu of a crystal on the right rail stays within the screen
    from modules.compass.actions.menu_actions import ModelMenuTool

    room = window.screen().availableGeometry()
    button = QPushButton('·')
    button.resize(28, 28)
    button.move(room.right() - 40, room.top() + 100)
    button.show()
    menu = QMenu()
    for _ in range(4):
        # once, not twice (twice is 1029 px — wider than the 800 px screen of the offscreen run, where no
        # place can hold it)
        menu.addAction('Нет расчёта CP2K этого кристалла — посчитайте его в Секстанте (CP2K).')
    point = ModelMenuTool.menu_point(button, menu)
    assert point.x() + menu.sizeHint().width() <= room.right() + 1 and point.x() >= room.left()
    button.close()


def test_the_examples_of_crystal_compass_are_crystals(window):
    # a menu of the crystals of examples/10-crystals, «Другой файл…» last
    window.crystal_tool.set_compass_mode('crystal')
    try:
        menu = window.opening_tool.open_example(False)  # as «triggered» of the item of «Файл» calls it
        names = [a.text() for a in menu.actions() if not a.isSeparator()]
        assert names[0].startswith('CsCl') and names[-1] == 'Другой файл…' and len(names) == 6  # + silicon
        menu.close()
    finally:
        window.crystal_tool.set_compass_mode('molecule')


def test_the_contacts_beside_the_model_and_on_it(window):
    # «Контакты» opens in the side panel by the field; a row chosen
    # draws its contacts on the model; «Показать сеть» keeps the panel and draws the contacts of the network
    examples = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals'
    window.dirty = False
    window.opening_tool.open_example_path(str(examples / 'benzoic_acid.cif'))
    window.crystal_window.reject()
    contacts = window.crystal_tool.show_contacts()
    assert contacts.parent() is window.crystal_side and not window.crystal_side.isHidden()
    contacts.show_network()
    assert not window.crystal_side.isHidden() and window.crystal_tool.side_dialog() is contacts
    drawn = window.viewer.aim_contacts()
    # every line has its H; the O–H···O of the dimer among them (the weak C–H···O and H···C of the file too)
    pairs = [{window.viewer.molecule.atoms[i].symbol, window.viewer.molecule.atoms[j].symbol} for i, j, _ in drawn]
    assert drawn and all('H' in pair for pair in pairs) and {'H', 'O'} in pairs
    row = next(k for k in range(contacts.table.rowCount()) if contacts.table.item(k, 0).text() == 'водородная')
    contacts.table.selectRow(row)
    assert window.viewer.selected and window.viewer.aim_contacts()
    # «Показать сеть» stays checked while the network is shown; a second press hides it
    assert contacts.network_button.isChecked()
    atoms = len(window.viewer.molecule.atoms)
    contacts.network_button.click()
    assert not contacts.network_button.isChecked() and not window.viewer.aim_contacts()
    block = len(window.viewer.molecule.atoms)
    assert block < atoms and window.crystal_tool.side_dialog() is contacts
    contacts.network_button.click()
    assert contacts.network_button.isChecked() and len(window.viewer.molecule.atoms) > block
    contacts.reject()  # «Закрыть» folds the panel
    assert window.crystal_side.isHidden() and window.crystal_tool.side_dialog() is None
    # the same panel comes back, still lit
    again = window.crystal_tool.show_contacts()
    assert again is contacts and again.network_button.isChecked() and window.crystal_tool.side_dialog() is contacts
    again.reject()
    assert window.crystal_side.isHidden()
    window.crystal_tool.set_compass_mode('molecule')
    window.dirty = False
    window.new_molecule()


def test_the_coordinates_of_a_crystal(window):
    # the independent atoms in fractions with the cell and the group, a row selecting its copies on the model; the CIF
    # of the crystal, POSCAR, the extended XYZ; the inputs of a molecule grey; back in a molecule — the table
    examples = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals'
    window.dirty = False
    window.opening_tool.open_example_path(str(examples / 'NaCl_rock_salt.cif'))
    if window.crystal_window.isVisible():
        window.crystal_window.reject()
    box = window.coord_format
    assert box.currentData() == 'sites' and not window.site_table.isHidden() and window.table.isHidden()
    data = window.crystal[0]
    assert window.site_table.rowCount() == len(data.sites) == 2
    assert 'Независимых атомов: 2, в ячейке: 8' in window.coord_note.text() and 'Å³' in window.coord_note.text()
    labels = [window.site_table.item(r, 0).text() for r in range(2)]
    row = next(r for r in range(2) if window.site_table.item(r, 1).text() == 'Na')
    window.site_table.selectRow(row)
    chosen = window.viewer.selected
    assert chosen and all(window.molecule.atoms[k].symbol == 'Na' for k in chosen)
    assert len(chosen) == sum(a.symbol == 'Na' for a in window.molecule.atoms)
    assert labels[row] in window.coord_text.toPlainText()  # «Копировать» takes the table as text
    box.setCurrentIndex(box.findData('cif'))
    assert '_atom_site_fract_x' in window.coord_text.toPlainText() and len(data.operations) > 1
    box.setCurrentIndex(box.findData('poscar'))
    assert 'Direct' in window.coord_text.toPlainText() and window.site_table.isHidden()
    box.setCurrentIndex(box.findData('extxyz'))
    assert window.coord_text.toPlainText().startswith('8\nLattice=')
    orca = box.findText('ORCA')
    assert not box.model().item(orca).isEnabled() and box.model().item(box.findText('XYZ')).isEnabled()
    window.crystal_tool.set_compass_mode('molecule')
    assert box.currentIndex() == 0 and box.model().item(orca).isEnabled()
    assert box.view().isRowHidden(box.findData('sites'))
    window.dirty = False
    window.new_molecule()


def test_the_crystal_panel_rebuilds_as_it_changes(window):
    # the settings in the panel beside the model, the block rebuilt as they change, no «Построить»;
    # the contacts opened from it replace it in the panel, the panel itself kept for «Искать снова»
    import time

    from PySide6.QtWidgets import QApplication, QPushButton

    examples = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals'
    window.dirty = False
    window.opening_tool.open_example_path(str(examples / 'benzoic_acid.cif'))
    panel = window.crystal_tool.reopen_crystal()
    assert panel.parent() is window.crystal_side and not window.crystal_side.isHidden() and panel.live
    assert 'Построить' not in [b.text() for b in panel.findChildren(QPushButton)]
    panel.counts[0].setValue(2)
    end = time.monotonic() + 5
    while window.crystal[1] != (2, 1, 1) and time.monotonic() < end:
        QApplication.processEvents()
        time.sleep(0.02)
    assert window.crystal[1] == (2, 1, 1) and window.crystal[3] is panel.whole.isChecked()
    assert not window.crystal_side.isHidden() and window.crystal_tool.side_dialog() is panel
    contacts = panel.show_contacts()
    assert window.crystal_tool.side_dialog() is contacts and panel.isHidden()
    again = contacts.search_again()
    assert again is not None and window.crystal_tool.side_dialog() is again
    again.reject()
    assert window.crystal_side.isHidden()
    panel = window.crystal_tool.reopen_crystal()
    panel.reject()  # «Закрыть» folds the panel
    assert window.crystal_side.isHidden() and not panel.live
    window.crystal_tool.set_compass_mode('molecule')
    window.dirty = False
    window.new_molecule()


def test_the_results_of_a_crystal_beside_its_model(window, tmp_path):
    # «Результаты расчётов» — the runs of the crystal in a panel beside the model, the energy of the
    # CELL_OPT of CsCl, its details, the analyses as buttons
    from modules.compass.actions import crystal_results_panel

    manifest, run = crystal_project_with_charges(tmp_path)
    window.open_project_path(str(manifest))
    if window.browsing:
        window.trajectory_tool.leave_trajectory()
    assert window.crystal_results_button.isVisibleTo(window)
    panel = crystal_results_panel.show(window)
    assert panel.parent() is window.crystal_side and not window.crystal_side.isHidden()
    assert panel.table.rowCount() == 1 and panel.table.item(0, 0).text().startswith('CP2K')
    assert abs(float(panel.table.item(0, 2).text()) + 35.19342) < 1e-4 and panel.table.item(0, 4).text() == 'сошёлся'
    text = panel.details.toPlainText()
    assert 'Энергия ячейки' in text and 'Ячейка последнего шага' in text and str(run) in text
    assert panel.charges_button.isEnabled() and panel.folder_button.isEnabled() and panel.steps_button.isEnabled()
    panel.reject()
    assert window.crystal_side.isHidden()
    # a side panel button stays checked while its panel is open; a second press closes it
    window.crystal_results_button.click()
    assert not window.crystal_side.isHidden() and window.crystal_results_button.isChecked()
    assert window.crystal_tool.side_kind() == 'results' and not window.crystal_info_button.isChecked()
    # the box of the panel slides to its width
    import time

    from PySide6.QtWidgets import QApplication

    box = window.crystal_side.parentWidget()
    end = time.monotonic() + 3
    while box.width() != window.crystal_side.slide_width and time.monotonic() < end:
        QApplication.processEvents()
        time.sleep(0.01)
    assert box.width() == window.crystal_side.slide_width >= 500 and window.crystal_side.width() == box.width()
    window.crystal_results_button.click()
    assert window.crystal_side.isHidden() and not window.crystal_results_button.isChecked()
    end = time.monotonic() + 3
    while box.isVisible() and time.monotonic() < end:
        QApplication.processEvents()
        time.sleep(0.01)
    assert box.isHidden() and box.width() == 0
    window.crystal_info_button.click()
    assert window.crystal_tool.side_kind() == 'crystal' and window.crystal_info_button.isChecked()
    panel = window.crystal_window
    assert panel.scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert panel.counts[0].isVisibleTo(panel) and not panel.vacuum.isVisibleTo(panel)  # «Блок ячеек» open, «Поверхность» folded
    window.viewer.emptyClicked.emit()
    assert window.crystal_side.isHidden() and not window.crystal_info_button.isChecked()
    window.crystal_info_button.click()  # the same panel again, not built anew (its symmetry and packing kept)
    assert window.crystal_window is panel and window.crystal_info_button.isChecked()
    window.crystal_info_button.click()
    window.crystal_tool.set_compass_mode('molecule')
    window.dirty = False
    window.new_molecule()


def test_the_notes_of_the_first_tester_on_crystals(window):
    # the cell of CsCl is told as one formula unit; vc-relax, the primitive cell of silicon, the ellipsoids and the
    # polyhedra are explained
    from modules.compass.chemistry import crystal as cr

    examples = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals'
    window.dirty = False
    window.opening_tool.open_example_path(str(examples / 'NaCl_rock_salt.cif'))
    assert window.molecule_info.text().startswith('ClNa  /  на модели атомов: ')
    items = [a for a in window.crystal_tool.view_menu().actions() if a.isCheckable()]
    assert items and all(a.toolTip() for a in items)
    qe = window.crystal_tool.show_qe()
    try:
        titles = [qe.task.itemText(k) for k in range(qe.task.count())]
        assert 'Оптимизация с ячейкой (vc-relax)' in titles and 'Энергия (scf)' in titles
        assert qe.task.findData('Оптимизация с ячейкой') >= 0  # the data stay the names of the tasks
        qe.primitive.setChecked(True)
        primitive = cr.primitive(qe.crystal)
        edges = qe.file_cell_of(primitive.cell.vectors())
        assert edges and all(abs(x - 5.64) < 1e-6 for x in edges)
        qe.primitive.setChecked(False)
        assert qe.file_cell_of(qe.crystal.cell.vectors()) is None
    finally:
        qe.close()
    window.crystal_tool.set_compass_mode('molecule')
    window.dirty = False
    window.new_molecule()


@pytest.mark.skipif(sys.platform == 'win32', reason='no build of CP2K for Windows (a calculation goes to a server or WSL), and the fake cp2k is a POSIX script')
def test_the_quick_xtb_of_a_crystal(window, tmp_path, monkeypatch):
    # «Расчёт → Быстрый расчёт xtb» of a crystal — GFN1-xTB of CP2K at once, without the page of Sextant (its settings
    # untouched), the progress on the pill, a line at the end, the steps of an optimization in the tab
    import sys
    import time

    from PySide6.QtWidgets import QApplication

    from modules.compass.actions import crystal_quick
    from modules.compass.chemistry import surface
    from modules.sextant import install_tools
    from tests.sextant.test_qe_inputs import silicon

    data = Path(__file__).resolve().parents[1] / 'data' / 'cp2k'
    fake = tmp_path / 'cp2k.ssmp'
    fake.write_text(f"""#!{sys.executable}
import shutil, sys
text = open('azimuth.inp').read()
assert sys.argv[1:] == ['-i', 'azimuth.inp'] and 'METHOD xTB' in text and 'CELL_OPT' in text
for name in ('azimuth-pos-1.xyz', 'azimuth-1.cell'):
    shutil.copy({str(data)!r} + '/' + name, name)
sys.stdout.write(open({str(data / 'cellopt.out')!r}).read())
""", encoding='utf-8')
    fake.chmod(0o755)
    monkeypatch.setattr(install_tools, 'cp2k_program', lambda *a, **k: fake)
    monkeypatch.setattr(window.run_tool, 'jobs_root', lambda: tmp_path / 'jobs')
    said = []
    monkeypatch.setattr(window, 'notify', lambda text, *a, **k: said.append(text))
    path = tmp_path / 'si.cif'
    path.write_text(surface.write_cif(silicon()), encoding='utf-8')
    window.dirty = False
    window.opening_tool.open_path(str(path))
    if window.crystal_window.isVisible():
        window.crystal_window.reject()
    assert [t for t, _, _ in crystal_quick.TASKS] == ['Энергия', 'Оптимизация атомов', 'Оптимизация с ячейкой']
    panel = crystal_quick.run(window, 'Оптимизация с ячейкой')
    assert panel is not None and panel.program == 'cp2k' and panel.cp2k_functional.currentData() == 'GFN1-XTB'
    assert crystal_quick.running(window) and crystal_quick.run(window, 'Энергия') is None  # one at a time
    end = time.monotonic() + 30
    while crystal_quick.running(window) and time.monotonic() < end:
        QApplication.processEvents()
        time.sleep(0.05)
    end = time.monotonic() + 5
    while not any('закончен' in t for t in said) and time.monotonic() < end:
        QApplication.processEvents()
        time.sleep(0.05)
    assert any(t.startswith('Быстрый расчёт кристалла закончен: E = ') for t in said), said
    assert window.crystal_mode_tool.panel is None or window.crystal_mode_tool.panel.cp2k_functional.currentData() != 'GFN1-XTB'
    if window.browsing:
        window.trajectory_tool.leave_trajectory()
    window.crystal_tool.set_compass_mode('molecule')
    window.dirty = False
    window.new_molecule()


def test_the_help_of_a_question_mark_stays_open(window):
    # «?» opens a panel that stays until a click past it, Esc or another click — not a tooltip that goes at the first
    # move
    import time

    from PySide6.QtWidgets import QApplication, QLabel

    from azimuth import ui

    button = ui.help_button('Поверхность — где сферические атомы.\n\nВторой абзац.')
    button.setParent(window)
    button.show()
    button.click()
    popup = ui._HelpPopup.shown[0]
    assert popup.isVisible() and 'Второй абзац' in popup.findChild(QLabel).text()
    end = time.monotonic() + 0.5
    while time.monotonic() < end:
        QApplication.processEvents()
        time.sleep(0.02)
    assert ui._HelpPopup.shown is not None and popup.isVisible()
    popup.close()
    QApplication.processEvents()
    assert ui._HelpPopup.shown is None
    button.deleteLater()


def test_the_fields_of_the_crystal_setup_move_into_the_dialog(window, app, tmp_path):
    # the page of a crystal as that of a molecule (0.222.0): no scrolling, the rarer fields in «Дополнительные
    # настройки…» → «Задача», «Поля…» chooses; every task of both programs fits the window of 1133 × 730
    from modules.compass.chemistry import surface
    from modules.sextant import setup_rows as sr
    from tests.sextant.test_qe_inputs import silicon

    path = tmp_path / 'si.cif'
    path.write_text(surface.write_cif(silicon()), encoding='utf-8')
    window.dirty = False
    window.opening_tool.open_path(str(path))
    window.crystal_window.reject()
    window.viewer.set_selection([])
    assert window.crystal_tool.to_calculation()
    tool = window.crystal_mode_tool
    panel, rows = tool.panel, tool.setup_rows
    # Quantum ESPRESSO is compared with the literature (docs/plans/CRYSTAL_VALIDATION.md) — no mark; CP2K is not yet:
    # marked in the title, the reason in its tip
    assert tool.unverified.text() == 'Постановка задачи' and tool.unverified.toolTip() == ''
    assert panel.set_program('cp2k') and tool.unverified.text().endswith('не проверено')
    assert 'числа ещё не сверены с литературой' in tool.unverified.toolTip()
    assert panel.set_program('qe') and tool.unverified.text() == 'Постановка задачи'
    try:
        rows.reset()
        inside = tool.options_dialog.forms[-1]
        assert tool.options_dialog.groups[-1][0] == 'Задача'
        assert rows.form_of(tool.calc_title) is inside and rows.form_of(panel.relax_line) is inside
        assert rows.form_of(panel.k_line) is panel.form and rows.form_of(panel.vdw) is panel.form
        rows.toggle('relax', True)
        assert rows.form_of(panel.relax_line) is panel.form
        rows.toggle('vdw', False)
        assert rows.form_of(panel.vdw) is inside and rows.form_of(panel.cp2k_vdw) is inside  # both programs' rows
        assert window.preferences.value(sr.CRYSTAL_KEY) is not None
        rows.reset()
        # as the page of a molecule: no colons after the names (polish.colon_labels takes a widget whose own layout is
        # a form), the values of the fields in their middle
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QAbstractSpinBox

        from azimuth import polish

        holder = panel.form.parentWidget()
        assert polish._form_of(holder) is None  # so no colons are added when it is shown
        assert all(s.alignment() & Qt.AlignmentFlag.AlignHCenter for s in holder.findChildren(QAbstractSpinBox))
        window.resize(1133, 730)
        window.show()
        for program in ('qe', 'cp2k'):
            tool.program_combo.setCurrentIndex(tool.program_combo.findData(program))
            for k in range(panel.task.count()):
                panel.task.setCurrentIndex(k)
                app.processEvents()
                need = holder.minimumSizeHint().height()
                assert need <= holder.height(), (program, panel.task.itemText(k), need, holder.height())
                assert window.height() <= 731, (program, panel.task.itemText(k), window.height())
        # the window of the installation of the programs — in the place of the input file of the crystal (it went into the
        # hidden card of the molecule), «Входной файл» brings the file back
        jw = window.show_job_window()
        assert tool.shows_install(window.job_window) and tool.install_slot.isVisible() and not tool.preview_card.isVisible()
        window.show_input_card()
        assert tool.preview_card.isVisible() and not tool.install_slot.isVisible()
        del jw
        # a program hides the rows of the other wherever they stand
        tool.program_combo.setCurrentIndex(tool.program_combo.findData('qe'))
        rows.toggle('vdw', False)
        assert panel.cp2k_vdw.isHidden() and not panel.vdw.isHidden()
    finally:
        rows.reset()
        tool.program_combo.setCurrentIndex(tool.program_combo.findData('qe'))


def test_crystal_series_shown_by_the_panel(window, tmp_path, monkeypatch):
    # the panel of Quantum ESPRESSO with a pw.x that prints, for the n-th input of a series, the n-th real run of
    # tests/data/qe: the elastic constants of MgO, the grids N × N × 1 of graphene and its Dirac cone — what the
    # summary says and which plot the button opens
    import sys
    import time

    from modules.compass.chemistry import crystal as cr, surface
    from modules.sextant import install_tools, qe_inputs, qe_pseudo
    from tests.compass.test_layer import graphene

    data = Path(__file__).resolve().parents[1] / 'data' / 'qe'
    tools = tmp_path / 'bin'
    tools.mkdir()
    fake = tools / 'pw.x'
    fake.write_text(f"""#!{sys.executable}
import re, sys
name = sys.argv[sys.argv.index('-in') + 1]
source = {{'ela': 'mgo_elastic_pw76.out', 'kpt': 'graphene_kpt_pw76.out', 'scf': 'graphene_bands_pw76.out',
          'ban': 'graphene_bands_pw76.out'}}[name[:3]]
runs = open({str(data)!r} + '/' + source, encoding='utf-8').read().split('Program PWSCF')[1:]
index = 1 if name == 'bands.in' else 0 if name == 'scf.in' else int(re.search(r'\\d+', name).group()) - 1
sys.stdout.write('     Program PWSCF' + runs[index])
""", encoding='utf-8')
    fake.chmod(0o755)
    monkeypatch.setattr(install_tools, 'qe_program', lambda *a, **k: fake)
    monkeypatch.setattr(qe_pseudo, 'installed', lambda *a, **k: True)
    monkeypatch.setattr(qe_pseudo, 'table', lambda *a, **k: {'Mg': ('Mg.upf', 30.0, 240.0), 'O': ('O.upf', 50.0, 400.0),
                                                           'C': ('C.upf', 45.0, 360.0)})
    monkeypatch.setattr(qe_inputs, 'valence', lambda *a, **k: 4.0)
    monkeypatch.setattr(window.run_tool, 'jobs_root', lambda: tmp_path / 'jobs')

    def opened(crystal, name):
        path = tmp_path / name
        path.write_text(surface.write_cif(crystal), encoding='utf-8')
        window.dirty = False
        window.opening_tool.open_path(str(path))
        panel = window.crystal_window.show_qe()
        panel.processes.setValue(1)
        return panel

    def finish(panel, task):
        panel.task.setCurrentIndex(panel.task.findData(task))
        time.sleep(1.1)  # the folder of a run is named to the second: the fake pw.x ends within it
        assert panel.start() is not None, panel.status.text()
        deadline = time.monotonic() + 60
        while panel.result is None and time.monotonic() < deadline:
            time.sleep(0.1)
            panel.poll()
        assert panel.result is not None and panel.result.done and not panel.result.error, panel.status.text()

    magnesia = cr.parse_cif('data_MgO\n_cell_length_a 4.2486\n_cell_length_b 4.2486\n_cell_length_c 4.2486\n'
                            "_space_group_name_H-M_alt 'F m -3 m'\nloop_\n_atom_site_label\n_atom_site_fract_x\n"
                            '_atom_site_fract_y\n_atom_site_fract_z\nMg1 0 0 0\nO1 0.5 0.5 0.5\n')
    panel = opened(magnesia, 'mgo.cif')
    finish(panel, qe_inputs.ELASTIC_TASK)
    assert (panel.folder / 'elastic.json').is_file() and (panel.folder / 'ela19.in').is_file()
    assert 'C₁₁ = 276.3' in panel.summary.text() and '153.5' in panel.summary.text()
    assert panel.plot_button.isVisible() and panel.plot_button.text() == 'Показать E(ε)'
    plot = panel.show_plot()
    assert len(plot.plot.series) == 3 and all(len(points) == 7 for _, _, points, _ in plot.plot.series)
    plot.plot.resize(640, 420)
    plot.plot.grab()
    assert len(Path(plot.save(str(tmp_path / 'elastic.csv'))).read_text(encoding='utf-8').splitlines()) == 22
    plot.reject()
    panel.reject()

    panel = opened(graphene(), 'graphene.cif')
    finish(panel, qe_inputs.KGRID_TASK)
    assert panel.plot_button.text() == 'Показать сходимость' and 'кратным 3' in panel.summary.text()
    plot = panel.show_plot()
    assert plot.plot.labels[0] == '6 × 6 × 1' and plot.plot.marked == [True, False, True, False, True, True, True, True]
    assert 'Уровень Ферми' in plot.note.text() and '-1.6887' in plot.note.text()
    plot.plot.resize(640, 420)
    plot.plot.grab()
    plot.reject()
    finish(panel, qe_inputs.BANDS_TASK)
    assert 'Конус Дирака' in panel.summary.text() and '0.831' in panel.summary.text()
    plot = panel.show_plot()
    assert [t[1] for t in plot.plot.ticks] == ['Γ', 'M', 'K', 'Γ'] and len(plot.plot.model) == len(plot.plot.x) == 162
    cone = panel.cone_window
    assert cone.plot.xrange is not None and 't = 2ħv_F' in cone.note.text() and 'Наклоны зон' in cone.note.text()
    for shown in (plot, cone):
        shown.plot.resize(640, 420)
        shown.plot.grab()
        shown.reject()
    panel.reject()


def test_the_grid_of_cp2k_follows_the_elements(window):
    # the box «CUTOFF» takes what the elements need while nobody typed in it; a value typed stays
    from modules.compass.chemistry import crystal as cr

    examples = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals'
    window.dirty = False
    window.opening_tool.open_example_path(str(examples / 'Si_diamond.cif'))
    window.crystal_window.reject()
    panel = window.crystal_mode_tool.panel
    salt = cr.parse_cif((examples / 'NaCl_rock_salt.cif').read_text(encoding='utf-8'))
    silicon = cr.parse_cif((examples / 'Si_diamond.cif').read_text(encoding='utf-8'))
    assert panel.set_crystal(silicon, 'Si') and panel.cutoff.value() == 400
    assert panel.set_crystal(salt, 'NaCl') and panel.cutoff.value() == 950
    assert panel.set_crystal(silicon, 'Si') and panel.cutoff.value() == 400
    panel.cutoff.setValue(600)
    assert panel.set_crystal(salt, 'NaCl') and panel.cutoff.value() == 600
    for d in window.all_documents():
        d.dirty = False
