"""The faint scales of the program's background as SVG, for the site (tools/build_atlas_site.py).

In the program hub/chrome.py Ornament paints them with QPainter: the azimuth dial in the upper right corner of every
section and a picture of the section in the lower left one (the book of the Atlas, the sextant, …). Here the same
geometry and the same strengths (alpha) are written as SVG, without Qt: each picture is a square of ZONE px, as
Ornament.atlas_pictures gave the Atlas page of the program — the dial with its box at the top right
corner of the window, the corner pictures with theirs at the bottom left. The colour is «currentColor» (the page sets
it; ink(svg, '#2a62b8') puts a
colour in, for a picture drawn on a canvas).

dial() book() sextant() compass() spectrum() -> str (an <svg> element). The numbers are those of Ornament._azimuth,
._sextant, ._compass, ._spectrum (and of
Ornament._book, the corner of the Atlas, until the book is now drawn only here);
tests/tools/test_site_scales.py checks them against the count of marks and the box.
"""

import math

ZONE = 430  # hub/chrome.py Ornament.ZONE
SPECTRUM_X0, SPECTRUM_DY = -100.0, 14.0  # hub/chrome.py Ornament._spectrum


def _f(value):
    return f'{value:.2f}'.rstrip('0').rstrip('.')


def _line(x1, y1, x2, y2, alpha, width, dash=False):
    return (f'<path d="M{_f(x1)} {_f(y1)}L{_f(x2)} {_f(y2)}" stroke-opacity="{alpha}" stroke-width="{width}"'
            + (' stroke-dasharray="4 3"' if dash else '') + '/>')


def _star(sx, sy, r1=7.0, alpha=0.22):
    r2 = r1 * 0.3
    points = ' '.join(f'{_f(sx + (r1 if k % 2 == 0 else r2) * math.sin(math.radians(k * 45)))},'
                      f'{_f(sy - (r1 if k % 2 == 0 else r2) * math.cos(math.radians(k * 45)))}' for k in range(8))
    return f'<polygon points="{points}" fill="currentColor" fill-opacity="{alpha}" stroke="none"/>'


def _svg(parts):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ZONE} {ZONE}" width="{ZONE}" height="{ZONE}" '
            f'fill="none" stroke="currentColor" aria-hidden="true">' + ''.join(parts) + '</svg>')


def ink(svg, colour):
    return svg.replace('currentColor', colour)


def dial():
    """Ornament._azimuth: marks every 5° (longer every 30°) of the left half, two circles, the cardinal lines."""
    R, cx, cy = 330.0, ZONE - 70.0, 70.0
    parts = []
    for deg in range(90, 271, 5):
        a = math.radians(deg)
        long = deg % 30 == 0
        r0 = R - (22 if long else 11)
        parts.append(_line(cx + R * math.cos(a), cy + R * math.sin(a), cx + r0 * math.cos(a), cy + r0 * math.sin(a),
                           0.16 if long else 0.08, 1.6 if long else 1.0))
    for r in (R, R * 0.62):
        parts.append(f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(r)}" stroke-opacity="0.09" stroke-width="1.2"/>')
    parts.append(_line(cx, cy - R, cx, cy + R, 0.07, 1.0, dash=True))
    parts.append(_line(cx - R, cy, cx + R, cy, 0.07, 1.0, dash=True))
    return _svg(parts)


DIAL_R, DIAL_CX, DIAL_CY = 330.0, ZONE - 70.0, 70.0
SPIN_PAD = 6.0


def spin_dial():
    """The dial of dial() with its marks all
    round (every 5°, longer every 30° — at rest it is the dial of the corner, the marks of its visible half the same),
    on a square of its own centred on the ring (spin_box), so that it can be turned as a whole while a topic loads."""
    R, cx, cy = DIAL_R, DIAL_CX, DIAL_CY
    parts = []
    for deg in range(0, 360, 5):
        a = math.radians(deg)
        long = deg % 30 == 0
        r0 = R - (22 if long else 11)
        parts.append(_line(cx + R * math.cos(a), cy + R * math.sin(a), cx + r0 * math.cos(a), cy + r0 * math.sin(a),
                           0.16 if long else 0.08, 1.6 if long else 1.0))
    for r in (R, R * 0.62):
        parts.append(f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(r)}" stroke-opacity="0.09" stroke-width="1.2"/>')
    parts.append(_line(cx, cy - R, cx, cy + R, 0.07, 1.0, dash=True))
    parts.append(_line(cx - R, cy, cx + R, cy, 0.07, 1.0, dash=True))
    x0, y0, side = spin_box()
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{_f(x0)} {_f(y0)} {_f(side)} {_f(side)}" '
            f'width="{_f(side)}" height="{_f(side)}" fill="none" stroke="currentColor" aria-hidden="true">'
            + ''.join(parts) + '</svg>')


