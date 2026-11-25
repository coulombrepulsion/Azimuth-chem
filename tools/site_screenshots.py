"""Pictures of the program for the panels of its sections on the home page of the site — taken from the program itself.

§1 PURPOSE The panel of every section on the home page of the site shows a picture or two of it. The pictures are
    windows of the program drawn by the program (QWidget.grab), not photographs of a screen: they can be made again
    after the interface has changed, by one command, and show no desktop of anybody.
§2 ALGORITHM
    The window of the program (hub.window.HubWindow) is made without being shown on the screen (the offscreen
    platform of Qt, twice the density of points), with settings, logs and projects of its own in a temporary folder
    — the settings and the projects of the user are not touched. For every picture of SHOTS the window is brought to
    a state (a section, a file of examples/ opened) and saved as PNG. A picture that could not be made is said and
    the rest are still made. No window that waits for an answer is shown: such a window answers «cancel» at once.
§4 SPECIFICATION
    python tools/site_screenshots.py [--out FOLDER] [--only NAME …] [--theme light|dark] [--size 1440x900] [--site]
                                     [--lang ru|en|zh]
    Every picture is made in both themes (NAME-dark.png, NAME-light.png) unless --theme names one. --lang: the
    program in that language (its texts, Qt's buttons); the pictures of en and zh are NAME-LANG-THEME (.png, and
    .webp with --site — build_atlas_site.shot_languages takes them), those of ru keep NAME-THEME.
    FOLDER by default: site-shots/ beside the program (not kept by git). Prints a line a picture.
    The pictures of the site (site/img-program/NAME-THEME.webp, 1600 px wide, named in site/index.html as
    <!--SHOT NAME key-->) are chosen from these. --site: every picture made whose NAME site/index.html
    names is also written there as WEBP (Pillow: 1600 × 1000, quality 80) — no step by hand.
    A window of its own (the surface of Hirshfeld, the powder pattern) is pictured alone, at the size of
    the main window, so that all the pictures of a panel have one shape (build_atlas_site.SHOT_SIZE).
    --manual: the pictures of the user manual (MANUAL_SHOTS, unless --only names others) — the light theme only,
    docs/manual/img/NAME.jpg (1800 px wide, quality 88: a book of thirty pictures stays a few megabytes);
    tools/manual_pdf.py puts them into the PDF. Not in it: the surface of Hirshfeld and its fingerprint — without a
    screen the surface is not drawn.
"""

import argparse
import os
import re
import sys
import tempfile
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


