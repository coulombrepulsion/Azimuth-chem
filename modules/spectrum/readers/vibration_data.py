"""ORCA text normal modes: retain printed Cartesian displacement ratios."""

from dataclasses import dataclass, replace
from math import isfinite, hypot, sin
import re
from azimuth.core import Atom, read_xyz
from azimuth.i18n import tr


@dataclass(frozen=True)
class Vibration:
    index: int
    frequency: float
    vectors: tuple[tuple[float, float, float], ...] | None = None
    intensity: float | None = None  # km/mol only, never substitute T**2
    raman_activity: float | None = None  # Raman activity S, A^4/amu (ORCA «RAMAN SPECTRUM»)
    depolarization: float | None = None  # depolarization ratio of linearly polarized light, 0..0.75
    # the rotational strength of the mode, 10⁻⁴⁴ esu²·cm²,
    # signed (ORCA «VCD SPECTRUM CALCULATION» of %freq DoVCD; Gaussian «Rot. str.» of Freq=VCD)
    vcd: float | None = None

    @property
    def animatable(self):
        _validate_mode(self)
        return self.frequency != 0 and self.vectors is not None and any(v != 0 for row in self.vectors for v in row)


def _validate_mode(mode):
    """Reject invalid values before they reach normalization or the renderer."""
    if not isfinite(mode.frequency):
        raise ValueError(tr('Частота должна быть конечным числом.'))
    if mode.vectors is not None:
        for row in mode.vectors:
            if len(row) != 3 or not all(isfinite(v) for v in row):
                raise ValueError(tr('Вектор смещения должен содержать три конечных числа.'))


