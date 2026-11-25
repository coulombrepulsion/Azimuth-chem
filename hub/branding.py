"""Hub drawing helpers: SVG icons in currentColor, the Azimuth wordmark, the sidebar typeface (moved from window.py)."""

from PySide6.QtCore import (
    QByteArray,
    QPointF,
    QRectF,
    Qt,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QFontMetricsF,
    QIcon,
    QIconEngine,
    QPainter,
    QPixmap,
    QPolygonF,
)
from PySide6.QtSvg import QSvgRenderer

from azimuth.icons import GLYPHS
from azimuth.paths import ROOT
from hub.texts import NAV_ACTIVE, NAV_COLOR, TEXT

# the side panel follows the theme — light: grey with a little blue and dark ink; dark: deep navy
SIDEBAR = {'nav': NAV_COLOR, 'active': NAV_ACTIVE, 'disabled': '#465264'}
SIDEBAR_THEMES = {
    False: {'nav': '#4b5a6e', 'active': '#2a62b8', 'disabled': '#a4afbd'},
    True: {'nav': NAV_COLOR, 'active': NAV_ACTIVE, 'disabled': '#465264'},
}


def set_sidebar_theme(dark):
    SIDEBAR.update(SIDEBAR_THEMES[bool(dark)])


BROWN = ('#b8893f', '#d6a95c')  # the light brown of the glyph's arrow (on light / on dark), as the З / Z


def brown_for(color):
    """The brown accent of the section icons (currentBrown in assets/navigation/*.svg) next to strokes of
    color: the stronger brown next to a dark stroke (light theme), the lighter one next to a light stroke."""
    c = QColor(color)
    light = (0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()) / 255 > 0.5
    return BROWN[1] if light else BROWN[0]


def paint_svg(svg, color):
    """The SVG text with currentColor and currentBrown filled in."""
    return svg.replace('currentBrown', brown_for(color)).replace('currentColor', color)


class SvgIconEngine(QIconEngine):
    """Navigation SVG drawn with currentColor: muted when off, white when the button is checked."""

    def __init__(self, svg):
        super().__init__()
        self.svg = svg

    def clone(self):
        return SvgIconEngine(self.svg)

    def pixmap(self, size, mode, state):
        pixmap = QPixmap(size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        try:
            self.paint(painter, pixmap.rect(), mode, state)
        finally:
            painter.end()
        return pixmap

    def paint(self, painter, rect, mode, state):
        color = SIDEBAR['active'] if state == QIcon.State.On else SIDEBAR['nav']
        if mode == QIcon.Mode.Disabled:
            color = SIDEBAR['disabled']
        # the brown details only on the chosen section (like its blue); the others wholly in the grey
        svg = paint_svg(self.svg, color) if state == QIcon.State.On else self.svg.replace('currentBrown', 'currentColor').replace('currentColor', color)
        QSvgRenderer(QByteArray(svg.encode())).render(painter, QRectF(rect))


def glyph_icon(name):
    """A azimuth glyph in the sidebar colours (the default glyph colour is dark on dark)."""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" '
        'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">' + GLYPHS[name] + '</g></svg>'
    )
    return QIcon(SvgIconEngine(svg))


WORDMARK = ROOT / 'assets' / 'wordmark'
FONTS = ROOT / 'assets' / 'fonts'  # Golos Text (SIL OFL 1.1), the typeface of the Atlas


def sidebar_family():
    """Register Golos Text Medium once; fall back to the system font when it cannot be loaded."""
    families = QFontDatabase.applicationFontFamilies(
        QFontDatabase.addApplicationFont(str(FONTS / 'GolosText-Medium.ttf'))
    )
    return families[0] if families else ''


STAR_GOLD = {'light': '#b8893f', 'dark': '#d6a95c'}  # the star of 方位 on a light and on a dark ground
# the gold of the next step (the frame of the
# button of the result, the ring of the sign of a work ended) — lighter than the star of the icons
NEXT_GOLD = {'light': '#e2bf78', 'dark': '#f2d595'}  # a little lighter
WORDMARK_MARGIN = 1  # logical px added above and below the wordmark's box


def wordmark_pixmap(language, height, ratio, dark=True):
    """The Azimuth wordmark (assets/wordmark: the A with the needle of the compass, З / Z ending in an arrow, a golden
    guide star — compass_wordmark.py)."""
    import re

    path = WORDMARK / f'wordmark-{"en" if language != "ru" else "ru"}-{"dark" if dark else "light"}.svg'
    # the outlined З / Z dips below the box of the wordmark (12 units of the font under the baseline and 12 of
    # the outline) and was cut off: the picture is WORDMARK_MARGIN whole logical px taller above and below (the box of
    # the SVG widened by as many units). The letters keep their size, and their place on whole pixels — a label that
    # centres the picture moves it by exactly the margin, so they stand where they stood and where the web page of the
    # Atlas draws them (it lets the same picture overflow its box)
    text = path.read_text(encoding='utf-8')
    x0, y0, w, h = (float(v) for v in re.search(r'viewBox="([^"]+)"', text).group(1).split())
    margin = WORDMARK_MARGIN * h / height  # units of the box per margin
    text = text.replace(re.search(r'viewBox="[^"]+"', text).group(0), f'viewBox="{x0:g} {y0 - margin:g} {w:g} {h + 2 * margin:g}"', 1)
    renderer = QSvgRenderer(QByteArray(text.encode('utf-8')))
    width = round(height * w / h)
    pixmap = QPixmap(round(width * ratio), round((height + 2 * WORDMARK_MARGIN) * ratio))
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    try:
        renderer.render(painter, QRectF(0, 0, pixmap.width(), pixmap.height()))
    finally:
        painter.end()
    pixmap.setDevicePixelRatio(ratio)
    return pixmap


