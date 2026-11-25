"""The orbitals and grids of a result in Spectrum: the CUBE window, the orbital window (Molden, fchk, an ORCA .gbw
turned into Molden, an output with printed orbitals), the orbitals handed to the density panel of Compass. Methods of
SpectrumWorkspace (self is the window), kept here to make workspace.py shorter.

Split off modules/spectrum/workspace.py (0.222.29).
"""

from pathlib import Path
from PySide6.QtWidgets import QFileDialog
from azimuth.i18n import tr


def cube_window(self, cube):
    from modules.spectrum.views.cube_view import CubeDialog

    if self.cube_dialog is None:
        self.cube_dialog = CubeDialog(self, dark=self.theme.currentIndex() == 1)
        self.cube_dialog.destroyed.connect(self.cube_closed)
    self.cube_dialog.load_cube(cube)
    self.cube_dialog.show()
    self.cube_dialog.raise_()


def cube_closed(self, *args):
    self.cube_dialog = None


def open_cube(self):
    path, _ = QFileDialog.getOpenFileName(
        self, tr('Открыть CUBE'), str(Path.home()), tr('CUBE (*.cube *.cub);;Все файлы (*)')
    )
    if not path:
        return
    try:
        from modules.spectrum.readers.cube import read_cube, MAX_BYTES

        p = Path(path)
        if p.stat().st_size > MAX_BYTES:
            raise ValueError(tr('CUBE: предел размера — 64 МБ.'))
        self.cube_window(self.read_heavy(p, tr('Чтение CUBE…'), lambda: read_cube(p.read_text(encoding='utf-8-sig'))))
    except ImportError:
        self.error(tr('Для 3D-просмотра нужны VTK и NumPy. Запустите файл Launch для установки зависимостей.'))
    except (ValueError, OSError, UnicodeError) as exc:
        self.error(exc)


def open_sibling_orbitals(self, analysis=False):
    """The orbital window of the shown result (an ORCA .gbw is turned into Molden first); analysis: the
    window «Анализ электронной плотности» at once. Returns the orbital window or None."""
    path = self.result_molden_path()
    if path is None:
        return None
    dialog = self.open_orbitals_path(path)
    if dialog is not None and analysis:
        dialog.density_analysis()
    return dialog


def load_result_orbitals(self):
    """(OrbitalSet, file name) of the shown result for the density panel of Compass, or None (message shown)."""
    from modules.spectrum.readers.orbital_files import read_orbitals

    path = self.result_molden_path()
    if path is None:
        return None
    try:
        if Path(path).stat().st_size > 64_000_000:
            raise ValueError(tr('Файл с орбиталями больше 64 МБ.'))
        orbital_set = self.read_heavy(path, tr('Чтение орбиталей…'), lambda: read_orbitals(
            Path(path).read_text(encoding='utf-8-sig', errors='replace')))  # 0.91.66 (R3)
        if hasattr(self, 'property_tool'):  # Multiwfn reads this file for ESP and QTAIM
            self.property_tool.remember_orbitals_file(orbital_set, Path(path))
        return orbital_set, Path(path).name
    except (OSError, ValueError) as exc:
        self.error(tr('Орбитали не прочитаны: ') + str(exc))
        return None


def result_molden_path(self):
    """The file of the orbitals of the shown result; an ORCA .gbw is turned into Molden first."""
    path = getattr(self, 'sibling_molden', None)
    if path is None and getattr(self, 'sibling_gbw', None) is not None:
        from modules.sextant import runner

        configured = self.run_tool.configured_program('orca') if hasattr(self, 'run_tool') else None
        from PySide6.QtCore import Qt as _Qt
        from PySide6.QtWidgets import QApplication

        QApplication.setOverrideCursor(_Qt.CursorShape.WaitCursor)
        try:
            path = runner.molden_from_gbw(self.sibling_gbw, configured)
        except ValueError as exc:
            self.error(exc)
            return None
        finally:
            QApplication.restoreOverrideCursor()
        self.sibling_molden, self.sibling_gbw = path, None
    return path


def open_orbitals(self):
    path, _ = QFileDialog.getOpenFileName(
        self,
        tr('Открыть орбитали'),
        str(Path.home()),
        tr('Орбитали (*.molden *.input *.molf *.mold *.fchk *.fch *.out *.log *.aux);;Все файлы (*)'),
    )
    if path:
        self.open_orbitals_path(path)


