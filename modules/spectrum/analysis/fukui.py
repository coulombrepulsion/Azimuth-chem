"""The Fukui functions and the dual descriptor condensed to the atoms, and the global indices of the conceptual DFT
.

§1 PURPOSE The beta of docs/plans/ROADMAP.md, item 8: where a molecule is attacked — by a nucleophile (f⁺: where an
    added electron goes), an electrophile (f⁻: where an electron is taken from), a radical (f⁰) — and the dual
    descriptor Δf = f⁺ − f⁻ (> 0 — an electrophilic site, < 0 — a nucleophilic one); with them the vertical ionization
    potential and electron affinity, the electronegativity, the hardness and the electrophilicity index of the molecule.
§2 ALGORITHM Three single points at one geometry: N electrons (the charge q and the multiplicity m of the molecule), N +
    1 (charge q − 1) and N − 1 (charge q + 1); for N ± 1 the multiplicity m − 1, or 2 for a singlet (the low spin; the
    other one is a choice of the user in the queue). The Hirshfeld charges of each wavefunction (Multiwfn 7 → 1 → 1,
    modules/spectrum/wavefunction/multiwfn_populations.py — the partition recommended for condensed Fukui functions: its
    f are almost never negative, unlike Mulliken's). The population of atom A is p_A = Z_A − q_A, so
        f⁺_A = p_A(N+1) − p_A(N) = q_A(N) − q_A(N+1), f⁻_A = q_A(N−1) − q_A(N), f⁰_A = (f⁺_A + f⁻_A) / 2,
        Δf_A = f⁺_A − f⁻_A; Σ f⁺ = Σ f⁻ = 1, Σ Δf = 0.
    The global indices (finite differences, vertical): IP = E(N−1) − E(N), EA = E(N) − E(N+1), μ = −(IP + EA)/2
    (χ = −μ), η = IP − EA, ω = μ² / (2η) (Parr — Szentpály — Liu 1999), in eV.
    References: Parr, Yang, J. Am. Chem. Soc. 106, 4049 (1984); Yang, Mortier, J. Am. Chem. Soc. 108, 5708 (1986) — the
    condensed form; Morell, Grand, Toro-Labbé, J. Phys. Chem. A 109, 205 (2005) — the dual descriptor.
§4 SPECIFICATION
    HARTREE_EV; STATES = ('n', 'anion', 'cation'); states(charge, multiplicity) -> [(key, charge, multiplicity)];
    condensed(q_n, q_anion, q_cation) -> {'plus', 'minus', 'zero', 'dual'} (tuples by atom);
    global_indices(e_n, e_anion, e_cation) -> {'ip', 'ea', 'mu', 'chi', 'eta', 'omega'} (eV; None without energies);
    table(symbols, charges, values) -> (header, rows); run(program, wavefunctions {key: path}, cores=1, step=None) ->
    ({key: charges}, {key: text}).
§7 TESTS tests/spectrum/test_fukui.py.
"""

from azimuth.i18n import tr

HARTREE_EV = 27.211386245988  # CODATA 2018
STATES = ('n', 'anion', 'cation')
TITLES = {'n': 'N', 'anion': 'N + 1', 'cation': 'N − 1'}


def states(charge, multiplicity):
    """The three calculations: (key, charge, multiplicity) of N, N + 1 and N − 1 electrons."""
    other = multiplicity - 1 if multiplicity > 1 else 2
    return [('n', charge, multiplicity), ('anion', charge - 1, other), ('cation', charge + 1, other)]


def condensed(q_n, q_anion, q_cation):
    if not (len(q_n) == len(q_anion) == len(q_cation)):
        raise ValueError(tr('У трёх расчётов разное число атомов — это не одна молекула.'))
    plus = tuple(a - b for a, b in zip(q_n, q_anion))
    minus = tuple(c - a for a, c in zip(q_n, q_cation))
    zero = tuple((p + m) / 2 for p, m in zip(plus, minus))
    dual = tuple(p - m for p, m in zip(plus, minus))
    return {'plus': plus, 'minus': minus, 'zero': zero, 'dual': dual}


def global_indices(e_n, e_anion, e_cation):
    if None in (e_n, e_anion, e_cation):
        return None
    ip = (e_cation - e_n) * HARTREE_EV
    ea = (e_n - e_anion) * HARTREE_EV
    mu = -(ip + ea) / 2
    eta = ip - ea
    return {'ip': ip, 'ea': ea, 'mu': mu, 'chi': -mu, 'eta': eta, 'omega': mu * mu / (2 * eta) if eta > 0 else None}


def table(symbols, charges, values):
    header = [tr('Атом'), 'q(N)', 'q(N+1)', 'q(N−1)', 'f⁺', 'f⁻', 'f⁰', 'Δf']
    rows = []
    for k, symbol in enumerate(symbols):
        rows.append([f'{symbol}{k + 1}'] + [f'{charges[key][k]:.5f}' for key in STATES]
                    + [f'{values[key][k]:.5f}' for key in ('plus', 'minus', 'zero', 'dual')])
    return header, rows


def run(program, wavefunctions, cores=1, step=None):
    """The Hirshfeld charges of the three wavefunctions ({'n' | 'anion' | 'cation': path}) by Multiwfn."""
    from modules.spectrum.wavefunction import multiwfn_populations

    charges, texts = {}, {}
    for k, key in enumerate(STATES):
        if step is not None and step(k, len(STATES)) is False:
            raise InterruptedError()
        charges[key], texts[key] = multiwfn_populations.run_hirshfeld(program, wavefunctions[key], cores, step)
    return charges, texts
