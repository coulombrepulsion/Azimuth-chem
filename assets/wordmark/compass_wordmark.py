"""The wordmark of Azimuth with the needle of the compass.

§1 PURPOSE
    «АЗИМУТ» / «AZIMUTH» as on the icon of the program: in the A, instead of the ruler, the needle of the
    compass — blue point to the right, grey tail, the pivot under the apex; З / Z drawn anew so that the letter itself
    ends in an arrow, as the golden arrow of the icon that shows how far the needle turned (the upper bowl of З is the
    letter of the font); the guide star golden. The arrow is at the end of the letter only.
§2 ALGORITHM
    The letters of the font (Golos Text 600) are taken from font/wordmark-{ru,en}-font.svg — the wordmark of 0.64.6
    made by make_wordmark.py, kept as the source (fontTools and the font files are not needed here). З: the upper
    bowl of the font cut at CUT (Sutherland–Hodgman on the flattened outline), the lower bowl a stroke of STROKE units
    along an ellipse that ends in an arrowhead; Z: a stroke along its three bars ending in an arrowhead. The stroke
    goes 12 units under the head (no seam of light).
§3 OUTPUT
    python3 assets/wordmark/compass_wordmark.py — wordmark-{ru,en}-{light,dark}.svg (the program: hub/branding.py),
    and the wordmarks of the web page of the Atlas (const WORD of modules/atlas/atlas_v2/quas_atlas/web/index.html,
    ru and en; zh is 方位 with the star) with classes: wI letters, wR ring, wZ gold (fill and stroke), wN tail, wP
    point, wH pivot, wE its eye.
"""
import math
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ATLAS = ROOT / 'modules' / 'atlas' / 'atlas_v2' / 'quas_atlas' / 'web' / 'index.html'
THEMES = {'light': dict(ink='#1b2230', acc='#2a62b8', gold='#b8893f', tail='#9aa4b5', eye='#ffffff'),
          'dark': dict(ink='#ffffff', acc='#6ea2f0', gold='#d6a95c', tail='#7d8aa3', eye='#1b2433')}
STROKE = 126  # the stroke of the drawn З / Z (the stems of Golos Text 600 at a cap height of 700: 124–150)
CUT = 300  # З: the font above this line (the bowl, the middle) …
SPLIT = 300  # … and below it right of this one; the lower left end is the line with the arrow
NEEDLE = dict(centre=344, half=330, y=203, width=74, pivot=46, eye=18)  # the A: apex at 344; the ruler stood at 203
SHIFT = 849  # the place of З / Z in the word


def ellipse(cx, cy, a, b, t0, t1, n=60):
    return [(cx + a * math.cos(math.radians(t0 + (t1 - t0) * k / n)), cy + b * math.sin(math.radians(t0 + (t1 - t0) * k / n)))
            for k in range(n + 1)]


def arrow_stroke(points, half, length):
    """(the stroke: path d, the head: path d) — the polyline without its last `length` units (and 12 more under the
    head), the head from there to where the letter ended"""
    pts = list(points)
    rest = length
    while rest > 0 and len(pts) > 1:
        (x0, y0), (x1, y1) = pts[-2], pts[-1]
        seg = math.hypot(x1 - x0, y1 - y0)
        if seg <= rest:
            pts.pop()
            rest -= seg
            continue
        f = (seg - rest) / seg
        pts[-1] = (x0 + (x1 - x0) * f, y0 + (y1 - y0) * f)
        rest = 0
    (x0, y0), (bx, by) = pts[-2], pts[-1]
    n = math.hypot(bx - x0, by - y0)
    dx, dy = (bx - x0) / n, (by - y0) / n
    head = [(bx - dy * half, by + dx * half), (bx + dx * length, by + dy * length), (bx + dy * half, by - dx * half)]
    pts[-1] = (bx + dx * 12, by + dy * 12)
    fmt = lambda p: f'{p[0]:.0f} {p[1]:.0f}'
    return 'M' + ' L'.join(fmt(p) for p in pts), 'M' + ' L'.join(fmt(p) for p in head) + ' Z'


