"""What is shown over the model of a crystal and built from it: the symmetry elements, the lattice nodes, a clicked
hydrogen bond, the ellipsoids, polyhedra, rings, tints, the range of coordinates, the network, the shell, the energy
framework. Methods of CrystalTool (self is the tool; the window only through its port self.w), kept here to make
crystal_actions.py shorter.

Split off modules/compass/actions/crystal_actions.py (0.222.30).
"""

from modules.compass.chemistry import crystal as cr
from modules.compass.chemistry import crystal_adp as adp
from modules.compass.chemistry import crystal_contacts as cc
from modules.compass.chemistry import crystal_symmetry as cs
from azimuth.i18n import tr


def symmetry_marks(self, data):
    """The elements of crystal_symmetry.elements in the coordinates of the model (A), or [] beyond the limit."""
    found = cs.elements(data)
    if len(found) > cs.ELEMENT_LIMIT:
        self.w.notify(tr('Элементов симметрии в ячейке {} — больше {}: не показаны.').format(len(found), cs.ELEMENT_LIMIT), 8000)
        return []
    cart = data.cell.cartesian
    items = []
    for e in found:
        g = e['frac']
        if e['kind'] in ('-1', '-3', '-4', '-6'):
            geometry = cart(g)
        else:
            geometry = tuple(cart(x) for x in g)
        items.append((e['symbol'], e['kind'], geometry))
    return items


def lattice_marks(self, data):
    """[(Cartesian point, centred)] — the nodes of the Bravais lattice of the block shown (its n₁ × n₂ × n₃
    cells); [] when the centring of the operations is unknown."""
    from modules.compass.chemistry import space_group_symbol as sg

    try:
        centring = cs.analyse(data).centring
    except ValueError:
        return []
    if centring not in sg.SHIFTS:
        return []
    crystal = getattr(self.w, 'crystal', None)
    n = tuple(int(k) for k in crystal[1]) if crystal and len(crystal) > 1 and len(crystal[1]) == 3 else (1, 1, 1)
    return [(data.cell.cartesian(f), any(abs(x - round(x)) > 1e-6 for x in f)) for f in sg.lattice_nodes(centring, n)]


def contact_clicked(self, h, a):
    """The hydrogen bond H···A under the mouse — its D–H···A, H···A and the
    angle in the status line; in «Компас · Кристалл» with the labels of the file, and its row chosen in an open
    «Контакты» window. Returns the text 'O2–H2A···O1' (the labels; in a molecule — element and number)."""
    from math import acos, degrees

    import numpy as np

    from modules.compass.chemistry.builder import connections

    molecule = self.w.viewer.molecule
    atoms = molecule.atoms
    donor = next((j if i == h else i for i, j, _ in connections(molecule) if h in (i, j)
                  and atoms[j if i == h else i].symbol != 'H'), None)
    crystal = getattr(self.w, 'crystal', None)
    data = crystal[0] if crystal and getattr(self.w, 'compass_mode', 'molecule') == 'crystal' else None
    if data is not None:
        cell = cr.unit_cell(data)
        vectors = np.array(data.cell.vectors(), float)
        inverse = np.linalg.inv(vectors)
        fractions = np.array([c[1:4] for c in cell], float)

        def label(k):
            f = np.array(atoms[k].position) @ inverse
            delta = (f - fractions) - np.round(f - fractions)
            near = int(np.argmin(np.linalg.norm(delta @ vectors, axis=1)))
            return cell[near][4] or f'{cell[near][0]}{near + 1}'
    else:
        def label(k):
            return f'{atoms[k].symbol}{k + 1}'
    text = (f'{label(donor)}–' if donor is not None else '') + f'{label(h)}···{label(a)}'
    ha = float(np.linalg.norm(np.subtract(atoms[a].position, atoms[h].position)))
    angle = None
    if donor is not None:
        u = np.subtract(atoms[donor].position, atoms[h].position)
        v = np.subtract(atoms[a].position, atoms[h].position)
        angle = degrees(acos(max(-1.0, min(1.0, float(u @ v / (np.linalg.norm(u) * np.linalg.norm(v)))))))
    said = text + tr(': H···A {} Å').format(f'{ha:.3f}') + (tr(', угол D–H···A {}°').format(f'{angle:.1f}') if angle else '')
    window = getattr(self, 'contacts_window', None)
    chosen = None
    try:  # in the side panel too (a window taken out of it is deleted)
        open_ = window is not None and not window.isHidden()
    except RuntimeError:
        open_ = False
    if data is not None and open_:
        rows = [k for k in range(window.table.rowCount()) if window.table.item(k, 1) is not None
                and window.table.item(k, 1).text() == text]
        if rows:
            chosen = min(rows, key=lambda k: abs(float(window.table.item(k, 2).text()) - ha))
            window.table.selectRow(chosen)
            window.table.scrollToItem(window.table.item(chosen, 1))
            said += tr(' — строка выбрана в «Контактах»')
    self.last_contact = (text, ha, angle, chosen)
    self.w.notify(said, 12000)
    return text


