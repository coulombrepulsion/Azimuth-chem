"""Small pictures of states in thin lines: the windows of the program show them where Quill stood until 0.247.0.

§0 STATE
    0.247.0 (2026-11-27, the owner: «квил в самой программе не нужна. Пусть она остается в Атласе как помощник, а в
    программе ее убрать и заменить на более минималистичные картинки/иконки»; the set approved on a mock-up: «И иконки
    подойдут»). Quill stays on the site (the Atlas) and in assets/quill/ for it.
§1 PURPOSE
    One picture for each name of azimuth.quill.NAMES: the states of a calculation, the empty places, the questions and
    the warnings. Thin lines (1.3 of 48) in one blue that reads on the light and on the dark page (INK); gold marks a
    state (#c99a3a), red-orange a failure (#d0603a) — written into the drawings.
§2 ALGORITHM
    svg(name) puts the drawing of PICTURES (48 × 48, «currentColor» for the ink) into an SVG document;
    pixmap(name, size, ratio) draws it by QSvgRenderer on a transparent picture of size × size logical pixels.
§4 SPECIFICATION
    INK; PICTURES {name: (what it shows, the drawing)}; ALIASES {name of Quill: name here};
    svg(name, ink=INK) -> str; pixmap(name, size, ratio=1.0, ink=INK) -> QPixmap (null for an unknown name).
§7 TESTS
    tests/core/test_state_icons.py.
"""

from __future__ import annotations

INK = '#4f86d6'  # between the blue of the light theme (#2a62b8) and of the dark one (#6ea2f0): reads on both

