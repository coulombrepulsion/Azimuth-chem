"""The elements for «Таблица Менделеева» of «Справка».

§1 PURPOSE
    The data of the window «Таблица Менделеева» (azimuth/element_window.py): the names, the ground
    state electron configurations, the electrons by shells (K, L, M …), the mean atomic mass and the isotopes.
§2 ALGORITHM
    configuration(Z): the subshells filled in the Madelung order (n + l, then n), 2(2l + 1) electrons each; the elements
    whose ground state differs from it (Cr, Cu, Nb … Pt, Au, the actinides, Lr) take theirs from EXCEPTIONS (NIST
    «Ground levels and ionization energies»); text(Z) — the core of the noble gas before it in brackets, the rest by
    n and l («[Ar] 3d⁶ 4s²»). shells(Z) — the electrons of each n. mean_mass(symbol) — Σ mass × abundance of
    azimuth/isotope_table.STABLE; an element without a natural composition — None, and LONGEST its mass number in
    brackets as the tables give it (the most stable isotope).
§4 SPECIFICATION
    NAMES {symbol: Russian name} (tr gives the English and Chinese); configuration(Z) -> {(n, l): electrons};
    text(Z) -> str; shells(Z) -> [electrons of n = 1, 2, …]; mean_mass(symbol) -> float | None; LONGEST {symbol: A}.
§7 TESTS tests/core/test_elements.py.
"""

from azimuth.core import SYMBOLS
from azimuth.isotope_table import STABLE, SUPERSCRIPT

NAMES = dict(zip(SYMBOLS[:118], (
    'Водород', 'Гелий', 'Литий', 'Бериллий', 'Бор', 'Углерод', 'Азот', 'Кислород', 'Фтор', 'Неон',
    'Натрий', 'Магний', 'Алюминий', 'Кремний', 'Фосфор', 'Сера', 'Хлор', 'Аргон', 'Калий', 'Кальций',
    'Скандий', 'Титан', 'Ванадий', 'Хром', 'Марганец', 'Железо', 'Кобальт', 'Никель', 'Медь', 'Цинк',
    'Галлий', 'Германий', 'Мышьяк', 'Селен', 'Бром', 'Криптон', 'Рубидий', 'Стронций', 'Иттрий', 'Цирконий',
    'Ниобий', 'Молибден', 'Технеций', 'Рутений', 'Родий', 'Палладий', 'Серебро', 'Кадмий', 'Индий', 'Олово',
    'Сурьма', 'Теллур', 'Йод', 'Ксенон', 'Цезий', 'Барий', 'Лантан', 'Церий', 'Празеодим', 'Неодим',
    'Прометий', 'Самарий', 'Европий', 'Гадолиний', 'Тербий', 'Диспрозий', 'Гольмий', 'Эрбий', 'Тулий', 'Иттербий',
    'Лютеций', 'Гафний', 'Тантал', 'Вольфрам', 'Рений', 'Осмий', 'Иридий', 'Платина', 'Золото', 'Ртуть',
    'Таллий', 'Свинец', 'Висмут', 'Полоний', 'Астат', 'Радон', 'Франций', 'Радий', 'Актиний', 'Торий',
    'Протактиний', 'Уран', 'Нептуний', 'Плутоний', 'Америций', 'Кюрий', 'Берклий', 'Калифорний', 'Эйнштейний',
    'Фермий', 'Менделевий', 'Нобелий', 'Лоуренсий', 'Резерфордий', 'Дубний', 'Сиборгий', 'Борий', 'Хассий',
    'Мейтнерий', 'Дармштадтий', 'Рентгений', 'Коперниций', 'Нихоний', 'Флеровий', 'Московий', 'Ливерморий',
    'Теннессин', 'Оганесон',
)))

# the mass number of the most stable isotope of an element without a natural composition (as in the tables, «[98]»)
LONGEST = {'Tc': 98, 'Pm': 145, 'Po': 209, 'At': 210, 'Rn': 222, 'Fr': 223, 'Ra': 226, 'Ac': 227, 'Np': 237,
           'Pu': 244, 'Am': 243, 'Cm': 247, 'Bk': 247, 'Cf': 251, 'Es': 252, 'Fm': 257, 'Md': 258, 'No': 259,
           'Lr': 266, 'Rf': 267, 'Db': 268, 'Sg': 269, 'Bh': 270, 'Hs': 269, 'Mt': 278, 'Ds': 281, 'Rg': 282,
           'Cn': 285, 'Nh': 286, 'Fl': 289, 'Mc': 290, 'Lv': 293, 'Ts': 294, 'Og': 294}

