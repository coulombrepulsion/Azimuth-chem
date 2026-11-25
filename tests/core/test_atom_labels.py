"""Atoms typed and shown with their element (azimuth/atom_labels.py)."""

import pytest

from azimuth import atom_labels as al

SYMBOLS = ['N', 'H', 'H', 'H', 'B', 'H', 'H', 'H']


def test_both_forms_are_taken():
    assert al.parse('1-4', 8) == [1, 2, 3, 4]
    assert al.parse('N1, H2-H4', 8, SYMBOLS) == [1, 2, 3, 4]
    assert al.parse('N1 H2 – H4; 7', 8, SYMBOLS) == [1, 2, 3, 4, 7]
    assert al.parse('B5–H8', 8, SYMBOLS) == [5, 6, 7, 8] and al.parse('1 - 4, H7', 8, SYMBOLS) == [1, 2, 3, 4, 7]
    assert al.parse('B', 8, SYMBOLS) == [5] and al.parse('H', 8, SYMBOLS) == [2, 3, 4, 6, 7, 8]
    assert al.parse('8-5', 8) == [5, 6, 7, 8] and al.parse('', 8) == []
    assert al.parse('N1', 8) == [1]  # without the symbols of the molecule the symbol is not checked


def test_a_wrong_element_or_number_is_refused():
    with pytest.raises(ValueError, match='Атом 5 — B, а не H'):
        al.parse('H5', 8, SYMBOLS)
    for wrong in ('9', 'C', '1-x', 'N1-', '0'):
        with pytest.raises(ValueError):
            al.parse(wrong, 8, SYMBOLS)


def test_shown_with_their_elements():
    assert al.text([1, 2, 3, 4], SYMBOLS) == 'N1–H4' and al.text([2, 3, 4, 7], SYMBOLS) == 'H2–H4, H7'
    assert al.text([1, 2, 5]) == '1, 2, 5' and al.text([5, 6, 7, 8]) == '5–8'
    assert al.parse(al.text([2, 3, 4, 7], SYMBOLS), 8, SYMBOLS) == [2, 3, 4, 7]  # what is shown is taken back
    assert al.label(SYMBOLS, 4) == 'B5' and al.label(None, 4) == '5'
