"""The examples folder (examples/README.md): every file opens and shows what the README promises.

Oracles: the README table itself (each file named there exists, each example file is named there) and the
promised content, checked with the program's own readers — properties, optimization steps, scan points,
frequencies, UV-Vis and NMR, orbitals, final correlated energies, the overlay, the crystals, the fragments.
"""

from pathlib import Path
import re

import pytest

from modules.compass.chemistry import crystal as cr
from modules.compass.chemistry import overlay, user_fragments
from modules.spectrum.readers.orbital_files import read_orbitals
from modules.spectrum.readers.outputs import read_any
from azimuth.core import read_xyz

EXAMPLES = Path(__file__).resolve().parents[2] / 'examples'


def read(rel):
    path = EXAMPLES / rel
    return read_any(path.read_text(encoding='utf-8', errors='replace'), path)


def test_readme_names_every_file_and_every_file_exists():
    text = (EXAMPLES / 'README.md').read_text(encoding='utf-8')
    rows = [line for line in text.splitlines() if line.startswith('| `') and '-' in line.split('|')[1]]
    named = set()
    for row in rows:
        folder = re.match(r'\| `([^`]+)`', row).group(1)
        cell = row.split('|')[2]
        pattern = r'папка `([^`]+)` \(открывать `([^`]+)`\)|папка `([^`]+)` \(`([^`]+)`\)'
        for name in re.findall(r'`([^`/]+\.(?:out|log|fchk|molden|xyz|cif|json))`', re.sub(pattern, '', cell)):
            named.add(f'{folder}/{name}')
        for sub in re.findall(pattern, row):
            d, f = (sub[0], sub[1]) if sub[0] else (sub[2], sub[3])
            named.add(f'{folder}/{d}/{f}')
    for rel in named:
        assert (EXAMPLES / rel).is_file(), rel
    present = {
        p.relative_to(EXAMPLES).as_posix()  # «/» on Windows too
        for p in EXAMPLES.glob('[0-9]*/**/*')
        if p.is_file() and p.suffix in ('.out', '.log', '.fchk', '.molden', '.xyz', '.cif', '.json')
        and not p.name.startswith(('g98', 'xtbopt', 'dvb_ir.xyz', 'dvb_opt.xyz', 'dvb_sp.xyz'))
    }
    assert present <= named, sorted(present - named)
    assert (EXAMPLES / 'LICENSE-cclib.txt').read_text(encoding='utf-8').startswith('BSD 3-Clause License')


def test_properties_steps_scans():
    for rel in ('1-properties/water_mp2_orca5.out', '1-properties/divinylbenzene_cation_orca6.out', '1-properties/divinylbenzene_cation_gaussian16.log'):
        assert read(rel).properties is not None, rel
    assert read('1-properties/divinylbenzene_cation_orca6.out').properties.spins
    for rel in ('2-optimization/divinylbenzene_opt_gaussian16.log', '2-optimization/divinylbenzene_opt_psi4.out', '2-optimization/xtb_divinylbenzene_opt/dvb_opt.out'):
        assert len(read(rel).steps) > 1, rel
    for rel in ('3-scans/dihedral_scan_relaxed_orca6.out', '3-scans/dihedral_scan_relaxed_gaussian16.log', '3-scans/zmatrix_scan_rigid_orca5.out'):
        assert read(rel).scan is not None and len(read(rel).scan.points) > 2, rel


