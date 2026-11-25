"""Quill stands on a surface: a hand-drawn hatched ground around her feet and the things that stand by her.

§1 PURPOSE
    Quill should stand on something, not hang in the air: a hatched ground around her feet and the things she
    touches. The pictures get the ground drawn into the files, so the program
    and the site show the same.
§2 ALGORITHM The floor of a picture is its lowest opaque row; a column whose lowest opaque pixel lies within BAND of the
    height of the figure above it stands on the floor (feet, the legs of a desk, a pile of books, a can) — things held
    in the air do not. Around every such contact point a flat ellipse (GROUND: 0.12 × 0.038 of the figure) — their union
    is the surface; a smaller one (TOUCH: 0.045 × 0.015) where they touch. The surface is hatched «/» at −55°, the touch
    cross- hatched at +55°: strokes with a little jitter of place, wave and width, drawn three times larger and reduced
    (smooth edges); the ink fades to the edges of the ellipses and of the picture (no cut at the sides). The colour is
    the warm brown of Quill's outlines; the canvas grows by PAD of its height at the bottom, the picture stays at its
    top. An animation gets one ground for all its frames, from the union of its figures (no flicker; quality 80,
    minimize_size).
§4 SPECIFICATION
    ground(image, size=None) -> RGBA image (taller by PAD); ground_file(path, out=None) -> out (an animated WebP keeps
    its frames, durations and loop); main: python3 tools/quill_ground.py FILE … [--sheet PATH] — in place.
§6 NOTES
    The pictures without the ground stay in the git history.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

BAND = 0.16
GROUND = (0.12, 0.038)
TOUCH = (0.045, 0.015)
PAD = 0.04
INK = (96, 70, 50)
STRENGTH = 0.8


def figure(alpha):
    """(contact points [(x, y)], size of the figure) of an alpha (h, w) 0..1."""
    solid = alpha > 0.5
    rows = np.where(solid.any(axis=1))[0]
    if not len(rows):
        return np.zeros((0, 2), int), 0
    y0, size = rows.max(), rows.max() - rows.min()
    cols = np.where(solid.any(axis=0))[0]
    bottom = solid.shape[0] - 1 - np.argmax(solid[::-1, cols], axis=0)
    keep = bottom >= y0 - BAND * size
    return np.stack([cols[keep], bottom[keep]], axis=1), size


def blobs(shape, pts, rx, ry, step=2):
    """The union of flat soft ellipses centred on the points."""
    H, w = shape
    out = np.zeros(shape)
    rx, ry = max(rx, 1.0), max(ry, 1.0)
    for x, y in pts[::step]:
        x0, x1 = int(max(0, x - rx)), int(min(w, x + rx + 1))
        y0, y1 = int(max(0, y - ry)), int(min(H, y + ry + 1))
        if x0 >= x1 or y0 >= y1:
            continue
        xx = (np.arange(x0, x1) - x) / rx
        yy = (np.arange(y0, y1) - y) / ry
        d = yy[:, None] ** 2 + xx[None, :] ** 2
        np.maximum(out[y0:y1, x0:x1], np.clip(1 - d, 0, 1), out=out[y0:y1, x0:x1])
    return out


def strokes(shape, size, angle, spacing, width, seed, scale=3):
    """Hand-drawn parallel strokes over the canvas: alpha 0..1."""
    H, w = shape
    rng = np.random.default_rng(seed)
    big = Image.new('L', (w * scale, H * scale), 0)
    draw = ImageDraw.Draw(big)
    t = np.tan(np.radians(angle))
    span = int(H * abs(t)) + 2
    x = -span
    while x < w + span:
        x0 = x + rng.uniform(-0.25, 0.25) * spacing
        wob = rng.uniform(-0.15, 0.15) * spacing
        pts = [((x0 + t * y + wob * np.sin(y / (0.07 * size + 1))) * scale, y * scale) for y in np.linspace(0, H, 12)]
        draw.line(pts, fill=int(255 * rng.uniform(0.75, 1.0)), width=max(1, int(width * scale * rng.uniform(0.8, 1.2))))
        x += spacing
    return np.asarray(big.resize((w, H), Image.LANCZOS)) / 255.0


class Ground:
    """The strokes of one picture (or of all the frames of an animation) and the ground of each frame."""

    def __init__(self, w, h, size):
        self.w, self.h, self.size = w, h, size
        self.H = h + int(round(PAD * h))
        spacing, width = max(3.0, 0.016 * size), max(1.0, 0.0035 * size)
        shape = (self.H, w)
        self.one = strokes(shape, size, -55, spacing, width, 1)
        self.two = strokes(shape, size, 55, spacing * 0.9, width, 2)
        edge = np.minimum(np.arange(w), np.arange(w)[::-1]) / max(1.0, 0.06 * size)
        self.edge = np.clip(edge, 0, 1)[None, :]

    def ink(self, alpha):
        pts, _ = figure(alpha)
        if not len(pts):
            return np.zeros((self.H, self.w))
        shape, s = (self.H, self.w), self.size
        g = np.clip(blobs(shape, pts, GROUND[0] * s, GROUND[1] * s) / 0.7, 0, 1) ** 0.9
        c = np.clip((blobs(shape, pts, TOUCH[0] * s, TOUCH[1] * s) - 0.1) / 0.5, 0, 1)
        return np.clip(self.one * g + self.two * c * 0.9, 0, 1) * STRENGTH * self.edge

    def apply(self, image):
        image = image.convert('RGBA')
        alpha = np.asarray(image)[..., 3] / 255.0
        base = np.zeros((self.H, self.w, 4), np.uint8)
        base[..., :3] = INK
        base[..., 3] = (self.ink(alpha) * 255).astype(np.uint8)
        canvas = Image.fromarray(base, 'RGBA')
        canvas.alpha_composite(image, (0, 0))
        return canvas


def ground(image, size=None):
    image = image.convert('RGBA')
    if size is None:
        size = figure(np.asarray(image)[..., 3] / 255.0)[1]
    return Ground(image.width, image.height, size).apply(image)


def ground_file(path, out=None, quality=90):
    path = Path(path)
    out = Path(out or path)
    source = Image.open(path)
    frames = getattr(source, 'n_frames', 1)
    if frames == 1:
        ground(source).save(out, 'WEBP', quality=quality, method=6)
        return out
    # an animation: one ground for all the frames, from the union of their figures (sampled) — it does not flicker and
    # the frames stay alike for the encoder
    union = None
    for k in range(0, frames, max(1, frames // 48)):
        source.seek(k)
        alpha = np.asarray(source.convert('RGBA'))[..., 3] / 255.0
        union = alpha if union is None else np.maximum(union, alpha)
    maker = Ground(source.width, source.height, figure(union)[1])
    ink = maker.ink(union)
    base = np.zeros((maker.H, maker.w, 4), np.uint8)
    base[..., :3] = INK
    base[..., 3] = (ink * 255).astype(np.uint8)
    floor = Image.fromarray(base, 'RGBA')
    images, durations = [], []
    for k in range(frames):
        source.seek(k)
        durations.append(source.info.get('duration') or 40)
        canvas = floor.copy()
        canvas.alpha_composite(source.convert('RGBA'), (0, 0))
        images.append(canvas)
    images[0].save(out, 'WEBP', save_all=True, append_images=images[1:], duration=durations,
                   loop=source.info.get('loop', 0), quality=80, method=4, minimize_size=True)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('files', nargs='*')
    parser.add_argument('--sheet', help='only a contact sheet of the pictures with the ground (nothing written)')
    args = parser.parse_args()
    if args.sheet:
        tiles = []
        for f in args.files:
            im = ground(Image.open(f))
            im.thumbnail((220, 220))
            tile = Image.new('RGBA', (220, 220), (246, 247, 250, 255))
            tile.alpha_composite(im, ((220 - im.width) // 2, (220 - im.height) // 2))
            tiles.append(tile)
        cols = 6
        sheet = Image.new('RGB', (220 * cols, 220 * ((len(tiles) + cols - 1) // cols)), 'white')
        for k, t in enumerate(tiles):
            sheet.paste(t.convert('RGB'), ((k % cols) * 220, (k // cols) * 220))
        sheet.save(args.sheet)
        return
    for f in args.files:
        ground_file(f)
        print(f, flush=True)


if __name__ == '__main__':
    sys.exit(main())
