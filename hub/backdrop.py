"""The depth of the background of the hub: light, shadows of the panels, isolines, the gyroscope, the glass.

§0 STATE
    0.245.0 (2026-11-27, the owner: «чтоб не просто равномерный фон одноцветный за панелями был… чтоб ощущалась
    трёхмерность»; the variant chosen on mock-ups: light and shadows in every section, isolines of a nitro group on
    the home page, panels as glass, the azimuth as a gyroscope that turns on the home page).
§1 PURPOSE
    What hub.chrome.Ornament draws besides the scales of the sections. Everything is drawn by that one layer over
    the page: no widget of a section is changed, none gets a graphics effect.
§2 ALGORITHM
    1. Light. The page keeps its colour; away from the upper left corner the bare page (where no panel lies) is
       darkened a little (shade): the light seems to come from that corner. Dark ink only, so the texts of a page
       keep their contrast.
    2. Shadows. Round every panel (a rectangle of Ornament.panels) rings of falling strength, moved DOWN px down;
       clipped by the caller to the bare page, so nothing darkens a panel.
    3. Isolines (the home page). The electron density of nitrobenzene in its plane as a model: for every atom
       w·(exp(−r/CORE) + TAIL·exp(−r/FAR)), w — the number of its electrons taken roughly (C 6, N 7, O 8, H 1). The
       molecule is SCALE px per Å, the centre of its ring left of and below the lower left corner (ANCHOR), the
       nitro group points up and to the right, so mostly the nitro group is seen. Lines of equal density at LEVELS
       (a geometric row) by marching squares on a grid of STEP px; computed once, in coordinates of the lower left
       corner of the page. A model, not a calculation: geometry C–C 1.39, C–N 1.47, N–O 1.22 Å, O–N–O 125°.
    4. Gyroscope. Three frames, one inside another: the outer ring turns about the vertical axis of the screen, the
       inner ring about the horizontal axis of the outer one, the needle with its small ring about the axis it lies
       on in the inner ring. Each point is turned and projected (weak perspective), every line is of one width
       whatever its turn; the strength of a line falls smoothly with its depth (no threshold: in the flat position
       all lines are alike). Gyro.start: the speeds rise from zero (RISE_FIRST s at the first start, RISE s later);
       Gyro.leave: every angle goes on to the next flat position (the inner ring — to a whole turn, so that the
       needle points north) in SETTLE s, slowing, and stops there.
    5. Glass. What lies on the background is drawn once into a small picture (1/GLASS of the size: drawn enlarged it
       is blurred) and shown under the panels moved by SHIFT and enlarged by GROW — as through thick glass.
§4 SPECIFICATION
    shade(painter, rect, dark); shadows(painter, panels, dark); edge_shadow(painter, height, dark);
    isolines() -> [(QPainterPath, alpha, width)] in (x, y − height of the page); draw_isolines(painter, height, ink);
    segments(field, xs, ys, level) -> array (n, 4) of x1, y1, x2, y2; chains(pieces) -> [[(x, y)]] (0.248.0);
    Gyro: angles, mode ('rest' | 'run' | 'settle'), moving, start(), leave(), advance(seconds) -> moving,
    size() -> px, picture(ink, ratio) -> QPixmap of size() × size() px;
    glass_picture(draw, width, height, margin) -> QPixmap; draw_glass(painter, picture, margin).
§7 TESTS
    tests/hub/test_backdrop.py.
"""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap

# -- light and shadows --------------------------------------------------------------------------------------------
SHADE = {False: (QColor(27, 34, 48), 0.075), True: (QColor(0, 0, 0), 0.34)}  # ink, strength in the far corner
SHADOW = {False: (QColor(27, 34, 48), 0.15), True: (QColor(0, 0, 0), 0.5)}  # ink, strength at the edge of a panel
REACH, DOWN, ROUND = 22, 5, 12  # px: how far a shadow goes, how far down it is moved, the corners of a panel


def shade(painter, rect, dark=False):
    """The bare page darker away from the upper left corner."""
    ink, strength = SHADE[bool(dark)]
    gradient = QLinearGradient(QPointF(rect.left(), rect.top()), QPointF(rect.right(), rect.bottom()))
    for stop, part in ((0.0, 0.0), (0.4, 0.0), (0.75, 0.55), (1.0, 1.0)):
        colour = QColor(ink)
        colour.setAlphaF(strength * part)
        gradient.setColorAt(stop, colour)
    painter.fillRect(rect, gradient)