def set_lattice_shown(self, on, data=None):
    """The nodes of the Bravais lattice over the model."""
    self.lattice_shown = bool(on)
    crystal = getattr(self.w, 'crystal', None)
    data = data if data is not None else (crystal[0] if crystal else None)
    self.w.viewer.lattice_points = self.lattice_marks(data) if (on and data is not None) else None
    self.w.viewer.update()


def set_symmetry_shown(self, on, data=None):
    """The symmetry elements of the crystal of the tab over the model (in its first cell)."""
    self.symmetry_shown = bool(on)
    crystal = getattr(self.w, 'crystal', None)
    data = data if data is not None else (crystal[0] if crystal else None)
    self.w.viewer.symmetry_items = self.symmetry_marks(data) if (on and data is not None) else None
    self.w.viewer.update()


def to_calculation(self):
    """The arrow of «Компас · Кристалл»: the selected atoms — their molecules to «Компас · Молекула»
    (selection_to_molecule); nothing selected — Sextant, «Quantum ESPRESSO (кристалл)» on this crystal."""
    if list(getattr(self.w.viewer, 'selected', ())):
        return self.selection_to_molecule()
    if getattr(self.w, 'crystal', None) is None:
        self.w.notify(tr('Откройте файл CIF: «Файл → Открыть…».'), 8000)
        return None
    self.w.navigate(1)
    return True


def selection_to_molecule(self):
    """The molecules holding the selected atoms of the crystal tab (crystal_contacts.cut) go to a new tab of
    «Компас · Молекула» — a molecule with its neighbours, a dimer — ready for «К параметрам расчёта»."""
    molecule = self.w.own_molecule()
    chosen = list(getattr(self.w.viewer, 'selected', ()))
    if not molecule.atoms or not chosen:
        self.w.notify(tr('Выделите на модели хотя бы по одному атому молекул, которые нужно взять (Shift — несколько).'), 8000)
        return None
    part = cc.cut(molecule, chosen)
    title = tr('{} · фрагмент').format(getattr(self, 'crystal_name', '') or molecule.title or 'CIF')
    self.set_compass_mode('molecule')
    document = self.w.new_document(title, part)
    text = tr('В «Компас · Молекула»: {} атомов ({}). Дальше — «К параметрам расчёта».').format(len(part.atoms), part.formula)
    from modules.sextant.interaction import fragments

    if len(fragments(part)) == 2:  # a pair — the task of its interaction energy
        text += ' ' + tr('Для пары — задача «Энергия взаимодействия с BSSE (две молекулы)» (ORCA).')
    self.w.notify(text, 12000)
    return document


def set_ellipsoids_shown(self, on, data=None):
    """The displacement ellipsoids of the atoms of the shown crystal (crystal_adp.for_atoms)."""
    self.ellipsoids_shown = bool(on)
    crystal = getattr(self.w, 'crystal', None)
    data = data if data is not None else (crystal[0] if crystal else None)
    self._update_ellipsoids(data)


def set_polyhedra_shown(self, on):
    """The coordination polyhedra of the metals of the shown model (crystal_symmetry.polyhedra)."""
    self.polyhedra_shown = bool(on)
    self._update_polyhedra()


def set_ring_marks_shown(self, on):
    """The rings of the model, their centroids, π–π stacks and C–H···π (crystal_rings.model_marks)."""
    self.ring_marks_shown = bool(on)
    marks = self._update_ring_marks()
    if on and marks is not None:
        self.w.notify(tr('Колец: {}, π–π-стопок: {}, C–H···π: {} — на модели.').format(
            len(marks['rings']), len(marks['stacks']), len(marks['ch_pi'])), 10000)


