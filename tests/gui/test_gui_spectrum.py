"""Window tests — Spectrum: results, vibrations, UV-Vis, NMR, thermochemistry and their windows (split from test_gui.py
on 2026-11-08)."""

from tests.gui_support import *  # noqa: F401,F403 — the fixtures app, window and the helpers


def test_vibration_animation_does_not_mutate_editor_or_equilibrium(window, app):
    from math import pi

    original = window.molecule
    window.demo_vibrations()
    window.show()
    app.processEvents()
    assert window.documents[0].molecule == original  # the result has its own tab
    shown, dirty = window.molecule, window.dirty
    panel = window.vibrations
    assert window.result_tabs.currentIndex() == 1 and panel.current == 6
    base = panel.base
    panel.phase = pi / 2
    panel.draw_frame()
    assert panel.viewer.molecule.atoms != base.atoms
    assert panel.viewer.molecule.bonds == base.bonds
    assert window.molecule == shown and window.dirty == dirty
    window.confirm_replace = lambda: True
    window.adopt_geometry()
    assert window.molecule.atoms == base.atoms
    assert not panel.timer.isActive()
    from modules.compass.view.viewer import MoleculeView

    assert type(panel.viewer).FIT > MoleculeView.FIT
    controls = panel.view_controls
    assert [b.property('quail_icon') for b in controls] == ['rotate-y-minus', 'rotate-y-plus', 'rotate-x-minus',
                                                            'rotate-x-plus', 'zoom-in', 'zoom-out']
    field = panel.viewer.geometry()
    corner = controls[-1].mapTo(panel.viewer.parentWidget(), controls[-1].rect().topRight())
    assert corner.x() > field.center().x() and corner.y() < field.center().y()  # over the top right of the field
    # the camera kept for the animation follows the size of the field (it was kept in pixels: small for good)
    panel.viewer.keep_camera()
    scale = panel.viewer.camera()[1]
    panel.viewer.resize(panel.viewer.width() * 2, panel.viewer.height() * 2)
    assert panel.viewer.camera()[1] == pytest.approx(2 * scale, rel=0.02)
    zoom, yaw = panel.viewer.zoom, panel.viewer.yaw
    controls[4].click()
    controls[1].click()
    assert panel.viewer.zoom > zoom and panel.viewer.yaw > yaw


def test_vibration_play_pause_reset_and_tab_hide(window, app):
    window.demo_vibrations()
    window.show()
    app.processEvents()
    panel = window.vibrations
    panel.play.click()
    assert panel.timer.isActive()
    panel.last_tick -= 0.05
    panel.tick()
    assert panel.phase > 0
    phase = panel.phase
    panel.play.click()
    assert not panel.timer.isActive() and panel.phase == phase
    panel.reset.click()
    assert panel.phase == 0 and panel.viewer.molecule.atoms == panel.base.atoms
    panel.play.click()
    window.result_tabs.setCurrentIndex(0)
    app.processEvents()
    assert not panel.timer.isActive() and not panel.play.isChecked()


def test_vibration_spectrum_selection_and_reload(window, app):
    window.demo_vibrations()
    window.show()
    app.processEvents()
    panel = window.vibrations
    idx, pt = panel.spectrum.peaks()[-1]
    QTest.mouseClick(panel.spectrum, Qt.MouseButton.LeftButton, pos=pt.toPoint())
    assert panel.current == idx == 8
    panel.table.setCurrentCell(0, 0)
    assert not panel.play.isEnabled()
    window.display_output('ORCA\nFINAL SINGLE POINT ENERGY -1', 'new.out')
    assert not panel.modes and panel.viewer.molecule is None and not panel.timer.isActive()
    assert not panel.play.isEnabled()


def test_frequency_without_vectors_remains_visible(window):
    window.demo_output()
    panel = window.vibrations
    assert panel.table.rowCount() == 9
    panel.table.setCurrentCell(6, 0)
    assert not panel.play.isEnabled() and not panel.arrows.isEnabled()


def test_result_properties_on_the_compass_model(window):
    # an ORCA output opened in Spectrum gives charges, Mayer orders and the dipole on the
    # Compass model, while the model shows the geometry of the result
    from dataclasses import replace as replaced
    from azimuth.core import Atom

    data = Path(__file__).parents[1] / 'data' / 'orca_cclib'
    window.display_output((data / 'water_mp2_orca5.0.out').read_text(encoding='utf-8'), 'water_mp2.out', False)
    assert window.result_properties is not None
    window.load_molecule(window.output.geometry)
    assert window.viewer.overlay_source(window.molecule) is None  # nothing chosen yet
    window.property_tool.choose_overlay('atom', 'mulliken')
    window.property_tool.choose_overlay('dipole', True)
    window.property_tool.choose_overlay('bonds', True)
    shown = window.viewer.overlay_source(window.molecule)
    assert shown['atom'] == ('mulliken', (-0.361723, 0.180857, 0.180866)) and shown['dipole'][1] == 1.71890
    window.viewer.grab()  # draws the labels, the orders and the arrow
    window.property_tool.fill_properties_menu(window.properties_menu)
    enabled = {a.text() for a in leaf_actions(window.properties_menu) if a.isEnabled()}
    assert 'Заряды Малликена' in enabled and 'Силы на атомах (минус градиент)' not in enabled
    # «±» split into three buttons above the model, each with its part of the menu
    assert list(window.property_buttons) == ['atoms', 'bonds', 'vectors']
    parts = {}
    for part, box in window.property_menus.items():
        window.property_tool.fill_properties_menu(box, part)
        parts[part] = {a.text() for a in leaf_actions(box) if a.text()}
    assert 'Заряды Малликена' in parts['atoms'] and 'Заряды ADCH и CM5…' in parts['atoms']
    assert 'Порядки связей Майера' in parts['bonds'] and 'Связи по порядкам Майера' in parts['bonds']
    assert parts['vectors'] >= {'Дипольный момент (стрелка от − к +)', 'Силы на атомах (минус градиент)'}
    assert not parts['atoms'] & {'Порядки связей Майера', 'Дипольный момент (стрелка от − к +)'}
    assert not parts['vectors'] & {'Заряды Малликена', 'Порядки связей Майера'}
    assert parts['atoms'] | parts['bonds'] | parts['vectors'] == {a.text() for a in leaf_actions(window.properties_menu)
                                                                  if a.text()}
    # the values at the atoms by kind in submenus, the analyses in their own; «•» — the kind on the model
    top = [x.text() for x in window.property_menus['atoms'].actions() if x.text()]
    assert top.index('Без подписей у атомов') < top.index('Заряды •') and 'Спиновые заселённости' in top  # after «Из файла»
    assert 'Посчитать по волновой функции' in top and 'Заряды Малликена' not in top
    # everything laid over the structure goes at one press (the structure stays)
    assert window.clear_overlays_button.toolTip().startswith('Убрать с модели')
    # each by its name
    assert window.property_tool.clear_model_overlays() == ['заряды Малликена', 'порядки связей', 'дипольный момент']
    assert window.viewer.overlay_source(window.molecule) is None and len(window.molecule.atoms) == 3
    assert window.property_tool.clear_model_overlays() == []
    window.property_tool.choose_overlay('bonds', True)
    window.property_tool.take_mayer_bonds()
    assert sorted(window.molecule.bonds) == [(0, 1, 1), (0, 2, 1)]
    atoms = list(window.molecule.atoms)
    atoms[1] = Atom('H', atoms[1].x + 0.2, atoms[1].y, atoms[1].z)
    window.load_molecule(replaced(window.molecule, atoms=tuple(atoms)))
    assert window.viewer.overlay_source(window.molecule) is None  # another structure: nothing drawn


def test_uv_vis_and_nmr_tabs(window, tmp_path):
    # TD-DFT excitations give the «UV-Vis» tab, shieldings the «ЯМР» tab; the NMR reference
    # is read from an output of the reference molecule (here a synthetic TMS-like table)
    from PySide6.QtCore import QSettings
    from modules.spectrum.readers.orca_spectra import read_shieldings
    from modules.spectrum.views.spectra_view import NMRPanel

    data = Path(__file__).parents[1] / 'data' / 'orca_cclib'
    window.display_output((data / 'dvb_td_orca6.0.out').read_text(encoding='utf-8'), 'td.out', False)
    tabs = window.result_tabs
    assert tabs.isTabVisible(window.uv_tab) and not tabs.isTabVisible(window.nmr_tab)
    assert tabs.currentIndex() == window.uv_tab and window.uv_panel.table.rowCount() == 10
    window.uv_panel.plot.resize(500, 260)
    window.uv_panel.plot.grab()
    nmr_text = (data / 'dvb_nmr_orca6.0.out').read_text(encoding='utf-8')
    window.display_output(nmr_text, 'nmr.out', False)
    assert tabs.isTabVisible(window.nmr_tab) and tabs.currentIndex() == window.nmr_tab
    panel = NMRPanel(QSettings(str(tmp_path / 'nmr.ini'), QSettings.Format.IniFormat))
    panel.load(read_shieldings(nmr_text), window.output.geometry)
    assert panel.element.currentText() == 'H' and panel.table.rowCount() == 5
    assert panel.table.item(0, 3).text() == '—'  # no reference yet
    rows = '\n'.join(f'  {k:5d}       H           31.500          9.0' for k in range(12))
    rows += '\n' + '\n'.join(f'  {k:5d}       C          190.000         0.0' for k in range(12, 16))
    panel.reference_from_text(
        f'CHEMICAL SHIELDING SUMMARY (ppm)\n---\n\n  Nucleus  Element    Isotropic     Anisotropy\n  -------  -------\n{rows}\n\n'
    )
    assert panel.table.item(0, 0).text() == 'H7, H8' and panel.table.item(0, 3).text() == f'{31.5 - 25.574:.2f}'
    panel.average.setChecked(False)
    assert panel.table.rowCount() == 10
    panel.plot.resize(400, 160)
    panel.plot.grab()