def shadows(painter, panels, dark=False):
    """Soft shadows round the panels (QRect); the caller clips them to the bare page. Filled frames from the farthest
    in: each adds what the strength grows by at its distance, so at a distance d it is strength·(1 − d/REACH)²."""
    ink, strength = SHADOW[bool(dark)]

    def at(d):
        return strength * max(0.0, 1 - d / REACH) ** 2

    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)
    for d in range(REACH - 1, -1, -2):
        colour = QColor(ink)
        colour.setAlphaF(max(0.0, at(d) - at(d + 2)))
        painter.setBrush(colour)
        for panel in panels:
            frame = QRectF(panel).translated(0, DOWN).adjusted(-d, -d, d, d)
            painter.drawRoundedRect(frame, ROUND + d, ROUND + d)
    painter.restore()


def edge_shadow(painter, height, dark=False, width=16):
    """The shadow the side panel throws on the page: a strip at the left edge."""
    ink, strength = SHADOW[bool(dark)]
    gradient = QLinearGradient(QPointF(0, 0), QPointF(width, 0))
    near, far = QColor(ink), QColor(ink)
    near.setAlphaF(strength * 0.7)
    far.setAlphaF(0.0)
    gradient.setColorAt(0.0, near)
    gradient.setColorAt(1.0, far)
    painter.fillRect(QRectF(0, 0, width, height), gradient)


# -- isolines of the home page ------------------------------------------------------------------------------------
SCALE = 190.0  # px per Å
ANCHOR = (-191.0, 72.0)  # the centre of the ring: px right of the left edge of the page, px below its bottom edge
TILT = -35.0  # °: the direction ring → nitro group on the screen (y down)
CORE, FAR, TAIL = 58.0, 150.0, 0.12  # px, px, the share of the far part
LEVELS = tuple(0.12 * 1.6 ** k for k in range(10))
STEP = 4  # px of the grid
FIELD = (-264.0, 964.0, -824.0, 44.0)  # px: x from, x to; y from, y to (from the bottom edge of the page; down — plus)
_ISOLINES = None


def nitrobenzene():
    """The atoms in the plane of the molecule: (x px, y px from the bottom edge of the page, weight)."""
    cx, cy = ANCHOR

    def at(r, degrees):
        a = math.radians(TILT + degrees)
        return cx + r * SCALE * math.cos(a), cy + r * SCALE * math.sin(a)

    atoms = [(*at(1.39, 60 * k), 6.0) for k in range(6)]  # the ring; the carbon k = 0 carries the nitro group
    atoms += [(*at(1.39 + 1.08, 60 * k), 1.0) for k in range(1, 6)]
    n = at(1.39 + 1.47, 0)
    atoms.append((*n, 7.0))
    for sign in (1, -1):  # N–O 1.22 Å, O–N–O 125°
        a = math.radians(TILT + sign * 62.5)
        atoms.append((n[0] + 1.22 * SCALE * math.cos(a), n[1] + 1.22 * SCALE * math.sin(a), 8.0))
    return atoms


def density(xs, ys):
    """The model density on the grid ys × xs."""
    x, y = np.meshgrid(xs, ys)
    field = np.zeros_like(x)
    for ax, ay, weight in nitrobenzene():
        r = np.hypot(x - ax, y - ay)
        field += weight * (np.exp(-r / CORE) + TAIL * np.exp(-r / FAR))
    return field


# marching squares: the corners of a cell a (upper left), b (upper right), c (lower right), d (lower left) give the
# number 8a + 4b + 2c + d; the sides 0 top, 1 right, 2 bottom, 3 left; the pairs of sides a line joins
_CASES = {1: ((3, 2),), 2: ((2, 1),), 3: ((3, 1),), 4: ((0, 1),), 5: ((0, 1), (3, 2)), 6: ((0, 2),), 7: ((0, 3),),
          8: ((0, 3),), 9: ((0, 2),), 10: ((0, 3), (1, 2)), 11: ((0, 1),), 12: ((3, 1),), 13: ((1, 2),), 14: ((3, 2),)}


