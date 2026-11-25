"""The analyses of a result in Spectrum that live on its tabs: the topology of the density, the maps and profiles,
the delocalization, the excitations and their NTO, the density of states. Methods of SpectrumWorkspace (self is the
window), kept here to make workspace.py shorter.

Split off modules/spectrum/workspace.py (0.222.29).
"""

from pathlib import Path
from PySide6.QtCore import Qt
from azimuth.i18n import tr


# -- the detailed table of the critical points of the result -------------------------------------------------
def find_result_topology(self):
    """«Найти критические точки» of the tab «Топология ЭП»: the search of the panel of Compass for the orbitals of
    the result (so that the list there and the table here show the same points)."""
    drawer = self.density_tool.ensure_density_content() if hasattr(self, 'density_tool') else None
    if drawer is None or drawer.panel is None:
        return None
    return drawer.panel.find_points()


def topology_found(self, orbital_set, source, topology):
    """The points found in the panel of Compass (or handed to it): the table of Spectrum shows them too."""
    self.topology_panel.show_for(orbital_set, source, topology)
    self.topology_panel.sync_model_button(getattr(self.viewer, 'aim', None) is not None)
    self.result_tabs.setTabVisible(self.topology_tab, True)


def field_shown(self, index):
    """The tab «Карты и профили» opened — the last map and profile built for these orbitals."""
    if index == getattr(self, 'field_tab', -1) and self.result_tabs.isTabVisible(index):
        return self.field_panel.load_saved()
    return False


def deloc_shown(self, index):
    """The tab «Делокализация» opened — what Multiwfn computed for these orbitals before."""
    if index == getattr(self, 'deloc_tab', -1) and self.result_tabs.isTabVisible(index):
        return self.deloc_panel.load_saved()
    return False


def topology_shown(self, index):
    """The tab «Топология ЭП»
    opened — the points kept for the orbitals of the result are shown then (their orbitals read once, as the tab
    «Плотность состояний» does), not when the result is opened."""
    if index != getattr(self, 'topology_tab', -1) or not self.result_tabs.isTabVisible(index):
        return False
    drawer = getattr(self, 'density_drawer', None)
    panel = drawer.panel if drawer is not None else None
    if (panel is not None and panel.topology is not None) or not hasattr(self, 'density_tool'):
        return False
    if not self.saved_topology_here():
        return False
    self.density_tool.ensure_density_content()
    self.refresh_topology_tab()
    return True


def saved_topology_here(self):
    """Are points kept (field_tables.save_topology) for the file of orbitals of the result shown?"""
    from modules.spectrum.wavefunction import field_tables

    path = self.result_orbitals() if hasattr(self, 'result_orbitals') else None
    if path is None:
        return False
    stem = Path(path).name.split('.')[0]
    return (Path(path).parent / field_tables.ANALYSIS / f'{stem}_{field_tables.SAVED_TOPOLOGY}.json').is_file()


def refresh_topology_tab(self):
    """After a result is shown: the table keeps the points of these orbitals only."""
    drawer = getattr(self, 'density_drawer', None)
    panel = drawer.panel if drawer is not None else None
    if panel is not None and panel.topology is not None:
        self.topology_panel.show_for(panel.orbital_set, panel.source, panel.topology)
    else:
        self.topology_panel.clear()


def excitation_source(self):
    """(Multiwfn, the wavefunction of the result, its TD-DFT output, cores) or None."""
    path = getattr(self, 'output_path', None)
    if path is None or not hasattr(self, 'property_tool'):
        return None
    source = self.property_tool.multiwfn_source()
    if source is None:
        return None
    program, wavefunction, cores = source
    return program, wavefunction, Path(path), cores


def transfer_context(self):
    """(the symbols of the atoms of the model, the atoms selected on it) for «Перенос заряда»."""
    molecule = getattr(self, 'molecule', None)
    if molecule is None or not molecule.atoms:
        return None
    viewer = getattr(self, 'viewer', None)
    return [a.symbol for a in molecule.atoms], lambda: sorted(getattr(viewer, 'selected', None) or ())


def show_nto(self, entry, which='hole'):
    """The hole (which='hole') or particle NTO of the heaviest pair of a state on the model: the orbitals of
    its .nto file (orca_2mkl) in the drawer of Compass, the row of that NTO chosen and shown; ValueError said."""
    from modules.spectrum.analysis import nto

    path = getattr(self, 'output_path', None)
    if path is None:
        raise ValueError(tr('Нет файла вывода этого результата.'))
    configured = self.run_tool.configured_program('orca') if hasattr(self, 'run_tool') else None
    orbitals = nto.nto_orbitals(path, entry, configured)
    pair = entry.pairs[0]
    number = pair.hole if which == 'hole' else pair.particle
    index = nto.orbital_index(orbitals, pair.spin, number)
    title = tr(f'NTO состояния {entry.state}: ') + (tr('откуда') if which == 'hole' else tr('куда')) + f' {number}{pair.spin}'  # noqa: E501
    drawer = self.density_tool.open_density_drawer(orbitals, title, tab=0)
    if drawer is None or drawer.orbitals_table is None:
        return False
    drawer.orbitals_table.selectRow(index)
    return drawer.show_orbital()


def dos_orbitals(self):
    """(OrbitalSet, name) of the result for «Плотность состояний» — those of the panel of Compass when it
    has them (read once), else read now under a wait cursor."""
    drawer = getattr(self, 'density_drawer', None)
    if drawer is not None and drawer.panel is not None and getattr(self, 'density_key', None) \
            and self.density_key[0] == 'path' and self.density_key[1] == str(self.result_orbitals()):
        return drawer.orbital_set, drawer.panel.source
    from PySide6.QtWidgets import QApplication

    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        return self.load_result_orbitals() if hasattr(self, 'load_result_orbitals') else None
    finally:
        QApplication.restoreOverrideCursor()


def dos_shown(self, index):
    """The tab «Плотность состояний» opened — its orbitals read (once per result)."""
    if index == getattr(self, 'dos_tab', -1) and self.result_tabs.isTabVisible(index):
        return self.dos_panel.load()
    return False