def test_nmr_reference_tms_at_the_level_of_the_result(window, app, tmp_path):
    # the reference is kept per level of theory; a TMS result remembers itself; «Рассчитать TMS этим
    # уровнем» puts the TMS input with the level of the result into Sextant
    from PySide6.QtCore import QSettings
    from modules.spectrum.analysis.nmr_reference import is_tms, tms_molecule
    from modules.spectrum.readers.orca_spectra import Shielding

    data = Path(__file__).parents[1] / 'data' / 'orca601'
    text = (data / 'h2o_nmr.out').read_text(encoding='utf-8')
    window.nmr_panel.preferences = QSettings(str(tmp_path / 'nmr.ini'), QSettings.Format.IniFormat)
    window.run_tool.jobs_root = lambda: tmp_path / 'jobs'
    window.display_output(text, 'h2o_nmr.out', False)
    panel = window.nmr_panel
    assert panel.level == 'B3LYP DEF2-SVP' and panel.tms_button.isEnabled()
    assert panel.table.item(0, 3).text() == '—' and 'Рассчитать TMS' in panel.note.text()
    tms = [Shielding(0, 'Si', 330.0, None)] + [Shielding(k, 'C', 190.0, None) for k in range(1, 5)]
    tms += [Shielding(k, 'H', 31.9, None) for k in range(5, 17)]
    panel.load(tms, tms_molecule(), 'B3LYP DEF2-SVP', 'tms text', 'ORCA')  # the TMS result of that level
    assert 'опора запомнена' in panel.note.text() and not panel.tms_button.isEnabled()
    window.display_output(text, 'h2o_nmr.out', False)
    panel.element.setCurrentIndex(panel.element.findText('H'))
    assert panel.table.item(0, 3).text() == f'{31.9 - 31.78:.2f}' and 'TMS уровня B3LYP DEF2-SVP' in panel.note.text()
    panel.load(panel.shieldings, panel.geometry, 'PBE0 DEF2-TZVP', text, 'ORCA')  # another level: no reference
    assert panel.table.item(0, 3).text() == '—'
    window.display_output(text, 'h2o_nmr.out', False)
    window.confirm_replace = lambda: True
    panel.request_tms()
    path = tmp_path / 'jobs' / 'nmr-reference' / 'TMS_B3LYP_DEF2-SVP.inp'
    assert path.exists() and '! B3LYP def2-SVP NMR TightSCF' in path.read_text(encoding='utf-8')
    assert is_tms(window.molecule) and window.stack.currentIndex() == 1
    assert window.input_edited and window.input_tool.edited_input().startswith('# TMS')
    window.input_tool.reset_input()
    window.navigate(0)



def test_nmr_multiplets_from_couplings(window, app, tmp_path, monkeypatch):
    # ethanol and chloroethene of ORCA 6.0.1
    from PySide6.QtCore import QSettings

    data = Path(__file__).parents[1] / 'data' / 'nmr_j'
    window.nmr_panel.preferences = QSettings(str(tmp_path / 'nmr.ini'), QSettings.Format.IniFormat)
    window.display_output((data / 'ethanol_ssall_orca.out').read_text(encoding='utf-8'), 'ethanol.out', False)
    panel = window.nmr_panel
    assert window.result_tabs.isTabVisible(window.nmr_tab) and panel.split.isEnabled() and panel.split.isChecked()
    panel.element.setCurrentIndex(panel.element.findText('H'))
    panel.set_reference('H', 31.9)
    panel.element_changed()
    texts = {panel.table.item(r, 0).text(): panel.table.item(r, 4).text() for r in range(panel.table.rowCount())}
    assert texts['H5, H6'] == 'кд, J = 7.2, 1.2 Гц' and texts['H7, H8, H9'].startswith('тд, J = 7.2')
    row = [panel.table.item(r, 0).text() for r in range(panel.table.rowCount())].index('H5, H6')
    panel.table.selectRow(row)
    assert len(panel.multiplet.lines) == 8 and panel.multiplet.title.startswith('H5, H6: кд')
    for widget in (panel.plot, panel.multiplet):
        widget.resize(500, 180)
        widget.grab()
    panel.element.setCurrentIndex(panel.element.findText('C'))
    assert panel.decoupled.isVisibleTo(panel) and panel.table.item(0, 4).text() == 'с'
    panel.decoupled.setChecked(False)
    assert any(panel.table.item(r, 4).text().startswith('т') for r in range(panel.table.rowCount()))
    panel.decoupled.setChecked(True)
    # chloroethene: three doublets of doublets; at 60 MHz the geminal pair is strongly coupled
    window.display_output((data / 'c2h3cl_ssall_orca.out').read_text(encoding='utf-8'), 'vinyl.out', False)
    panel.element.setCurrentIndex(panel.element.findText('H'))
    panel.set_reference('H', 31.9)
    panel.element_changed()
    assert {panel.table.item(r, 4).text()[:2] for r in range(panel.table.rowCount())} == {'дд'}
    panel.mhz.setValue(60)
    notes = []
    for r in range(panel.table.rowCount()):
        panel.table.selectRow(r)
        notes.append(panel.multiplet_note.text())
    assert any('Сильная связь' in n for n in notes)
    panel.mhz.setValue(400)
    path = tmp_path / 'nmr.csv'
    from modules.spectrum.views import spectra_view

    monkeypatch.setattr(spectra_view.QFileDialog, 'getSaveFileName', staticmethod(lambda *a, **k: (str(path), '')))
    panel.export()
    assert 'multiplet' in path.read_text(encoding='utf-8-sig').splitlines()[0]


def test_orbital_window_from_molden_fchk_and_orca_output(window, app, tmp_path):
    # orbitals without CUBE files — the table, ВЗМО/НСМО, the level diagram, fields on a grid
    import shutil

    data = Path(__file__).parents[1] / 'data' / 'orbitals'
    molden = tmp_path / 'water.molden'
    shutil.copy(data / 'molden5.7_water_mp2.molden', molden)
    dialog = window.open_orbitals_text(molden.read_text(encoding='utf-8'), molden.name)
    shown = []
    dialog.show_cube = lambda cube, density: shown.append((cube, density))
    dialog.target.setCurrentIndex(dialog.target.findData('window'))  # the default is the Compass model
    assert dialog.table.rowCount() == 7 and dialog.current() == 4  # orbital 5 is the HOMO
    assert dialog.table.item(4, 6).text() == 'ВЗМО' and dialog.table.item(5, 6).text() == 'НСМО'
    dialog.step.setCurrentIndex(0)
    dialog.show_orbital()
    dialog.show_density(False)
    assert [d for _, d in shown] == [False, True] and shown[0][0].ids == (5,)
    assert not dialog.spin_button.isEnabled()
    dialog.levels.resize(200, 400)
    dialog.levels.grab()
    dialog.close()
    # an ORCA output that printed its basis and orbitals offers them itself
    out = tmp_path / 'dvb.out'
    shutil.copy(data / 'dvb_sp_dft_orca6.0.out', out)
    window.open_output_path(str(out), show=False)
    assert not window.orbitals_button.isHidden() and window.sibling_molden == out
    # Compass: Файл → Открыть… with a .fchk loads the structure and opens the orbital window
    fchk = tmp_path / 'water.fchk'
    shutil.copy(data / 'water_mp2_g16.fchk', fchk)
    window.dirty = False
    window.opening_tool.open_path(str(fchk))
    assert [a.symbol for a in window.molecule.atoms] == ['O', 'H', 'H']
    assert window.orbitals_dialog.orbital_set.source == 'Gaussian fchk'
    window.orbitals_dialog.close()