def flatten(d, steps=10):
    """the points of one closed outline of M, L, H, V, Q (absolute)"""
    tokens = re.findall(r'[MLHVQZ]|-?\d+(?:\.\d+)?', d)
    pts, i, cur, cmd = [], 0, (0.0, 0.0), None
    while i < len(tokens):
        if tokens[i].isalpha():
            cmd = tokens[i]
            i += 1
            if cmd == 'Z':
                continue
        if cmd in ('M', 'L'):
            cur = (float(tokens[i]), float(tokens[i + 1]))
            i += 2
            pts.append(cur)
        elif cmd == 'H':
            cur = (float(tokens[i]), cur[1])
            i += 1
            pts.append(cur)
        elif cmd == 'V':
            cur = (cur[0], float(tokens[i]))
            i += 1
            pts.append(cur)
        elif cmd == 'Q':
            c, e = (float(tokens[i]), float(tokens[i + 1])), (float(tokens[i + 2]), float(tokens[i + 3]))
            i += 4
            for k in range(1, steps + 1):
                u = k / steps
                pts.append(((1 - u) ** 2 * cur[0] + 2 * (1 - u) * u * c[0] + u * u * e[0],
                            (1 - u) ** 2 * cur[1] + 2 * (1 - u) * u * c[1] + u * u * e[1]))
            cur = e
        else:
            i += 1
    return pts


def clip(pts, inside, cross):
    """the part of a polygon inside a half-plane (Sutherland–Hodgman); cross(p, q) — the point where pq crosses its edge"""
    out = []
    for k, p in enumerate(pts):
        q = pts[(k + 1) % len(pts)]
        if inside(p):
            out.append(p)
        if inside(p) != inside(q):
            out.append(cross(p, q))
    return out


def at_y(y):
    return lambda p, q: (p[0] + (q[0] - p[0]) * (y - p[1]) / (q[1] - p[1]), y)


def at_x(x):
    return lambda p, q: (x, p[1] + (q[1] - p[1]) * (x - p[0]) / (q[0] - p[0]))


def outline(pts):
    return 'M' + ' L'.join(f'{x:.1f} {y:.1f}' for x, y in pts) + ' Z'


def letter(lang, font_path):
    """[(role, path, join)] of З / Z: role 'fill' (a shape) or 'stroke' (the line of STROKE units)"""
    if lang == 'ru':
        # the letter of the font all but its lower left end: above CUT whole, below it right of SPLIT;
        # from there the line goes on along the end of the font (a quarter of an ellipse to the cut of the end at
        # x 35–191, y 219) and a little further up, and ends in the arrowhead
        pts = flatten(font_path)
        # the two parts overlap by 4 units: no seam of light along the cut where they meet
        upper = clip(pts, lambda p: p[1] >= CUT - 2, at_y(CUT - 2))
        lower = clip(clip(pts, lambda p: p[1] < CUT + 2, at_y(CUT + 2)), lambda p: p[0] >= SPLIT, at_x(SPLIT))
        end = [(SPLIT + 12, 51)] + ellipse(SPLIT, 219, SPLIT - 113, 168, -90, -180, 40)[1:] + [(113, 300)]
        stroke, head = arrow_stroke(end, 105, 130)
        return [('fill', outline(upper)), ('fill', outline(lower)), ('stroke', stroke, 'round'), ('fill', head)]
    # «В Z — удлини нижнюю часть»: the lower bar goes on to the right, its arrow beyond the letter
    stroke, head = arrow_stroke([(40, 625), (560, 625), (75, 75), (700, 75)], 85, 125)
    return [('stroke', stroke, 'miter'), ('fill', head)]


def parts(lang):
    source = (HERE / 'font' / f'wordmark-{lang}-font.svg').read_text(encoding='utf-8')
    box = re.search(r'viewBox="([^"]+)"', source).group(1)
    ink = re.search(r'<g fill="#1b2230">(.*?)</g><g stroke=', source).group(1)
    legs = re.match(r'<path d="([^"]+)"/>', ink).group(1)
    letters = re.findall(r'<path transform="translate\((\d+),0\)" d="([^"]+)"/>', ink)
    zed = re.search(rf'<path fill="#b8893f" transform="translate\({SHIFT},0\)" d="([^"]+)"/>', ink).group(1)
    star = re.search(r'<path fill="#2a62b8" d="([^"]+)" stroke="none"/>', source).group(1)
    return box, legs, letters, letter(lang, zed), star


