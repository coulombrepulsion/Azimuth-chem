"""MOPAC 23.2.5 results — the output and its .aux (modules/spectrum/readers/mopac.py).

Oracles, independent of the reader:
  * numbers copied by hand from the user's outputs (tests/data/mopac, MOPAC 23.2.5, conda-forge, macOS arm64);
  * the Cartesian displacements printed in the output («NORMAL COORDINATE ANALYSIS (Total motion = 1 Angstrom)»),
    read here with a regex of the test: the modes of the .aux divided by sqrt(mass) must be proportional to them;
  * physics: the charges add up to the charge of the molecule; a polar molecule in COSMO water is more polarized
    (larger charges and dipole) and lower in ΔHf; 3N−6 vibrations, the degenerate pairs of benzene (D6h);
  * experiment: PM7 is fitted to heats of formation — water ΔfH°(gas) = −241.826 kJ/mol = −57.798 kcal/mol (NIST
    Chemistry WebBook / CODATA key values).
"""

from pathlib import Path
import re

import numpy as np
import pytest

from modules.spectrum.readers.mopac import FORCE_GRADIENT, is_mopac, read_aux, read_mopac
from modules.spectrum.readers.outputs import program, read_any

DATA = Path(__file__).parents[1] / 'data' / 'mopac'


def result(name):
    path = DATA / f'{name}.out'
    return read_any(path.read_text(encoding='utf-8'), str(path))


def test_water_optimization_as_printed():
    out = result('h2o_pm7_opt')
    assert program((DATA / 'h2o_pm7_opt.out').read_text(encoding='utf-8')) == 'MOPAC'
    assert out.program == 'MOPAC 23.2.5 PM7' and out.normal_exit and out.optimization_converged
    assert out.energies == () and out.final_energy is None  # not a total energy: no reaction diagram, no thermo
    assert out.heat_of_formation == -57.7999  # .aux «-0.577999D+02»; the output prints -57.79986
    assert [a.symbol for a in out.geometry.atoms] == ['O', 'H', 'H']
    assert out.geometry.atoms[1].position == pytest.approx((0.0, 0.759811803, -0.463714605))
    assert len(out.steps) == 4 and all(s.energy is None and s.geometry is not None for s in out.steps)
    assert out.properties.charges['mopac'] == (-0.64936, 0.32468, 0.32468)
    assert out.properties.dipole_debye == pytest.approx(2.12927)
    assert 'не полная энергия' in out.assessment


def test_heat_of_formation_of_water_against_experiment():
    assert result('h2o_pm7_opt').heat_of_formation == pytest.approx(-241.826 / 4.184, abs=0.5)


def test_charges_add_up_to_the_charge_of_the_molecule():
    for name, charge in (('h2o_pm7_opt', 0), ('ch2o_pm7_opt', 0), ('c6h6_pm7_opt', 0), ('nh4_pm7_cation_opt', 1),
                         ('ch3_pm7_uhf_doublet_opt', 0), ('h2o_pm6_1scf', 0), ('ch2o_am1_1scf', 0)):
        assert sum(result(name).properties.charges['mopac']) == pytest.approx(charge, abs=2e-4), name
    assert result('nh4_pm7_cation_opt').heat_of_formation == 154.806


def test_cosmo_water_is_more_polarized_and_lower():
    gas, water = result('h2o_pm7_opt'), result('h2o_pm7_cosmo_opt')
    assert water.heat_of_formation == pytest.approx(-65.2246) and water.heat_of_formation < gas.heat_of_formation
    assert abs(water.properties.charges['mopac'][0]) > abs(gas.properties.charges['mopac'][0])
    assert water.properties.dipole_debye > gas.properties.dipole_debye


def test_methods_and_single_points():
    assert result('h2o_pm6_1scf').program == 'MOPAC 23.2.5 PM6' and result('h2o_pm6_1scf').heat_of_formation == -54.2172
    am1 = result('ch2o_am1_1scf')
    assert am1.program == 'MOPAC 23.2.5 AM1' and am1.heat_of_formation == -30.8326 and not am1.optimization_converged
    assert result('ch3_pm7_uhf_doublet_opt').heat_of_formation == 27.9697


def printed_cartesian_modes(text):
    """The columns of «NORMAL COORDINATE ANALYSIS (Total motion = 1 Angstrom)», read by the test itself."""
    block = text.split('NORMAL COORDINATE ANALYSIS', 1)[1].split('MASS-WEIGHTED', 1)[0]
    columns = {}
    for line in block.splitlines():
        fields = line.split()
        if fields and fields[0].isdigit() and all(re.fullmatch(r'-?\d+\.\d+', f) for f in fields[1:]) and len(fields) > 1:
            columns.setdefault(int(fields[0]), []).extend(float(f) for f in fields[1:])
    rows = [columns[k] for k in sorted(columns)]
    return np.array(rows).T  # mode x coordinate


