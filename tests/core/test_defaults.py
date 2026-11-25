"""The defaults of «Файл → Настройки» (azimuth/defaults.py) and the code that follows them."""

from azimuth import defaults
from azimuth.core import Atom, Molecule
from modules.compass.chemistry import builder


class Store(dict):
    def value(self, key, default=None):
        return self.get(key, default)

    def setValue(self, key, value):
        self[key] = value


def test_values_of_the_settings_are_checked():
    try:
        # an INI file gives text; wrong or out of range — the default (the value fixed in the code before)
        store = Store(bond_factor='1.3', common_orientation='true', ir_style='bars', picture_scale='9', uv_fwhm='nan',
                      ir_width='35')
        got = defaults.load(store)
        assert got['bond_factor'] == 1.3 and got['common_orientation'] is True and got['ir_width'] == 35.0
        assert got['ir_style'] == 'sticks' and got['picture_scale'] == 3 and got['uv_fwhm'] == 0.3
        assert defaults.put('picture_crop', 'false', store) is False and store['picture_crop'] is False
        assert defaults.put('bond_order_min', 0.25, store) == 0.25 == defaults.get('bond_order_min')
        assert defaults.load(None) == {k: v[1] for k, v in defaults.KEYS.items()}
        assert defaults.get('bond_factor') == 1.22 and defaults.get('bond_order_min') == 0.5
    finally:
        defaults.reset()


def test_bonds_follow_the_factor():
    # two carbons 1.8 Å apart: 1.22 × (0.76 + 0.76) = 1.85 Å — a bond; at 1.10 × — 1.67 Å: none
    pair = Molecule('C2', (Atom('C', 0, 0, 0), Atom('C', 1.8, 0, 0)), None)
    try:
        assert builder.connections(pair) == ((0, 1, 1),)
        defaults.put('bond_factor', 1.10)
        assert builder.connections(pair) == ()  # the same molecule: the cache knows the factor
        defaults.put('bond_factor', 1.22)
        assert builder.connections(pair) == ((0, 1, 1),)
    finally:
        defaults.reset()


def test_energy_units():
    # 1 hartree = 627.509474 kcal/mol = 2625.499639 kJ/mol = 27.211386246 eV (CODATA 2018)
    try:
        assert defaults.energy_factor() == 627.509474 and defaults.energy_name() == 'ккал/моль'
        defaults.put('energy_unit', 'kj')
        assert abs(defaults.energy_factor() / 627.509474 - 4.184) < 1e-6  # the thermochemical calorie
        defaults.put('energy_unit', 'ev')
        assert defaults.energy_name() == 'эВ' and abs(defaults.energy_factor() - 27.211386246) < 1e-9
        assert defaults.put('energy_unit', 'cm-1') == 'kcal'  # not a choice: the default
        assert defaults.put('quick_atoms', '300') == 300 and defaults.put('quick_atoms', -1) == 0
    finally:
        defaults.reset()