def _update_ring_marks(self):
    from modules.compass.chemistry import crystal_rings as rg

    molecule = self.w.viewer.molecule
    marks = None
    if getattr(self, 'ring_marks_shown', False) and molecule is not None and molecule.atoms:
        marks = rg.model_marks(molecule)
        self.w.viewer.ring_marks = (molecule, marks)
    else:
        self.w.viewer.ring_marks = None
    self.w.viewer.update()
    return marks


def set_tints_shown(self, on):
    """The molecules of the model coloured by the operation that makes them (crystal_packing.colours)."""
    self.tints_shown = bool(on)
    legend = self._update_tints()
    if on and legend:
        self.w.notify(tr('Цвет — операция симметрии: ') + '; '.join(f'{text} ({count})' for _, text, count in legend[:6])
                      + ('…' if len(legend) > 6 else ''), 12000)


def _update_tints(self):
    from modules.compass.chemistry import crystal_packing as cp

    molecule = self.w.viewer.molecule
    crystal = getattr(self.w, 'crystal', None)
    legend = None
    if (getattr(self, 'tints_shown', False) and crystal and getattr(self.w, 'slab', None) is None
            and molecule is not None and molecule.atoms):
        self.w.viewer.atom_tints = (molecule, cp.colours(crystal[0], molecule))
        legend = cp.legend(crystal[0], molecule)
    else:
        self.w.viewer.atom_tints = None
    self.w.viewer.update()
    return legend


def build_range(self, data, lo, hi, whole=False):
    """The atoms (or whole molecules by their centroids) within lo ≤ (x, y, z) ≤ hi, fractional."""
    from modules.compass.chemistry import crystal_packing as cp

    self.set_compass_mode('crystal')
    try:
        molecule = cp.build_range(data, lo, hi, whole)
    except ValueError as exc:
        self.w.error(exc)
        return False
    if not self.crystal_tab(getattr(self, 'crystal_name', '') or data.title):
        return False
    self.w.crystal = (data, (1, 1, 1), False, bool(whole))
    self.crystal_range = (tuple(lo), tuple(hi))
    self.w.slab = None
    self.w.viewer.symmetry_items = self.symmetry_marks(data) if getattr(self, 'symmetry_shown', False) else None
    self.w.viewer.lattice_points = self.lattice_marks(data) if getattr(self, 'lattice_shown', False) else None
    self.w.load_molecule(molecule)
    self._update_ellipsoids(data)
    self._update_polyhedra()
    self.w.viewer.cell_lines = cr.cell_edges(data.cell) if getattr(self, 'cell_shown', True) else None
    self.w.viewer.update()
    self._built()
    self.w.notify(tr('Кристалл: {} атомов в диапазоне координат.').format(len(molecule.atoms)), 10000)
    return True


def _update_polyhedra(self):
    molecule = self.w.viewer.molecule
    if getattr(self, 'polyhedra_shown', False) and molecule is not None and molecule.atoms:
        found = cs.polyhedra(molecule)
        self.w.viewer.polyhedra = (molecule, [(symbol, faces) for _, symbol, faces in found])
    else:
        self.w.viewer.polyhedra = None
    self.w.viewer.update()


def _update_ellipsoids(self, data):
    molecule = self.w.viewer.molecule
    if getattr(self, 'ellipsoids_shown', False) and data is not None and molecule is not None and molecule.atoms:
        self.w.viewer.ellipsoids = (molecule, adp.for_atoms(data, [a.position for a in molecule.atoms]))
    else:
        self.w.viewer.ellipsoids = None
    self.w.viewer.update()


