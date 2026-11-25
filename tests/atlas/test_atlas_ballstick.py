"""Atlas ball-and-stick renderer (modules/atlas/atlas_v2/quas_atlas/web/assets/js/ballstick.js).

The JavaScript file is a port of modules/compass/view/raster.py; raster.py is the reference (its own tests in
tests/compass/test_raster.py use analytic oracles). Equivalence tier: bound. Opaque pixels and coverage agree within
1 unit of 8-bit rounding (the same float formulas; float32 buffers in both). Partly covered pixels are compared
after converting the reference's premultiplied 8-bit colour back to straight alpha, which amplifies its
rounding: |delta| <= 0.5 * 255 / alpha + 1. Needs Node.js; skipped without it (the page itself is checked in a
browser, see CHANGELOG).
"""

import base64
import json
import re
import shutil
import subprocess
from math import sqrt

import numpy as np
import pytest

from modules.atlas.paths import ATLAS_HOME
from modules.compass.view.raster import render

WEB = ATLAS_HOME / 'quas_atlas' / 'web'
JS = WEB / 'assets' / 'js' / 'ballstick.js'
RED, BLUE, GREY = (220, 40, 40), (40, 40, 220), (120, 136, 151)
SCENES = [
    (120, 100, [(40.5, 50.5, 0.0, 30.0, RED)], [((40.5, 50.5, 0.0), (110.0, 50.5, 0.0), 8.0, BLUE, BLUE, (0.5, 0.5))]),
    (100, 100, [(50.5, 50.5, 0.0, 30.0, RED)], [((0.0, 50.5, 60.0), (100.0, 50.5, 60.0), 5.0, BLUE, BLUE, (0.5, 0.5))]),
    (
        140,
        120,
        [(30.0 + 25 * k, 40.0 + 15 * k, 5.0 * k, 14.0, RED) for k in range(4)],
        [
            ((30.0, 40.0, 0.0), (105.0, 85.0, 15.0), 4.0, RED, BLUE, (0.4, 0.6)),
            ((30.0, 40.0, 0.0), (55.0, 55.0, 5.0), 3.0, GREY, RED, (0.5, 0.5)),
        ],
    ),
]


def js_render(width, height, spheres, rods, ss):
    if shutil.which('node') is None:
        pytest.skip('Node.js is not installed')
    sp = [dict(x=x, y=y, z=z, r=r, c=list(c)) for x, y, z, r, c in spheres]
    rd = [
        dict(a=list(a), b=list(b), rho=rho, ca=list(ca), cb=list(cb), u0=u[0], u1=u[1]) for a, b, rho, ca, cb, u in rods
    ]
    code = (
        f'const B=require({json.dumps(str(JS))});'
        f'const r=B.rasterizeFull({width},{height},{json.dumps(sp)},{json.dumps(rd)},{ss});'
        "process.stdout.write(Buffer.from(r.buffer).toString('base64'))"
    )
    out = subprocess.run(['node', '-e', code], capture_output=True, text=True, check=True, timeout=60).stdout
    return np.frombuffer(base64.b64decode(out), np.uint8).reshape(height, width, 4).astype(float)


@pytest.mark.parametrize('ss', [1, 2])
@pytest.mark.parametrize('scene', range(len(SCENES)))
def test_port_agrees_with_raster_py(scene, ss):
    width, height, spheres, rods = SCENES[scene]
    reference = render(width, height, spheres, rods, supersample=ss).astype(float)  # B, G, R, A premultiplied
    alpha = reference[..., 3]
    straight = reference[..., [2, 1, 0]] * 255 / np.maximum(alpha, 1)[..., None]
    got = js_render(width, height, spheres, rods, ss)
    assert np.abs(got[..., 3] - alpha).max() <= 1
    opaque, edge = alpha == 255, (alpha > 0) & (alpha < 255)
    assert np.abs(got[..., :3][opaque] - straight[opaque]).max() <= 1
    if edge.any():
        bound = 0.5 * 255 / alpha[edge] + 1
        assert (np.abs(got[..., :3][edge] - straight[edge]).max(axis=-1) <= bound).all()


def test_rod_meets_its_atom_along_the_analytic_intersection_line():
    # the same analytic oracle as for raster.py: x0 = sqrt(r^2 - rho^2) from the centre
    r, rho, cx, cy = 30.0, 12.0, 40.5, 50.5
    x0 = cx + sqrt(r * r - rho * rho)
    image = js_render(
        120, 100, [(cx, cy, 0.0, r, RED)], [((cx, cy, 0.0), (cx + 70, cy, 0.0), rho, BLUE, BLUE, (0.5, 0.5))], 1
    )
    for dy in (-6, 0, 6):
        before, after = image[int(cy) + dy, int(x0 - 2)], image[int(cy) + dy, int(x0 + 2)]
        assert before[0] > before[2] and after[2] > after[0]


@pytest.mark.parametrize('lang', ['ru', 'en', 'zh'])
def test_symmetry_page_uses_the_renderer(lang):
    page = (WEB / lang / 'symmetry.html').read_text(encoding='utf-8')
    scripts = re.findall(r'<script src="([^"]+)"', page)
    assert '../assets/js/ballstick.js' in scripts
    assert (
        scripts.index('../assets/js/ballstick.js') < scripts.index('js/symmetry.js') < scripts.index('js/symmetry.2.js')
    )
    model = (WEB / lang / 'js' / 'symmetry.js').read_text(encoding='utf-8')
    compare = (WEB / lang / 'js' / 'symmetry.2.js').read_text(encoding='utf-8')
    for code in (model, compare):  # balls and sticks, and the previous positions in the style of Compass
        assert 'BallStick.draw(' in code and 'BallStick.ghost(' in code
