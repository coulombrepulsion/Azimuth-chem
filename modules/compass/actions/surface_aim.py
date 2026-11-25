"""The critical points and bond paths of QTAIM on the model of Compass: shown, the weak contacts kept, the kinds
followed, the point chosen let go, the buttons of the panels. Methods of SurfaceTool (self is the tool; the window only
through its port self.w), kept here to make surface_actions.py shorter.

Split off modules/compass/actions/surface_actions.py (0.222.30).
"""

import numpy as np


def show_aim(self, topology, orbital_set, title='', selected=None, labels=None, go=True, contacts=None):
    """The critical points and bond paths of a Topology (modules/spectrum/analysis/density.py) on the model;
    the nuclei (3, −3) are points too when given; selected — the position (Å) of the point marked;
    labels — the numbers of the table (n1, b1 …) of topology.points, drawn next to them; go=False — Compass is
    not shown (Spectrum changes the points without leaving); contacts — (i, j, kind) of the weak
    interactions the search named (modules/spectrum/analysis/contacts.py), drawn as bonds of their kind."""
    frame = self.structure_frame(orbital_set.molecule, title)
    if frame is None:
        return False

    def put(points):
        return (np.asarray(points, float) - frame['from']) @ frame['rotation'] + frame['to']

    self.w.viewer.aim = {
        'atoms': self.w.molecule.atoms,
        'points': [(p.kind, put(p.position[None])[0]) for p in topology.points],
        'paths': [put(path) for path in topology.paths],
        'selected': None if selected is None else put(np.asarray(selected, float)[None])[0],
        'labels': list(labels) if labels is not None and len(labels) == len(topology.points) else [],
    }
    if contacts is not None:
        # the lines of the weak
        # interactions stay when the points are taken away — while the structure is the same
        self.w.viewer.found_contacts = {'atoms': self.w.molecule.atoms, 'contacts': list(contacts)}
    self.w.viewer.update()
    self.sync_aim_buttons(True)
    self.follow_aim_kind(topology)
    if go and self.w.has('navigate'):
        self.w.navigate(0)
    return True


def keep_contacts(self, orbital_set, contacts):
    """The weak interactions of a search onto the model at once (found_contacts) — only when the model
    shows the structure of these orbitals (the same atoms in the same order): nothing is replaced or asked."""
    from modules.compass.view import result_overlay
    from modules.spectrum.readers.orca_properties import Properties

    if not self.w.molecule or not self.w.molecule.atoms:
        return False
    if result_overlay.match(Properties(orbital_set.molecule), self.w.coordinate_tool.table_molecule()) is None:
        return False
    self.w.viewer.found_contacts = {'atoms': self.w.molecule.atoms, 'contacts': list(contacts)}
    self.w.viewer.update()
    return True


def follow_aim_kind(self, topology):
    """The list of kinds of the panel of Compass
    shows the kind of the points put on the model (all when they are of several kinds)."""
    kinds = {p.kind for p in topology.points}
    key = kinds.pop() if len(kinds) == 1 else 'all'
    for panel in self.aim_panels():
        if not getattr(panel, 'compact', False):
            continue
        try:
            panel.follow_kind(key)
        except (RuntimeError, AttributeError):
            pass


def unmark_aim(self):
    """A click on the empty field of the model lets the point chosen go — its ring, and its row in the tables of the
    points."""
    aim = getattr(self.w.viewer, 'aim', None)
    if not aim or aim.get('selected') is None:
        return False
    for panel in self.aim_panels():
        try:
            panel.table.clearSelection()
        except (RuntimeError, AttributeError):
            pass
    if self.w.viewer.aim:
        self.w.viewer.aim['selected'] = None
    self.w.viewer.update()
    return True


def clear_aim(self):
    self.w.viewer.aim = None
    self.w.viewer.update()
    self.sync_aim_buttons(False)


def aim_panels(self):
    """The views of the critical points whose button «На модель / Убрать с модели» follows the model."""
    panels = []
    drawer = getattr(self.w, 'density_drawer', None)
    if drawer is not None and drawer.panel is not None:
        panels.append(drawer.panel)
    if getattr(self.w, 'topology_panel', None) is not None:
        panels.append(self.w.topology_panel)
    dialog = getattr(self.w, 'orbitals_dialog', None)
    try:
        analysis = getattr(dialog, 'density_dialog', None) if dialog is not None else None
        if analysis is not None:
            analysis.isVisible()  # raises when already deleted
            panels.append(analysis)
    except RuntimeError:
        pass
    return panels


def sync_aim_buttons(self, shown):
    for panel in self.aim_panels():
        try:
            panel.sync_model_button(shown and panel.topology is not None)
        except (RuntimeError, AttributeError):
            pass
