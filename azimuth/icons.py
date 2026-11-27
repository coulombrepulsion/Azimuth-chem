"""Original, scalable toolbar glyphs. No external icon assets or fonts."""

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QIconEngine, QPalette, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

GLYPHS = {
    'play': '<path d="M6 3l15 9-15 9z"/>',
    'pause': '<path d="M7 3v18M17 3v18"/>',
    'stop': '<rect x="5" y="5" width="14" height="14" rx="1"/>',
    'vectors': '<circle cx="6" cy="17" r="3"/><path d="M8 15L20 3M12 3h8v8M3 3l5 5"/>',
    'sun': '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2"/>',
    'moon': '<path d="M20 15A9 9 0 019 3a9 9 0 1011 12z"/>',
    'geometry-fragment': '<circle cx="5" cy="16" r="2.2"/><circle cx="12" cy="16" r="2.2"/><circle cx="19" cy="10" r="2.2"/><path d="M7.2 16h2.6M13.7 14.6l3.6-3.2M4 6.5h7.5M9.5 4.5l2 2-2 2"/>',
    'geometry-atom': '<circle cx="8" cy="15" r="4.5"/><path d="M15 6.5h6M18 3.5v6M3 6.5h7"/>',
    'menu': '<path d="M4 6.5h16M4 12h16M4 17.5h16"/>',
    # the molecules of the project (the list of the tab) — ☰ stays the drawer of the result
    'molecule-list': '<circle cx="5.5" cy="6.5" r="2"/><circle cx="5.5" cy="12" r="2"/><circle cx="5.5" cy="17.5" r="2"/><path d="M10 6.5h10M10 12h10M10 17.5h10"/>',
    'folder': '<path d="M3.5 7.5V18a1.5 1.5 0 001.5 1.5h14a1.5 1.5 0 001.5-1.5V9.5A1.5 1.5 0 0019 8h-7l-2-2.5H5A1.5 1.5 0 003.5 7v.5z"/>',
    'close': '<path d="M6 6l12 12M18 6L6 18"/>',
    'ruler': '<path d="M3.5 15.5L15.5 3.5l5 5-12 12z"/><path d="M7 12l1.8 1.8M9.8 9.2l1.2 1.2M12.4 6.6l1.8 1.8"/>',
    # the ruler with a small cross in the corner: nothing is selected — the button takes every measurement off the model
    'ruler_clear': '<path d="M3.5 15.5L15.5 3.5l5 5-12 12z"/><path d="M7 12l1.8 1.8M9.8 9.2l1.2 1.2M12.4 6.6l1.8 1.8"/>'
                   '<path d="M16.8 16.8l4.4 4.4M21.2 16.8l-4.4 4.4"/>',
    'move-selection': '<rect x="3.5" y="3.5" width="11" height="11" rx="2" stroke-dasharray="2.2 2.2"/><circle cx="9" cy="9" r="2"/><path d="M17 13v8M13 17h8M15.5 14.5L17 13l1.5 1.5M15.5 19.5L17 21l1.5-1.5M14.5 15.5L13 17l1.5 1.5M19.5 15.5L21 17l-1.5 1.5"/>',
    'lock': '<rect x="5" y="11" width="14" height="9.5" rx="2"/><path d="M8 11V8a4 4 0 018 0v3M12 15v2"/>',
    'cleanup': '<path d="M4 20l9-9M11 9l4 4"/><path d="M15.5 3.5l.9 2 2 .9-2 .9-.9 2-.9-2-2-.9 2-.9zM19.5 11l.6 1.3 1.3.6-1.3.6-.6 1.3-.6-1.3-1.3-.6 1.3-.6z"/>',
    'hydrogens': '<circle cx="9" cy="14" r="4.5"/><path d="M12.3 10.8l3.4-3.4"/><circle cx="17.8" cy="5.6" r="2.2"/><path d="M18 15v6M15 18h6"/>',
    'symmetry': '<path d="M12 3v18" stroke-dasharray="2.2 2.4"/><path d="M9.5 7L4 17h5.5zM14.5 7L20 17h-5.5z"/>',
    # «Эксперимент и конформеры» of the spectra — a flask
    'experiment': '<path d="M9.5 3.5h5M10.5 3.5v5.2L5 18.4a1.6 1.6 0 001.4 2.4h11.2a1.6 1.6 0 001.4-2.4l-5.5-9.7V3.5"/><path d="M7.4 14.5h9.2"/>',
    'overlay': '<circle cx="7" cy="15" r="2.6"/><circle cx="15" cy="8" r="2.6"/><path d="M8.9 13.2l4.2-3.4"/><circle cx="9.5" cy="16.5" r="2.6" stroke-dasharray="1.6 1.6"/><circle cx="17.5" cy="10" r="2.6" stroke-dasharray="1.6 1.6"/><path d="M11.5 15l3.9-3.3" stroke-dasharray="1.6 1.6"/>',
    'charges': '<circle cx="8" cy="9" r="5"/><path d="M5.6 9h4.8M8 6.6v4.8"/><circle cx="16.5" cy="15.5" r="4.5"/><path d="M14.3 15.5h4.4"/>',
    'iupac': '<path d="M3.5 12.2V4.5a1 1 0 011-1h7.7l8.6 8.6a1 1 0 010 1.4l-7.3 7.3a1 1 0 01-1.4 0z"/><circle cx="8" cy="8" r="1.5"/>',
    'step-prev': '<path d="M15 6l-6 6 6 6"/>',
    'step-next': '<path d="M9 6l6 6-6 6"/>',
    'best': '<circle cx="6" cy="15" r="2"/><circle cx="18" cy="15" r="2"/><circle cx="12" cy="7" r="2"/><path d="M7.2 13.4l3.6-4.8M16.8 13.4l-3.6-4.8M3 20.5h18"/>',
    'camera': '<path d="M4.5 8H7l1.5-2.5h7L17 8h2.5A1.5 1.5 0 0121 9.5v8a1.5 1.5 0 01-1.5 1.5h-15A1.5 1.5 0 013 17.5v-8A1.5 1.5 0 014.5 8z"/><circle cx="12" cy="13" r="3.3"/>',
    'zoom-in': '<circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5L20.5 20.5M8 10.5h5M10.5 8v5"/>',
    'zoom-out': '<circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5L20.5 20.5M8 10.5h5"/>',
    'pan-left': '<path d="M19 12H5M11 6l-6 6 6 6"/>',
    'pan-right': '<path d="M5 12h14M13 6l6 6-6 6"/>',
    'pan-up': '<path d="M12 19V5M6 11l6-6 6 6"/>',
    'pan-down': '<path d="M12 5v14M6 13l6 6 6-6"/>',
    # «Обзор / выделение» — the arrow of a pointer and the corner of a dashed frame of choosing
    'select': '<path d="M12 3.5h8.5v8.5" stroke-dasharray="2 2.2"/><path d="M5 4.5v14l3.7-3.4 2.7 5.6 2.4-1.1-2.7-5.5 5-.3z"/>',
    'edit': '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13 7l4 4"/>',
    'move': '<path d="M12 3v18M3 12h18M9.5 5.5L12 3l2.5 2.5M9.5 18.5L12 21l2.5-2.5M5.5 9.5L3 12l2.5 2.5M18.5 9.5L21 12l-2.5 2.5"/>',
    'center': '<path d="M4 8V5.5A1.5 1.5 0 015.5 4H8M16 4h2.5A1.5 1.5 0 0120 5.5V8M20 16v2.5a1.5 1.5 0 01-1.5 1.5H16M8 20H5.5A1.5 1.5 0 014 18.5V16"/><circle cx="12" cy="12" r="2.5"/>',
    'atom': '<circle cx="10" cy="14" r="6"/><path d="M18 3v6M15 6h6"/>',
    'element': '<rect x="3" y="9" width="18" height="11" rx="1.5"/><path d="M3 9V5.5h4V9M17 9V5.5h4V9M9 9v11M15 9v11M3 14.5h18"/>',
    'fragment': '<path d="M3 12h5"/><circle cx="10.5" cy="12" r="2.5"/><path d="M12.6 10.6l3.3-3.3M12.6 13.4l3.3 3.3"/><circle cx="17.8" cy="5.4" r="2"/><circle cx="17.8" cy="18.6" r="2"/>',
    'molecule': '<path d="M12 3l7.8 4.5v9L12 21l-7.8-4.5v-9z"/><circle cx="12" cy="12" r="3.6"/>',
    'move-atom': '<circle cx="12" cy="12" r="3.5"/><path d="M12 2.5v4M12 17.5v4M2.5 12h4M17.5 12h4M10.3 4.2L12 2.5l1.7 1.7M10.3 19.8l1.7 1.7 1.7-1.7M4.2 10.3L2.5 12l1.7 1.7M19.8 10.3l1.7 1.7-1.7 1.7"/>',
    'move-fragment': '<circle cx="5" cy="18" r="2.2"/><path d="M6.8 16.5l4.2-3.4"/><circle cx="13.3" cy="11.2" r="3"/><path d="M14.5 3.5a8.5 8.5 0 016.2 6.8M20.9 6.4v4h-4"/>',
    'move-molecule': '<circle cx="12" cy="8.5" r="2.2"/><circle cx="7.5" cy="15" r="2.2"/><circle cx="16.5" cy="15" r="2.2"/><path d="M10.8 10.3l-2 2.8M13.2 10.3l2 2.8M9.7 15h4.6"/><rect x="2.5" y="3" width="19" height="18" rx="3.5" stroke-dasharray="2.2 2.6"/>',
    # an unbranched chain (a zigzag of four atoms) for «Двигать цепочку»
    'move-chain': '<circle cx="4" cy="15" r="1.9"/><circle cx="9.5" cy="9" r="1.9"/><circle cx="15" cy="15" r="1.9"/><circle cx="20.5" cy="9" r="1.9"/><path d="M5.3 13.6l2.9-3.2M10.8 10.4l2.9 3.2M16.3 13.6l2.9-3.2"/><path d="M3 20.5h18" stroke-dasharray="2.2 2.4"/>',
    'axes': '<path d="M6 4v14h14M6 18l-3 3M3.8 6.2L6 4l2.2 2.2M17.8 15.8L20 18l-2.2 2.2"/>',
    'isometry': '<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z"/><path d="M4 7.5l8 4.5 8-4.5M12 12v9"/>',
    'perspective': '<path d="M4 9h10v11H4z"/><path d="M4 9l5-5h11v11l-6 5M14 9l6-5"/>',
    # «Взять цвет с экрана» — a pipette (its bulb up right, its tip down left)
    'pipette': '<path d="M13.2 6.8l4 4M15.2 8.8l2.6-2.6a2.1 2.1 0 00-3-3l-2.6 2.6"/><path d="M14.2 7.8L5.5 16.5 4 20l3.5-1.5 8.7-8.7"/>',
    'copy': '<rect x="8" y="8" width="12" height="13" rx="2"/><path d="M16 8V5a2 2 0 00-2-2H6a2 2 0 00-2 2v10a2 2 0 002 2h2"/>',
    'delete': '<path d="M4 7h16M9 7V4.5h6V7M6.5 7l1 13h9l1-13M10 11v5M14 11v5"/>',
    'undo': '<path d="M9 5L4 10l5 5"/><path d="M4 10h10a5 5 0 010 10h-3"/>',
    'redo': '<path d="M15 5l5 5-5 5"/><path d="M20 10H10a5 5 0 000 10h3"/>',
    'connect': '<circle cx="5" cy="12" r="2.5"/><circle cx="19" cy="12" r="2.5"/><path d="M7.5 12h9"/>',
    # the buttons «±» split — the bond orders (a double bond) and the vectors of a result (a dipole arrow)
    'bond-orders': '<circle cx="5" cy="12" r="2.5"/><circle cx="19" cy="12" r="2.5"/><path d="M7.5 10.3h9M7.5 13.7h9"/>',
    'dipole': '<path d="M3 12h16M15 8l4 4-4 4M6.5 9v6"/>',
    # «Убрать с модели всё наложенное» — an eraser over a baseline
    'clear-model': '<path d="M9.5 19.5L4 14l9-9 7 7-7.5 7.5z"/><path d="M8.5 9.5l7 7M13 19.5h7.5"/>',
    'disconnect': '<circle cx="5" cy="12" r="2.5"/><circle cx="19" cy="12" r="2.5"/><path d="M7.5 12h2.5M14 12h2.5M10.5 8l3 8"/>',
    'length-plus': '<path d="M3 12h18M6.5 8.5L3 12l3.5 3.5M17.5 8.5L21 12l-3.5 3.5"/>',
    'length-minus': '<path d="M3 12h6M15 12h6M5.5 8.5L9 12l-3.5 3.5M18.5 8.5L15 12l3.5 3.5"/>',
    'twist-plus': '<path d="M3 12h18"/><path d="M9 6.3A6 6 0 1 1 7.2 16"/><path d="M9 3v3.5H5.5"/>',
    # document tabs, the expanding buttons, the crystal section
    'plus': '<path d="M12 5v14M5 12h14"/>',
    # «Окно расчёта» on the card of the input file (the way back of «Входной файл», mirrored); the check of
    # the connection to a server; the advanced settings (sliders — the gear stays for the server profile)
    'forward': '<path d="M15 14l5-5-5-5"/><path d="M20 9H9.5a5.5 5.5 0 000 11H13"/>',
    'ping': '<path d="M4.5 10.5a10.5 10.5 0 0115 0M7.5 13.8a6.3 6.3 0 019 0"/><circle cx="12" cy="18" r="1.6"/>',
    'sliders': '<path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/><path d="M4 12h5M13 12h7"/><circle cx="11" cy="12" r="2"/>',
    'back': '<path d="M9 14L4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 010 11H11"/>',
    'expand': '<path d="M14 4h6v6M10 20H4v-6M20 4l-7 7M4 20l7-7"/>',  # the input file over the whole column
    'collapse': '<path d="M20 10h-6V4M4 14h6v6M14 10l7-7M10 14l-7 7"/>',  # back from the whole column
    # a cog with eight teeth
    'gear': '<path d="M18.80 9.64 L21.38 9.94 L21.38 14.06 L18.80 14.36 L18.48 15.14 L20.09 17.18 L17.18 20.09 L15.14 18.48 L14.36 18.80 L14.06 21.38 L9.94 21.38 L9.64 18.80 L8.86 18.48 L6.82 20.09 L3.91 17.18 L5.52 15.14 L5.20 14.36 L2.62 14.06 L2.62 9.94 L5.20 9.64 L5.52 8.86 L3.91 6.82 L6.82 3.91 L8.86 5.52 L9.64 5.20 L9.94 2.62 L14.06 2.62 L14.36 5.20 L15.14 5.52 L17.18 3.91 L20.09 6.82 L18.48 8.86Z"/><circle cx="12" cy="12" r="3.2"/>',
    'tidy-live': '<path d="M3.5 20.5l8-8M10 10.5l3.5 3.5"/><path d="M16 3l.8 1.8 1.8.8-1.8.8-.8 1.8-.8-1.8-1.8-.8 1.8-.8z"/><path d="M21 13.5a5 5 0 0 1-8.6 3.5"/><path d="M21 17.6v-4.1h-4.1"/>',
    'hydrogens-auto': '<circle cx="9" cy="14" r="4.5"/><path d="M12.3 10.8l3.4-3.4"/><circle cx="17.8" cy="5.6" r="2.2"/><path d="M21.5 18a3.5 3.5 0 1 1-1.1-2.6"/><path d="M21 13.2v2.6h-2.6"/>',
    'initial-geometry': '<circle cx="6.5" cy="16.5" r="2.8" stroke-dasharray="2.2 1.8"/><circle cx="17.5" cy="7.5" r="2.8" stroke-dasharray="2.2 1.8"/><path d="M8.8 14.6l6.4-5.2" stroke-dasharray="2 2"/><path d="M4 4.5h4.5M4 4.5v4.5"/>',
    # «Логарифмическая шкала» of a profile — axes, a curve and the marks of a log axis drawn closer and closer
    'log-scale': '<path d="M4 3.5v16.5h16.5"/><path d="M6.5 17c2.5-7 6-10.5 13-11.5"/><path d="M8 20v-1.8M12 20v-1.8M14.5 20v-1.8M16.2 20v-1.8M17.4 20v-1.8"/>',
    'save': '<path d="M5 3.5h11l3.5 3.5V19a1.5 1.5 0 01-1.5 1.5H5A1.5 1.5 0 013.5 19V5A1.5 1.5 0 015 3.5z"/><path d="M8 3.5V9h7V3.5M7.5 20.5v-6h9v6"/>',
    'minimize': '<path d="M6 18.5h12"/><path d="M12 4.5v9M8.5 10L12 13.5 15.5 10"/>',
    'hide': '<path d="M3 12s3.5-6 9-6 9 6 9 6-3.5 6-9 6-9-6-9-6z"/><circle cx="12" cy="12" r="2.5"/><path d="M4.5 19.5l15-15"/>',
    'window': '<rect x="3.5" y="4.5" width="17" height="15" rx="2"/><path d="M3.5 8.5h17M7 12.5h6M7 15.5h9"/>',
    'download': '<path d="M12 4v11M7.5 10.5L12 15l4.5-4.5M5 19.5h14"/>',
    'file-open': '<path d="M6.5 3.5h7.5l4.5 4.5V19a1.5 1.5 0 01-1.5 1.5h-10.5A1.5 1.5 0 015 19V5a1.5 1.5 0 011.5-1.5z"/><path d="M14 3.5V8h4.5M12 18v-6.5M9.25 14.25L12 11.5l2.75 2.75"/>',
    'check': '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    # the output file of a program (lines of text and a cursor at the end), the electron density (contours)
    'output': '<path d="M6.5 3.5h11A1.5 1.5 0 0119 5v14a1.5 1.5 0 01-1.5 1.5h-11A1.5 1.5 0 015 19V5a1.5 1.5 0 011.5-1.5z"/><path d="M8 8h8M8 11.5h8M8 15h4M14 15h2"/>',
    # where the calculation runs — this computer (a monitor) or a server (two units of a rack)
    'computer': '<rect x="3" y="4" width="18" height="12" rx="1.5"/><path d="M9 20h6M12 16v4"/>',
    'server': '<rect x="4" y="3.5" width="16" height="7" rx="1.5"/><rect x="4" y="13.5" width="16" height="7" rx="1.5"/><path d="M7.5 7h.5M7.5 17h.5M11 7h5.5M11 17h5.5"/>',
    'density': '<circle cx="12" cy="12" r="2"/><ellipse cx="12" cy="12" rx="5.5" ry="4.5"/><ellipse cx="12" cy="12" rx="9" ry="7.5" stroke-dasharray="2.2 2"/>',
    'search': '<circle cx="10.6" cy="10.6" r="6.4"/><path d="M15.3 15.3L19.6 19.6"/>',
    'crystal': '<path d="M5 8l7-4 7 4v8l-7 4-7-4z"/><path d="M5 8l7 4 7-4M12 12v8"/><circle cx="12" cy="4" r="1.3"/><circle cx="5" cy="8" r="1.3"/><circle cx="19" cy="8" r="1.3"/><circle cx="12" cy="12" r="1.3"/>',
    'cell': '<rect x="4" y="4" width="16" height="16" rx="1" stroke-dasharray="2.4 2.2"/><circle cx="4" cy="4" r="1.4"/><circle cx="20" cy="4" r="1.4"/><circle cx="4" cy="20" r="1.4"/><circle cx="20" cy="20" r="1.4"/><circle cx="12" cy="12" r="1.6"/>',
    'surface-slab': '<path d="M3 15l9-4 9 4-9 4z"/><path d="M3 15v2.5l9 4 9-4V15"/><circle cx="8" cy="11" r="1.3"/><circle cx="12" cy="9" r="1.3"/><circle cx="16" cy="11" r="1.3"/>',
    'twist-minus': '<path d="M3 12h18"/><path d="M15 6.3A6 6 0 1 0 16.8 16"/><path d="M15 3v3.5h3.5"/>',
    'next': '<path d="M5 5l9 7-9 7z"/><path d="M18 5v14"/>',  # «Пропустить» in a queue
    'queue': '<path d="M4 6h11M4 12h11M4 18h7"/><path d="M17 15l4 3-4 3z"/>',  # a queue of calculations
    # the ways between the model and the results — Spectrum (an axis with three bands of a spectrum) and
    # Compass (the ring and the needle of a compass)
    'spectrum': '<path d="M3 20h18"/><path d="M3.5 17.5c2 0 2.6-11 4.3-11s2.3 11 3.8 11 1.6-6.5 3.1-6.5 1.6 6.5 3.1 6.5h2.7"/>',
    'panel-toggle': '<path d="M9.5 6.5L4 12l5.5 5.5"/><path d="M14.5 6.5L20 12l-5.5 5.5"/>',  # ‹›
    'compass': '<circle cx="12" cy="12" r="8.5"/><path d="M15.6 8.4l-2.2 5-5 2.2 2.2-5z"/><path d="M12 2v1.5M12 20.5V22M2 12h1.5M20.5 12H22"/>',
}
from azimuth.button_icons import BUTTON_GLYPHS  # noqa: E402 — 0.91.67: the glyphs of the text buttons