def spin_box():
    """(x, y, side) of the picture of spin_dial in the units of dial() (its square of ZONE): centred on the ring."""
    side = 2 * (DIAL_R + SPIN_PAD)
    return DIAL_CX - side / 2, DIAL_CY - side / 2, side


def sextant():
    """Ornament._sextant: a quarter of the limb — marks every 3° (longer every 15°), two arcs, the index arm, the star."""
    cx, cy, R = -36.0, ZONE + 36.0, 236.0
    parts = []
    for deg in range(270, 361, 3):
        a = math.radians(deg)
        long = deg % 15 == 0
        r0 = R - (18 if long else 9)
        parts.append(_line(cx + R * math.cos(a), cy + R * math.sin(a), cx + r0 * math.cos(a), cy + r0 * math.sin(a),
                           0.20 if long else 0.10, 1.4 if long else 0.9))
    for r in (R, R * 0.70):
        parts.append(f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(r)}" stroke-opacity="0.11" stroke-width="1.1"/>')
    a = math.radians(-38)
    parts.append(_line(cx, cy, cx + R * 1.06 * math.cos(a), cy + R * 1.06 * math.sin(a), 0.08, 1.0, dash=True))
    parts.append(_star(cx + R * 1.18 * math.cos(a), cy + R * 1.18 * math.sin(a)))
    return _svg(parts)


def book():
    """Ornament._book: the corner of an open book — two curved pages with lines of text, the spine, a ribbon, the star."""
    x0, y0 = -120.0, ZONE + 95.0
    sp, L, top, sag = x0 + 250.0, 250.0, 280.0, 20.0
    parts = []

    def curve(start, control, end, alpha, width=1.0):
        parts.append(f'<path d="M{_f(start[0])} {_f(start[1])}Q{_f(control[0])} {_f(control[1])} {_f(end[0])} {_f(end[1])}" '
                     f'stroke-opacity="{alpha}" stroke-width="{width}"/>')

    for s in (-1, 1):
        ox = sp + s * L
        parts.append(
            f'<path d="M{_f(sp)} {_f(y0 - top)}Q{_f(sp + s * L * 0.45)} {_f(y0 - top - sag - 12)} {_f(ox)} {_f(y0 - top - sag)}'
            f'L{_f(ox)} {_f(y0 - sag)}Q{_f(sp + s * L * 0.45)} {_f(y0 - sag - 12)} {_f(sp)} {_f(y0)}" '
            f'stroke-opacity="0.14" stroke-width="1.2"/>')
        for k, alpha in ((5, 0.09), (10, 0.07)):
            curve((sp, y0 + k * 0.6), (sp + s * L * 0.45, y0 - sag - 12 + k), (ox - s * k * 0.3, y0 - sag + k), alpha)
        for i in range(1, 8):
            yy = y0 - top + i / 8.6 * top
            curve((sp + s * 14, yy - 1), (sp + s * L * 0.45, yy - 12), (ox - s * 16, yy - sag + 2),
                  0.09 if i % 3 == 0 else 0.07)
    parts.append(_line(sp, y0 - top, sp, y0, 0.16, 1.3))
    ribbon = [(sp + 40, y0 - top - 18), (sp + 40, y0 - top + 70), (sp + 48, y0 - top + 60), (sp + 56, y0 - top + 70),
              (sp + 56, y0 - top - 17)]
    parts.append('<polyline points="' + ' '.join(f'{_f(x)},{_f(y)}' for x, y in ribbon)
                 + '" stroke-opacity="0.12" stroke-width="1.1"/>')
    parts.append(_star(sp + L + 28, y0 - top - 46))
    return _svg(parts)