def test_vibrations_spectra_orbitals_programs():
    for rel in ('4-vibrations/divinylbenzene_freq_gaussian16.log', '4-vibrations/divinylbenzene_freq_psi4.out', '4-vibrations/xtb_divinylbenzene_freq/dvb_ir.out'):
        out = read(rel)
        assert len(out.frequencies) == 54 and out.modes and all(m.vectors for m in out.modes), rel
    for rel in ('5-uv-vis-nmr/divinylbenzene_tddft_orca6.out', '5-uv-vis-nmr/divinylbenzene_tddft_gaussian16.log'):
        assert read(rel).absorption, rel
    for rel in ('5-uv-vis-nmr/divinylbenzene_nmr_orca6.out', '5-uv-vis-nmr/divinylbenzene_nmr_gaussian16.log'):
        assert read(rel).shieldings, rel
    for rel in ('6-orbitals/water_mp2_gaussian16.fchk', '6-orbitals/water_gamess.molden', '6-orbitals/divinylbenzene_orbitals_orca6.out', '6-orbitals/MoOCl4_ecp_gaussian16.fchk'):
        orbitals = read_orbitals((EXAMPLES / rel).read_text(encoding='utf-8', errors='replace'))
        assert orbitals.molecule.atoms, rel
    g = read('7-programs/water_ccsdt_gaussian16.log').final_energy
    p = read('7-programs/water_ccsdt_psi4.out').final_energy
    assert g[0] == p[0] == 'CCSD(T)'
    xtb = read('7-programs/xtb_divinylbenzene_sp/dvb_sp.out')
    assert xtb.properties.bond_kind == 'Wiberg' and xtb.properties.charges['xtb']


def test_compare_torsion_crystals_fragments():
    a = read_xyz((EXAMPLES / '8-compare/ethanol.xyz').read_text(encoding='utf-8'))
    b = read_xyz((EXAMPLES / '8-compare/ethanol_other_order.xyz').read_text(encoding='utf-8'))
    r = overlay.superimpose(a, b)
    assert r.rmsd < 1e-5 and not r.same_order  # the coordinates are rounded to 1e-6 A
    anti = read_xyz((EXAMPLES / '8-compare/butane_anti.xyz').read_text(encoding='utf-8'))
    gauche = read_xyz((EXAMPLES / '8-compare/butane_gauche.xyz').read_text(encoding='utf-8'))
    assert overlay.superimpose(anti, gauche).rmsd > 0.3
    for name in ('butane.xyz', 'ethanol.xyz'):
        assert read_xyz((EXAMPLES / '9-torsion' / name).read_text(encoding='utf-8')).atoms
    nacl = cr.parse_cif((EXAMPLES / '10-crystals/NaCl_rock_salt.cif').read_text(encoding='utf-8'))
    m = cr.build(nacl, (1, 1, 1), True)
    assert sum(x.symbol == 'Na' for x in m.atoms) == 14 and sum(x.symbol == 'Cl' for x in m.atoms) == 13
    cscl = cr.parse_cif((EXAMPLES / '10-crystals/CsCl.cif').read_text(encoding='utf-8'))
    assert sorted(s for s, *_ in cr.unit_cell(cscl)) == ['Cl', 'Cs']
    graphite = cr.parse_cif((EXAMPLES / '10-crystals/graphite_P1.cif').read_text(encoding='utf-8'))
    assert len(cr.unit_cell(graphite)) == 4 and graphite.notes
    fragments = user_fragments.parse((EXAMPLES / '11-fragments/example_fragments.json').read_text(encoding='utf-8'))
    assert len(fragments) == 3 and all(atoms[0][0] == 'C' for atoms, _ in fragments.values())


@pytest.mark.parametrize('name', ['teaching-demo.out', 'optimization-demo.out', 'vibrations-demo.out'])
def test_teaching_files_stay(name):
    assert (EXAMPLES / name).is_file()


def test_the_simple_molecules_and_their_point_groups():
    # the point groups the README promises,
    # by the analysis of the point group button; the bond lengths of the README read back from the files
    from math import dist

    from modules.compass.chemistry import symmetry

    for name, group, bond in (('water', 'C2v', 0.9572), ('methane', 'Td', 1.087), ('ammonia', 'C3v', 1.012),
                              ('benzene', 'D6h', 1.397)):
        molecule = read_xyz((EXAMPLES / '0-molecules' / f'{name}.xyz').read_text(encoding='utf-8'))
        assert symmetry.analyze(molecule)['name'] == group, name
        assert abs(dist(molecule.atoms[0].position, molecule.atoms[1].position) - bond) < 1e-5, name