def test_water_frequencies_and_the_printed_displacements():
    out = result('h2o_pm7_force_thermo')
    assert [f for _, f in out.frequencies] == [1394.92, 2809.65, 2856.03]  # 3N−6; the trivial modes are left out
    assert all(m.intensity is None for m in out.modes)  # MOPAC gives no IR intensity in km/mol
    assert not [n for n in out.notes if 'стационарной' in n]
    printed = printed_cartesian_modes((DATA / 'h2o_pm7_force_thermo.out').read_text(encoding='utf-8'))
    assert printed.shape == (3, 9)
    for mode, row in zip(out.modes, printed):
        ours = np.array(mode.vectors).ravel()
        scale = np.dot(ours, row) / np.dot(row, row)
        assert np.max(np.abs(ours - scale * row)) < 2e-3 * np.max(np.abs(ours))  # proportional to 4-digit rounding


def test_counts_of_vibrations():
    assert len(result('c2h4_pm7_force').frequencies) == 12
    assert len(result('ch2o_pm7_force').frequencies) == 6
    assert len(result('ch3_pm7_uhf_doublet_force').frequencies) == 6
    benzene = [f for _, f in result('c6h6_pm7_force_thermo').frequencies]
    assert len(benzene) == 30
    pairs = sum(1 for a, b in zip(benzene, benzene[1:]) if abs(a - b) < 0.5)
    assert pairs == 10  # D6h: 10 doubly degenerate vibrations (E1g, E2g, E1u, E2u) and 10 single ones


def test_frequencies_away_from_a_stationary_point_are_flagged():
    out = result('h2o_pm7_force_unoptimized')
    items = read_aux((DATA / 'h2o_pm7_force_unoptimized.aux').read_text(encoding='utf-8'))
    gnorm = float(items['GRADIENT_NORM'][-1][1][0].replace('D', 'E'))
    assert gnorm == pytest.approx(1.83981) and gnorm > FORCE_GRADIENT
    assert any('не в стационарной точке' in n for n in out.notes) and 'не в стационарной точке' in out.assessment
    trivial = [float(v) for v in items['VIB._FREQ'][-1][1][3:]]
    assert max(abs(v) for v in trivial) > 100  # the «zero» modes are far from zero here


def test_without_the_aux_file_the_output_alone_is_read():
    text = (DATA / 'h2o_pm7_opt.out').read_text(encoding='utf-8')
    out = read_mopac(text)
    assert out.heat_of_formation == -57.79986 and len(out.geometry.atoms) == 3 and out.frequencies == ()
    assert out.properties is None and out.normal_exit


def test_recognition():
    assert is_mopac((DATA / 'h2o_pm7_opt.out').read_text(encoding='utf-8'))
    orca = Path(__file__).parents[1] / 'data' / 'orca601' / 'h2o_opt.out'
    assert not is_mopac(orca.read_text(encoding='utf-8')) and program(orca.read_text(encoding='utf-8')) == 'ORCA'
    with pytest.raises(ValueError):
        read_mopac('not an output')


def test_an_overflow_in_the_aux_leaves_out_its_key_only(tmp_path):
    # MOPAC writes asterisks (an overflow, glued to the number before it) into a key of a single atom; the result opens,
    # only that key is left out
    from pathlib import Path

    from modules.spectrum.readers.mopac import read_mopac

    data = Path(__file__).parents[1] / 'data' / 'mopac'
    out = tmp_path / 'c2h4_pm7_opt.out'
    out.write_text((data / 'c2h4_pm7_opt.out').read_text(encoding='utf-8', errors='replace'), encoding='utf-8')
    aux = (data / 'c2h4_pm7_opt.aux').read_text(encoding='utf-8', errors='replace')
    aux = aux.replace(' DIP_VEC:DEBYE[3]= +0.36230D-09 +0.33381D-09 +0.55709D-09',
                      ' DIP_VEC:DEBYE[3]= 0.0000********* +0.33381D-09')
    out.with_suffix('.aux').write_text(aux, encoding='utf-8')
    output = read_mopac(out.read_text(encoding='utf-8'), out)
    assert output.geometry is not None and len(output.geometry.atoms) == 6


def test_a_geometry_mopac_refused_is_not_a_normal_end():
    # «GEOMETRY IN ERROR» of MOPAC 23.2.5 (two atoms 0.15 Å apart): no heat of formation, and the «JOB ENDED NORMALLY»
    # at the end of such a file is not a normal end of a calculation
    out = read_mopac((DATA / 'h2o_atoms_too_close.out').read_text(encoding='utf-8'))
    assert not out.normal_exit and out.heat_of_formation is None
    assert read_mopac((DATA / 'c2h4_pm7_force.out').read_text(encoding='utf-8')).normal_exit
    # FORCE refused far from a stationary point (MOPAC 23.2.5, the gradient 16 over its limit 10): no normal end
    refused = read_mopac((DATA / 'h2o_force_gradient_too_large.out').read_text(encoding='utf-8'))
    assert not refused.normal_exit and not refused.frequencies