MANUAL_SHOTS = ('home', 'compass', 'compass-optimization', 'compass-scan', 'sextant', 'spectrum-optimization',
                'spectrum-vibrations', 'spectrum-uv', 'crystal', 'crystal-contacts', 'crystal-powder', 'sextant-crystal')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--out', default=str(ROOT / 'site-shots'))
    parser.add_argument('--only', nargs='*')
    parser.add_argument('--theme', choices=['light', 'dark'], help='one theme only (both by default)')
    parser.add_argument('--size', default='1440x900')
    parser.add_argument('--site', action='store_true', help='also write the pictures named in site/index.html as WEBP')
    parser.add_argument('--lang', choices=['ru', 'en', 'zh'], default='ru', help='the language of the program (ru by default)')
    parser.add_argument('--manual', action='store_true', help='the pictures of the user manual (docs/manual/img, JPEG)')
    args = parser.parse_args(argv)
    if args.manual:
        args.theme = 'light'
        args.out = str(ROOT / 'site-shots' / 'manual')
        args.only = args.only or list(MANUAL_SHOTS)
    suffix = '' if args.lang == 'ru' else '-' + args.lang  # NAME-THEME in Russian, NAME-LANG-THEME in the others
    width, height = (int(x) for x in args.size.lower().split('x'))
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    os.environ.setdefault('QT_SCALE_FACTOR', '2')
    scratch = Path(tempfile.mkdtemp(prefix='azimuth-site-shots-'))
    os.environ['AZIMUTH_SETTINGS_FILE'] = str(scratch / 'settings.ini')
    os.environ['AZIMUTH_LOG_DIR'] = str(scratch / 'logs')
    os.environ['AZIMUTH_PROJECTS_DIR'] = str(scratch / 'projects')
    (scratch / 'logs').mkdir()
    (scratch / 'projects').mkdir()

    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QInputDialog, QMenu, QMessageBox, QWidget

    # a window that waits for an answer is never shown here: nobody would answer it
    QDialog.exec = lambda self, *a, **k: 0
    QMenu.exec = lambda self, *a, **k: None
    for name in ('information', 'warning', 'critical', 'question', 'about'):
        setattr(QMessageBox, name, staticmethod(lambda *a, **k: QMessageBox.StandardButton.No))
    for name in ('getText', 'getItem', 'getInt', 'getDouble', 'getMultiLineText'):
        setattr(QInputDialog, name, staticmethod(lambda *a, **k: ('', False)))
    for name in ('getOpenFileName', 'getSaveFileName'):
        setattr(QFileDialog, name, staticmethod(lambda *a, **k: ('', '')))
    QFileDialog.getOpenFileNames = staticmethod(lambda *a, **k: ([], ''))
    QFileDialog.getExistingDirectory = staticmethod(lambda *a, **k: '')

    from azimuth.app import STYLE
    from hub.window import HubWindow

    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(STYLE)
    from azimuth import i18n

    i18n.set_language(args.lang)  # the texts made while the window is built
    preferences = QSettings(str(scratch / 'hub.ini'), QSettings.Format.IniFormat)
    preferences.setValue('hub_language', args.lang)
    hub = HubWindow('compass', preferences=preferences)
    studio = hub.studio
    if args.lang != 'ru':
        hub.set_language(args.lang)  # the side panel, the sections, Qt's buttons
    try:  # the built-in drawing of the molecule: the 3D one of the graphics card is not drawn without a screen
        studio.viewer.engine = 'raster'
        studio.viewer.set_native(False)
        studio.viewer._model_image = None
    except Exception:
        traceback.print_exc()
    hub.resize(width, height)
    hub.show()
    themes = [args.theme] if args.theme else ['dark', 'light']
    studio.theme.setCurrentIndex(1 if themes[0] == 'dark' else 0)

    def settle(seconds=1.6):
        end = time.monotonic() + seconds
        before = None
        while time.monotonic() < end:
            app.processEvents()
            time.sleep(0.03)
        for _ in range(40):
            app.processEvents()
            picture = hub.grab().toImage()
            if before is not None and picture == before:
                break
            before = picture
            time.sleep(0.05)

    examples = ROOT / 'examples'
    kept = {}

    def clean():  # no passing message, no status line, no home folder of the one who made the pictures
        from PySide6.QtWidgets import QLineEdit, QPlainTextEdit, QStatusBar, QTextEdit

        for widget in [studio] + list(hub.findChildren(QWidget)):
            if hasattr(widget, 'hide_notice'):
                try:
                    widget.hide_notice()
                except Exception:
                    pass
        for bar in hub.findChildren(QStatusBar):
            bar.clearMessage()
        home_folder = str(Path.home())
        for box in hub.findChildren(QPlainTextEdit) + hub.findChildren(QTextEdit):
            if home_folder in box.toPlainText():  # quietly: not an edit by hand («Файл изменён вручную»)
                box.blockSignals(True)
                box.document().blockSignals(True)
                box.setPlainText(box.toPlainText().replace(home_folder, '~'))
                box.document().blockSignals(False)
                box.blockSignals(False)
        for box in hub.findChildren(QLineEdit):
            if home_folder in box.text():
                box.blockSignals(True)
                box.setText(box.text().replace(home_folder, '~'))
                box.blockSignals(False)

    def opened(relative):
        studio.opening_tool.open_path(str(examples / relative))
        window = getattr(studio, 'crystal_window', None)
        if window is not None and window.isVisible():
            window.reject()

    def refit():  # the molecule fills its field (a field shown for the first time was fitted while still small)
        from modules.compass.view.viewer import MoleculeView

        for view in hub.findChildren(MoleculeView):
            if view.isVisible():
                try:
                    view.reset_view()
                except Exception:
                    traceback.print_exc()

    def section(ident):
        hub.show_section(ident, animate=False)
        settle(0.6)
        refit()

    def home():
        from hub import window as hub_window

        hub.show_section(getattr(hub_window, 'HOME', 'home'), animate=False)

    def compass():
        hub.open_atlas_molecule('Бензол · C₆H₆')
        section('compass')

    def compass_optimization():
        opened('2-optimization/divinylbenzene_opt_gaussian16.log')
        section('compass')

    def compass_scan():
        opened('3-scans/dihedral_scan_relaxed_orca6.out')
        section('compass')

    def sextant():
        hub.open_atlas_molecule('Бензол · C₆H₆')
        section('sextant')

    def spectrum_optimization():
        opened('2-optimization/divinylbenzene_opt_gaussian16.log')
        section('spectrum')

    def spectrum_scan():
        opened('3-scans/dihedral_scan_relaxed_orca6.out')
        section('spectrum')

    def spectrum_vibrations():
        opened('4-vibrations/divinylbenzene_freq_gaussian16.log')
        section('spectrum')

    def spectrum_uv():
        opened('5-uv-vis-nmr/divinylbenzene_tddft_orca6.out')
        section('spectrum')

    def spectrum_properties():
        opened('1-properties/divinylbenzene_cation_orca6.out')
        section('spectrum')

    def crystal():
        opened('10-crystals/NaCl_rock_salt.cif')
        section('crystal')

    def crystal_molecular():
        opened('10-crystals/benzoic_acid.cif')
        section('crystal')

    def crystal_graphite():
        opened('10-crystals/graphite_P1.cif')
        section('crystal')

    # the crystal features of 0.111–0.199 on the site
    def benzoic():  # opened once: one more tab of the same file at every picture is not what a user sees
        if not kept.get('benzoic'):
            opened('10-crystals/benzoic_acid.cif')
            kept['benzoic'] = True
        section('crystal')
        return studio.crystal_tool

    def closer(factor):  # the molecules of interest fill the field (the whole block is fitted by section)
        from modules.compass.view.viewer import MoleculeView

        for view in hub.findChildren(MoleculeView):
            if view.isVisible():
                view.zoom_view(factor)

    def alone(window):  # a window of its own, at the size of the main one (one shape for all the pictures)
        window.resize(width, height)
        window.show()
        settle(0.8)
        return window

    def crystal_contacts():  # the network of the hydrogen bonds (the dimers of the acid) on the model
        tool = benzoic()
        hidden = tool.hidden_window()
        tool.build_network(hidden.chosen(), ('hydrogen',), hidden.criteria(), 1, None)
        section('crystal')
        closer(3.0)

    def crystal_hirshfeld():  # the surface by d_norm on the model; its window is kept for the fingerprint
        from modules.compass.actions import hirshfeld_window

        benzoic()
        window = hirshfeld_window.show(studio)
        kept['hirshfeld'] = window
        window.show_on_model()
        window.hide()
        section('crystal')
        closer(3.0)

    def crystal_fingerprint():
        window = kept.get('hirshfeld')
        if window is None:
            crystal_hirshfeld()
            window = kept['hirshfeld']
        return alone(window)

    def crystal_powder():
        hidden = benzoic().hidden_window()
        window = hidden.show_powder()
        window.compute()
        return alone(window)

    def sextant_crystal():  # the task of a periodic calculation (Quantum ESPRESSO, CP2K)
        benzoic()
        section('sextant')

    SHOTS = [('home', home), ('compass', compass), ('compass-optimization', compass_optimization), ('compass-scan', compass_scan),
             ('sextant', sextant), ('spectrum-optimization', spectrum_optimization), ('spectrum-scan', spectrum_scan),
             ('spectrum-vibrations', spectrum_vibrations), ('spectrum-uv', spectrum_uv), ('spectrum-properties', spectrum_properties),
             ('crystal', crystal), ('crystal-molecular', crystal_molecular), ('crystal-graphite', crystal_graphite),
             ('crystal-contacts', crystal_contacts), ('crystal-hirshfeld', crystal_hirshfeld),
             ('crystal-fingerprint', crystal_fingerprint), ('crystal-powder', crystal_powder),
             ('sextant-crystal', sextant_crystal)]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    on_site = set(re.findall(r'<!--SHOT ([a-z-]+) [A-Za-z0-9]+-->',
                             (ROOT / 'site' / 'index.html').read_text(encoding='utf-8')))

    def to_site(path, name, theme):  # --site: the WEBP of the site, 1600 × 1000 (build_atlas_site.SHOT_SIZE)
        from PIL import Image

        target = ROOT / 'site' / 'img-program' / f'{name}{suffix}-{theme}.webp'
        with Image.open(path) as image:
            image.convert('RGB').resize((1600, 1000), Image.LANCZOS).save(target, 'WEBP', quality=80, method=6)
        return target
    def to_manual(path, name):
        from PIL import Image

        folder = ROOT / 'docs' / 'manual' / 'img'
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f'{name}.jpg'
        with Image.open(path) as image:
            image = image.convert('RGB')
            if image.width > 1800:
                image = image.resize((1800, round(image.height * 1800 / image.width)), Image.LANCZOS)
            image.save(target, 'JPEG', quality=88, optimize=True, progressive=True)
        return target
    failed = 0
    for name, prepare in SHOTS:
        if args.only and name not in args.only:
            continue
        try:
            target = prepare() or hub  # a window of its own when prepare gives one
            settle()
            clean()
            for theme in themes:  # the same state in both themes: the page of the site shows the one of its own theme
                studio.theme.setCurrentIndex(1 if theme == 'dark' else 0)
                settle(0.5)
                clean()
                picture = target.grab()
                path = out / f'{name}{suffix}-{theme}.png'
                picture.save(str(path))
                print(f'{name}{suffix}-{theme}: {picture.width()}x{picture.height()} → {path}  (section {hub.current})', flush=True)
                if args.manual:
                    print('   → ' + str(to_manual(path, name)), flush=True)
                if args.site and name in on_site:
                    print('   → ' + str(to_site(path, name, theme)), flush=True)
            if target is not hub:
                target.hide()
        except Exception:
            failed += 1
            print(f'{name}: not made', flush=True)
            traceback.print_exc()
    try:
        studio.dirty = False
        for d in studio.all_documents():
            d.dirty = False
    except Exception:
        pass
    sys.stdout.flush()
    os._exit(1 if failed else 0)  # the window is not closed the long way: nothing here is to be saved


if __name__ == '__main__':
    main()