def compass():
    """Ornament._compass: a quarter of a compass card — marks every 5° (longer every 45°), three rings, the needle to
    the north-east and its star."""
    cx, cy, R = -36.0, ZONE + 36.0, 236.0
    parts = []
    for deg in range(270, 361, 5):
        a = math.radians(deg)
        long = deg % 45 == 0
        r0 = R - (20 if long else 9)
        parts.append(_line(cx + R * math.cos(a), cy + R * math.sin(a), cx + r0 * math.cos(a), cy + r0 * math.sin(a),
                           0.20 if long else 0.10, 1.4 if long else 0.9))
    for r in (R, R * 0.74, R * 0.3):
        parts.append(f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(r)}" stroke-opacity="0.11" stroke-width="1.1"/>')
    a, side, w = math.radians(-45), math.radians(45), 9.0
    tip = (cx + R * 0.92 * math.cos(a), cy + R * 0.92 * math.sin(a))
    mid = (cx + R * 0.38 * math.cos(a), cy + R * 0.38 * math.sin(a))
    left = (mid[0] + w * math.cos(side), mid[1] + w * math.sin(side))
    right = (mid[0] - w * math.cos(side), mid[1] - w * math.sin(side))
    parts.append('<polygon points="' + ' '.join(f'{_f(x)},{_f(y)}' for x, y in ((cx, cy), left, tip, right))
                 + '" stroke-opacity="0.14" stroke-width="1.1"/>')
    parts.append(_line(cx, cy, tip[0], tip[1], 0.08, 1.0, dash=True))
    parts.append(_star(cx + R * 1.12 * math.cos(a), cy + R * 1.12 * math.sin(a)))
    return _svg(parts)


def spectrum():
    """Ornament._spectrum: an axis with marks and six bands of a spectrum (Lorentz curves) rising from it, dashed
    lines under three of them and the star over the highest. Its start outside the corner (SPECTRUM_X0,
    SPECTRUM_DY) — a part shows, as of the dial of the compass and of the sextant."""
    x0, y0, width = SPECTRUM_X0, ZONE - SPECTRUM_DY, 380.0
    parts = [_line(x0, y0, x0 + width, y0, 0.14, 1.2), _line(x0, y0, x0, y0 - 190, 0.14, 1.2)]
    for k in range(21):
        long = k % 5 == 0
        x = x0 + k * width / 20
        parts.append(_line(x, y0, x, y0 + (9 if long else 5), 0.16 if long else 0.09, 1.0))
    bands = ((0.18, 120, 9), (0.33, 62, 6), (0.47, 168, 7), (0.6, 40, 5), (0.74, 96, 11), (0.88, 54, 6))
    points = [(x0, y0)]
    for t in range(0, 381, 2):
        y = sum(h * g * g / ((t - c * width) ** 2 + g * g) for c, h, g in bands)
        points.append((x0 + t, y0 - y))
    parts.append('<polyline points="' + ' '.join(f'{_f(x)},{_f(y)}' for x, y in points)
                 + '" stroke-opacity="0.16" stroke-width="1.2"/>')
    for c, h, _ in bands[::2]:
        parts.append(_line(x0 + c * width, y0, x0 + c * width, y0 - h - 12, 0.07, 1.0, dash=True))
    parts.append(_star(x0 + 0.47 * width, y0 - 168 - 30))
    return _svg(parts)


# Small line pictures of the cards of the home page (24 × 24, stroke currentColor) — one idea each, no logos.
ICONS = {
    # «Формула, которая считает»: a curve over its axes and a slider under them
    'formula': '<path d="M3 3v12h18"/><path d="M4 13c3 0 4-8 7-8s4 6 9 6"/><path d="M3 20h18"/><circle cx="14" cy="20" r="1.8" fill="currentColor"/>',
    # «Проверено эталонами»: a ruler with a check mark
    'checked': '<rect x="2.5" y="14" width="19" height="6" rx="1"/><path d="M6 14v3M10 14v2M14 14v3M18 14v2"/><path d="M7 8l3 3 7-7"/>',
    # «Три языка»: two speech bubbles
    'languages': '<path d="M3 4h11v8H8l-3 3v-3H3z"/><path d="M14 8h7v8h-2v3l-3-3h-5v-3"/>',
    # macOS on Apple Silicon: a laptop
    'laptop': '<rect x="4" y="5" width="16" height="11" rx="1.5"/><path d="M2 19h20"/>',
    # Windows x64: a monitor on its stand
    'desktop': '<rect x="3" y="4" width="18" height="12" rx="1.5"/><path d="M9 20h6M12 16v4"/>',
    # Linux x86_64: a window of a terminal with its prompt
    'terminal': '<rect x="3" y="4" width="18" height="16" rx="1.5"/><path d="M3 8h18"/><path d="M7 12l3 2.5L7 17"/><path d="M12 17h5"/>',
}


def icon(name):
    return ('<svg class="cardIcon" viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" '
            'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + ICONS[name] + '</svg>')