def test_gaussian_xtb_and_psi4_results(window, app, tmp_path):
    # the outputs of Gaussian, xtb and Psi4 open like ORCA's: modes, spectra, steps, properties
    import shutil

    data = Path(__file__).parents[1] / 'data'
    window.open_output_path(str(data / 'gaussian' / 'dvb_ir_g16.log'), show=False)
    assert window.output.program == 'Gaussian 16' and window.result_tabs.currentIndex() == 1
    assert window.output_source.text().endswith('Gaussian 16')
    window.open_output_path(str(data / 'gaussian' / 'dvb_td_g16.log'), show=False)
    assert window.result_tabs.isTabVisible(window.uv_tab) and window.uv_panel.table.rowCount() == 5
    run = tmp_path / 'opt'
    shutil.copytree(data / 'xtb' / 'dvb_opt', run)
    window.dirty = False
    window.opening_tool.open_path(str(run / 'dvb_opt.out'))
    assert window.output.program == 'xtb 6.6.1' and len(window.drawer.steps) == 6
    assert window.result_properties.bond_kind == 'Wiberg'
    window.open_output_path(str(data / 'psi4' / 'water_ccsdt_psi4-1.7.out'), show=False)
    assert 'CCSD(T)' in window.result_summary.text()


def test_vibration_arrows_gif_xyz_and_displaced_geometry(window, app, tmp_path, monkeypatch):
    # arrows of their own length both ways, one period as GIF and XYZ frames, a geometry
    # displaced along the mode taken to Compass
    from math import dist
    from PySide6.QtWidgets import QMessageBox

    from modules.compass.chemistry.formats import read_xyz_frames

    window.demo_vibrations()
    window.show()
    app.processEvents()
    panel = window.vibrations
    assert panel.gif_button.isEnabled() and panel.plus_button.isEnabled()
    panel.arrows.setChecked(True)
    panel.both.setChecked(True)
    panel.arrow_length.setValue(1.2)
    assert panel.viewer.both_ways and panel.viewer.vector_scale == pytest.approx(1.2)
    gif = panel.save_gif(tmp_path / 'mode.gif', count=8)
    data = (tmp_path / 'mode.gif').read_bytes()
    assert gif and data[:6] in (b'GIF89a', b'GIF87a') and data.count(b'\x21\xf9\x04') >= 8  # 8 frames
    assert panel.viewer.molecule.atoms == panel.base.atoms  # the still picture is back
    xyz = panel.save_xyz(tmp_path / 'mode.xyz', count=12)
    frames = read_xyz_frames(xyz and (tmp_path / 'mode.xyz').read_text(encoding='utf-8'))
    assert len(frames) == 12
    monkeypatch.setattr(QMessageBox, 'question', lambda *a, **k: QMessageBox.StandardButton.Yes)
    window.dirty = False
    moved = panel.request_displaced(-1)
    assert window.stack.currentIndex() == 0 and len(window.molecule.atoms) == len(moved.atoms)
    for shown, wanted in zip(window.molecule.atoms, moved.atoms):  # Compass keeps 8 decimals (1e-8 Å)
        assert shown.symbol == wanted.symbol and dist(shown.position, wanted.position) < 1e-7
    largest = max(dist(a.position, b.position) for a, b in zip(moved.atoms, panel.base.atoms))
    assert largest == pytest.approx(panel.amplitude.value(), abs=1e-9)


def test_spectrum_thermochemistry_convergence_and_comparison(window, app):
    # the «Термохимия» tab of a frequency result (σ from the point group, the totals of Psi4), the
    # «Сходимость» tab of an optimization, a second IR and UV-Vis spectrum drawn for comparison
    data = Path(__file__).parents[1] / 'data'
    ir = data / 'psi4' / 'dvb_ir_rhf_psi4-1.7.out'
    window.display_output(ir.read_text(encoding='utf-8'), ir.name, False, str(ir))
    tabs = window.result_tabs
    assert tabs.isTabVisible(window.thermo_tab) and not tabs.isTabVisible(window.convergence_tab)
    panel = window.thermo_panel
    assert panel.sigma.value() == 2 and panel.multiplicity.value() == 1  # C2h; «multiplicity = 1» of Psi4
    assert panel.result.total(panel.result.gibbs) == pytest.approx(-379.60972224, abs=1e-7)
    assert 'C2h' in panel.group.text() and panel.table.rowCount() == 9
    panel.temperature.setValue(500.0)
    assert panel.result.temperature == 500.0 and panel.result.gibbs < 0.16038928  # −TS grows with T
    panel.qrrho.setChecked(True)
    assert panel.result.qrrho and 'ZPE' in panel.text()
    panel.temperature.setValue(298.15)
    panel.qrrho.setChecked(False)

    opt = data / 'psi4' / 'dvb_gopt_rhf_psi4-1.7.out'
    window.display_output(opt.read_text(encoding='utf-8'), opt.name, False, str(opt))
    assert tabs.isTabVisible(window.convergence_tab) and not tabs.isTabVisible(window.thermo_tab)
    conv = window.convergence_panel
    assert conv.history.steps == 5 and 'Psi4' in conv.summary.text()
    conv.plot.resize(600, 360)
    conv.plot.grab()
    rows, header = conv.csv_rows()
    assert header[:2] == ['step', 'dE_kcal_mol'] and len(rows) == 5 and rows[-1][1] == 0.0
    xtb = data / 'xtb' / 'dvb_opt' / 'dvb_opt.out'
    window.display_output(xtb.read_text(encoding='utf-8'), xtb.name, False, str(xtb))
    assert window.convergence_panel.table.rowCount() == 1  # the gradient norm of xtbopt.log

    gaussian = data / 'gaussian' / 'dvb_ir_g16.log'
    window.display_output(ir.read_text(encoding='utf-8'), ir.name, False, str(ir))
    from modules.spectrum.readers.outputs import read_any

    other = read_any(gaussian.read_text(encoding='utf-8'), str(gaussian))
    vib = window.vibrations
    assert vib.set_reference(other.modes, gaussian.name) and vib.ir_clear.isVisibleTo(vib)
    for smooth in (0, 1):
        vib.ir_style.setCurrentIndex(smooth)
        vib.spectrum.resize(600, 260)
        vib.spectrum.grab()
    vib.ir_style.setCurrentIndex(0)  # sticks: the axis is km/mol for both results (the curve is a density)
    xmax, ymax = vib.spectrum.limits()
    assert ymax >= max(m.intensity for m in other.modes if m.intensity is not None and m.frequency > 0) * 0.999
    vib.set_reference(None)
    assert vib.spectrum.reference is None and not vib.ir_clear.isVisibleTo(vib)

    td_orca = data / 'orca_cclib' / 'dvb_td_orca6.0.out'
    td_gaussian = data / 'gaussian' / 'dvb_td_g16.log'
    window.display_output(td_orca.read_text(encoding='utf-8'), td_orca.name, False, str(td_orca))
    uv = window.uv_panel
    gaussian_td = read_any(td_gaussian.read_text(encoding='utf-8'), str(td_gaussian))
    assert uv.set_reference(gaussian_td.absorption, td_gaussian.name)
    uv.plot.resize(600, 260)
    uv.plot.grab()
    lo, hi = uv.plot.frame(uv.plot.data()[0])
    assert lo <= min(e.wavelength for e in gaussian_td.absorption if e.fosc > 0) <= hi
    assert not uv.set_reference(())  # nothing allowed: no comparison


def test_ecd_view_of_the_uv_vis_tab(window, tmp_path):
    # rotatory strengths switch on «Круговой дихроизм (ЭКД)»: a signed curve, the column R; an achiral
    # molecule (water, ORCA 6.0.1) is called achiral; an output without CD tables has no switch
    data = Path(__file__).parents[1] / 'data'
    g09 = data / 'gaussian09' / 'ind_acid_td_g09.out'
    window.display_output(g09.read_bytes().decode('ascii'), g09.name, False, str(g09))
    uv = window.uv_panel
    assert uv.kind.isVisibleTo(uv) and not uv.table.isColumnHidden(uv.R_COLUMN)
    assert uv.table.item(0, uv.R_COLUMN).text() == '10.9516'  # the velocity gauge
    assert uv.plot.mode == 'uv'
    uv.kind.setCurrentIndex(uv.kind.findData('cd'))
    assert uv.plot.mode == 'cd' and 'калибровка скоростей' in uv.summary.text() and '·10⁻⁴⁰' in uv.summary.text()
    x, y, shown = uv.plot.data()
    assert y.min() < 0 < y.max() and len(shown) == 40
    uv.plot.resize(600, 260)
    uv.plot.grab()
    target = tmp_path / 'ecd.csv'
    from unittest import mock
    with mock.patch('modules.spectrum.views.spectra_view.QFileDialog.getSaveFileName', return_value=(str(target), '')):
        uv.export()
    rows = csv_rows(target)
    assert 'delta_epsilon_L_mol-1_cm-1' in rows[0] and any(float(r[1]) < 0 for r in rows[1:] if len(r) > 1)
    water = data / 'orca601' / 'h2o_tddft.out'
    window.display_output(water.read_text(encoding='utf-8'), water.name, False, str(water))
    assert uv.kind.isVisibleTo(uv) and uv.plot.mode == 'cd' and 'ахиральна' in uv.summary.text()
    uv.plot.grab()
    no_cd = water.read_text(encoding='utf-8').replace('CD SPECTRUM', 'XX SPECTRUM')
    window.display_output(no_cd, 'no_cd.out', False)
    assert not uv.kind.isVisibleTo(uv) and uv.plot.mode == 'uv' and uv.table.isColumnHidden(uv.R_COLUMN)
    uv.kind.setCurrentIndex(0)