def build_network(self, data, kinds=('hydrogen',), criteria=None, layers=1, chosen=None):
    """The molecules of the cell and those the hydrogen bonds join to them (crystal_contacts.network);
    or the bonds of the kinds given (σ-hole bonds, all the specific ones); with the criteria of
    the «Контакты» window; the π–π stacks and the C–H···π ('pi', 'ch_pi'); grown layers times,
    only by the contacts chosen (the rows picked)."""
    self.set_compass_mode('crystal')
    try:
        molecule, added = cc.network(data, kinds, layers=layers, chosen=chosen, **(criteria or {}))
    except ValueError as exc:
        self.w.error(exc)
        return False
    if not molecule.atoms:
        self.w.notify(tr('В этом кристалле нет отдельных молекул — сети молекул нет.'), 8000)
        return False
    if not self.crystal_tab(getattr(self, 'crystal_name', '') or data.title):
        return False
    self.w.crystal = (data, (1, 1, 1), False, True)
    self.w.slab = None
    self.w.viewer.symmetry_items = self.symmetry_marks(data) if getattr(self, 'symmetry_shown', False) else None
    self.w.viewer.lattice_points = self.lattice_marks(data) if getattr(self, 'lattice_shown', False) else None
    self.w.load_molecule(molecule)
    self._built()
    self.network_on = True
    self._update_ellipsoids(data)
    self._update_polyhedra()
    self.w.viewer.cell_lines = cr.cell_edges(data.cell) if getattr(self, 'cell_shown', True) else None
    self.w.viewer.update()
    # the contacts of the network drawn as lines
    lines = 0
    plain = tuple(k for k in kinds if k not in cc.PI_KINDS)
    if plain:
        try:
            found = [c for c in cc.contacts(data, **(criteria or {})) if c.kind in plain]
            if chosen is not None:
                found = list(chosen)
            lines = self.show_contacts_on_model(data, found, plain)
        except ValueError:
            lines = 0
    text = (tr('Сеть водородных связей: молекулы ячейки и {} соседних молекул, {} атомов.') if tuple(kinds) == ('hydrogen',)
            else tr('Сеть контактов: молекулы ячейки и {} соседних молекул, {} атомов.'))
    self.w.notify(text.format(added, len(molecule.atoms)) + (tr(' Контактов на модели: {} — пунктиром.').format(lines)
                                                              if lines else ''), 10000)
    return True


def build_shell(self, data, found):
    """The molecular shell (crystal_shell.Shell) on the model, its centre selected."""
    self.set_compass_mode('crystal')
    if not self.crystal_tab(getattr(self, 'crystal_name', '') or data.title):
        return False
    self.w.crystal = (data, (1, 1, 1), False, True)
    self.w.slab = None
    self.w.viewer.symmetry_items = self.symmetry_marks(data) if getattr(self, 'symmetry_shown', False) else None
    self.w.viewer.lattice_points = self.lattice_marks(data) if getattr(self, 'lattice_shown', False) else None
    self.w.load_molecule(found.molecule)
    self._built()
    self._update_ellipsoids(data)
    self._update_polyhedra()
    self.w.viewer.cell_lines = cr.cell_edges(data.cell) if getattr(self, 'cell_shown', True) else None
    self.w.viewer.set_selection(range(found.centre_atoms))
    self.w.viewer.update()
    self.w.notify(tr('Молекулярная оболочка: {} соседних молекул, {} атомов; центр выделен.').format(
        len(found.neighbours), len(found.molecule.atoms)), 10000)
    return True


def show_energy_frame(self, data, plan, result):
    """The molecule, its neighbours (the shell of crystal_pairs.plan) and the energy framework over them."""
    from modules.compass.chemistry import crystal_pairs

    if not self.build_shell(data, plan.shell):
        return False
    cylinders = crystal_pairs.frame(result, plan.centroids[0], plan.centroids[1])
    self.w.viewer.energy_frame = (self.w.viewer.molecule, cylinders)
    self.w.viewer.update()
    self.w.notify(tr('Энергетический каркас: синие — притяжение, толщина — по энергии пары; самая сильная пара '
                     '{} кДж/моль.').format(f'{min((x.energy for x in result.pairs if x.energy is not None), default=0):.1f}'),
                  10000)
    return True


def show_hirshfeld_model(self, data, surf):
    """The molecule of a Hirshfeld surface and its neighbours (crystal_hirshfeld.Surface; the H at their
    neutron distances) on the model, the molecule selected; returns the molecule shown, or None."""
    from types import SimpleNamespace

    from azimuth.core import Atom, Molecule

    found = SimpleNamespace(
        molecule=Molecule(surf.molecule.title, tuple(Atom(s, x, y, z) for s, x, y, z in surf.atoms + surf.others),
                          None),
        centre_atoms=len(surf.atoms), neighbours=())
    if not self.build_shell(data, found):
        return None
    self.w.notify(tr('Поверхность Хиршфельда: молекула выделена, вокруг — её соседи.'), 8000)
    return self.w.own_molecule()
