from pathlib import Path
from math import pi
import pytest
from modules.spectrum.readers.orca import read_output
from modules.spectrum.readers.vibration_data import normalized_vectors, displaced

DEMO = (Path(__file__).parents[2] / 'examples/vibrations-demo.out').read_text()


def test_modes_match_ids_and_xyz_components():
    out = read_output(DEMO)
    assert len(out.modes) == 9 and len(out.vibration_geometry.atoms) == 3
    assert out.modes[6].vectors[0] == (0, 0, -0.0756)
    assert out.modes[6].vectors[1] == (-0.4, 0, 0.6)
    assert out.modes[7].vectors[1] == (0.7586, 0, 0.5043)
    assert out.modes[8].vectors[2] == (0.7586, 0, -0.5043)
    assert out.modes[6].intensity == 35 and out.modes[8].intensity == 80
    assert not any(m.animatable for m in out.modes[:6])


def test_partial_matrix_disables_only_incomplete_columns():
    text = DEMO.replace('8 0.600000 0.504300 -0.504300', '')
    out = read_output(text)
    assert all(m.vectors is None for m in out.modes[6:])
    assert out.modes[0].vectors is not None


def test_missing_modes_never_fabricates_displacements():
    out = read_output(DEMO.split('NORMAL MODES')[0])
    assert len(out.modes) == 9 and all(m.vectors is None for m in out.modes)


def test_repeated_frequency_section_does_not_reuse_old_vectors():
    out = read_output(DEMO + '\nVIBRATIONAL FREQUENCIES\n' + ''.join(f'{i}: 10 cm**-1\n' for i in range(9)))
    assert all(m.vectors is None and m.intensity is None for m in out.modes)


def test_incomplete_geometry_cannot_animate():
    out = read_output(DEMO.replace('H -0.7586 0 0.5043', ''))
    assert out.vibration_geometry is None
    assert all(m.vectors is None for m in out.modes)


def test_duplicate_rows_and_nonfinite_vectors_are_rejected():
    for replacement in ['8 0.600000 0.504300 -0.504300\n8 0.600000 0.504300 -0.504300', '8 1e999 1e999 1e999']:
        out = read_output(DEMO.replace('8 0.600000 0.504300 -0.504300', replacement))
        assert all(m.vectors is None for m in out.modes[6:])


def test_orca6_symmetry_label_row_and_d_exponent():
    text = DEMO.replace('6 7 8\n', '6 7 8\n1-A1 2-A1 1-B2\n').replace('-0.075600', '-7.5600D-02')
    assert read_output(text).modes[6].vectors[0][2] == pytest.approx(-0.0756)


def test_old_ir_t_squared_not_claimed_as_km_per_mol():
    text = DEMO.replace('eps      Int', 'eps      T**2').replace('km/mol', 'a.u.')
    assert all(m.intensity is None for m in read_output(text).modes)


def test_ir_frequency_mismatch_not_associated():
    text = DEMO.replace('6: 1600.00 0.1', '6: 1500.00 0.1')
    assert read_output(text).modes[6].intensity is None


def test_displacement_preserves_ratios_and_base():
    out = read_output(DEMO)
    base = out.vibration_geometry
    v = normalized_vectors(out.modes[7])
    plus = displaced(base, v, 0.25, pi / 2)
    minus = displaced(base, v, 0.25, 3 * pi / 2)
    assert base.atoms[0].z == 0
    assert plus.atoms[1].x - base.atoms[1].x == pytest.approx(-(minus.atoms[1].x - base.atoms[1].x))
    assert max(
        sum((a - b) ** 2 for a, b in zip(x.position, y.position)) ** 0.5 for x, y in zip(plus.atoms, base.atoms)
    ) == pytest.approx(0.25)
    assert v[0][2] / v[1][2] == pytest.approx(-0.06355 / 0.5043)
    assert displaced(base, v, 0.25, 0).atoms == base.atoms


def test_imaginary_mode_kept_signed_and_animatable():
    out = read_output(DEMO.replace('6: 1600.00 cm**-1', '6: -180.00 cm**-1 ***imaginary mode***'))
    assert out.modes[6].frequency == -180 and out.modes[6].animatable


def test_nonfinite_frequency_not_sent_to_animation_or_spectrum():
    out = read_output(DEMO.replace('6: 1600.00 cm**-1', '6: 1e999 cm**-1'))
    assert 6 not in [m.index for m in out.modes]