def segments(field, xs, ys, level):
    """The pieces of the line field = level: an array (n, 4) of x1, y1, x2, y2."""
    a, b, c, d = field[:-1, :-1], field[:-1, 1:], field[1:, 1:], field[1:, :-1]
    number = (a > level) * 8 + (b > level) * 4 + (c > level) * 2 + (d > level) * 1
    left, right = np.broadcast_to(xs[:-1], a.shape), np.broadcast_to(xs[1:], a.shape)
    top, bottom = np.broadcast_to(ys[:-1, None], a.shape), np.broadcast_to(ys[1:, None], a.shape)
    with np.errstate(divide='ignore', invalid='ignore'):
        px = (left + (right - left) * (level - a) / (b - a), right, left + (right - left) * (level - d) / (c - d), left)
        py = (top, top + (bottom - top) * (level - b) / (c - b), bottom, top + (bottom - top) * (level - a) / (d - a))
    found = []
    for case, pairs in _CASES.items():
        mask = number == case
        if not mask.any():
            continue
        for first, second in pairs:
            found.append(np.stack([np.broadcast_to(px[first], a.shape)[mask], np.broadcast_to(py[first], a.shape)[mask],
                                   np.broadcast_to(px[second], a.shape)[mask],
                                   np.broadcast_to(py[second], a.shape)[mask]], axis=1))
    return np.concatenate(found) if found else np.zeros((0, 4))


def chains(pieces):
    """The pieces of segments() joined end to end into broken lines [[(x, y), …], …]: the neighbouring cells compute
    the point of their common side alike, so the ends meet exactly (rounded to 1e-4 px)."""
    def key(x, y):
        return round(x, 4), round(y, 4)

    ends = {}
    for k, (x1, y1, x2, y2) in enumerate(pieces.tolist()):
        ends.setdefault(key(x1, y1), []).append((k, 0))
        ends.setdefault(key(x2, y2), []).append((k, 1))
    used = [False] * len(pieces)
    found = []
    data = pieces.tolist()

    def walk(k, end):
        line = []
        while True:
            used[k] = True
            x1, y1, x2, y2 = data[k]
            point = (x2, y2) if end == 0 else (x1, y1)  # the other end of the piece
            line.append(point)
            nxt = next(((j, e) for j, e in ends.get(key(*point), []) if not used[j]), None)
            if nxt is None:
                return line
            k, end = nxt

    for k in range(len(data)):
        if used[k]:
            continue
        x1, y1, x2, y2 = data[k]
        forward = walk(k, 0)  # from (x1, y1) on
        used[k] = False
        backward = walk(k, 1)  # from (x2, y2) back
        found.append(list(reversed(backward[:-1])) + [(x1, y1)] + forward if len(backward) > 1 else [(x1, y1)] + forward)
    return found


def smooth(path, line):
    """A broken line drawn smooth: through the middles of its pieces, the corners as the control points."""
    if len(line) < 3:
        path.moveTo(*line[0])
        for point in line[1:]:
            path.lineTo(*point)
        return
    closed = line[0] == line[-1]
    points = line[:-1] if closed else line
    middles = [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in zip(points, points[1:] + points[:1])]
    if closed:
        path.moveTo(*middles[-1])
        for corner, middle in zip(points, middles):
            path.quadTo(corner[0], corner[1], middle[0], middle[1])
    else:
        path.moveTo(*points[0])
        for corner, middle in zip(points[1:-1], middles[1:-1]):
            path.quadTo(corner[0], corner[1], middle[0], middle[1])
        path.lineTo(*points[-1])


def isolines():
    """[(path, alpha, width)]: the lines of LEVELS, x from the left edge of the page, y from its bottom edge."""
    global _ISOLINES
    if _ISOLINES is None:
        xs = np.arange(FIELD[0], FIELD[1] + STEP, STEP)
        ys = np.arange(FIELD[2], FIELD[3] + STEP, STEP)
        field = density(xs, ys)
        lines = []
        for k, level in enumerate(LEVELS):
            path = QPainterPath()
            for line in chains(segments(field, xs, ys, level)):  # whole lines: pieces drawn one by one showed beads
                smooth(path, line)
            strong = k % 4 == 1
            fade = 0.55 + 0.45 * min(1.0, k / 4)  # the far lines fainter
            lines.append((path, (0.21 if strong else 0.13) * fade, 1.1 if strong else 0.7))
        _ISOLINES = lines
    return _ISOLINES


def draw_isolines(painter, height, ink, strength=1.0):
    painter.save()
    painter.translate(0, height)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    for path, alpha, width in isolines():
        colour = QColor(ink)
        colour.setAlphaF(min(1.0, alpha * strength))
        painter.setPen(QPen(colour, width))
        painter.drawPath(path)
    painter.restore()