def wordmark_cuts(language):
    """Letter boundaries of the wordmark as fractions of its width: the A, each letter, the star."""
    import re

    text = (WORDMARK / f'wordmark-{"en" if language != "ru" else "ru"}-dark.svg').read_text(encoding='utf-8')
    x0, _, width, _ = (float(v) for v in re.search(r'viewBox="([^"]+)"', text).group(1).split())
    starts = [0.0] + [float(v) for v in re.findall(r'translate\(([0-9.]+),0\)', text)]
    star = re.search(r'd="(M[^"]+)" stroke="none"', text)
    if star:
        starts.append(min(float(v) for v in re.findall(r'[ML]([0-9.]+) ', star.group(1))))
    edges = [x0] + [x - 40 for x in starts[1:]] + [x0 + width]
    return [(edge - x0) / width for edge in edges]


def zh_wordmark_pixmap(height, ratio, ink, accent, family='', with_cuts=False):
    """方位 with the guide star of the wordmark (the star of the letter A), height = font pixel size."""
    font = QFont(family) if family else QFont()
    font.setPixelSize(round(height))
    font.setWeight(QFont.Weight.DemiBold)
    font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 112)
    metrics = QFontMetricsF(font)
    text = TEXT['zh']['brand']
    advance = metrics.horizontalAdvance(text)
    radius, gap = height * 0.22, height * 0.10
    width, tall = advance + gap + 2 * radius + 2, height * 1.16  # tight box: fits the 30 px header row
    pixmap = QPixmap(round(width * ratio), round(tall * ratio))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setFont(font)
        painter.setPen(QColor(ink))
        baseline = height * 0.98
        painter.drawText(QPointF(0, baseline), text)
        cx, cy = advance + gap + radius, baseline - height * 0.86 + radius
        inner = radius * 0.21  # the four-point star of assets/wordmark (170 / 36)
        points = [
            (0, -radius),
            (inner, -inner),
            (radius, 0),
            (inner, inner),
            (0, radius),
            (-inner, inner),
            (-radius, 0),
            (-inner, -inner),
        ]
        painter.setPen(Qt.PenStyle.NoPen)
        # the guide star golden, as on the icon and in the wordmarks (assets/wordmark/compass_wordmark.py)
        painter.setBrush(QColor(STAR_GOLD['dark' if QColor(ink).lightness() > 128 else 'light']))
        painter.drawPolygon(QPolygonF([QPointF(cx + x, cy + y) for x, y in points]))
    finally:
        painter.end()
    if with_cuts:  # 方 | 位 | star, for the letter reveal in the sidebar
        first = metrics.horizontalAdvance(text[0])
        return pixmap, [0.0, first / width, (advance + gap / 2) / width, 1.0]
    return pixmap


def svg_pixmap(svg, color, size, ratio):
    """A 24x24 stroke icon drawn with currentColor in the given colour."""
    pixmap = QPixmap(round(size * ratio), round(size * ratio))
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    try:
        QSvgRenderer(QByteArray(paint_svg(svg, color).encode())).render(
            painter, QRectF(0, 0, pixmap.width(), pixmap.height())
        )
    finally:
        painter.end()
    pixmap.setDevicePixelRatio(ratio)
    return pixmap


# the program's glyph without the tile background, for the interface (home page, sidebar).
# The tiles with a background (assets/app-icon/azimuth*.png) remain the application icon only.
GLYPH = ROOT / 'assets' / 'app-icon'


def glyph_path(dark, small=False):
    """assets/app-icon[/dark]/glyph[-small].svg: light strokes for dark surfaces when dark=True."""
    return GLYPH / ('dark' if dark else '') / ('glyph-small.svg' if small else 'glyph.svg')


def glyph_pixmap(dark, size, ratio, small=False):
    """The transparent glyph drawn at size x size logical pixels (null pixmap if the file is missing)."""
    renderer = QSvgRenderer(str(glyph_path(dark, small)))
    if not renderer.isValid():
        return QPixmap()
    pixmap = QPixmap(round(size * ratio), round(size * ratio))
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    try:
        renderer.render(painter, QRectF(0, 0, pixmap.width(), pixmap.height()))
    finally:
        painter.end()
    pixmap.setDevicePixelRatio(ratio)
    return pixmap


def glyph_logo(dark=True):
    """Icon of the sidebar logo: the light glyph on the dark panel, the dark one on the light panel."""
    icon = QIcon()
    for size in (24, 32, 42, 48, 64, 84, 128):
        pixmap = glyph_pixmap(dark, size, 1.0, small=True)
        if not pixmap.isNull():
            icon.addPixmap(pixmap)
    return icon