PICTURES = {
    'calc-running': ('Расчёт идёт',
     '<circle cx="24" cy="24" r="21" stroke-opacity="0.35"/><path d="M24 24V9" /><path d="M24 24l9 6" stroke-opacity="0.6"/><circle cx="24" cy="24" r="1.6" fill="currentColor"/><path d="M24 3a21 21 0 0 1 18.2 10.5" stroke="#c99a3a" stroke-width="2"/>'),
    'calc-done': ('Расчёт закончен',
     '<circle cx="24" cy="24" r="21" stroke-opacity="0.35"/><path d="M15 24.5l6 6 12-13" stroke-width="1.8"/><path d="M24 3l1.6 3.4L29 8l-3.4 1.6L24 13l-1.6-3.4L19 8l3.4-1.6z" stroke="#c99a3a" fill="none"/>'),
    'calc-failed': ('Расчёт не удался',
     '<circle cx="24" cy="24" r="21" stroke-opacity="0.35"/><path d="M24 13v14" stroke="#d0603a" stroke-width="1.8"/><circle cx="24" cy="33" r="1.4" fill="#d0603a" stroke="none"/>'),
    'calc-stopped': ('Расчёт остановлен',
     '<circle cx="24" cy="24" r="21" stroke-opacity="0.35"/><rect x="16.5" y="16.5" width="15" height="15" rx="2"/>'),
    'stop-running': ('Остановить идущий расчёт?',
     '<circle cx="24" cy="24" r="21" stroke-opacity="0.35"/><path d="M24 24V10"/><circle cx="24" cy="24" r="1.6" fill="currentColor"/><path d="M33 33l6 6M39 33l-6 6" stroke="#d0603a"/>'),
    'empty-model': ('Пустое поле Компаса',
     '<circle cx="24" cy="24" r="21" stroke-opacity="0.25" stroke-dasharray="2 3"/><circle cx="24" cy="20" r="5"/><circle cx="15" cy="30" r="3.2"/><circle cx="33" cy="30" r="3.2"/><path d="M20.5 23l-3.2 4.5M27.5 23l3.2 4.5" stroke-opacity="0.6"/><path d="M36 10v6M33 13h6" stroke="#c99a3a"/>'),
    'empty-crystal': ('Пустое поле кристалла',
     '<path d="M12 18l12-7 12 7v14l-12 7-12-7z" stroke-opacity="0.8"/><path d="M12 18l12 7 12-7M24 25v14" stroke-opacity="0.45"/><path d="M38 8v6M35 11h6" stroke="#c99a3a"/>'),
    'empty-result': ('Пустой Спектр',
     '<path d="M7 38h34M7 38V10" stroke-opacity="0.5"/><path d="M9 37c4 0 5-2 7-9s3-9 4-9 2 4 3 9 2 9 5 9 3-4 4-12 2-11 3-11 2 6 3 12 2 11 4 11" /><path d="M37 8l1 2.2 2.2 1-2.2 1-1 2.2-1-2.2-2.2-1 2.2-1z" stroke="#c99a3a"/>'),
    'sextant-empty': ('Расчёт без атомов',
     '<path d="M8 40A32 32 0 0 1 40 8" stroke-opacity="0.45"/><path d="M8 40L34 14" stroke-dasharray="2 3"/><circle cx="8" cy="40" r="2" fill="currentColor"/><path d="M38 9l1 2.2 2.2 1-2.2 1-1 2.2-1-2.2-2.2-1 2.2-1z" stroke="#c99a3a"/>'),
    'no-orbitals': ('Орбиталей нет',
     '<ellipse cx="24" cy="16" rx="7" ry="9" stroke-dasharray="2.5 2.5"/><ellipse cx="24" cy="32" rx="7" ry="9" stroke-dasharray="2.5 2.5"/><circle cx="24" cy="24" r="1.6" fill="currentColor"/>'),
    'no-points': ('Точек ещё нет',
     '<circle cx="14" cy="16" r="3" stroke-dasharray="2 2"/><circle cx="34" cy="14" r="3" stroke-dasharray="2 2"/><circle cx="24" cy="33" r="3" stroke-dasharray="2 2"/><path d="M17 17l14-2.5M15.5 19l7 11M32.5 17l-7 13" stroke-opacity="0.3"/>'),
    'nothing-found': ('Ничего не найдено',
     '<circle cx="21" cy="21" r="12"/><path d="M30 30l10 10" stroke-width="1.8"/><path d="M16 21h10" stroke-opacity="0.5"/>'),
    'file-unreadable': ('Файл не прочитан',
     '<path d="M13 6h15l8 8v28H13z"/><path d="M28 6v8h8" stroke-opacity="0.6"/><path d="M19 24l10 10M29 24L19 34" stroke="#d0603a"/>'),
    'error': ('Не удалось выполнить действие',
     '<path d="M24 6l20 35H4z"/><path d="M24 18v11" stroke="#d0603a" stroke-width="1.8"/><circle cx="24" cy="34" r="1.4" fill="#d0603a" stroke="none"/>'),
    'offline': ('Нет связи с сервером',
     '<rect x="9" y="8" width="30" height="10" rx="2"/><rect x="9" y="22" width="30" height="10" rx="2"/><circle cx="14" cy="13" r="1.2" fill="currentColor"/><circle cx="14" cy="27" r="1.2" fill="currentColor"/><path d="M24 36v5M17 41h14" stroke-opacity="0.5"/><path d="M30 37l8 8M38 37l-8 8" stroke="#d0603a"/>'),
    'program-missing': ('Программа не найдена',
     '<rect x="6" y="9" width="36" height="28" rx="3"/><path d="M6 15h36" stroke-opacity="0.5"/><path d="M12 22l5 4-5 4" /><path d="M21 30h7" stroke-dasharray="2 2"/><path d="M33 27a4 4 0 1 1 4 4v2M37 36.5v.2" stroke="#c99a3a"/>'),
    'install': ('Установка программ',
     '<path d="M24 6v22M16 20l8 8 8-8"/><path d="M8 32v8h32v-8" stroke-opacity="0.6"/>'),
    'input-check': ('Проверка входного файла',
     '<path d="M11 6h18l8 8v28H11z"/><path d="M16 18h13M16 24h16M16 30h9" stroke-opacity="0.5"/><path d="M28 34l3.5 3.5L38 30" stroke="#c99a3a" stroke-width="1.8"/>'),
    'save': ('Сохранить изменения?',
     '<path d="M9 9h24l6 6v24H9z"/><path d="M15 9v9h16V9" stroke-opacity="0.6"/><rect x="15" y="26" width="18" height="13" stroke-opacity="0.6"/><path d="M41 4l1 2.2 2.2 1-2.2 1-1 2.2-1-2.2-2.2-1 2.2-1z" stroke="#c99a3a"/>'),
    'delete': ('Удалить / заменить',
     '<path d="M10 13h28M19 13V8h10v5"/><path d="M13 13l2 27h18l2-27"/><path d="M21 19v15M27 19v15" stroke-opacity="0.5"/>'),
    'journal': ('Что нового',
     '<path d="M24 11c-5-3-11-3-17-1v28c6-2 12-2 17 1 5-3 11-3 17-1V10c-6-2-12-2-17 1z"/><path d="M24 11v28" stroke-opacity="0.5"/><path d="M33 4l1 2.2 2.2 1-2.2 1-1 2.2-1-2.2-2.2-1 2.2-1z" stroke="#c99a3a"/>'),
    'notes': ('Заметки',
     '<path d="M12 6h24v36H12z"/><path d="M17 14h14M17 20h14M17 26h9" stroke-opacity="0.5"/><path d="M30 34l8-8 3 3-8 8h-3z" stroke="#c99a3a"/>'),
    'home-desk': ('Главная',
     '<circle cx="24" cy="24" r="21" stroke-opacity="0.35"/><circle cx="24" cy="24" r="15" stroke-opacity="0.25"/><path d="M24 9l3.5 15L24 39l-3.5-15z"/><path d="M24 9l3.5 15h-7z" fill="currentColor" fill-opacity="0.25" stroke="none"/>'),
}
# the names of the pictures of Quill without one of their own here
ALIASES = {'empty-model-mirrored': 'empty-model'}


def svg(name, ink=INK):
    """The SVG document of a picture ('' for an unknown name)."""
    name = ALIASES.get(name, name)
    if name not in PICTURES:
        return ''
    body = PICTURES[name][1].replace('currentColor', ink)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" fill="none" '
            f'stroke="{ink}" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round">{body}</svg>')


def pixmap(name, size, ratio=1.0, ink=INK):
    from PySide6.QtCore import QByteArray, QRectF, Qt
    from PySide6.QtGui import QPainter, QPixmap
    from PySide6.QtSvg import QSvgRenderer

    text = svg(name, ink)
    if not text:
        return QPixmap()
    ratio = max(1.0, float(ratio))
    side = max(1, round(size * ratio))
    picture = QPixmap(side, side)
    picture.fill(Qt.GlobalColor.transparent)
    renderer = QSvgRenderer(QByteArray(text.encode('utf-8')))
    painter = QPainter(picture)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, side, side))
    painter.end()
    picture.setDevicePixelRatio(ratio)
    return picture