# -- the gyroscope of the azimuth ---------------------------------------------------------------------------------
class Gyro:
    """The gyroscope: the angles of its three frames and their motion."""

    SPEED = (360 / 44, 360 / 30, -360 / 16)  # °/s: the outer ring, the inner ring, the needle
    FLAT = (180.0, 360.0, 180.0)  # ° between the positions in which a frame lies in the plane as at rest
    RISE_FIRST, RISE, SETTLE = 3.0, 1.2, 4.2  # s
    AHEAD = 30.0  # °: a frame closer than this to a flat position goes on to the next one
    SIDE, OUTER, INNER, ROTOR = 352, 150.0, 116.0, 78.0  # px: the picture and the radii (drawn GROW times larger)
    GROW = 1.5  # 0.248.0 (the owner: «гироскоп побольше, и сместить больше в угол»)
    CENTRE = (70.0, 70.0)  # px from the right and the top edge of the page: as the flat dial of 0.244.0
    EYE = 1100.0  # px: the distance of the eye (weak perspective)
    LINE = 0.8  # px
    SHADES = 6  # the strengths a line is drawn in by its depth

    def __init__(self):
        self.angles = [0.0, 0.0, 0.0]
        self.mode = 'rest'
        self.since = 0.0
        self.rise = self.RISE_FIRST
        self.started = False
        self._from = self._to = None

    @property
    def moving(self):
        return self.mode != 'rest'

    def start(self):
        if self.mode == 'run':
            return
        self.rise = self.RISE if self.started else self.RISE_FIRST
        self.started = True
        self.mode, self.since = 'run', 0.0

    def leave(self):
        """To the nearest flat position ahead, slowing; then rest."""
        if self.mode != 'run':
            return
        self._from = list(self.angles)
        self._to = []
        for angle, speed, turn in zip(self.angles, self.SPEED, self.FLAT):
            if speed > 0:
                self._to.append(math.ceil((angle + self.AHEAD) / turn) * turn)
            else:
                self._to.append(math.floor((angle - self.AHEAD) / turn) * turn)
        self.mode, self.since = 'settle', 0.0

    def advance(self, seconds):
        """The angles after `seconds` more; True while something moves."""
        seconds = max(0.0, min(seconds, 0.1))
        self.since += seconds
        if self.mode == 'run':
            u = min(1.0, self.since / self.rise)
            for k, speed in enumerate(self.SPEED):
                self.angles[k] += speed * u * (2 - u) * seconds
        elif self.mode == 'settle':
            u = min(1.0, self.since / self.SETTLE)
            eased = 1 - (1 - u) ** 3
            self.angles = [a + (b - a) * eased for a, b in zip(self._from, self._to)]
            if u >= 1.0:
                self.angles = [a % 360.0 for a in self._to]
                self.mode = 'rest'
        return self.moving

    # the frames: a point of a frame (n, 3) → the same point in the coordinates of the screen (x right, y up, z to the eye)
    @staticmethod
    def _about_y(points, degrees):
        a = math.radians(degrees)
        x, y, z = points[:, 0], points[:, 1], points[:, 2]
        return np.stack([x * math.cos(a) + z * math.sin(a), y, -x * math.sin(a) + z * math.cos(a)], axis=1)

    @staticmethod
    def _about_x(points, degrees):
        a = math.radians(degrees)
        x, y, z = points[:, 0], points[:, 1], points[:, 2]
        return np.stack([x, y * math.cos(a) - z * math.sin(a), y * math.sin(a) + z * math.cos(a)], axis=1)

    def placed(self, points, frame):
        """frame: 0 the outer ring, 1 the inner ring, 2 the needle."""
        points = np.asarray(points, dtype=float)
        if frame >= 2:
            points = self._about_y(points, self.angles[2])
        if frame >= 1:
            points = self._about_x(points, self.angles[1])
        return self._about_y(points, self.angles[0])

    def lines(self):
        """[(points (n, 3) of a broken line in its frame, frame, strength)]."""
        def ring(r, pieces=72):
            t = np.linspace(0.0, 2 * math.pi, pieces + 1)
            return np.stack([r * np.cos(t), r * np.sin(t), np.zeros_like(t)], axis=1)

        found = [(ring(self.OUTER), 0, 0.6)]
        for k in range(12):  # twelve marks, every third one longer
            c, s = math.cos(math.radians(30 * k)), math.sin(math.radians(30 * k))
            r0 = self.OUTER - (13 if k % 3 == 0 else 7)
            found.append(([[r0 * c, r0 * s, 0], [self.OUTER * c, self.OUTER * s, 0]], 0, 0.6))
        for sign in (1, -1):  # the axle of the inner ring in the outer one, of the needle in the inner one
            found.append(([[sign * self.INNER, 0, 0], [sign * self.OUTER, 0, 0]], 0, 0.6))
            found.append(([[0, sign * self.ROTOR, 0], [0, sign * self.INNER, 0]], 1, 0.6))
        found.append((ring(self.INNER), 1, 0.6))
        for degrees in (0, 45, 135, 180, 225, 315):  # six marks of the middle ring (not where the needle's axle is)
            c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
            r0 = self.INNER - (10 if degrees % 180 == 0 else 6)
            found.append(([[r0 * c, r0 * s, 0], [self.INNER * c, self.INNER * s, 0]], 1, 0.6))
        found.append((ring(self.ROTOR, 60), 2, 0.5))
        found.append(([[0, 66, 0], [13, 0, 0], [0, -66, 0], [-13, 0, 0], [0, 66, 0]], 2, 0.7))
        return found

    def project(self, points):
        """(n, 3) on the screen → x, y of the picture (its centre SIDE / 2) and the depth z."""
        factor = self.EYE / (self.EYE - points[:, 2]) * self.GROW
        half = self.size() / 2
        return half + points[:, 0] * factor, half - points[:, 1] * factor, points[:, 2]

    def size(self):
        """px: the side of the picture."""
        return round(self.SIDE * self.GROW)

    def picture(self, ink, ratio=1.0):
        """The gyroscope as it stands now, on a transparent picture of size() × size() px."""
        side = max(1, round(self.size() * ratio))
        picture = QPixmap(side, side)
        picture.setDevicePixelRatio(ratio)
        picture.fill(Qt.GlobalColor.transparent)
        painter = QPainter(picture)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.paint(painter, ink)
        painter.end()
        return picture

    def paint(self, painter, ink):
        buckets = [[] for _ in range(self.SHADES)]
        for points, frame, strength in self.lines():
            x, y, z = self.project(self.placed(points, frame))
            depth = np.clip((z[:-1] + z[1:]) / 120.0, -1.0, 1.0)  # of the middle of each piece
            share = 0.7 + 0.3 * depth  # 0.4 far … 1.0 near; 0.7 in the plane of the screen
            index = np.clip(np.rint((share - 0.4) / 0.6 * (self.SHADES - 1)).astype(int), 0, self.SHADES - 1)
            for k in range(len(index)):
                buckets[index[k]].append((QLineF(x[k], y[k], x[k + 1], y[k + 1]), strength))
        colour = QColor(ink)
        for number, bucket in enumerate(buckets):
            share = 0.4 + 0.6 * number / (self.SHADES - 1)
            for strength in sorted({s for _, s in bucket}):
                colour.setAlphaF(strength * share)
                pen = QPen(colour, self.LINE)
                pen.setCapStyle(Qt.PenCapStyle.FlatCap)
                painter.setPen(pen)
                painter.drawLines([line for line, s in bucket if s == strength])
        # the northern half of the needle filled, the hub
        x, y, _ = self.project(self.placed([[0, 66, 0], [13, 0, 0], [-13, 0, 0]], 2))
        path = QPainterPath(QPointF(x[0], y[0]))
        path.lineTo(x[1], y[1])
        path.lineTo(x[2], y[2])
        path.closeSubpath()
        colour.setAlphaF(0.2)
        painter.fillPath(path, colour)
        colour.setAlphaF(0.6)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(colour)
        half = self.size() / 2
        painter.drawEllipse(QPointF(half, half), 2.5, 2.5)
        painter.setBrush(Qt.BrushStyle.NoBrush)


# -- glass --------------------------------------------------------------------------------------------------------
GLASS = 3  # the picture under the panels is kept 1/GLASS of its size: drawn enlarged, it is blurred
SHIFT, GROW = (4.0, 3.0), 1.015  # px the picture is moved by under a panel; how much larger it is shown (0.248.0: was 9, 6 and 3 %)


def glass_picture(draw, width, height, margin):
    """draw(painter) paints the background in the coordinates of the page; the picture holds it from x = −margin
    (what continues under the side panel), GLASS times smaller."""
    picture = QPixmap(max(1, math.ceil((width + margin) / GLASS)), max(1, math.ceil(height / GLASS)))
    picture.fill(Qt.GlobalColor.transparent)
    painter = QPainter(picture)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(1 / GLASS, 1 / GLASS)
    painter.translate(margin, 0)
    draw(painter)
    painter.end()
    return picture


def draw_glass(painter, picture, margin):
    """The picture of glass_picture as seen through a panel: blurred, moved and a little enlarged."""
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    target = QRectF(-margin * GROW + SHIFT[0], SHIFT[1], picture.width() * GLASS * GROW, picture.height() * GLASS * GROW)
    painter.drawPixmap(target, picture, QRectF(picture.rect()))
    painter.restore()
