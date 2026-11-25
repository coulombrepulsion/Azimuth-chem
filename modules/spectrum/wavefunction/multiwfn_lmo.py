"""Multiwfn: the localized molecular orbitals — Pipek–Mezey and Foster–Boys.

§1 PURPOSE The beta of docs/plans/ROADMAP.md, item 5: the bonds and the lone pairs as orbitals — the canonical orbitals
    are spread over the molecule; the localized ones (LMO) are what a chemist draws: the cores, the lone pairs, the
    two-center bonds (and the delocalized π of a ring). In the page «Орбитали» of the drawer of Compass, next to the
    canonical ones.
§2 ALGORITHM Main menu 19 (orbital localization) → −6 (the method: 1 Pipek–Mezey with Mulliken populations, 3 with Becke
    populations — for diffuse basis sets, 10 Foster–Boys) → 1 (the occupied orbitals only; the cores too, the default of
    Multiwfn) → «0», «q». Multiwfn writes the orbitals to new.fch (the virtual ones unchanged; the energies of the
    canonical orbitals are copied there and mean nothing for an LMO) and prints «Major character of occupied LMOs»:
    «Almost single center LMOs» (an atom > 85 %), «Almost two-center LMOs» (the two largest > 80 %), «More delocalized
    LMOs» (the three largest printed) — «N: a(El) p% b(El) q% …». The kinds named here: one center — «остов» for the
    n_core most localized of the atom (the largest share: a core ≈ 99.8 %, a lone pair ≈ 94 %; by number would be wrong
    — Boys put the O 1s of water fifth), «НП» (a lone pair) for the rest; two centers — «связь»; more — «делок.».
    n_core: the closed shells below the valence shell (1 for Li–Ne, 5 for Na–Ar, 9 for K–Kr, 18 for Rb–Xe, 27 for Cs–Rn)
    less those replaced by an ECP ((Z − Z_eff) / 2). Recorded on Multiwfn 2026.7.15 (tests/data/multiwfn/lmo_*.txt,
    tools/record_multiwfn_lmo.py): water of Gaussian 16, benzaldehyde of ORCA (Molden), Pipek–Mezey, its Becke variant
    and Boys. The cation of divinylbenzene (an open shell, Molden) made Multiwfn fall (SIGSEGV) after the α orbitals
    with the composition by Hirshfeld; with −9 → 1 (Mulliken for the occupied LMOs) it localized α and β — the summary
    in two blocks, the β numbered from 1 again.
§4 SPECIFICATION
    METHODS = {'pm': '1', 'pm-becke': '3', 'boys': '10'}; NAMES; answers(method, open_shell=False) -> tuple;
    parse_summary(text) -> {(spin, number):
    (kind, [(atom 1-based, symbol, percent)])} with kind 'one' | 'two' | 'more'; core_count(z, z_eff) -> int;
    kinds(summary, orbital_set) -> {(spin, number): 'остов' | 'НП' | 'связь' | 'делок.'};
    describe(atoms) -> str («O1 99.7 %», «O1–H2 63/34 %»…); run_lmo(program, path, method, cores=1, step=None,
    timeout=1800, open_shell=False) -> (text of new.fch, summary, output).
§7 TESTS tests/spectrum/test_multiwfn_lmo.py.
"""

import re

from azimuth.i18n import tr
from modules.spectrum.wavefunction import multiwfn

# the items of −6 as Multiwfn 2026.7.15 lists them; its hint: 1 and 2 are fast but may fail with diffuse functions, 3 and
# 10 are slower and fully compatible with them (only 10 does not separate σ and π)
METHODS = {'pm': '1', 'pm-becke': '3', 'boys': '10'}
NAMES = {'pm': 'Пипек — Меззи', 'pm-becke': 'Пипек — Меззи (Беке)', 'boys': 'Бойс'}
_HEADS = (('Almost single center LMOs', 'one'), ('Almost two-center LMOs', 'two'), ('More delocalized LMOs', 'more'))
_ENTRY = re.compile(r'(\d+):\s+((?:\s*\d+\(\s*[A-Za-z]{1,3}\s*\)\s*-?\d+\.\d+%)+)')
_SHARE = re.compile(r'(\d+)\(\s*([A-Za-z]{1,3})\s*\)\s*(-?\d+\.\d+)%')
CORE_SHELLS = ((2, 0), (10, 1), (18, 5), (36, 9), (54, 18), (86, 27), (118, 43))  # (last Z of the row, core orbitals)