def test_forces_of_the_optimization_steps(window, app):
    # the Cartesian gradient of every ORCA cycle; with «Силы на атомах» on, the step chosen in the
    # drawer shows minus its gradient
    show_model(window, app)
    lines = (Path(__file__).parents[1] / 'data' / 'orca_cclib' / 'dvb_gopt_orca6.0.out').read_text(encoding='utf-8').split('\n')
    out, n = [], 0
    for line in lines:
        if line.startswith('CARTESIAN COORDINATES (ANGSTROEM)') and n < 3:
            n += 1
            out.append(f'*                GEOMETRY OPTIMIZATION CYCLE {n}            *')
        out.append(line)
    window.display_output('\n'.join(out), 'dvb_gopt.out', False)
    assert window.output.steps[1].gradient is not None and window.property_tool.steps_have_gradient()
    # chosen with the steps closed and no gradient of the last geometry — the steps open at the last step with forces
    props = window.result_properties
    window.result_properties = None if props is None else __import__('dataclasses').replace(props, gradient=None)
    try:
        window.property_tool.choose_overlay('forces', True)
        app.processEvents()
        assert window.browsing and window.property_tool.browsed_step_gradient() is not None
        assert window.property_tool.result_overlay(window.viewer.molecule)['forces']
    finally:
        window.property_tool.choose_overlay('forces', False)
        window.result_properties = props
        window.trajectory_tool.set_trajectory_open(False)
    window.trajectory_tool.set_trajectory_open(True)
    app.processEvents()
    window.drawer.select(1)
    window.property_tool.choose_overlay('forces', True)
    try:
        shown = window.property_tool.result_overlay(window.viewer.molecule)
        gradient = window.output.steps[1].gradient
        assert shown is not None and len(shown['forces']) == 20
        largest = max(range(20), key=lambda i: sum(g * g for g in gradient[i]))
        force = shown['forces'][largest]
        assert sum(f * f for f in force) == pytest.approx(sum(g * g for g in gradient[largest]), rel=1e-9)
        window.viewer.grab()
    finally:
        window.property_tool.choose_overlay('forces', False)
        window.trajectory_tool.set_trajectory_open(False)


def test_drawer_page_of_vibrations(window, app):
    # the page «Частоты» of the drawer — the vibrations of the result, the chosen one moves on the model (the
    # structure of the tab is not touched), space stops it; another page stops it; closing shows the structure again
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QKeyEvent

    show_model(window, app)
    window.demo_vibrations()
    app.processEvents()
    drawer = window.drawer
    try:
        assert drawer.modes and drawer.modes_table.rowCount() == len(drawer.modes) and drawer.modes_base is not None
        assert not window.trajectory_button.isHidden()  # ☰ with something to show
        window.trajectory_tool.set_trajectory_open(True, 'modes')
        assert window.stack.currentIndex() == 0 and drawer.page() == 'modes' and window.browsing
        assert drawer.pages.currentIndex() == 1 and drawer.title.text() == 'Колебания'
        own = window.own_molecule()
        animatable = [i for i, m in enumerate(drawer.modes) if m.animatable]
        assert animatable and drawer.mode_current == animatable[0] and drawer.mode_timer.isActive()
        drawer.phase = 1.2
        drawer._emit_mode()
        moved = window.viewer.molecule
        assert [a.position for a in moved.atoms] != [a.position for a in drawer.modes_base.atoms]
        assert window.own_molecule() is own
        window.eventFilter(window.viewer, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier))
        assert not drawer.mode_timer.isActive()
        if len(animatable) > 1:
            window.eventFilter(window.viewer, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier))
            assert drawer.mode_current == animatable[0] + 1
        # «Перейти в Спектр» of the page — Spectrum on «Колебания и ИК»; the icon of Compass there brings the
        # vibration chosen back to the page «Частоты» of the panel
        drawer.spectrum_button.click()
        assert window.stack.currentIndex() == 2 and window.result_tabs.currentIndex() == window.vibrations_tab
        assert window.vibrations.compass_button.property('quail_icon') == 'compass'
        assert window.density_compass_button.property('quail_icon') == 'compass'
        assert window.uv_panel.hole_button.property('quail_icon') == 'compass'
        last = animatable[-1]
        window.vibrations.table.selectRow(last)
        window.vibrations.compass_button.click()
        assert window.stack.currentIndex() == 0 and drawer.page() == 'modes' and drawer.mode_current == last
        assert window.open_spectrum_for('conformers') == window.vibrations_tab  # nothing of it in Spectrum: the tab stays
        window.navigate(0)
        window.trajectory_tool.set_trajectory_open(True, 'modes')
        drawer.set_page('steps')
        assert drawer.pages.currentIndex() == 0 and not drawer.mode_timer.isActive()
        window.trajectory_tool.set_trajectory_open(False)
        assert not window.browsing and window.molecule == own  # the structure of the tab again (the table rebuilds it)
    finally:
        window.trajectory_tool.set_trajectory_open(False)
        for d in window.all_documents():
            d.dirty = False
        window.dirty = False


def test_reaction_diagram_window(window, app, tmp_path):
    # Spectrum → «Диаграмма реакции»: a result as a stage, a typed transition state, another result;
    # ΔE and ΔG, renaming and moving, PNG / SVG / CSV, saving and opening the diagram
    from modules.spectrum.analysis import reaction

    data = Path(__file__).parents[1] / 'data' / 'psi4' / 'dvb_ir_rhf_psi4-1.7.out'
    window.open_output_path(str(data), show=False)
    assert window.reaction_button.isEnabled()
    w = window.add_result_to_reaction()
    try:
        assert window.reaction_diagram() is w and len(w.stages) == 1
        first = w.stages[0].species[0]
        assert first.formula == 'C10H10'
        w.add_typed(reaction.typed_species('TS', first.energy + 0.03, 0.19, 0.2, 0.16, formula='C10H10', ts=True))
        assert w.add_files([str(data)]) == []
        assert [s.kind for s in w.stages] == ['min', 'ts', 'min']
        r = w.refresh()
        assert r.barriers and r.barriers[0].forward == pytest.approx(0.03 * 627.5094740631, rel=1e-9)
        assert r.values[2] == pytest.approx(0.0, abs=1e-9)
        w.quantity.setCurrentIndex(w.quantity.findData('G'))
        app.processEvents()
        assert w.result.quantity == 'G' and w.result.values[2] == pytest.approx(0.0, abs=1e-9)
        assert '‡' in w.summary.text()
        assert 'k прямой' in w.summary.text() and 't½' in w.summary.text() and w.rates_button.isEnabled()
        header, body = w.rate_rows()
        assert header[0] == 'T, K' and [row[0] for row in body if row[3] == 'прямое'][:2] == ['200', '250']
        assert len({row[0] for row in body}) == 10  # 200–600 K and the chosen 298.15 K
        w.rename(1, 'Переходное')
        assert w.reference.itemText(1) == 'Переходное'
        w.move(1, 1)
        assert w.stages[2].label == 'Переходное' and w.result.kinds == ('min', 'min', 'ts')
        for name in ('d.png', 'd.svg', 'd.csv'):
            w.save_picture(tmp_path / name)
            assert (tmp_path / name).stat().st_size > 50
        w.save_diagram(tmp_path / 'r.json')
        w.remove(0)
        assert len(w.stages) == 2
        assert w.open_diagram(tmp_path / 'r.json') == [] and len(w.stages) == 3
        assert w.quantity.currentData() == 'G' and w.stages[2].kind == 'ts'
    finally:
        w.close()


