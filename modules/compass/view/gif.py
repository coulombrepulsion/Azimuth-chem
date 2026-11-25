"""Animated GIF of Compass pictures: rotation of the molecule, optimization steps.

Pillow is used when it is installed (better colours); otherwise a small encoder of this file
writes the GIF itself: a fixed palette of 6×7×6 colours plus grey levels, LZW compression, an
endless loop (NETSCAPE2.0), transparent pixels kept transparent.
"""

import struct

import numpy as np

MAX_WIDTH = 640


def rgba(image):
    """QImage → numpy H×W×4 (uint8), at most MAX_WIDTH pixels wide."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage

    if image.width() > MAX_WIDTH:
        image = image.scaledToWidth(MAX_WIDTH, Qt.TransformationMode.SmoothTransformation)
    image = image.convertToFormat(QImage.Format.Format_RGBA8888)
    w, h = image.width(), image.height()
    data = bytes(image.constBits())[: image.bytesPerLine() * h]
    arr = np.frombuffer(data, dtype=np.uint8).reshape(h, image.bytesPerLine() // 4, 4)[:, :w]
    return arr.copy()


def write_gif(path, frames, delay_ms=100):
    if not frames:
        raise ValueError('no frames')
    arrays = [f if isinstance(f, np.ndarray) else rgba(f) for f in frames]
    h = min(a.shape[0] for a in arrays)
    w = min(a.shape[1] for a in arrays)
    arrays = [a[:h, :w] for a in arrays]
    try:
        from PIL import Image
    except ImportError:
        Image = None
    if Image is not None:
        images = [Image.fromarray(a, 'RGBA') for a in arrays]
        images[0].save(str(path), save_all=True, append_images=images[1:], duration=delay_ms, loop=0, disposal=2)
        return path
    with open(path, 'wb') as out:
        out.write(encode(arrays, delay_ms))
    return path


# -- the encoder without Pillow --------------------------------------------------------------------
def _palette():
    pal = [(r * 51, g * 42 + (g > 5) * 3, b * 51) for r in range(6) for g in range(7) for b in range(6)]  # 252
    pal += [(64, 64, 64), (128, 128, 128), (192, 192, 192)]
    pal += [(0, 0, 0)]  # 255: transparent
    return np.array(pal, dtype=np.uint8)


def _indices(a):
    r = np.rint(a[..., 0] / 51.0).astype(np.int32)
    g = np.clip(np.rint(a[..., 1] / 42.5).astype(np.int32), 0, 6)
    b = np.rint(a[..., 2] / 51.0).astype(np.int32)
    idx = (r * 7 + g) * 6 + b
    idx[a[..., 3] < 128] = 255
    return idx.astype(np.uint8)


def _lzw(data, min_size=8):
    clear, end = 1 << min_size, (1 << min_size) + 1
    table = {bytes([i]): i for i in range(clear)}
    size, nxt = min_size + 1, end + 1
    bits, nbits, out = 0, 0, bytearray()

    def emit(code):
        nonlocal bits, nbits
        bits |= code << nbits
        nbits += size
        while nbits >= 8:
            out.append(bits & 255)
            bits >>= 8
            nbits -= 8

    emit(clear)
    w = b''
    for byte in data:
        wc = w + bytes((byte,))
        if wc in table:
            w = wc
            continue
        emit(table[w])
        if nxt < 4096:
            table[wc] = nxt
            nxt += 1
            if nxt > (1 << size) and size < 12:
                size += 1
        else:
            emit(clear)
            table = {bytes([i]): i for i in range(clear)}
            size, nxt = min_size + 1, end + 1
        w = bytes((byte,))
    if w:
        emit(table[w])
    emit(end)
    if nbits:
        out.append(bits & 255)
    blocks = bytearray([min_size])
    for k in range(0, len(out), 255):
        chunk = out[k : k + 255]
        blocks.append(len(chunk))
        blocks += chunk
    blocks.append(0)
    return bytes(blocks)


def encode(arrays, delay_ms):
    h, w = arrays[0].shape[:2]
    out = bytearray(b'GIF89a' + struct.pack('<HHBBB', w, h, 0xF7, 0, 0))
    out += _palette().tobytes()
    out += b'\x21\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00'
    for a in arrays:
        out += b'\x21\xf9\x04' + struct.pack(
            '<BHBB', 0x09, max(2, delay_ms // 10), 255, 0
        )  # disposal 2, transparent 255
        out += b'\x2c' + struct.pack('<HHHHB', 0, 0, w, h, 0)
        out += _lzw(_indices(a).tobytes())
    out += b'\x3b'
    return bytes(out)
