"""The compass of the icon of the program, for the signs of waiting.
Oracle: assets/app-icon/glyph.svg (from SMALL_BELOW px up) and glyph-small.svg (smaller) — read off their lines and
paths: the ring, the divisions, the meridian, the arc of the azimuth, the needle, its axis; no star. Units of the icon:
the centre at 0, the ring of radius 330, the glyph BOX across (its viewBox 760); angles clockwise from the north.
Drawn by azimuth.controls.draw_compass (the program) and tools/build_atlas_site.compass_svg (the site)."""

BOX = 760.0
SMALL_BELOW = 40  # px: a smaller compass is the small glyph (thicker lines, the four divisions of the cardinal points)

# ring: stroke width; ticks: (every degrees, from radius, to radius, width, opacity of the ink) — a division is drawn
# by the first row its angle falls on; meridian: the dotted line from the axis to the north — (length, width, opacity,
# dash, gap) or None; arc: (radius, width);
# needle: (point length, half width at the axis, tail length); axis: (radius, radius of its eye)
VARIANTS = {
    'full': {'ring': 12.0,
             'ticks': ((90, 326.0, 284.0, 10.0, 0.9), (30, 326.0, 300.0, 6.0, 0.55), (5, 326.0, 312.0, 4.0, 0.3)),
             'meridian': (300.0, 8.0, 0.35, 4.0, 22.0), 'arc': (215.0, 22.0), 'needle': (300.0, 36.0, 150.0), 'axis': (26.0, 10.0)},
    'small': {'ring': 28.0, 'ticks': ((90, 326.0, 270.0, 26.0, 0.9),),
              'meridian': None, 'arc': (200.0, 44.0), 'needle': (300.0, 58.0, 150.0), 'axis': (34.0, 13.0)},
}
RING_RADIUS, RING_OPACITY = 330.0, 0.5

# the colours of glyph.svg (False) and of dark/glyph.svg (True, light strokes for a dark ground)
COLOURS = {False: {'ring': '#2a62b8', 'ink': '#1b2230', 'arc': '#b8893f', 'point': '#2a62b8', 'tail': '#9aa6b8',
                   'axis': '#1b2230', 'eye': '#ffffff'},
           True: {'ring': '#6ea2f0', 'ink': '#e7eaf0', 'arc': '#e6d2ad', 'point': '#6ea2f0', 'tail': '#3a4a66',
                  'axis': '#e7eaf0', 'eye': '#141a22'}}


def variant(side):
    """The glyph for a compass side px across."""
    return 'small' if side < SMALL_BELOW else 'full'


def divisions(name):
    """[(degrees, from radius, to radius, width, opacity)] of the dial of the variant, each angle once."""
    out = {}
    for step, r0, r1, width, opacity in VARIANTS[name]['ticks']:
        for degrees in range(0, 360, step):
            out.setdefault(degrees, (degrees, r0, r1, width, opacity))
    return sorted(out.values())