def answers(method='pm', open_shell=False):
    """An open shell — the composition of the LMOs by Mulliken (−9 → 1): with Hirshfeld (the default) Multiwfn
    2026.7.15 fell (SIGSEGV) after the α orbitals of the recorded cation; with Mulliken it localized α and β."""
    head = ('19', '-9', '1') if open_shell else ('19',)
    return head + ('-6', METHODS[method], '1', '0', 'q')


def parse_summary(text):
    """The kinds and the atoms of the LMOs: {(spin, number): (kind, shares)} from «Major character of occupied LMOs»
    (spin 'alpha') or, for an open shell, «… of alpha occupied LMOs» and «… of beta occupied LMOs» (the β orbitals are
    numbered from 1 again, as in the file)."""
    lines = text.replace('\r', '').split('\n')
    found = {}
    for k, line in enumerate(lines):
        block = re.search(r'Major character of (alpha |beta )?occupied LMOs', line)
        if not block:
            continue
        spin = 'beta' if (block.group(1) or '').strip() == 'beta' else 'alpha'
        kind = None
        for row in lines[k + 1:]:
            head = next((name for marker, name in _HEADS if marker in row), None)
            if head is not None:
                kind = head
                continue
            if not row.strip():
                if kind == 'more':
                    break
                continue
            if kind is None or 'Exporting' in row or 'Major character' in row or 'Calculating' in row:
                break
            for match in _ENTRY.finditer(row):
                shares = [(int(a), s, float(p)) for a, s, p in _SHARE.findall(match.group(2))]
                found[(spin, int(match.group(1)))] = (kind, shares)
    return found


def core_count(z, z_eff=None):
    """The core orbitals of an atom (closed shells below the valence shell), less those taken by an ECP."""
    core = next(n for last, n in CORE_SHELLS if z <= last)
    if z_eff is not None and z_eff < z:
        core -= int(round((z - z_eff) / 2))
    return max(0, core)


def kinds(summary, orbital_set):
    from azimuth.core import Z

    symbols = [a.symbol for a in orbital_set.molecule.atoms]
    effective = list(getattr(orbital_set, 'charges', ()) or ())
    left = {}
    for k, s in enumerate(symbols):
        z = Z.get(s, 0)
        left[k + 1] = core_count(z, effective[k] if k < len(effective) else None)
    named = {}
    # the cores of an atom: its most localized one-center LMOs (≈ 99.8 % against ≈ 94 % of a lone pair) — not the
    # first by number: Boys put the O 1s of water fifth (recorded)
    single = {}
    for key, (kind, shares) in summary.items():
        if kind == 'one':
            single.setdefault((key[0], shares[0][0]), []).append((-shares[0][2], key[1], key))
    for (spin, atom), found in single.items():
        found.sort()
        for rank, (_, _, key) in enumerate(found):
            named[key] = 'остов' if rank < left.get(atom, 0) else 'НП'
    for key, (kind, _) in summary.items():
        if kind != 'one':
            named[key] = 'связь' if kind == 'two' else 'делок.'
    return named


def describe(shares):
    if len(shares) == 1:
        a, s, p = shares[0]
        return f'{s}{a} {p:.0f} %'
    atoms = '–'.join(f'{s}{a}' for a, s, _ in shares)
    return f'{atoms} {"/".join(f"{p:.0f}" for _, _, p in shares)} %'


def run_lmo(program, path, method='pm', cores=1, step=None, timeout=1800, open_shell=False):
    """The LMOs of the file of orbitals path: (the text of new.fch, the summary, the output of Multiwfn)."""
    text, kept = multiwfn._run(program, path, answers(method, open_shell), cores, step, timeout, keep=('new.fch',))
    fch = kept.get('new.fch')
    if not fch:
        raise ValueError(tr('Multiwfn не записал локализованные орбитали. Конец его вывода:') + '\n' + multiwfn._tail(text))
    return fch, parse_summary(text), text
