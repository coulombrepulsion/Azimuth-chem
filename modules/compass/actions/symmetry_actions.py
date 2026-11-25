"""Compass: point group, symmetrization and standard orientation (moved from workspace.py)."""

from dataclasses import replace
from PySide6.QtCore import Qt
from PySide6.QtGui import QActionGroup
from PySide6.QtWidgets import (
    QMenu,
)
from azimuth.core import Atom
from modules.compass.chemistry import symmetry

from azimuth.ui import smooth
from azimuth.i18n import tr


class SymmetryTool:
    """Was the mixin SymmetryActions of the window; a tool of its own — it reaches the window only through the names of
    PORT (azimuth/window_port.WindowPort)."""

    PORT = (
        '_symmetry_asked',
        '_symmetry_key',
        'browsing',
        'compass_mode',
        'crystal',
        'dirty',
        'geometry_error',
        'load_molecule',
        'molecule',
        'molecule_info',
        'molecule_summary',
        'notify',
        'preferences',
        'slab',
        'standard_action',
        'symmetrize_action',
        'symmetry_button',
        'symmetry_result',
        'symmetry_tol',
        'viewer',
    )

    def __init__(self, window):
        from azimuth.window_port import WindowPort

        self.w = WindowPort(window, self.PORT)


    # -- symmetry -----------------------------------------------------------------------
    def analyze_symmetry(self, force=False):
        """The analysis of the current structure at the chosen tolerance (cached)."""
        mol = self.w.molecule
        key = (tuple((a.symbol, round(a.x, 6), round(a.y, 6), round(a.z, 6)) for a in mol.atoms), self.w.symmetry_tol)
        if key != self.w._symmetry_key or force:
            if len(mol.atoms) > symmetry.AUTO_ATOMS and not force:
                return None
            try:
                self.w.symmetry_result = symmetry.analyze(mol, self.w.symmetry_tol)
            except Exception as exc:
                self.w.symmetry_result = {'err': 'failed', 'text': str(exc)}
            self.w._symmetry_key = key
        return self.w.symmetry_result

    # -- the crystal ---------------------------------------------------------------------
    def crystal_data(self):
        """The crystal of the tab of «Компас · Кристалл» (not a slab), or None: then the button finds the point group of
        the crystal (its class), not of the block of atoms on the screen."""
        if getattr(self.w, 'compass_mode', 'molecule') != 'crystal' or getattr(self.w, 'slab', None) is not None:
            return None
        crystal = getattr(self.w, 'crystal', None)
        return crystal[0] if crystal else None

    def crystal_symmetry(self):
        """{'name': Schoenflies, 'hm': Hermann–Mauguin, 'group': the space group, 'system'} of the crystal, or None."""
        from modules.compass.chemistry import crystal_symmetry as cs

        data = self.crystal_data()
        if data is None:
            return None
        key = (id(data), 'crystal')
        cached = getattr(self, '_crystal_result', None)
        if cached is not None and cached[0] == key:
            return cached[1]
        s = cs.analyse(data)
        result = None
        if s.point_group:
            number = s.number or data.number
            group = (data.space_group or '').strip() or '—'
            z = (f'{s.z:g}' if isinstance(s.z, float) else str(s.z)) if s.z else ''
            result = {'name': cs.SCHOENFLIES[s.point_group], 'hm': s.point_group, 'system': s.system,
                      'group': group + (f' (№ {number})' if number else ''), 'order': 1, 'crystal': True, 'z': z}
        self._crystal_result = (key, result)
        return result

    def _crystal_text(self, result):
        if result is None:
            return tr('Точечная группа кристалла не определена: операции файла не образуют кристаллографической группы.')
        return tr('Кристаллический класс (точечная группа) {} = {} · пространственная группа {} · {} сингония.').format(
            result['hm'], result['name'], result['group'], tr(result['system']))

    def symmetry_geometry(self):
        return tuple((a.symbol, round(a.x, 6), round(a.y, 6), round(a.z, 6)) for a in self.w.molecule.atoms)

    def symmetry_shown(self):
        """The point group is found only when asked (the button), for the geometry it was asked for."""
        return bool(self.w.molecule.atoms) and getattr(self.w, '_symmetry_asked', None) == (self.symmetry_geometry(), self.w.symmetry_tol)

    def determine_symmetry(self, *, apply=True):
        """The symmetry button: the first press finds the point group (shown in the summary), the next one —
        when there is symmetry — symmetrises and turns to the standard orientation. Apply=False —
        «Инструменты → Определить точечную группу»: only finds it (symmetrising is the next items of that menu)."""
        if not self.w.molecule.atoms:
            self.w.notify(tr('Нет атомов — определять нечего.'))
            return None
        if self.crystal_data() is not None:  # the class of the crystal; nothing to symmetrise
            result = self.crystal_symmetry()
            self.w._symmetry_asked = (self.symmetry_geometry(), self.w.symmetry_tol)
            self.update_symmetry()
            self.w.notify(self._crystal_text(result), 15000)
            return result
        if apply and self.symmetry_shown():
            result = self.analyze_symmetry(force=True)
            if result and 'name' in result and result.get('order', 1) > 1:
                self.apply_symmetry(True)
                return result
            near = getattr(self, '_symmetry_near', None)
            if near is not None and near[0] == self.symmetry_geometry():  # C1, near a higher group
                self.apply_symmetry(True, near[1])
                return near[1]
        result = self.analyze_symmetry(force=True)
        self.w._symmetry_asked = (self.symmetry_geometry(), self.w.symmetry_tol)
        self.update_symmetry()
        if result and 'name' in result:
            order = result.get('order', 1)  # a failed analysis says C1 without an order (it raised KeyError)
            # only the group: the owner asked for the group, not for advice to symmetrise (2026-11-22); what the
            # next press does is in the tooltip of the button
            text = tr(f'Точечная группа {result["name"]}.')
            if order == 1 and len(self.w.molecule.atoms) <= symmetry.MAX_ATOMS:
                near = symmetry.nearest_higher(self.w.molecule, self.w.symmetry_tol)
                self._symmetry_near = (self.symmetry_geometry(), near) if near is not None else None
                if near is not None:  # C1 as it is, but near a higher group — say which and how far
                    text += tr(f' Структура близка к {near["name"]}: атомы отклоняются от неё в среднем на '
                               f'{near["rmsd"]:.2f} Å.')
            self.w.notify(text, 15000)
        else:
            self.w.notify(self.symmetry_problem(result))
        return result

    @staticmethod
    def symmetry_problem(result):
        """Why there is no point group, in words."""
        err = (result or {}).get('err')
        if err == 'several':
            return tr(f'Точечная группа определяется только для одной молекулы, а в поле их {result["count"]}.')
        if err == 'too_big':
            return tr(f'Точечная группа определяется для структур до {symmetry.MAX_ATOMS} атомов.')
        if err == 'one_atom':
            return tr('Один атом — точечная группа не определяется.')
        return tr('Точечная группа не определена.')

    def update_symmetry(self):
        """The summary «H₂O / атомов: 3»; after the button also the point group, e.g. «… / C<sub>2v</sub>»."""
        if not self.w.has('molecule_info') or not self.w.geometry_error.isHidden():
            return
        text = self.w.molecule_summary(self.w.molecule)
        shown = self.symmetry_shown()
        crystal = self.crystal_data() is not None
        info = self.crystal_symmetry() if crystal else None
        result = (info if crystal else self.analyze_symmetry()) if shown else None
        if info or (result and 'name' in result):
            text = text.replace('&', '&amp;').replace('<', '&lt;')
        if info:  # the space group and Z of the crystal are always in the summary
            text += '  /  ' + (info['group'] + (f', Z = {info["z"]}' if info.get('z') else '')).replace('<', '&lt;')
        if result and 'name' in result:
            text += '  /  ' + symmetry.group_html(result['name'])
            if crystal:
                text += f' ({result["hm"]})'
        self.w.molecule_info.setText(text)
        ready = bool(self.w.molecule.atoms) and not self.w.browsing
        for item in (self.w.symmetrize_action, self.w.standard_action, self.w.symmetry_button):
            item.setEnabled(ready and (item is self.w.symmetry_button or not crystal))
        name = result['name'] if result and 'name' in result else None
        order = result.get('order', 1) if name else 1
        if crystal:
            self.w.symmetry_button.setToolTip(self._crystal_text(result) if result else
                                              tr('Определить точечную группу кристалла (кристаллический класс)'))
            return
        self.w.symmetry_button.setToolTip(
            tr(f'Симметризовать до {name} и повернуть в стандартную ориентацию')
            if name and order > 1
            else tr('Точечная группа C1 — симметризовать нечего')
            if name
            else tr('Определить точечную группу · повторное нажатие — симметризовать')
        )

    def symmetry_menu(self):
        menu = smooth(QMenu(self.w.widget))
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        menu.setWindowFlags(menu.windowFlags() | Qt.WindowType.FramelessWindowHint)
        if self.crystal_data() is not None:  # the crystal — its class and space group, nothing to symmetrise
            result = self.crystal_symmetry()
            lines = ([tr('Кристаллический класс: {} = {}').format(result['hm'], result['name']),
                      tr('Пространственная группа: {}').format(result['group']),
                      tr('Сингония: {}').format(tr(result['system']))] if result else [self._crystal_text(None)])
            for text in lines:
                menu.addAction(text).setEnabled(False)
            return menu
        result = self.analyze_symmetry(force=True)
        if result and 'name' in result:
            head = tr(f'Точечная группа: {result["name"]}') + (
                tr(f' · найдена с допуском {result["tol"]:.2g} Å')
                if abs(result['tol'] - self.w.symmetry_tol) > 1e-9
                else ''
            )
            shift = tr(f'Сдвиг атомов при симметризации: RMSD {result["rmsd"]:.3f} Å')
        else:
            head = self.symmetry_problem(result).rstrip('.')
            shift = ''
        for text in (head, shift):
            if text:
                item = menu.addAction(text)
                item.setEnabled(False)
        menu.addSeparator()
        order = result.get('order', 1) if result and 'name' in result else 1
        for item in (self.w.symmetrize_action, self.w.standard_action):
            item.setEnabled(order > 1 and not self.w.browsing)
            menu.addAction(item)
        menu.addSeparator()
        tols = menu.addMenu(tr('Допуск'))
        group = QActionGroup(tols)
        for value in (0.05, 0.1, 0.2, 0.3, 0.5):  # 0.5 — as symmetry.LOOSER
            item = tols.addAction(f'{value:g} Å')
            item.setCheckable(True)
            item.setChecked(abs(value - self.w.symmetry_tol) < 1e-9)
            group.addAction(item)
            item.triggered.connect(lambda checked=False, v=value: self.set_symmetry_tol(v))
        return menu

    def closest_standard(self, target):
        """The standard orientation is unique only up to 180° turns about x, y, z: keep the one
        nearest to the current coordinates, so that pressing again changes nothing."""
        import numpy as np
        from modules.compass.chemistry.symmetry import _symfind

        sf = _symfind()
        mass = np.array([sf._w(a.symbol) for a in self.w.molecule.atoms])
        now = np.array([a.position for a in self.w.molecule.atoms])
        now = now - (mass[:, None] * now).sum(0) / mass.sum()
        new = np.array([a.position for a in target.atoms])
        # already in a standard orientation (any of the 24 axis-aligned frames): leave it as it is
        from itertools import permutations

        frames = []
        for perm in permutations(range(3)):
            for signs in ((sx, sy, sz) for sx in (1, -1) for sy in (1, -1) for sz in (1, -1)):
                m = np.zeros((3, 3))
                for row, (col, sign) in enumerate(zip(perm, signs)):
                    m[row, col] = sign
                if np.linalg.det(m) > 0:
                    frames.append(m)
        if min(float(np.sum((new @ m.T - now) ** 2)) for m in frames) < 1e-8 * len(new):
            return replace(target, atoms=self.w.molecule.atoms)
        # otherwise the nearest of the four turns that keep the principal axis on z
        best = min(
            ((sx, sy, sx * sy) for sx in (1, -1) for sy in (1, -1)),
            key=lambda d: float(np.sum((new * np.array(d) - now) ** 2)),
        )
        return replace(
            target,
            atoms=tuple(Atom(a.symbol, *(float(v) for v in p)) for a, p in zip(target.atoms, new * np.array(best))),
        )

    def set_symmetry_tol(self, value):
        self.w.symmetry_tol = value
        self.w.preferences.setValue('symmetry_tol', value)
        self.update_symmetry()

    def apply_symmetry(self, standard, result=None):
        """Symmetrise in place, or symmetrise and turn to the standard orientation of the group. Result — a
        group found at a looser tolerance (symmetry.nearest_higher), else the one at the chosen tolerance."""
        if self.w.browsing:
            return
        if self.crystal_data() is not None:  # a crystal is not symmetrised: its symmetry is that of the file
            self.w.notify(self._crystal_text(self.crystal_symmetry()), 10000)
            return
        result = result or self.analyze_symmetry(force=True)
        if not result or 'name' not in result or result.get('order', 1) <= 1:
            self.w.notify(tr('Симметрии нет (C1): симметризовать нечего.'), 8000)
            return
        target = result['standard' if standard else 'in_place']
        if standard:
            target = self.closest_standard(target)
        self.w.viewer.locked_camera = None if standard else self.w.viewer.locked_camera
        self.w.load_molecule(replace(self.w.molecule, atoms=target.atoms), preserve_view=not standard)
        self.w.dirty = True
        self.w._symmetry_asked = (self.symmetry_geometry(), self.w.symmetry_tol)  # the group stays shown
        self.update_symmetry()
        self.w.notify(
            tr(f'Симметризовано до {result["name"]} · сдвиг атомов RMSD {result["rmsd"]:.3f} Å')
            + (tr(' · стандартная ориентация') if standard else ''),
            10000,
        )