def test_one_row_of_tabs_for_compass_sextant_and_spectrum(window, app):
    # every molecule tab keeps its own settings of the calculation and its own result, in all the sections;
    # from «Компас · Кристалл» Sextant brings the molecule tabs back; the orbitals of a result are offered in Compass at
    # once. The rows of the tabs above Sextant and Spectrum are gone (a visible tab is a project) — the tabs
    # are switched by switch_document
    data = Path(__file__).parents[1] / 'data'
    show_model(window, app)
    water = window.molecule
    assert len(window.documents) == 1 and not hasattr(window, 'tab_mirrors')
    window.task.setCurrentIndex(window.task.findText('Энергия'))
    window.open_output_path(str(data / 'gaussian' / 'dvb_ir_g16.log'), show=False)
    assert len(window.documents) == 2 and window.current_document == 1  # the result in a new tab
    assert window.molecule.formula == 'C10H10' and window.output.program == 'Gaussian 16'
    window.task.setCurrentIndex(window.task.findText('Оптимизация + частоты'))
    window.switch_document(0)
    assert window.current_document == 0 and window.molecule == water
    assert window.output is None and 'результата ещё нет' in window.result_summary.text()
    assert window.task.currentText() == 'Энергия'  # the settings of this tab
    window.switch_document(1)
    assert window.current_document == 1 and window.output.program == 'Gaussian 16'
    assert window.task.currentText() == 'Оптимизация + частоты' and window.result_tabs.currentIndex() == 1
    # from the crystals Sextant works on the molecules
    window.crystal_tool.set_compass_mode('crystal')
    assert window.document_kind == 'crystal'
    window.navigate(1)
    assert window.document_kind == 'molecule' and window.current_document == 1 and window.molecule.formula == 'C10H10'
    window.navigate(0)
    # a new tab, closed again
    window.new_document()
    assert len(window.documents) == 3 and window.current_document == 2
    window.close_document(2)
    assert len(window.documents) == 2 and window.current_document == 1
    # orbitals of a result: offered in Compass
    window.switch_document(0)
    import shutil
    from tempfile import mkdtemp

    folder = Path(mkdtemp())
    out = folder / 'dvb.out'
    shutil.copy(data / 'orbitals' / 'dvb_sp_dft_orca6.0.out', out)
    window.open_output_path(str(out), show=False)
    window.surface_tool.fill_surface_menu(window.surface_menu)
    assert any(a.text() == 'Орбитали и плотность…' for a in window.surface_menu.actions())
    assert all(window.drawer.tab_bar.isTabEnabled(k) for k in (2, 3, 4))  # its pages; three
    for d in window.all_documents():
        d.dirty = False
    window.dirty = False


def test_excitation_analysis_in_spectrum(window, app, tmp_path):
    # UV-Vis «Анализ возбуждений» and «Дырка и электрон на модели» for the user's TD-DFT of benzaldehyde (ORCA,
    # 10 states): a fake Multiwfn prints the outputs recorded with Multiwfn 2026.7.15 (S1, S3 — every other state gets
    # the S1 output) and writes grids for the hole and the electron
    from modules.spectrum.readers.orca_spectra import read_absorption

    data = Path(__file__).parents[1] / 'data' / 'multiwfn'
    cube = data / 'water_fchk_homo.cub.gz'
    fake = fake_program(tmp_path, f'''
if answer(1) == '4':
    cat({q(data / "benzaldehyde_orca_delta_r_s1_2026.7.15.txt")})
    sys.exit(0)
if answer(3) == '3':
    cat({q(data / "benzaldehyde_orca_hole_s3_2026.7.15.txt")})
else:
    cat({q(data / "benzaldehyde_orca_hole_s1_2026.7.15.txt")})
gunzip({q(cube)}, 'hole.cub')
gunzip({q(cube)}, 'electron.cub')
''')
    out = data / 'benzaldehyde_cam-b3lyp_orca.out'
    molden = tmp_path / 'benz.molden.input'
    molden.write_text('[Molden Format]\n', encoding='utf-8')
    panel = window.uv_panel
    shown = []
    old = (panel.analysis_source, panel.analysis_show)
    panel.set_analysis(lambda: (fake, molden, out, 1), lambda h, e, t: shown.append((h, e, t)) or True)
    try:
        panel.load(read_absorption(out.read_text(encoding='utf-8')))
        assert panel.analysis_button.isVisibleTo(panel) and panel.table.isColumnHidden(5)
        found = panel.analyse()
        assert found[3]['d'] == 1.111 and found[1]['delta_r'] == pytest.approx(1.749411)
        assert not panel.table.isColumnHidden(5) and panel.table.item(2, 5).text() == '1.111'
        assert panel.table.item(0, 12).text() == 'локальное'
        rows = csv_rows(tmp_path / 'Анализ' / 'benz_excitations.csv')
        assert len(rows) == 11 and rows[3][4] == '1.111' and rows[1][8] == '1.749'
        # only the states chosen; the others keep their indices
        panel.analysis_scope.setCurrentIndex(panel.analysis_scope.findData('chosen'))
        panel.table.selectRow(4)
        assert panel.chosen_states() == [5]
        assert set(panel.analyse()) == {5} and panel.table.item(2, 5).text() == '1.111'
        panel.analysis_scope.setCurrentIndex(panel.analysis_scope.findData('bright'))
        assert all(panel.excitations[k - 1].fosc >= 0.01 for k in panel.chosen_states())
        panel.analysis_scope.setCurrentIndex(0)
        panel.table.selectRow(2)
        assert panel.hole_on_model() and len(shown) == 1 and shown[0][2].startswith('Состояние')
        # the hole and the electron on the Compass model
        assert window.surface_tool.show_excitation(shown[0][0], shown[0][1], shown[0][2])
        assert window.surface_source['kind'] == 'excitation' and len(window.viewer.surface['meshes']) == 2
    finally:
        panel.analysis_source, panel.analysis_show = old
        window.surface_tool.clear_surface()


def test_charge_transfer_window(window, app, tmp_path):
    # UV-Vis «Перенос заряда…» for S1 of the user's benzaldehyde: a fake Multiwfn prints the IFCT recorded with
    # Multiwfn 2026.7.15 (18 → 8) and writes the transition matrices recorded (18 → 2: −1 fragments, 4 the atoms); the
    # first fragment from the atoms selected in Compass (CHO), the ring the rest; the summary, the table, the heat map
    # by fragments and by atoms, the CSV in «Анализ»
    from modules.spectrum.readers.orca_spectra import read_absorption

    data = Path(__file__).parents[1] / 'data' / 'multiwfn'
    fake = fake_program(tmp_path, f'''
if answer(1) == '8':
    cat({q(data / "exc_ifct2_s1.txt")})
    sys.exit(0)
if answer(6) == '-1':
    cp({q(data / "exc_heatmap2_fragments__tmat.txt")}, 'tmat.txt')
else:
    cp({q(data / "exc_heatmap2_atoms__tmat.txt")}, 'tmat.txt')
''')
    out = data / 'benzaldehyde_cam-b3lyp_orca.out'
    molden = tmp_path / 'benz.molden.input'
    molden.write_text('[Molden Format]\n', encoding='utf-8')
    panel = window.uv_panel
    symbols = ['O', 'C'] + ['C'] * 6 + ['H'] * 6
    old = (panel.analysis_source, panel.analysis_show, panel.transfer_context)
    panel.set_analysis(lambda: (fake, molden, out, 1), lambda h, e, t: True)
    panel.set_transfer(lambda: (symbols, lambda: [0, 1, 8]))
    try:
        panel.load(read_absorption(out.read_text(encoding='utf-8')))
        assert panel.transfer_button.isVisibleTo(panel)
        panel.table.selectRow(0)
        dialog = panel.charge_transfer()
        assert dialog is not None and dialog.state == 1
        assert not dialog.compute()  # no fragment yet
        assert 'фрагмент' in dialog.status.text()
        dialog.take_selection()
        assert dialog.fragment_edits[0].text() == 'O1, C2, H9'  # with the elements
        assert dialog.compute()
        assert dialog.result['ct'] == 35.388 and dialog.parts[1] == [3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14]
        assert '35.4' in dialog.summary.text() and '14.8' in dialog.summary.text()
        assert dialog.table.rowCount() == 2 and dialog.table.item(0, 2).text() == '85.44'
        assert dialog.table.item(1, 1).text() == 'C3–C8, H10–H14' and dialog.table.item(0, 4).text() == '-0.148'
        assert 'Ф1 → Ф2' in dialog.transfers.text()
        assert dialog.heat.matrix.shape == (2, 2) and dialog.heat.labels == ['Ф1', 'Ф2']
        dialog.view.setCurrentIndex(dialog.view.findData('atoms'))
        assert dialog.heat.matrix.shape == (14, 14) and dialog.heat.labels[:2] == ['O1', 'C2']
        dialog.heat.resize(320, 320)
        dialog.heat.grab()
        rows = csv_rows(tmp_path / 'Анализ' / 'benz_charge_transfer_S1.csv')
        assert len(rows) == 4 and rows[1][0] == 'Ф1' and rows[1][2] == '85.44'
        dialog.close()
    finally:
        panel.analysis_source, panel.analysis_show = old[:2]
        panel.set_transfer(old[2])