def open_orbitals_path(self, path):
    try:
        if Path(path).stat().st_size > 64_000_000:
            raise ValueError(tr('Файл с орбиталями больше 64 МБ.'))
        from modules.spectrum.readers.orbital_files import read_orbitals

        def read():  # a big file read and parsed off the thread of the window
            try:
                return read_orbitals(Path(path).read_text(encoding='utf-8-sig', errors='replace'))
            except ValueError as exc:
                return exc

        parsed = self.read_heavy(path, tr('Чтение орбиталей…'), read)
        if isinstance(parsed, ValueError):
            self.error(tr('Орбитали не прочитаны: ') + str(parsed))
            return None
        dialog = self.open_orbitals_text(None, Path(path).name, parsed)
        if dialog is not None and hasattr(self, 'property_tool'):  # ESP and QTAIM — Multiwfn
            self.property_tool.remember_orbitals_file(dialog.orbital_set, Path(path))
            orbital_set = dialog.orbital_set
            dialog.set_multiwfn(lambda: self.property_tool.multiwfn_for(orbital_set),
                                (lambda: self.surface_tool.multiwfn_esp(Path(path))) if hasattr(self, 'surface_tool') else None)
            dialog.grid_source = lambda: self.property_tool.multiwfn_quiet(orbital_set)  # grids from Multiwfn
        return dialog
    except (OSError, ValueError) as exc:
        self.error(exc)
        return None


def open_orbitals_text(self, text, source, orbital_set=None):
    """The orbital window: a Molden file, a Gaussian .fchk, an ORCA output with print[p_mos];
    orbital_set — already read, text is not read then."""
    from modules.spectrum.readers.orbital_files import read_orbitals
    from modules.spectrum.views.orbitals_view import OrbitalsDialog

    if orbital_set is None:
        try:
            orbital_set = read_orbitals(text)
        except ValueError as exc:
            self.error(tr('Орбитали не прочитаны: ') + str(exc))
            return None
    compass = None  # the field on the Compass model
    if hasattr(self, 'surface_tool'):
        compass = lambda cube, kind, orbitals, title: self.surface_tool.show_surface(cube, kind, orbitals, title=title)  # noqa: E731
    aim = None  # the critical points and bond paths on the Compass model
    if hasattr(self, 'surface_tool'):
        aim = lambda topology, orbitals, title, **kw: self.surface_tool.show_aim(topology, orbitals, title=title, **kw)  # noqa: E731
    handover = None  # a field put on the model hands the work over to the density panel of Compass
    if hasattr(self, 'density_tool'):
        handover = lambda orbitals, title, tab, state: self.density_tool.open_density_drawer(orbitals, title, tab, state)  # noqa: E731
    previous = getattr(self, 'orbitals_dialog', None)
    try:
        if previous is not None and not previous.isVisible():
            previous.close()  # handed over before: not needed any more
    except RuntimeError:  # already deleted
        pass
    dialog = OrbitalsDialog(orbital_set, source, self.show_orbital_cube, self, compass, aim, to_compass=handover)
    if hasattr(self, 'surface_tool'):  # the points of its analysis window are taken off the model here
        dialog.clear_aim = self.surface_tool.clear_aim
        dialog.keep_contacts = self.surface_tool.keep_contacts
        dialog.aim_shown = lambda: getattr(self.viewer, 'aim', None) is not None
    dialog.show()
    dialog.raise_()
    self.orbitals_dialog = dialog
    return dialog


def show_orbital_cube(self, cube, density):
    try:
        self.cube_window(cube)
    except ImportError:
        self.error(tr('Для 3D-просмотра нужны VTK и NumPy. Запустите файл Launch для установки зависимостей.'))
        return
    self.cube_dialog.kind.setCurrentIndex(1 if density else 0)
    if density:
        self.cube_dialog.level.setValue(0.02)


def demo_cube(self):
    try:
        from modules.spectrum.readers.cube import demo_cube

        self.cube_window(demo_cube())
    except ImportError:
        self.error(tr('Для 3D-просмотра нужны VTK и NumPy. Запустите файл Launch для установки зависимостей.'))