GLYPHS.update({k: v for k, v in BUTTON_GLYPHS.items() if k not in GLYPHS})


class GlyphEngine(QIconEngine):
    def __init__(self, name, color=None, spark=False):
        super().__init__()
        self.name = name
        self.color = color  # a fixed colour (white on the blue «primary» buttons)
        self.spark = spark  # a small gold star at the top right (the icon beside a heading, 0.249.4)

    def clone(self):
        return GlyphEngine(self.name, self.color, self.spark)

    def pixmap(self, size, mode, state):
        pixmap = QPixmap(size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        try:
            self.paint(painter, pixmap.rect(), mode, state)
        finally:
            painter.end()
        return pixmap

    def scaledPixmap(self, size, mode, state, scale):
        """The glyph drawn at the pixels of the screen — Qt asks the pixmap of a scale (Windows 125 %, 150 %,
        Retina 200 %) here; without it the pixmap of the logical size was stretched and the icons were blurred."""
        from PySide6.QtCore import QSize

        scale = max(1.0, float(scale or 1.0))
        # a glyph drawn once is kept for its size, mode, state, scale and the palette
        key = (size.width(), size.height(), mode, state, scale, QApplication.palette().cacheKey())
        kept = self.__dict__.setdefault('_drawn', {})
        if key in kept:
            return kept[key]
        if len(kept) > 24:
            kept.clear()
        pixmap = QPixmap(QSize(max(1, round(size.width() * scale)), max(1, round(size.height() * scale))))
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        try:
            self.paint(painter, pixmap.rect(), mode, state)
        finally:
            painter.end()
        pixmap.setDevicePixelRatio(scale)
        kept[key] = pixmap
        return pixmap

    def paint(self, painter, rect, mode, state):
        palette = QApplication.palette()
        group = QPalette.ColorGroup.Disabled if mode == QIcon.Mode.Disabled else QPalette.ColorGroup.Active
        dark = palette.color(QPalette.ColorRole.Window).lightness() < 128
        # a checked button keeps a light tint, the glyph takes the accent colour
        color = (
            ('#6ea2f0' if dark else '#2a62b8')
            if state == QIcon.State.On
            else palette.color(group, QPalette.ColorRole.ButtonText).name()
        )
        if self.color:  # the blue button keeps its white glyph; greyed with the button
            color = '#95a4ae' if mode == QIcon.Mode.Disabled else self.color
        glyph = GLYPHS.get(self.name, '')
        if self.name.startswith('rotate-'):
            _, axis, direction = self.name.split('-')
            path = (
                'M5.5 9A7 7 0 1 1 5 14M5 4.5V9h4.5' if direction == 'plus' else 'M18.5 9A7 7 0 1 0 19 14M19 4.5V9h-4.5'
            )
            glyph = f'<path d="{path}"/><text x="12" y="15" fill="{color}" stroke="none" text-anchor="middle" font-family="sans-serif" font-size="8.5" font-weight="600">{axis.upper()}</text>'
        if self.name == 'label-custom':  # own labels — a tag
            glyph = '<path d="M3.5 12l5.5-6.5h11.5v13H9z"/><circle cx="9.6" cy="12" r="1.2"/><path d="M13 10h4.5M13 14h3"/>'
        elif self.name in ('label-number', 'label-element', 'label-both'):
            # only these three — «label-style» (the menu «Стиль подписей…») is a glyph of its own; the hover over
            # «Подписи атомов» raised KeyError 'style'
            text = {'number': '1', 'element': 'H', 'both': 'H1'}[self.name[6:]]
            glyph = f'<circle cx="12" cy="12" r="9"/><text x="12" y="15.6" fill="{color}" stroke="none" text-anchor="middle" font-family="sans-serif" font-size="{9 if len(text) > 1 else 10.5}" font-weight="600">{text}</text>'
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="{color}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{glyph}</g></svg>'
        painter.save()
        painter.translate(rect.x(), rect.y())
        painter.scale(rect.width() / 24, rect.height() / 24)
        from PySide6.QtCore import QRectF

        if self.spark:  # the glyph in the lower left 20 of 24, the star in the corner left free
            QSvgRenderer(QByteArray(svg.encode())).render(painter, QRectF(0, 4, 20, 20))
            gold = SPARK['dark' if dark else 'light']
            star = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="' + gold + '" d="M20 0.6l1 '
                    '2.6 2.6 1-2.6 1-1 2.6-1-2.6-2.6-1 2.6-1z"/></svg>')
            QSvgRenderer(QByteArray(star.encode())).render(painter, QRectF(0, 0, 24, 24))
        else:
            QSvgRenderer(QByteArray(svg.encode())).render(painter, QRectF(0, 0, 24, 24))
        painter.restore()


SPARK = {'light': '#c99a3a', 'dark': '#e2bf78'}  # the gold of the stars of the pictures of the program


def icon(name, color=None, spark=False):
    """spark — the icon of a heading: the glyph a little smaller, a gold four-pointed star at its top right (the gold
    of the headings moved from the line under them into their icons, 0.249.4)."""
    return QIcon(GlyphEngine(name, color, spark))


def iconify(button, name, title):
    from PySide6.QtCore import QSize

    # 34 px buttons with 20 px glyphs, styled by QPushButton[iconic="true"] in the theme
    button.setProperty('iconic', True)
    button.setStyleSheet('')
    button.setText('')
    button.setIcon(icon(name))
    button.setIconSize(QSize(21, 21))
    button.setFixedSize(34, 34)
    button.setToolTip(title)
    button.setAccessibleName(title.split(' · ')[0])
    button.setProperty('quail_icon', name)
    return button