def test_history_of_calculations_window(window, tmp_path, monkeypatch):
    # «Расчёт → История расчётов…» — the calculations with their state now; a finished one opens its result,
    # one on a server can be taken up again («Проверить на сервере»), a missing folder is said
    from azimuth.core import Calculation
    from modules.sextant import history, runner

    saved = window.preferences.value(history.KEY, '')
    try:
        done = tmp_path / 'done'
        done.mkdir()
        (done / 'w.out').write_text('...\n****ORCA TERMINATED NORMALLY****\n')
        far = tmp_path / 'far'
        far.mkdir()
        (far / 'w.out').write_text('')
        (far / 'job.json').write_text('{"job": "7", "folder": "~/azimuth/far"}')
        items = []
        for folder, place in ((tmp_path / 'gone', ''), (far, 'serv3'), (done, '')):
            spec = runner.JobSpec('orca', folder, ('orca',), folder / 'w.out', {})
            items = history.add(items, history.record(spec, 'orca', Calculation(), 'H₂O · ORCA', place))
        history.save(window.preferences, [dict(d, state='') for d in items])
        opened = []
        monkeypatch.setattr(window.opening_tool, 'open_path', lambda path: opened.append(path))
        dialog = window.run_tool.show_history()
        assert dialog.table.rowCount() == 3
        assert dialog.states == ['finished', 'server', 'missing']
        dialog.table.selectRow(0)
        assert dialog.open_button.isEnabled() and not dialog.resume_button.isEnabled()
        dialog.open_button.click()
        assert opened == [str(done / 'w.out')]
        dialog.table.selectRow(1)
        assert dialog.resume_button.isEnabled() and not dialog.open_button.isEnabled()
        dialog.table.selectRow(2)
        assert not dialog.folder_button.isEnabled()
        dialog.forget_button.click()
        assert dialog.table.rowCount() == 2
        # «Очистить список» — after the question; the folders stay
        from PySide6.QtWidgets import QMessageBox

        assert dialog.clear_button.isEnabled()
        monkeypatch.setattr(QMessageBox, 'question', lambda *a, **k: QMessageBox.StandardButton.No)
        assert dialog.clear() == 0 and dialog.table.rowCount() == 2
        monkeypatch.setattr(QMessageBox, 'question', lambda *a, **k: QMessageBox.StandardButton.Yes)
        assert dialog.clear() == 2 and history.load(window.preferences) == []
        assert dialog.table.isHidden() and not dialog.empty.isHidden() and not dialog.clear_button.isEnabled()
        assert done.is_dir() and far.is_dir()
        dialog.close()
    finally:
        window.preferences.setValue(history.KEY, saved)


def test_density_of_states_tab(window, app, tmp_path):
    # «Плотность состояний» — for a result with orbitals; read when the tab is opened; the elements as fragments,
    # the atoms chosen in Compass and the rest, OPDOS of two, the export as CSV
    source = Path(__file__).parents[2] / 'examples' / '6-orbitals' / 'divinylbenzene_orbitals_orca6.out'
    out = tmp_path / 'dvb.out'
    out.write_text(source.read_text(encoding='utf-8'), encoding='utf-8')
    window.display_output(out.read_text(encoding='utf-8'), out.name, True, str(out))
    tabs, panel = window.result_tabs, window.dos_panel
    assert tabs.isTabVisible(window.dos_tab) and panel.data is None  # not read before the tab is opened
    tabs.setCurrentIndex(window.dos_tab)
    app.processEvents()
    data = panel.data
    assert data is not None and [name for name, _ in data['parts']] == ['C', 'H']
    assert data['homo'] is not None and data['lumo'] > data['homo'] and 'щель' in panel.note.text()
    window.viewer.selected = [0, 1]
    panel.fragments.setCurrentIndex(panel.fragments.findData('chosen'))
    assert [name for name, _ in panel.data['parts']] == ['C1–C2', 'остальные']
    panel.opdos.setChecked(True)
    assert panel.data['opdos'] is not None and panel.data['pair_name'] == 'C1–C2 ↔ остальные'
    panel.export(tmp_path / 'dos.csv')
    rows = (tmp_path / 'dos.csv').read_text(encoding='utf-8-sig').splitlines()
    assert len(rows) == 1 + len(panel.data['x']) and 'opdos' in rows[0]
    window.viewer.selected = []
    panel.opdos.setChecked(False)
    panel.fragments.setCurrentIndex(0)
    tabs.setCurrentIndex(0)


def test_job_window_before_any_calculation_and_the_note_of_frequencies(window, app):
    # the user — «Если молекула еще не построена и в секстанте нажать в Расчет -> Окно расчета — то панель
    # входного файла станет пустой… пусть будет прочерк»; «Частоты и термохимия» — the note under the task was cut off
    window.show()
    window.navigate(1)
    app.processEvents()
    assert window.job is None
    window.show_job_window()
    app.processEvents()
    jw = window.job_window
    assert jw.heading.text() == '—' and 'Расчёта ещё не было' in jw.status.text()
    assert not jw.stop_button.isEnabled() and not jw.output_button.isEnabled() and jw.bar.isHidden()
    assert not jw.input_button.isHidden()
    jw.input_button.click()
    app.processEvents()
    assert window.preview_card.isVisible()
    window.task.setCurrentIndex(window.task.findText('Частоты и термохимия'))
    app.processEvents()
    note = window.task_note
    assert note.isVisible() and 'без оптимизации' in note.text()
    assert note.height() >= note.heightForWidth(note.width())  # all its lines at its width
    window.task.setCurrentIndex(0)
    window._job_shown = False


def test_ir_scaling_factor_and_csv_for_russian_excel(window, tmp_path):
    # the factor of NIST CCCBDB for the method and basis of the result (B3LYP/STO-3G of the Gaussian test
    # data: 0.892) is offered; ticked, the spectrum (not the table of modes) is scaled and says so; the CSV of the
    # spectrum follows «Таблицы CSV» — «;» and the decimal comma for a Russian Excel
    import shutil

    from modules.spectrum.wavefunction import field_tables

    out = tmp_path / 'dvb_ir.log'
    shutil.copy(Path(__file__).parents[1] / 'data' / 'gaussian' / 'dvb_ir_g16.log', out)
    window.open_output_path(str(out), show=False)
    v = window.vibrations
    assert v.scale_suggestion is not None and v.scale_suggestion.factor == 0.892 and v.ir_scale.value() == 0.892
    first = next(m for m in v.modes if m.frequency > 0)
    assert not v.ir_scale_on.isChecked() and v.spectrum.modes[v.modes.index(first)].frequency == first.frequency
    v.ir_scale_on.setChecked(True)
    assert v.spectrum.modes[v.modes.index(first)].frequency == pytest.approx(first.frequency * 0.892)
    assert v.table.item(v.modes.index(first), 1).text() == f'{first.frequency:.2f}'  # the table as in the output
    saved = field_tables.style
    try:
        field_tables.style = 'ru'
        v.spectrum.export(tmp_path / 'ir.csv')
        head, second = (tmp_path / 'ir.csv').read_text(encoding='utf-8-sig').splitlines()[:2]
        assert ';' in head and 'x0.892' in head and ',' in second and '.' not in second
    finally:
        field_tables.style = saved
        v.ir_scale_on.setChecked(False)


def test_raman_spectrum_in_the_vibrations_tab(window, tmp_path):
    # an ORCA result with Raman activities (water, NumFreq) shows «ИК / Раман», the activity and ρ in the
    # table; the plot draws the activities (and the scaled frequencies); the analytic result has no switch and its
    # summary says why
    import shutil

    from modules.spectrum.wavefunction import field_tables

    data = Path(__file__).parents[1] / 'data' / 'raman'
    out = tmp_path / 'h2o_raman.out'
    shutil.copy(data / 'h2o_raman_numfreq_orca.out', out)
    window.open_output_path(str(out), show=False)
    v = window.vibrations
    assert v.ir_kind.isVisibleTo(v) and not v.table.isColumnHidden(4) and not v.table.isColumnHidden(5)
    row = next(i for i, m in enumerate(v.modes) if m.index == 8)
    assert v.table.item(row, 4).text() == '38.998' and v.table.item(row, 5).text() == '0.750'
    assert v.spectrum.kind == 'ir' and v.spectrum.modes[row].intensity == 19.76
    v.ir_kind.setCurrentIndex(v.ir_kind.findData('activity'))
    assert v.spectrum.kind == 'activity' and v.spectrum.modes[row].intensity == 38.997507
    v.table.setCurrentCell(row, 0)
    assert 'деполяризованная' in v.detail.text()
    v.ir_scale_on.setChecked(True)
    try:
        assert v.spectrum.modes[row].intensity == 38.997507  # the factor keeps the Raman values
        v.spectrum.resize(500, 220)
        v.spectrum.grab()
    finally:
        v.ir_scale_on.setChecked(False)
    v.ir_kind.setCurrentIndex(v.ir_kind.findData('intensity'))
    assert max(m.intensity for m in v.spectrum.modes if m.intensity is not None) == pytest.approx(100)
    saved = field_tables.style
    try:
        field_tables.style = 'en'
        v.spectrum.export(tmp_path / 'raman.csv')
        assert 'raman_intensity_relative' in (tmp_path / 'raman.csv').read_text(encoding='utf-8-sig').splitlines()[0]
    finally:
        field_tables.style = saved
    analytic = tmp_path / 'h2o_analytic.out'
    shutil.copy(data / 'h2o_analytic_freq_no_raman_orca.out', analytic)
    window.open_output_path(str(analytic), show=False)
    assert not v.ir_kind.isVisibleTo(v) and v.table.isColumnHidden(4) and v.spectrum.kind == 'ir'
    assert 'NumFreq' in window.output.assessment
    v.ir_kind.setCurrentIndex(0)


