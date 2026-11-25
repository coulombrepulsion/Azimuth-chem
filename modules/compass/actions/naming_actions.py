"""Compass: the «IUPAC» button next to the molecule summary.

Pressing it names the built structure in the language of the program: by the rules of iupac.py; if they do
not cover it, from the program's names table (names.py); if the structure is not there either, PubChem is
asked in a worker thread (pubchem.py; English only, said so in the message line). The name replaces the
title in the summary until the connectivity changes; a change
of language renames it (except the English PubChem name).
"""

import threading

from PySide6.QtCore import QObject, Signal

from modules.compass.chemistry import iupac, pubchem
from modules.compass.chemistry.editing import perceived_orders
from azimuth.i18n import tr


class _Relay(QObject):
    """Brings the PubChem answer from the worker thread to the window's thread (queued signal)."""

    done = Signal(object)


def topology(molecule):
    """What a name depends on: the elements and the bonds with their orders."""
    bonds = sorted((min(i, j), max(i, j), o) for i, j, o in perceived_orders(molecule))
    return tuple(a.symbol for a in molecule.atoms), tuple(bonds)


def pubchem_problem(error):
    """What went wrong with a request to PubChem, for the message line (also for «Молекула по названию…»)."""
    why = pubchem.reason(error)
    return {
        'certificate': tr('PubChem: не удалось проверить сертификат сервера. Python с python.org не знает корневых сертификатов — запустите «Install Certificates.command» из папки Python в «Программах».'),
        'timeout': tr('PubChem не ответил вовремя — попробуйте ещё раз.'),
        'server': tr('PubChem ответил ошибкой: ') + str(getattr(error, 'code', '')),
    }.get(why, tr('PubChem недоступен — проверьте подключение к интернету.') + ' (' + str(getattr(error, 'reason', error))[:120] + ')')


class NamingTool:
    """Was the mixin NamingActions of the window; a tool of its own — it reaches the window only through the names of
    PORT (azimuth/window_port.WindowPort)."""

    PORT = (
        '_iupac',
        'coord_format',
        'coordinate_tool',
        'iupac_button',
        'molecule',
        'name_found',
        'notify',
        'symmetry_tool',
    )

    def __init__(self, window):
        from azimuth.window_port import WindowPort

        self.w = WindowPort(window, self.PORT)



    def iupac_title(self, molecule, lang):
        """The name to show instead of the title, or None."""
        state = self.w._iupac
        if not state or not molecule.atoms or state['key'] != topology(molecule):
            return None
        if state['source'] == 'pubchem':
            return state['pubchem']
        return self._own_name(molecule, lang)

    def _own_name(self, molecule, lang):
        from modules.compass.chemistry.names import name as table_name
        from modules.compass.chemistry.builder import connections

        found = iupac.name(molecule, lang)
        if found:
            return found
        return (
            table_name([a.symbol for a in molecule.atoms], [(i, j) for i, j, _ in connections(molecule)], lang) or None
        )

    def show_iupac_name(self):
        from modules.compass.workspace import LANG_CODE

        molecule = self.w.molecule
        if not molecule.atoms:
            self.w.notify(tr('Нечего называть: структура пустая.'))
            return
        key = topology(molecule)
        if iupac.name(molecule, LANG_CODE()):
            self.w._iupac = {'key': key, 'source': 'rules', 'pubchem': None}
            self.w.notify(tr('Название по правилам IUPAC.'))
            self.w.symmetry_tool.update_symmetry()
            self._named(molecule)
            return
        if self._own_name(molecule, LANG_CODE()):
            self.w._iupac = {'key': key, 'source': 'table', 'pubchem': None}
            self.w.notify(
                tr('Название из справочника программы: для этой структуры правила IUPAC в Компасе не написаны.')
            )
            self.w.symmetry_tool.update_symmetry()
            self._named(molecule)
            return
        smiles = pubchem.to_smiles(molecule)
        if not hasattr(self, '_naming_relay'):
            self._naming_relay = _Relay(self.w.widget)
            self._naming_relay.done.connect(self._pubchem_answer)
        self.w.iupac_button.setEnabled(False)
        self.w.notify(tr('Запрашиваю название в PubChem…'), 15000)
        relay = self._naming_relay

        def work():
            try:
                relay.done.emit((key, pubchem.lookup(smiles), None))
            except Exception as exc:  # no network, timeout, server error: reported in the window
                relay.done.emit((key, None, exc))

        threading.Thread(target=work, daemon=True).start()

    def _pubchem_answer(self, answer):
        key, found, error = answer
        self.w.iupac_button.setEnabled(True)
        if key != topology(self.w.molecule):
            return  # the structure changed while waiting
        if error is not None:  # say what went wrong, not always «no internet»
            self.w.notify(pubchem_problem(error), 15000)
            return
        if not found:
            self.w.notify(tr('Название не найдено: такой структуры нет ни в правилах Компаса, ни в PubChem.'), 10000)
            return
        self.w._iupac = {'key': key, 'source': 'pubchem', 'pubchem': found}
        self.w.notify(tr('Название из PubChem (только на английском).'), 10000)
        self.w.symmetry_tool.update_symmetry()
        self._named(self.w.molecule)

    def _named(self, molecule):
        """        the name found goes to the molecule of the project (ProjectNavigation.name_found)."""
        from modules.compass.workspace import LANG_CODE

        name = self.iupac_title(molecule, LANG_CODE())
        if name and self.w.has('name_found'):
            self.w.name_found(name)

    # -- InChI in the coordinates tab (from PubChem) --------------------------------------------------
    def inchi_text(self, molecule):
        """The text of «InChI» of the coordinates tab: InChI and InChIKey asked from PubChem once per structure (by
        its SMILES, in a worker thread); meanwhile and after a failure — a message."""
        if not molecule.atoms:
            return ''
        key = topology(molecule)
        cache = self.__dict__.setdefault('_inchi', {})
        if key in cache:
            found = cache[key]
            return f'{found[0]}\n{found[1]}' if isinstance(found, tuple) else found
        cache[key] = tr('Запрашиваю InChI в PubChem…')
        smiles = pubchem.to_smiles(molecule)
        if not hasattr(self, '_inchi_relay'):
            self._inchi_relay = _Relay(self.w.widget)
            self._inchi_relay.done.connect(self._inchi_answer)
        relay = self._inchi_relay

        def work():
            try:
                relay.done.emit((key, pubchem.lookup_inchi(smiles), None))
            except Exception as exc:  # no network, timeout, server error: said in the tab
                relay.done.emit((key, None, exc))

        threading.Thread(target=work, daemon=True).start()
        return cache[key]

    def _inchi_answer(self, answer):
        key, found, error = answer
        cache = self.__dict__.setdefault('_inchi', {})
        if error is not None:
            cache[key] = tr('InChI не получен: PubChem недоступен или не ответил. Выберите «InChI» ещё раз, чтобы повторить.')
        elif not found:
            cache[key] = tr('PubChem не знает такой структуры — InChI нет.')
        else:
            cache[key] = found
        if self.w.has('coord_format') and self.w.coord_format.currentText() == 'InChI':
            self.w.coordinate_tool.refresh_coordinates()

    def forget_failed_inchi(self):
        cache = self.__dict__.get('_inchi', {})
        for key in [k for k, v in cache.items() if not isinstance(v, tuple)]:
            del cache[key]
