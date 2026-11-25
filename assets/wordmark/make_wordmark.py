import sys, math

sys.path.insert(0, '/tmp/bshim')
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen

F = '/home/claude/v2/quas_atlas/src/quas_atlas/web/assets/fonts/'
fonts = {
    'cyr': TTFont(F + 'golos-text-cyrillic-600-normal.woff2'),
    'lat': TTFont(F + 'golos-text-latin-600-normal.woff2'),
}


def glyph(ch):
    f = fonts['cyr' if ord(ch) > 0x400 else 'lat']
    name = f.getBestCmap()[ord(ch)]
    gs = f.getGlyphSet()
    g = gs[name]
    pen = SVGPathPen(gs)
    g.draw(pen)
    bp = BoundsPen(gs)
    g.draw(bp)
    return pen.getCommands(), g.width, bp.bounds, f['head'].unitsPerEm, f['OS/2'].sCapHeight


def build(word, track=0.16, arcA=True, star=True, star_r=170):
    parts = []
    x = 0
    cap = None
    upm = None
    accent = []
    for i, ch in enumerate(word):
        d, adv, b, upm, cap = glyph(ch)
        if ch in 'АA' and arcA:
            h = cap
            hw = 136
            ax = x + adv / 2
            lx = x + 18
            rx = x + adv - 18
            L = f'M{lx:.0f} 0 L{lx + hw:.0f} 0 L{ax + hw / 2:.0f} {h:.0f} L{ax - hw / 2:.0f} {h:.0f} Z'
            R = f'M{rx - hw:.0f} 0 L{rx:.0f} 0 L{ax + hw / 2:.0f} {h:.0f} L{ax - hw / 2:.0f} {h:.0f} Z'
            parts.append(f'<path d="{L} {R}"/>')
            # a ring over the apex of the A, as in Å — the ångström (class wR, in the ink of the letters)
            parts.append(f'<circle class="wR" cx="{ax:.0f}" cy="{h + 76:.0f}" r="44" fill="none" stroke="currentColor" stroke-width="26"/>')
            # the ruler a straight bar low in the letter, shifted right --
            # from the left leg to beyond the right leg -- with white marks, every second one longer
            yb = h * 0.29
            outer_l = lx + yb * (ax - hw / 2 - lx) / h
            outer_r = rx - yb * (rx - ax - hw / 2) / h
            xl = outer_l + hw * 1.4
            xr = outer_r + hw * 0.80
            bw = hw * 0.70
            accent.append(f'<path d="M{xl:.0f} {yb:.0f} L{xr:.0f} {yb:.0f}" fill="none" stroke-width="{bw:.0f}"/>')
            step = 56
            y0 = yb - bw / 2
            ticks = []
            k = 0
            tx = xl + step * 0.75
            while tx < xr - step * 0.4:
                L = bw * (0.58 if k % 2 == 0 else 0.36)
                ticks.append(f'M{tx:.0f} {y0:.0f} L{tx:.0f} {y0 + L:.0f}')
                tx += step
                k += 1
            accent.append(
                f'<path class="wT" d="{" ".join(ticks)}" fill="none" stroke="#ffffff" stroke-width="{hw * 0.085:.0f}"/>'
            )
        else:
            # З / Z in the light brown of the glyph's turning arrow (class wZ, coloured in svg_for); on the dark
            # panel a stronger brown (#d6a95c) than the pale arrow of the dark glyph (#e6d2ad: hardly told from white)
            mark = ' class="wZ"' if ch in 'ЗZ' else ''
            parts.append(f'<path{mark} transform="translate({x:.0f},0)" d="{d}"/>')
        x += adv + (track * upm if i < len(word) - 1 else 0)
    W = x
    H = cap
    if star:
        sx = W + 0.12 * upm + star_r
        sy = H - star_r * 0.15
        r1, r2 = star_r, star_r * 0.3
        pts = []
        for k in range(8):
            rr = r1 if k % 2 == 0 else r2
            t = math.radians(k * 45)
            pts.append(f'{sx + rr * math.sin(t):.0f} {sy + rr * math.cos(t):.0f}')
        accent.append('<path class="wS" d="M' + ' L'.join(pts) + ' Z" stroke="none"/>')
        W = sx + star_r
    body = ''.join(parts)
    acc = ''.join(accent)
    return W, H, body, acc


for word, name in (('АЗИМУТ', 'ru'), ('AZIMUTH', 'en')):
    W, H, body, acc = build(word)
    pad = 10
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-pad} {-pad} {W + 2 * pad:.0f} {H + 2 * pad:.0f}" class="qWord">'
        f'<g transform="translate(0,{H:.0f}) scale(1,-1)"><g fill="currentColor">{body}</g>'
        f'<g stroke="var(--accent,#6ea2f0)" fill="none">{acc}</g></g></svg>'
    )
    open(f'word-{name}.svg', 'w', encoding='utf-8').write(svg)
print('ok')


def svg_for(word, ink, accent, cls=None, letter=None):
    W, H, body, acc = build(word)
    pad = 10
    top = 130
    head = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-pad} {-pad - top} {W + 2 * pad:.0f} {H + 2 * pad + top:.0f}"'
        + (f' class="{cls}" aria-hidden="true"' if cls else '')
        + '>'
    )
    if cls:  # web: colours from CSS
        return (
            head
            + f'<g transform="translate(0,{H:.0f}) scale(1,-1)"><g class="wI">{body}</g><g class="wA" fill="none">{acc}</g></g></svg>'
        )
    acc = acc.replace('class="wS" ', f'fill="{accent}" ')
    # the brown З / Z; without the thin outline in the ink of the other letters (the user's wish) — З
    # still dips 12 units under the baseline, hub/branding.py wordmark_pixmap draws with a margin
    body = body.replace('stroke="currentColor"', f'stroke="{ink}"')
    body = body.replace('class="wZ" ', f'fill="{letter or ink}" ')
    return (
        head
        + f'<g transform="translate(0,{H:.0f}) scale(1,-1)"><g fill="{ink}">{body}</g><g stroke="{accent}" fill="none">{acc}</g></g></svg>'
    )


import json

web = {k: svg_for(w, None, None, 'qWord') for k, w in (('ru', 'АЗИМУТ'), ('en', 'AZIMUTH'))}
json.dump(web, open('web_words.json', 'w', encoding='utf-8'), ensure_ascii=False)
for k, w in (('ru', 'АЗИМУТ'), ('en', 'AZIMUTH')):
    open(f'wordmark-{k}-dark.svg', 'w', encoding='utf-8').write(svg_for(w, '#ffffff', '#6ea2f0', letter='#d6a95c'))  # on the dark sidebar
    open(f'wordmark-{k}-light.svg', 'w', encoding='utf-8').write(svg_for(w, '#1b2230', '#2a62b8', letter='#b8893f'))
print({k: len(v) for k, v in web.items()}, "'" in web['ru'])