def test_mopac_result_in_spectrum(window, tmp_path):
    # a MOPAC result (PM7 frequencies of water, with its .aux) opens in Spectrum: ΔHf in the summary instead of
    # an energy, the three vibrations, MOPAC charges on the model; no total energy, so no reaction diagram
    import shutil

    data = Path(__file__).parents[1] / 'data' / 'mopac'
    for suffix in ('.out', '.aux'):
        shutil.copy(data / f'h2o_pm7_force_thermo{suffix}', tmp_path / f'water{suffix}')
    window.open_output_path(str(tmp_path / 'water.out'), show=False)
    assert window.output.program == 'MOPAC 23.2.5 PM7' and window.output.heat_of_formation == -57.7999
    assert 'теплота образования -57.800 ккал/моль' in window.result_summary.text()
    assert not window.reaction_button.isEnabled()
    assert len(window.vibrations.modes) == 3 and window.vibrations.table.item(0, 2).text() == '—'
    from modules.compass.view.result_overlay import available

    assert 'mopac' in available(window.output.properties)


def test_mopac_orbitals_and_thermochemistry_in_spectrum(window, app, tmp_path):
    # the .aux next to a MOPAC output is its orbital file (Slater functions as Gaussians); the «Термохимия» tab
    # gives ΔHf(T) by MOPAC's formula and checks itself against the THERMO table of MOPAC at its temperatures
    import shutil

    data = Path(__file__).parents[1] / 'data' / 'mopac'
    for suffix in ('.out', '.aux'):
        shutil.copy(data / f'h2o_pm7_force_thermo{suffix}', tmp_path / f'water{suffix}')
    window.open_output_path(str(tmp_path / 'water.out'), show=False)
    assert window.sibling_molden == tmp_path / 'water.aux' and not window.orbitals_button.isHidden()
    # the folder of the result (no analysis yet: the folder of the output itself)
    assert not window.result_folder_button.isHidden() and window.result_folder() == tmp_path
    (tmp_path / 'Анализ').mkdir()
    assert window.result_folder() == tmp_path / 'Анализ'
    dialog = window.open_sibling_orbitals()
    try:
        assert dialog is not None and dialog.orbital_set.zdo and dialog.table.rowCount() == 6
        assert dialog.table.item(3, 6).text() == 'ВЗМО' and dialog.table.item(4, 6).text() == 'НСМО'
    finally:
        dialog.close()
    tabs = window.result_tabs
    assert tabs.isTabVisible(window.thermo_tab)
    # the tabs of the result are shown by the bar in the top row (with the tabs of the molecules after it);
    # under common tabs — «Результат» (the energies, the thermochemistry), «Спектры» with one tab shown is
    # that tab («Колебания и ИК»); the tabs of the current group are a second bar over the page
    assert tabs.isTabVisible(window.vibrations_tab)  # frequencies — the tab is there
    shown = [i for i in range(tabs.count()) if tabs.isTabVisible(i)]
    assert sorted(i for _, members in tabs.entries for i in members) == shown
    titles = [tabs.header.tabText(k) for k in range(tabs.header.count())]
    assert titles[0] == 'Результат' and 'Колебания и ИК' in titles and 'Спектры' not in titles
    assert tabs.entry_of(window.thermo_tab) == tabs.entry_of(0) == 0 and tabs.entry_of(window.uv_tab) == -1
    # the bar is as wide as its tabs (on the user's Mac it stayed one tab wide: 159 of 416 px)
    assert tabs.header.width() == sum(tabs.header.tabSizeHint(k).width() for k in range(tabs.header.count()))
    assert not tabs.tabBar().isVisible()
    tabs.setCurrentIndex(0)
    # no second bar — the tabs of the group shown are a drop-down list over the page, titled by the one
    # shown (isHidden, not isVisibleTo: the page of Spectrum is not the current page of the stack in this test)
    chooser = tabs.chooser
    assert tabs.subheader.isHidden() and not chooser.isHidden() and chooser.currentText() == 'Энергии и частоты'
    names = [chooser.itemText(k) for k in range(chooser.count())]
    assert names[0] == 'Энергии и частоты' and 'Термохимия' in names
    chooser.setCurrentIndex(names.index('Термохимия'))
    chooser.activated.emit(names.index('Термохимия'))  # chosen in the list
    assert tabs.currentIndex() == window.thermo_tab and window.use_geometry.isHidden()
    assert chooser.currentText() == 'Термохимия'
    tabs.header.setCurrentIndex(titles.index('Колебания и ИК'))
    assert tabs.currentIndex() == window.vibrations_tab and chooser.isHidden()  # one page: no list
    tabs.header.setCurrentIndex(0)  # back to the group: on the tab chosen there last
    assert tabs.currentIndex() == window.thermo_tab and chooser.currentText() == 'Термохимия'
    panel = window.thermo_panel
    assert panel.sigma.value() == 2 and panel.multiplicity.value() == 1 and not panel.multiplicity_missing
    panel.temperature.setValue(298.0)
    last = panel.table.rowCount() - 1
    assert 'ΔHf(T)' in panel.table.item(last, 0).text() and panel.table.item(last, 2).text() == '-57.800'
    assert 'MOPAC при 298.00 К' in panel.notes.text() and 'S = 45.051' in panel.notes.text()
    panel.temperature.setValue(398.0)
    assert panel.table.item(last, 2).text() == '-56.983' and 'S = 47.412' in panel.notes.text()
    panel.temperature.setValue(298.15)
    assert 'поставьте одну из этих T' in panel.notes.text()


def test_spectrum_tools(window, app, tmp_path):
    # the isotope cluster, the energies of several results and the Boltzmann shares — in Spectrum
    from modules.spectrum.wavefunction import field_tables

    iso = window.spectrum_tools.show_isotopes('CH2Cl2')
    found = iso.show_pattern()
    assert [s for s, _, _ in found[:3]] == [0, 1, 2] and iso.peaks.item(0, 0).text() == 'M'
    assert 'Моноизотопная масса: 83.95' in iso.masses.text()
    assert iso.show_pattern('Xx2') is None and iso.peaks.rowCount() == 0
    iso.show_pattern('CH2Cl2')
    assert field_tables.read_csv(iso.save_csv(str(tmp_path / 'iso.csv')))[0] == ['Пик', 'm/z', '%']
    iso.close()
    box = window.spectrum_tools.boltzmann_dialog()
    box.text.setPlainText('a -76.4321\nb -76.4300')
    rows = box.compute()
    assert rows[0][3] > 0.9 and box.table.rowCount() == 2
    box.close()
    from modules.spectrum.analysis.reaction import typed_species

    made = {'x.out': typed_species('x', -10.0, formula='H2O'), 'y.out': typed_species('y', -9.999, formula='H2O')}
    from modules.spectrum.views.tools_view import EnergiesDialog

    files = EnergiesDialog(window)
    result = files.fill(['x.out', 'y.out'], read=lambda p, label: made[p])
    assert result['by'] == 'E' and files.table.rowCount() == 2 and files.table.item(1, 5).text() == '0.63'
    files.close()
    # «Равновесие двух форм…»: the same real result (ORCA 6.0.1, water, Opt Freq) as both forms — K = 1; then the
    # symmetry number of B halved by hand: K = 2 (q_rot ∝ 1/σ), 66.7 % of B
    water = str(Path(__file__).parents[1] / 'data' / 'orca601' / 'h2o_optfreq.out')
    pair = window.spectrum_tools.equilibrium_dialog([water, water])
    assert pair.sigmas[0].value() == 2 and pair.mirrors[0].value() == 1  # C2v
    assert pair.table.rowCount() == 10 and pair.table.item(0, 0).text() == '200'
    at = next(r for r in range(10) if pair.table.item(r, 0).text() == '298.15')
    assert pair.table.item(at, 2).text() == '1' and pair.table.item(at, 4).text() == '50.0'
    pair.sigmas[1].setValue(1)
    assert pair.table.item(at, 2).text() == '2' and pair.table.item(at, 4).text() == '66.7'
    assert pair.factors.item(2, 1).text() == '2' and pair.factors.rowCount() == 7
    pair.mirrors[0].setValue(2)
    assert pair.table.item(at, 2).text() == '1'
    pair.close()