def needle_parts():
    n = NEEDLE
    x0, x1, xc, y, h = n['centre'] - n['half'], n['centre'] + n['half'], n['centre'], n['y'], n['width']
    return (f'M{x0} {y} L{xc} {y + h} L{xc} {y - h} Z', f'M{xc} {y + h} L{x1} {y} L{xc} {y - h} Z', (xc, y))


def asset(lang, theme):
    c = THEMES[theme]
    box, legs, letters, zed, star = parts(lang)
    tail, point, (cx, cy) = needle_parts()
    gold = ''.join(f'<path fill="{c["gold"]}" d="{p[1]}"/>' if p[0] == 'fill' else
                   f'<path d="{p[1]}" fill="none" stroke="{c["gold"]}" stroke-width="{STROKE}" stroke-linejoin="{p[2]}" stroke-miterlimit="8"/>'
                   for p in zed)
    body = (f'<path d="{legs}"/><circle class="wR" cx="344" cy="776" r="44" fill="none" stroke="{c["ink"]}" stroke-width="26"/>'
            f'<g transform="translate({SHIFT},0)">{gold}</g>'
            + ''.join(f'<path transform="translate({x},0)" d="{d}"/>' for x, d in letters))
    needle = (f'<path fill="{c["tail"]}" d="{tail}"/><path fill="{c["acc"]}" d="{point}"/>'
              f'<circle cx="{cx}" cy="{cy}" r="{NEEDLE["pivot"]}" fill="{c["ink"]}"/><circle cx="{cx}" cy="{cy}" r="{NEEDLE["eye"]}" fill="{c["eye"]}"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{box}"><g transform="translate(0,700) scale(1,-1)">'
            f'<g fill="{c["ink"]}">{body}</g><g>{needle}</g>'
            f'<g stroke="{c["acc"]}" fill="none"><path fill="{c["gold"]}" d="{star}" stroke="none"/></g></g></svg>')


def web(lang):
    box, legs, letters, zed, star = parts(lang)
    tail, point, (cx, cy) = needle_parts()
    gold = ''.join(f'<path class="wZ" d="{p[1]}"/>' if p[0] == 'fill' else
                   f'<path class="wZ" style="fill:none" d="{p[1]}" stroke-width="{STROKE}" stroke-linejoin="{p[2]}" stroke-miterlimit="8"/>'
                   for p in zed)
    body = (f'<path d="{legs}"/><circle class="wR" cx="344" cy="776" r="44" fill="none" stroke="currentColor" stroke-width="26"/>'
            f'<g transform="translate({SHIFT},0)">{gold}</g>'
            + ''.join(f'<path transform="translate({x},0)" d="{d}"/>' for x, d in letters))
    needle = (f'<path class="wN" d="{tail}"/><path class="wP" d="{point}"/>'
              f'<circle class="wH" cx="{cx}" cy="{cy}" r="{NEEDLE["pivot"]}"/><circle class="wE" cx="{cx}" cy="{cy}" r="{NEEDLE["eye"]}"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{box}" class="qWord" aria-hidden="true">'
            f'<g transform="translate(0,700) scale(1,-1)"><g class="wI">{body}</g><g>{needle}</g>'
            f'<g class="wA" fill="none"><path class="wZ" d="{star}" stroke="none"/></g></g></svg>')


def main():
    for lang in ('ru', 'en'):
        for theme in ('light', 'dark'):
            (HERE / f'wordmark-{lang}-{theme}.svg').write_text(asset(lang, theme), encoding='utf-8')
    if ATLAS.is_file():
        text = ATLAS.read_text(encoding='utf-8')
        start = text.index('const WORD=')
        end = text.index('};', start) + 2
        words = text[start:end]
        for lang in ('ru', 'en'):
            words = re.sub(rf"{lang}:'(?:[^'\\]|\\.)*'", lambda m, lang=lang: f"{lang}:'{web(lang)}'", words, count=1)
        ATLAS.write_text(text[:start] + words + text[end:], encoding='utf-8')
    print('wordmarks written')


if __name__ == '__main__':
    main()
