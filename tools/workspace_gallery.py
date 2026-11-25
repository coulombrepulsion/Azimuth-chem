"""Снимки Секстанта и Спектра: каждая программа и задача Секстанта, каждая вкладка Спектра на примерах.

Запуск из папки программы: .venv/bin/python tools/workspace_gallery.py (Windows: .venv\\Scripts\\python ...)

Окно программы откроется на экране примерно на полминуты — ничего не нажимайте. Настройки — свои, во временном файле:
настройки пользователя не меняются. Снимки — в .gallery/workspaces/ (PNG); по ним правится вид окон (как
tools/dialog_gallery.py для диалогов).
"""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('AZIMUTH_SETTINGS_FILE', os.path.join(tempfile.mkdtemp(prefix='azimuth-gallery-'), 'settings.ini'))
os.environ['AZIMUTH_MULTIWFN_SEARCH'] = '0'

from PySide6.QtWidgets import QApplication  # noqa: E402

OUT = ROOT / '.gallery' / 'workspaces'
SIZE = (1360, 820)  # a laptop: the window of the user's screenshots
RESULTS = (
    'examples/teaching-demo.out',
    'examples/4-vibrations/divinylbenzene_freq_gaussian16.log',
    'examples/5-uv-vis-nmr/divinylbenzene_tddft_orca6.out',
    'examples/5-uv-vis-nmr/divinylbenzene_nmr_orca6.out',
    'examples/2-optimization/divinylbenzene_opt_psi4.out',
    'tests/data/mopac/h2o_pm7_force_thermo.out',
)


def settle(app, rounds=6):
    for _ in range(rounds):
        app.processEvents()


def shot(window, app, name):
    settle(app)
    path = OUT / f'{name}.png'
    window.grab().save(str(path))
    print(path.relative_to(ROOT), flush=True)


def main():
    from azimuth.app import STYLE, Studio
    from azimuth.core import EXAMPLES, read_xyz
    from azimuth.i18n import combo_key

    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob('*.png'):
        old.unlink()
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    window = Studio(example=True, probe_machine=False)
    window.resize(*SIZE)
    window.show()
    settle(app, 20)
    window.dirty = False
    window.load_molecule(read_xyz(EXAMPLES['Вода · H₂O']))
    window.navigate(1)
    for kind in ('orca', 'gaussian', 'psi4', 'xtb', 'mopac'):
        window.program.setCurrentIndex(window.program.findData(kind))
        settle(app)
        for i in range(window.task.count()):
            window.task.setCurrentIndex(i)
            shot(window, app, f'sextant_{kind}_{i + 1}_{combo_key(window.task).split()[0]}')
    window.program.setCurrentIndex(window.program.findData('orca'))
    for n, name in enumerate(RESULTS, 1):
        path = ROOT / name
        if not path.is_file():
            print('нет файла', name)
            continue
        text = path.read_text(encoding='utf-8', errors='replace')
        window.display_output(text, path.name, True, str(path))
        settle(app, 10)
        tabs = window.result_tabs
        for t in range(tabs.count()):
            if tabs.isTabVisible(t):
                tabs.setCurrentIndex(t)
                shot(window, app, f'spectrum_{n}_{t + 1}_{tabs.tabText(t).split()[0]}')
    # the panel of Compass on the page of the vibrations (its «Перейти в Спектр»), the critical points of the
    # water of examples/6-orbitals (recorded output of Multiwfn) numbered on the model and in Spectrum
    path = ROOT / RESULTS[1]
    window.display_output(path.read_text(encoding='utf-8', errors='replace'), path.name, True, str(path))
    settle(app, 10)
    window.navigate(0)
    window.trajectory_tool.set_trajectory_open(True, 'modes')
    settle(app, 10)
    window.drawer.set_mode_playing(False)
    shot(window, app, 'compass_drawer_modes')
    window.trajectory_tool.set_trajectory_open(False)
    try:
        from modules.spectrum.analysis import density
        from modules.spectrum.wavefunction import multiwfn
        from modules.spectrum.readers.orbital_files import read_orbitals

        data = ROOT / 'tests' / 'data' / 'multiwfn'
        orbitals = read_orbitals((ROOT / 'examples' / '6-orbitals' / 'water_mp2_gaussian16.fchk').read_text(encoding='utf-8'))
        cps = multiwfn.parse_cps((data / 'water_fchk_CPprop_2026.7.15.txt').read_text(encoding='utf-8'))
        topology = density.topology_from(cps, orbitals)
        window.dirty = False
        window.load_molecule(orbitals.molecule)
        window.topology_panel.show_for(orbitals, 'water', topology)
        window.result_tabs.setTabVisible(window.topology_tab, True)
        window.topology_panel.points_on_model(handed=False)
        settle(app, 10)
        shot(window, app, 'compass_qtaim_labels')
        window.navigate(2)
        window.result_tabs.setCurrentIndex(window.topology_tab)
        panel = window.topology_panel
        for key in ('all', 'nucleus', 'bond'):
            panel.kind_filter.setCurrentIndex(panel.kind_filter.findData(key))
            shot(window, app, f'spectrum_qtaim_{key}')
        panel.kind_filter.setCurrentIndex(0)
        window.surface_tool.clear_aim()
    except (OSError, ValueError) as exc:
        print('QTAIM:', exc)
    reaction = window.reaction_diagram()  # the window of the reaction diagram, with two results as stages
    if reaction is not None:
        reaction.add_files([str(ROOT / RESULTS[1]), str(ROOT / RESULTS[2])])
        reaction.resize(1100, 640)
        settle(app, 10)
        reaction.grab().save(str(OUT / 'reaction.png'))
        print((OUT / 'reaction.png').relative_to(ROOT), flush=True)
        reaction.close()
    window.dirty = False
    for d in window.all_documents():
        d.dirty = False
    window.close()
    print(f'\nСнимки: {OUT}')


if __name__ == '__main__':
    main()
