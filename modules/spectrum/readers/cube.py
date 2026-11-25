"""Bounded Gaussian CUBE reader. Grid basis and geometry returned in angstrom."""

from dataclasses import dataclass
from io import StringIO
from math import prod
import warnings

import numpy as np
from azimuth.core import Atom, Molecule, SYMBOLS
from modules.compass.chemistry.geometry_tools import BOHR
from azimuth.i18n import tr

MAX_BYTES = 64_000_000
MAX_VALUES = 4_000_000


@dataclass(frozen=True)
class Cube:
    title: str
    molecule: Molecule
    origin: np.ndarray
    axes: np.ndarray  # row i: displacement of one grid increment along i
    values: np.ndarray  # x,y,z,dataset; z varies fastest in each dataset
    ids: tuple[int, ...]
    units: str


def read_cube(text):
    if len(text) > MAX_BYTES:
        raise ValueError(tr('CUBE: предел размера — 64 МБ.'))
    stream = StringIO(text)
    title = stream.readline().rstrip()
    comment = stream.readline().rstrip()

    def fields(count):
        row = stream.readline().split()
        if len(row) != count:
            raise ValueError(tr('CUBE: неполная или неподдерживаемая строка заголовка.'))
        return row

    def real(v):
        value = float(v.replace('D', 'E').replace('d', 'e'))
        if not np.isfinite(value):
            raise ValueError(tr('CUBE содержит нечисловые или бесконечные значения.'))
        return value

    try:
        head = stream.readline().split()
        if len(head) not in (4, 5):
            raise ValueError(tr('CUBE: неверный заголовок сетки.'))
        natoms = int(head[0])
        origin = np.array([real(v) for v in head[1:4]])
        nval = int(head[4]) if len(head) == 5 else 1
        if abs(natoms) > 500:
            raise ValueError(tr('CUBE: в этой версии не более 500 атомов.'))
        if not 1 <= nval <= 32:
            raise ValueError(tr('CUBE: неподдерживаемое число наборов данных.'))
        if natoms < 0 and nval != 1:
            raise ValueError(tr('CUBE: неоднозначное сочетание NVAL и списка орбиталей.'))
        dims = []
        axes = []
        for _ in range(3):
            row = fields(4)
            dims.append(int(row[0]))
            axes.append([real(v) for v in row[1:]])
        if any(abs(n) < 2 for n in dims):
            raise ValueError(tr('CUBE: нужно не менее двух точек вдоль каждой оси.'))
        if not (all(n > 0 for n in dims) or all(n < 0 for n in dims)):
            raise ValueError(tr('CUBE: смешанные знаки размерностей сетки — единицы неоднозначны.'))
        factor = BOHR if dims[0] > 0 else 1.0
        units = tr('боры → Å') if dims[0] > 0 else tr('Å (отрицательные размерности)')
        dims = tuple(abs(n) for n in dims)
        axes = np.array(axes) * factor
        origin *= factor
        if abs(np.linalg.det(axes)) < 1e-14:
            raise ValueError(tr('CUBE: вырожденные оси сетки.'))
        if prod(dims) > 2_000_000:
            raise ValueError(tr('CUBE: предел — 2 миллиона точек сетки.'))
        atoms = []
        for _ in range(abs(natoms)):
            row = fields(5)
            z = int(row[0])
            real(row[1])
            if not 1 <= z <= len(SYMBOLS):
                raise ValueError(tr('CUBE: фиктивные атомы и неизвестные элементы пока не поддержаны.'))
            atoms.append(Atom(SYMBOLS[z - 1], *(real(v) * factor for v in row[2:])))
        # the values are parsed by NumPy from the text, not through a list of
        # millions of strings (two more copies of the data while reading)
        rest = stream.read()
        ids = tuple(range(1, nval + 1))
        if natoms < 0:
            first = rest.split(None, 1)
            if not first:
                raise ValueError(tr('CUBE: отсутствует список орбиталей.'))
            nval = int(first[0])
            if not 1 <= nval <= 32:
                raise ValueError(tr('CUBE: число орбиталей должно быть от 1 до 32.'))
            listed = rest.split(None, nval + 1)
            ids = tuple(int(v) for v in listed[1 : 1 + nval])
            rest = listed[nval + 1] if len(listed) > nval + 1 else ''
            if len(ids) != nval or len(set(ids)) != nval:
                raise ValueError(tr('CUBE: неверный список орбиталей.'))
        expected = prod(dims) * nval
        if expected > MAX_VALUES:
            raise ValueError(tr('CUBE: слишком много значений; экспортируйте отдельную орбиталь.'))
        if 'D' in rest or 'd' in rest:  # Fortran exponents
            rest = rest.replace('D', 'E').replace('d', 'e')
        with warnings.catch_warnings():
            warnings.simplefilter('error')  # a word among the numbers: NumPy stops there and warns
            try:
                flat = np.fromstring(rest, dtype=np.float64, sep=' ')
            except (DeprecationWarning, ValueError) as exc:
                raise ValueError(tr('CUBE: не удалось прочитать числовые данные или заголовок.')) from exc
        if flat.size != expected:
            raise ValueError(
                tr(
                    f'CUBE: ожидалось {expected} значений, найдено {flat.size}. Файл неполный или формат не поддержан.'
                )
            )
        if not np.isfinite(flat).all():
            raise ValueError(tr('CUBE содержит нечисловые или бесконечные значения.'))
        values = flat.reshape((*dims, nval))
        if np.max(np.abs(values)) > np.finfo(np.float32).max:
            raise ValueError(tr('CUBE: значения превышают допустимый диапазон визуализатора.'))
        return Cube(title + ' · ' + comment, Molecule(title, tuple(atoms)), origin, axes, values, ids, units)
    except (ValueError, OverflowError) as exc:
        if str(exc).startswith('CUBE'):
            raise
        raise ValueError(tr('CUBE: не удалось прочитать числовые данные или заголовок.')) from exc


def demo_cube():
    """Analytic signed p-like field, deliberately not a molecular calculation."""
    n = 45
    axis = np.linspace(-4, 4, n)
    x, y, z = np.meshgrid(axis, axis, axis, indexing='ij')
    field = x * np.exp(-(x * x + y * y + z * z))
    return Cube(
        tr('УЧЕБНЫЙ ПРИМЕР · аналитическая p-подобная функция, не расчёт'),
        Molecule(tr('Учебный атом'), (Atom('H', 0, 0, 0),)),
        np.array([-4.0, -4.0, -4.0]),
        np.eye(3) * (8 / (n - 1)),
        field[..., None],
        (1,),
        tr('Å · учебный пример'),
    )