# the usual families of the periodic table,
# each with its pastel; the superheavy Nh–Lv are taken by their place (post-transition metals), Ts a halogen, Og a noble
# gas — as most tables colour them, though their chemistry is not known
CATEGORIES = (
    ('Щелочные металлы', '#f7cfcf', 'Li Na K Rb Cs Fr'),
    ('Щёлочноземельные металлы', '#fadcc0', 'Be Mg Ca Sr Ba Ra'),
    ('Переходные металлы', '#f5e9b8', 'Sc Ti V Cr Mn Fe Co Ni Cu Zn Y Zr Nb Mo Tc Ru Rh Pd Ag Cd Hf Ta W Re Os Ir Pt '
                                      'Au Hg Rf Db Sg Bh Hs Mt Ds Rg Cn'),
    ('Постпереходные металлы', '#d4ecc8', 'Al Ga In Sn Tl Pb Bi Po Nh Fl Mc Lv'),
    ('Полуметаллы', '#c9e8e1', 'B Si Ge As Sb Te'),
    ('Неметаллы', '#cfe0f7', 'H C N O P S Se'),
    ('Галогены', '#dcd3f5', 'F Cl Br I At Ts'),
    ('Благородные газы', '#f0d2ec', 'He Ne Ar Kr Xe Rn Og'),
    ('Лантаниды', '#e6f0c4', 'La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu'),
    ('Актиниды', '#e5d9cf', 'Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr'),
)
CATEGORY = {symbol: (name, colour) for name, colour, symbols in CATEGORIES for symbol in symbols.split()}

LETTERS = 'spdfghi'
NOBLE = {2: 'He', 10: 'Ne', 18: 'Ar', 36: 'Kr', 54: 'Xe', 86: 'Rn'}
# the ground states that are not the Madelung filling — the subshells after the noble-gas core
EXCEPTIONS = {
    'Cr': '3d5 4s1', 'Cu': '3d10 4s1', 'Nb': '4d4 5s1', 'Mo': '4d5 5s1', 'Ru': '4d7 5s1', 'Rh': '4d8 5s1',
    'Pd': '4d10', 'Ag': '4d10 5s1', 'La': '5d1 6s2', 'Ce': '4f1 5d1 6s2', 'Gd': '4f7 5d1 6s2',
    'Pt': '4f14 5d9 6s1', 'Au': '4f14 5d10 6s1', 'Ac': '6d1 7s2', 'Th': '6d2 7s2', 'Pa': '5f2 6d1 7s2',
    'U': '5f3 6d1 7s2', 'Np': '5f4 6d1 7s2', 'Cm': '5f7 6d1 7s2', 'Lr': '5f14 7s2 7p1',
}


def _madelung(z):
    order = sorted(((n, l) for n in range(1, 9) for l in range(0, n)), key=lambda s: (s[0] + s[1], s[0]))
    filled, left = {}, z
    for n, l in order:
        if left <= 0:
            break
        take = min(left, 2 * (2 * l + 1))
        filled[(n, l)] = take
        left -= take
    return filled


def _core(z):
    return max((k for k in NOBLE if k < z), default=0)


def configuration(z):
    """{(n, l): electrons} of the ground state of the element of atomic number z."""
    symbol = SYMBOLS[z - 1]
    if symbol not in EXCEPTIONS:
        return _madelung(z)
    filled = dict(_madelung(_core(z)))
    for part in EXCEPTIONS[symbol].split():
        n, l, count = int(part[0]), LETTERS.index(part[1]), int(part[2:])
        filled[(n, l)] = count
    return filled


def text(z):
    """«[Ar] 3d⁶ 4s²» — the core of the noble gas before the element, the rest by n and l."""
    filled = configuration(z)
    core = _core(z)
    inner = _madelung(core) if core else {}
    rest = {key: count for key, count in filled.items() if inner.get(key, 0) != count}
    parts = [f'{n}{LETTERS[l]}{str(count).translate(SUPERSCRIPT)}' for (n, l), count in sorted(rest.items())]
    return ' '.join(([f'[{NOBLE[core]}]'] if core else []) + parts)


def shells(z):
    """The electrons of each shell n = 1, 2, … (K, L, M …)."""
    filled = configuration(z)
    top = max(n for n, _ in filled)
    return [sum(c for (n, _), c in filled.items() if n == k) for k in range(1, top + 1)]


def mean_mass(symbol):
    """The mean atomic mass of the natural mixture (u), or None for an element without one."""
    rows = STABLE.get(symbol)
    if not rows:
        return None
    return sum(mass * share for _, mass, share in rows) / sum(share for *_, share in rows)
