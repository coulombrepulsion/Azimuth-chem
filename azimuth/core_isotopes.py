"""Isotopes of the atoms of a calculation: the table of the isotopes, their abundance, names, masses and the text of
them in an input.

Split off azimuth/core.py (0.222.30); azimuth.core still names them.
"""



# the isotopes offered by «Изотоп» of an atom (Compass) — symbol: [(name, mass in u)]: every stable one of
# azimuth/isotope_table.py, the radioactive T and ¹⁴C too, lightest first
def _isotopes():
    from azimuth.isotope_table import RADIOACTIVE, STABLE, name

    table = {}
    for symbol in set(STABLE) | set(RADIOACTIVE):
        found = [(number, mass) for number, mass, _ in STABLE.get(symbol, ())] + list(RADIOACTIVE.get(symbol, ()))
        table[symbol] = [(name(symbol, number), mass) for number, mass in sorted(found)]
    return table


ISOTOPES = _isotopes()


def isotope_abundance(symbol, mass):
    """The natural abundance (0…1) of the isotope of this mass, or None (radioactive, or a mass of the user's own)."""
    from azimuth.isotope_table import STABLE

    return next((x for _, m, x in STABLE.get(symbol, ()) if abs(m - mass) < 1e-4), None)


def isotope_name(symbol, mass):
    """The short name of an isotope on the model: «D», «T», «¹³C» … (the nearest of ISOTOPES), else the mass number
    of the mass with the symbol."""
    choices = ISOTOPES.get(symbol, [])
    if choices:
        name, value = min(choices, key=lambda item: abs(item[1] - mass))
        if abs(value - mass) < 0.5:
            return name
    from azimuth.isotope_table import SUPERSCRIPT  # a mass of the user's own: its mass number

    return str(round(mass)).translate(SUPERSCRIPT) + symbol


def isotope_masses(text, molecule=None):
    """{0-based index: mass} of Calculation.isotopes («3 H 2.014102; 7 C 13.003355»); an entry whose atom is gone or
    is now another element (the structure was edited) is left out."""
    found = {}
    for part in (text or '').replace(',', ';').split(';'):
        fields = part.split()
        if len(fields) != 3:
            continue
        try:
            index, symbol, mass = int(fields[0]) - 1, fields[1], float(fields[2])
        except ValueError:
            continue
        if index < 0 or mass <= 0:
            continue
        if molecule is not None and (index >= len(molecule.atoms) or molecule.atoms[index].symbol != symbol):
            continue
        found[index] = mass
    return found


def isotope_text(masses, molecule):
    """Calculation.isotopes of {0-based index: mass}."""
    return '; '.join(f'{k + 1} {molecule.atoms[k].symbol} {m:.6f}' for k, m in sorted(masses.items())
                     if 0 <= k < len(molecule.atoms))