def read_vibrations(text, frequencies):
    from modules.spectrum.readers.orca import NUMBER, number

    if 'VIBRATIONAL FREQUENCIES' not in text:
        return None, ()
    prefix, section = text.rsplit('VIBRATIONAL FREQUENCIES', 1)
    geometry = None
    blocks = re.split(r'CARTESIAN COORDINATES\s*\(ANGSTROE?M\)', prefix)
    if len(blocks) > 1:
        rows = []
        for line in blocks[-1].splitlines():
            if not rows and (not line.strip() or set(line.strip()) == {'-'}):
                continue
            if not line.strip():
                break
            if not re.fullmatch(r'\s*[A-Z][a-z]?\s+' + NUMBER + r'\s+' + NUMBER + r'\s+' + NUMBER + r'\s*', line):
                rows = []
                break
            f = line.split()
            rows.append(' '.join([f[0], *(str(number(v)) for v in f[1:])]))
        if rows:
            try:
                geometry = read_xyz(tr(f'{len(rows)}\nГеометрия частот ORCA\n') + '\n'.join(rows))
            except ValueError:
                pass
    # A complete 3N frequency list provides an independent check on geometry size.
    n = 3 * len(geometry.atoms) if geometry else 0
    if set(i for i, _ in frequencies) != set(range(n)) or len(frequencies) != n:
        geometry = None
        n = 0
    columns = {}
    bad = set()
    header = []
    started = False
    if n and 'NORMAL MODES' in section:
        matrix = section.split('NORMAL MODES', 1)[1]
        matrix = re.split(r'IR SPECTRUM|RAMAN SPECTRUM|VCD SPECTRUM|THERMOCHEMISTRY', matrix)[0]
        for line in matrix.splitlines():
            fields = line.split()
            if not fields:
                continue
            if all(f.isdigit() for f in fields) and len(set(fields)) == len(fields) and all(int(f) < n for f in fields):
                header = [int(f) for f in fields]
                started = False
                for c in header:
                    if c in columns:
                        bad.add(c)
                    columns.setdefault(c, {})
                continue
            if header and len(fields) == len(header) + 1 and fields[0].isdigit():
                try:
                    values = [number(f) for f in fields[1:]]
                except ValueError:
                    bad.update(header)
                    header = []
                    continue
                row = int(fields[0])
                started = True
                for c, value in zip(header, values):
                    if row >= n or row in columns[c] or not isfinite(value):
                        bad.add(c)
                    columns[c][row] = value
            elif started and header:
                # End prose cannot supply missing rows of a block.
                header = []
    intensities = {}
    if 'IR SPECTRUM' in section:
        ir = section.split('IR SPECTRUM', 1)[1]
        ir = re.split(r'RAMAN SPECTRUM|VCD SPECTRUM|THERMOCHEMISTRY', ir)[0]
        has_units = False
        has_int = False
        started = False
        known = dict(frequencies)
        for line in ir.splitlines():
            has_units = has_units or 'km/mol' in line
            has_int = has_int or bool(re.search(r'\bInt\b', line))
            m = re.match(r'\s*(\d+)\s*:\s*(' + NUMBER + r')\s+(' + NUMBER + r')\s+(' + NUMBER + r')', line)
            if m:
                started = True
                idx = int(m[1])
                freq = number(m[2])
                value = number(m[4])
                if (
                    has_units
                    and has_int
                    and idx in known
                    and abs(known[idx] - freq) < 0.1
                    and isfinite(value)
                    and value >= 0
                ):
                    intensities[idx] = value
            elif started and line.strip():
                break
    raman = _raman_rows(section, dict(frequencies))
    vcd = vcd_rows(text, dict(frequencies))  # the whole output: the place of the table is not checked
    modes = []
    for i, f in frequencies:
        if not isfinite(f):
            continue
        values = columns.get(i, {})
        vectors = (
            tuple(tuple(values[3 * a + k] for k in range(3)) for a in range(n // 3))
            if n and i not in bad and set(values) == set(range(n))
            else None
        )
        activity, depolarization = raman.get(i, (None, None))
        modes.append(Vibration(i, f, vectors, intensities.get(i), activity, depolarization, vcd.get(i)))
    return geometry, tuple(modes)


def vcd_rows(section, known):
    """{mode: R, 10⁻⁴⁴ esu²·cm²} from the last «VCD SPECTRUM CALCULATION» of ORCA (%freq DoVCD true end
    with analytic frequencies; the table «Mode Freq VCD-Intensity / (1/cm) (1E-44*esu^2*cm^2)», rows «8 90.5 13.12» —
    the ORCA 6.0 tutorial «Vibrational Circular Dichroism»); a row whose frequency is not the mode's (it is printed
    with one decimal: 0.6 cm⁻¹) is left out."""
    from modules.spectrum.readers.orca import NUMBER, number

    if 'VCD SPECTRUM CALCULATION' not in section:
        return {}
    table = section.rsplit('VCD SPECTRUM CALCULATION', 1)[1]
    table = re.split(r'THERMOCHEMISTRY|RAMAN SPECTRUM|IR SPECTRUM|VIBRATIONAL FREQUENCIES', table)[0]
    if 'VCD-Intensity' not in table:
        return {}
    table = table.split('VCD-Intensity', 1)[1]
    found, started = {}, False
    for line in table.splitlines():
        m = re.match(r'\s*(\d+)\s+(' + NUMBER + r')\s+(' + NUMBER + r')\s*$', line)
        if m:
            started = True
            index, frequency, value = int(m[1]), number(m[2]), number(m[3])
            if index in known and abs(known[index] - frequency) < 0.6 and isfinite(value):
                found[index] = value
        elif started and line.strip() and not set(line.strip()) <= {'-'}:
            break
    return found


DEPOLARIZATION_MAX = 0.75  # linearly polarized light: rho = 3 g^2 / (45 a^2 + 4 g^2) <= 3/4 (a = 0)


def _raman_rows(section, known):
    """{mode: (activity A^4/amu, depolarization)} from the «RAMAN SPECTRUM» table of ORCA («Mode freq
    (cm**-1) Activity Depolarization», rows «6: 1709.38 7.539542 0.541696»); a row whose frequency is not the
    mode's (0.1 cm^-1), whose activity is negative or whose depolarization lies outside 0..0.75 is left out."""
    from modules.spectrum.readers.orca import NUMBER, number

    if 'RAMAN SPECTRUM' not in section:
        return {}
    part = re.split(r'THERMOCHEMISTRY|The first frequency', section.split('RAMAN SPECTRUM', 1)[1])[0]
    row = re.compile(r'\s*(\d+)\s*:\s*(' + NUMBER + r')\s+(' + NUMBER + r')\s+(' + NUMBER + r')\s*$')
    found = {}
    started = False
    for line in part.splitlines():
        m = row.match(line)
        if m:
            started = True
            index, freq, activity, rho = int(m[1]), number(m[2]), number(m[3]), number(m[4])
            if (index in known and abs(known[index] - freq) < 0.1 and isfinite(activity) and activity >= 0
                    and isfinite(rho) and -1e-6 <= rho <= DEPOLARIZATION_MAX + 1e-6):
                found[index] = (activity, rho)
        elif started and line.strip():
            break
    return found


def normalized_vectors(mode):
    """Normalize safely; mathematical contract and error bounds: docs/features/VIBRATIONS.md."""
    if not mode.animatable:
        return ()
    # Scaling first prevents both squaring overflow and subnormal underflow.
    scale = max(abs(v) for row in mode.vectors for v in row)
    scaled = tuple(tuple(v / scale for v in row) for row in mode.vectors)
    maximum = max(hypot(*row) for row in scaled)
    return tuple(tuple(v / maximum for v in row) for row in scaled)


def displaced(geometry, vectors, amplitude, phase):
    """Peak displacement of the largest-moving atom is amplitude in angstrom."""
    if len(vectors) != len(geometry.atoms):
        raise ValueError(tr('Число векторов не совпадает с числом атомов.'))
    factor = amplitude * sin(phase)
    return replace(
        geometry,
        atoms=tuple(
            Atom(a.symbol, *(p + factor * d for p, d in zip(a.position, v))) for a, v in zip(geometry.atoms, vectors)
        ),
    )


# -- frames and displaced geometries ------------------------------------------------------
# One period of the animation as frames (for a GIF or a multi-frame XYZ) and a geometry moved along a
# mode (to leave a saddle point along an imaginary mode, or to look at one side of a vibration).
# The vectors are normalized_vectors(mode): the largest-moving atom has length 1, so amplitude and step
# are the largest displacement of one atom in angstrom, as in displaced().
FRAMES = 20


def vibration_frames(geometry, vectors, amplitude, count=FRAMES):
    """count geometries over one period: frame k has the phase 2 pi k / count (frame 0 = geometry)."""
    from math import pi

    if not isinstance(count, int) or not 4 <= count <= 240:
        raise ValueError(tr('Число кадров — от 4 до 240.'))
    if not isfinite(amplitude) or not 0 < amplitude <= 2:
        raise ValueError(tr('Амплитуда — от 0 до 2 Å.'))
    return [displaced(geometry, vectors, amplitude, 2 * pi * k / count) for k in range(count)]


def displaced_along(geometry, vectors, step, sign):
    """geometry moved by sign * step (Å, largest atom) along the mode; sign is +1 or -1."""
    from math import pi

    if sign not in (1, -1):
        raise ValueError('sign must be +1 or -1')
    if not isfinite(step) or not 0 < step <= 2:
        raise ValueError(tr('Смещение — от 0 до 2 Å.'))
    return displaced(geometry, vectors, step, sign * pi / 2)


def frames_xyz(frames, label):
    """Several XYZ frames in one text; each comment line names the mode and the phase."""
    parts = []
    for k, frame in enumerate(frames):
        parts.append(replace(frame, title=f'{label}; frame {k + 1}/{len(frames)}').xyz().rstrip('\n'))
    return '\n'.join(parts) + '\n'
