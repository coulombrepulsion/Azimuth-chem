"""Independent contract tests for educational vibration normalization.

Expected values follow the public normalization specification, without relying
on implementation details.  Tolerance allows a small fixed number of rounded
floating-point operations.
"""

import math
import sys

import pytest

from modules.spectrum.readers.vibration_data import Vibration, normalized_vectors


TOL = 32 * sys.float_info.epsilon


def assert_vectors_close(actual, expected):
    assert isinstance(actual, tuple)
    assert len(actual) == len(expected)
    for actual_vector, expected_vector in zip(actual, expected):
        assert isinstance(actual_vector, tuple)
        assert len(actual_vector) == 3
        for actual_component, expected_component in zip(actual_vector, expected_vector):
            assert math.isfinite(actual_component)
            assert actual_component == pytest.approx(expected_component, rel=TOL, abs=TOL)


@pytest.mark.parametrize("frequency", [123.0, -123.0])
def test_normalizes_by_largest_atom_norm_preserving_relative_displacements(frequency):
    vectors = ((3.0, 4.0, 0.0), (0.0, -2.0, 0.0), (0.0, 0.0, 0.0))
    mode = Vibration(index=7, frequency=frequency, vectors=vectors, intensity=0.5)
    actual = normalized_vectors(mode)
    assert_vectors_close(actual, ((0.6, 0.8, 0.0), (0.0, -0.4, 0.0), (0.0, 0.0, 0.0)))
    assert max(math.hypot(*vector) for vector in actual) == pytest.approx(1.0, rel=TOL)
    assert mode.index == 7
    assert mode.frequency == frequency
    assert mode.intensity == 0.5
    assert mode.vectors == vectors
    assert normalized_vectors(mode) == actual


def test_handles_norm_larger_than_largest_representable_float():
    mode = Vibration(index=1, frequency=10.0, vectors=((1.7e308, 1.7e308, 1.7e308), (-1.7e308, 0.0, 0.0)))
    component = 1.0 / math.sqrt(3.0)
    assert_vectors_close(normalized_vectors(mode), ((component, component, component), (-component, 0.0, 0.0)))


def test_subnormal_components_keep_ratios_without_norm_rounding_loss():
    scale = 1e-320
    mode = Vibration(index=1, frequency=10.0, vectors=((3 * scale, 4 * scale, 0.0), (-scale, 0.0, 0.0)))
    assert_vectors_close(normalized_vectors(mode), ((0.6, 0.8, 0.0), (-0.2, 0.0, 0.0)))


@pytest.mark.parametrize("magnitude", [1e308, 1e-320, math.ulp(0.0)])
def test_single_nonzero_component_of_extreme_magnitude(magnitude):
    mode = Vibration(index=1, frequency=-1.0, vectors=((0.0, -magnitude, 0.0),))
    assert normalized_vectors(mode) == ((0.0, -1.0, 0.0),)


@pytest.mark.parametrize("vectors", [None, (), ((0.0, 0.0, 0.0),), ((0.0, -0.0, 0.0), (0.0, 0.0, 0.0))])
def test_absent_or_zero_displacements_return_empty_tuple(vectors):
    assert normalized_vectors(Vibration(index=1, frequency=10.0, vectors=vectors)) == ()


@pytest.mark.parametrize("frequency", [0.0, -0.0])
def test_zero_frequency_returns_empty_tuple(frequency):
    assert normalized_vectors(Vibration(index=1, frequency=frequency, vectors=((1.0, 2.0, 3.0),))) == ()


def test_default_optional_fields_and_empty_result():
    mode = Vibration(index=1, frequency=10.0)
    assert mode.vectors is None
    assert mode.intensity is None
    assert normalized_vectors(mode) == ()


@pytest.mark.parametrize("frequency", [float("nan"), float("inf"), float("-inf")])
def test_rejects_nonfinite_frequency(frequency):
    with pytest.raises(ValueError):
        normalized_vectors(Vibration(index=1, frequency=frequency, vectors=((1.0, 0.0, 0.0),)))


@pytest.mark.parametrize("component", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("axis", [0, 1, 2])
def test_rejects_nonfinite_component_in_every_axis(component, axis):
    vector = [0.0, 0.0, 0.0]
    vector[axis] = component
    with pytest.raises(ValueError):
        normalized_vectors(Vibration(index=1, frequency=-1.0, vectors=((1.0, 0.0, 0.0), tuple(vector))))


@pytest.mark.parametrize("vector", [(), (1.0,), (1.0, 2.0), (1.0, 2.0, 3.0, 4.0)])
def test_rejects_malformed_vector_dimensions(vector):
    with pytest.raises(ValueError):
        normalized_vectors(Vibration(index=1, frequency=10.0, vectors=((1.0, 0.0, 0.0), vector)))
