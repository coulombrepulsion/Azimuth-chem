"""Compass: «Вид → Ленты белка» — the ribbon of a protein over or instead of its atoms; «Правка → Геометрия →
Построить пептид…» — a peptide from its sequence (modules/compass/chemistry/peptide.py).

The backbone, the secondary structure and the mesh come from modules/compass/chemistry/protein.py; the ribbon is shown
as the surface of the model (viewer.surface, drawn by QPainter or VTK like an orbital), so it turns and zooms with the
atoms and disappears when the structure changes. The atoms of the chains are hidden («Вид → Скрыть атомы → Показать все
атомы» brings them back over the ribbon); ligands and water stay.
"""

from dataclasses import dataclass
from typing import Callable

from PySide6.QtGui import QAction

from azimuth.i18n import tr


@dataclass(frozen=True)
class ProteinPort:
    parent: object  # of the actions and the dialog
    viewer: Callable[[], object]  # the 3D model: its surface and hidden atoms
    molecule: Callable[[], object]
    notify: Callable[[str, int], None]
    error: Callable[[Exception], None]
    confirm_replace: Callable[[], bool]
    edit_structure: Callable[[object, str], None]


class ProteinTool:
    """Was the mixin ProteinActions of the window; knows the window only through ProteinPort."""

    def __init__(self, port):
        self.port = port
        self._ribbon_hidden = frozenset()
        self.ribbon_action = QAction(tr('Ленты белка'), port.parent)
        self.ribbon_action.setCheckable(True)
        self.ribbon_action.setToolTip(tr('α-спирали — красные ленты, β-слои — жёлтые стрелки, остальное — серая трубка; '
                                         'атомы цепей скрываются, лиганды и вода остаются'))
        self.ribbon_action.toggled.connect(self.show_ribbon)
        self.peptide_action = QAction(tr('Построить пептид…'), port.parent)
        self.peptide_action.setToolTip(tr('Пептид по однобуквенной последовательности: α-спираль, β-слой или вытянутая '
                                          'цепь; L-аминокислоты'))
        self.peptide_action.triggered.connect(lambda *_: self.peptide_dialog())

    def peptide_dialog(self, values=None):
        """The sequence and the conformation (values = (sequence, key) without the window — the tests)."""
        from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit

        from modules.compass.chemistry import peptide

        if values is None:
            box = QDialog(self.port.parent)
            box.setWindowTitle(tr('Построить пептид'))
            form = QFormLayout(box)
            sequence = QLineEdit('AAAAAAAAAA')
            sequence.setToolTip(tr('Однобуквенные коды: ') + ' '.join(f'{k} {v[0]}' for k, v in peptide.RESIDUES.items()))
            form.addRow(tr('Последовательность (N → C):'), sequence)
            shape = QComboBox()
            for key, (_, _, title) in peptide.CONFORMATIONS.items():
                shape.addItem(tr(title), key)
            form.addRow(tr('Конформация:'), shape)
            note = QLabel(tr('φ и ψ задаются точно, боковые цепи разворачиваются без столкновений; концы NH₂ и COOH. '
                             'До {} остатков.').format(peptide.MAX_RESIDUES))
            note.setWordWrap(True)
            form.addRow(note)
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            buttons.accepted.connect(box.accept)
            buttons.rejected.connect(box.reject)
            form.addRow(buttons)
            if box.exec() != QDialog.DialogCode.Accepted:
                return None
            values = (sequence.text(), shape.currentData())
        if not self.port.confirm_replace():
            return None
        try:
            molecule = peptide.build(*values)
        except ValueError as exc:
            self.port.error(exc)
            return None
        title = tr(peptide.CONFORMATIONS[values[1]][2])
        self.port.edit_structure(molecule, tr('Пептид {}: {} — L-аминокислоты, φ/ψ точные; боковые цепи — начальное '
                                         'положение, его стоит оптимизировать.').format(molecule.title, title))
        return molecule

    def show_ribbon(self, on=True):
        """Draw the ribbon (on) or take it away; returns the numbers of residues by kind {'H', 'E', 'C'} or None."""
        from modules.compass.chemistry import protein

        viewer = self.port.viewer()
        if not on:
            if viewer.surface and viewer.surface.get('kind') == 'ribbon':
                viewer.surface = None
            viewer.user_hidden = frozenset(viewer.user_hidden) - self._ribbon_hidden
            self._ribbon_hidden = frozenset()
            viewer.update()
            return None
        molecule = self.port.molecule()
        try:
            chains = protein.backbone(molecule)
            if not chains:
                raise ValueError(tr('Белковой цепи не найдено: нужны хотя бы два остатка N–Cα–C(=O), связанные пептидной '
                                    'связью.'))
            ss = protein.secondary(molecule, chains)
            mesh = protein.ribbon(molecule, chains, ss)
        except (ValueError, IndexError) as exc:
            self.ribbon_action.blockSignals(True)
            self.ribbon_action.setChecked(False)
            self.ribbon_action.blockSignals(False)
            self.port.error(exc if isinstance(exc, ValueError) else ValueError(str(exc)))
            return None
        counts = {kind: sum(s.count(kind) for s in ss) for kind in 'HEC'}
        viewer.surface = {
            'kind': 'ribbon', 'atoms': molecule.atoms, 'meshes': [mesh], 'opacity': 1.0,
            'legend': tr('Ленты: спираль · β-слой · петля'), 'limit': None, 'scale': None, 'range': None,
            'markers': [], 'build': None, 'fine': None,
        }
        self._ribbon_hidden = frozenset(protein.protein_atoms(molecule, chains))
        viewer.user_hidden = frozenset(viewer.user_hidden) | self._ribbon_hidden
        viewer.update()
        total = sum(len(c) for c in chains)
        self.port.notify(tr('Цепей: {}, остатков: {}; в спиралях {}, в β-слоях {}. Атомы цепей скрыты — «Вид → Скрыть атомы → '
                       'Показать все атомы».').format(len(chains), total, counts['H'], counts['E']), 9000)
        return counts