def test_experiment_and_conformers_over_the_spectra(window, tmp_path):
    # a measured spectrum over the computed
    # one with how alike they are, the fit (the factor of the frequencies, the shift of the energies) and the average
    # of conformers by their Boltzmann shares
    import shutil

    import numpy as np

    from modules.spectrum.analysis.experiment import shifted_excitations
    from modules.spectrum.analysis.ir_spectrum import broaden

    data = Path(__file__).parents[1] / 'data'
    ir = data / 'gaussian' / 'dvb_ir_g16.log'
    window.display_output(ir.read_text(encoding='utf-8'), ir.name, False, str(ir))
    vib = window.vibrations
    assert vib.source_path == str(ir)
    vib.ir_scale_on.setChecked(False)
    vib.ir_width.setValue(20)
    x, y = broaden(vib.spectrum_modes(vib.modes), 20)
    measured = tmp_path / 'ir.csv'  # «measured»: the computed × 0.97, as %T, decimal commas and «;»
    measured.write_text('cm-1;%T\n' + ''.join(f'{a * 0.97:.2f};{100 * 10 ** (-b / y.max()):.4f}\n'.replace('.', ',')
                                             for a, b in zip(x, y) if 400 <= a * 0.97 <= 4000), encoding='utf-8')
    said = vib.open_experiment(str(measured))
    assert said and vib.spectrum.experiment is not None
    # fitted at once
    assert vib.ir_scale_on.isChecked() and abs(vib.ir_scale.value() - 0.97) <= 0.003 and 'множитель' in said
    assert vib.spectrum.score() > 0.95
    vib.ir_scale.setValue(1.0)
    assert vib.fit_experiment() and abs(vib.ir_scale.value() - 0.97) <= 0.003  # and again from the menu
    for smooth in (0, 1):
        vib.ir_style.setCurrentIndex(smooth)
        vib.spectrum.resize(600, 260)
        vib.spectrum.grab()
    menu = vib.extras_menu()
    texts = [a.text() for a in menu.actions()]
    menu.close()
    assert 'Подогнать к эксперименту' in texts and 'Среднее по конформерам…' in texts
    copies = [shutil.copy(ir, tmp_path / name) for name in ('conf-a.log', 'conf-b.log')]
    assert vib.build_conformers(copies, 298.15)
    modes, name = vib.spectrum.ensemble
    assert 'среднее по 2' in name
    total = sum(m.intensity for m in modes)
    assert total == pytest.approx(sum(m.intensity for m in vib.spectrum_modes(vib.modes) if m.intensity is not None))
    vib.spectrum.grab()
    dialog = vib.open_conformers()
    assert dialog.paths == [str(ir)] and not dialog.build_button.isEnabled()
    built = []
    dialog.build.connect(lambda *args: built.append(args))
    dialog.accept()  # «Закрыть»
    assert not built  # and no message (a QMessageBox would fail the test at its end)
    vib.clear_conformers()
    vib.clear_experiment()
    assert vib.spectrum.ensemble is None and vib.spectrum.experiment is None

    td = data / 'orca_cclib' / 'dvb_td_orca6.0.out'
    window.display_output(td.read_text(encoding='utf-8'), td.name, False, str(td))
    uv = window.uv_panel
    x, y = uv.plot.curve(shifted_excitations(uv.excitations, -0.3))
    measured = tmp_path / 'uv.txt'
    measured.write_text('nm absorbance\n' + ''.join(f'{a:.2f} {b:.5g}\n' for a, b in zip(x, y)), encoding='utf-8')
    assert uv.open_experiment(str(measured)) and abs(uv.plot.shift_ev + 0.3) <= 0.011  # fitted at once
    uv.plot.resize(600, 260)
    uv.plot.grab()
    menu = uv.extras_menu()
    assert any(a.text().startswith('Убрать сдвиг') for a in menu.actions())
    menu.close()
    assert uv.build_conformers([shutil.copy(td, tmp_path / n) for n in ('a.out', 'b.out')], 298.15)
    assert uv.plot.ensemble and np.isfinite(uv.plot.ensemble_curve()[1]).all()
    uv.plot.grab()
    window.display_output(td.read_text(encoding='utf-8'), td.name, False, str(td))
    assert uv.plot.shift_ev == 0  # a new result: no shift of another one


def test_a_measured_spectrum_from_nist(window, monkeypatch):
    # «Найти в NIST…» with a fake server — the formula of the result searched for, the compound, its spectrum laid over
    # the plot
    import time

    from PySide6.QtWidgets import QApplication

    from modules.spectrum.analysis.ir_spectrum import broaden
    from modules.spectrum.readers import nist

    data = Path(__file__).parents[1] / 'data'
    ir = data / 'gaussian' / 'dvb_ir_g16.log'
    window.display_output(ir.read_text(encoding='utf-8'), ir.name, False, str(ir))
    vib = window.vibrations
    assert vib.source_formula == 'C10H10'
    x, y = broaden(vib.spectrum_modes(vib.modes), 20)
    keep = (x >= 400) & (x <= 4000)
    jcamp = ('##TITLE=divinylbenzene\n##STATE=gas\n##ORIGIN=test\n##XUNITS=1/CM\n##YUNITS=ABSORBANCE\n'
             '##XYPOINTS=(XY..XY)\n' + ''.join(f'{a:.2f}, {b:.6g}\n' for a, b in zip(x[keep], y[keep])) + '##END=\n')
    asked = []
    monkeypatch.setattr(nist, 'search', lambda text: asked.append(text) or [('C1321740', 'Divinylbenzene')])
    monkeypatch.setattr(nist, 'spectra', lambda ident, kind: asked.append((ident, kind)) or [(0, 'gas · test', jcamp)])
    shown = vib.open_nist()

    def settled(seconds=5):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            QApplication.processEvents()
            if not shown.busy and shown.spectra.rowCount():
                return True
            time.sleep(0.01)
        return False

    assert settled()
    assert asked == ['C10H10', ('C1321740', 'IR')] and shown.compounds.item(0, 0).text() == 'Divinylbenzene'
    assert shown.spectra.item(0, 1).text() == 'gas · test'
    assert shown.use()
    assert vib.spectrum.experiment is not None and vib.spectrum.experiment[2] == 'Divinylbenzene · NIST'
    assert vib.spectrum.score() > 0.99


def test_vcd_and_emission(window, tmp_path):
    # the VCD of the vibrations — a signed spectrum, the column
    # R; the emission of an optimization of an excited state — the view «Излучение» of the tab UV-Vis
    from unittest import mock

    from tests.spectrum.test_vcd import ORCA_VCD

    data = Path(__file__).parents[1] / 'data'
    text = (data / 'orca601' / 'h2o_optfreq.out').read_text(encoding='utf-8')
    at = text.index('IR SPECTRUM')
    window.display_output(text[:at] + ORCA_VCD + '\n' + text[at:], 'h2o_vcd.out', False)
    vib = window.vibrations
    assert 'vcd' in vib.kinds() and vib.ir_kind.isVisibleTo(vib) and not vib.table.isColumnHidden(6)
    vib.ir_kind.setCurrentIndex(vib.ir_kind.findData('vcd'))
    assert vib.spectrum.signed and 'ВКД' in vib.spectrum.axis_title()
    for smooth in (0, 1):
        vib.ir_style.setCurrentIndex(smooth)
        vib.spectrum.resize(600, 260)
        vib.spectrum.grab()
    vib.ir_style.setCurrentIndex(0)
    assert vib.spectrum.limits()[1] == 13.12  # sticks: the largest |R|
    vib.ir_kind.setCurrentIndex(0)

    opt = data / 'orca611' / 'ch2o_excited_opt_libxc_b3lyp.out'
    window.display_output(opt.read_text(encoding='utf-8'), opt.name, False, str(opt))
    uv = window.uv_panel
    assert uv.emission is not None and uv.kind.isVisibleTo(uv)
    uv.kind.setCurrentIndex(uv.kind.findData('em'))
    assert uv.emission_plot.isVisibleTo(uv) and not uv.plot.isVisibleTo(uv)
    assert 'Флуоресценция S1' in uv.summary.text() and 'стоксов сдвиг' in uv.summary.text()
    uv.emission_plot.resize(600, 260)
    uv.emission_plot.grab()
    target = tmp_path / 'emission.csv'
    with mock.patch('modules.spectrum.views.spectra_view.QFileDialog.getSaveFileName', return_value=(str(target), '')):
        uv.export()
    rows = csv_rows(target)
    assert rows[0][:3] == ['wavelength_nm', 'absorption_relative', 'emission_relative'] and len(rows) > 100
    uv.kind.setCurrentIndex(0)
    assert uv.plot.isVisibleTo(uv) and not uv.emission_plot.isVisibleTo(uv)
