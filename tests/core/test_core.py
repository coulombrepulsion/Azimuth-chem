from dataclasses import replace
from pathlib import Path
import pytest
from azimuth.core import *
from modules.spectrum.readers.orca import read_output

WATER = next(iter(EXAMPLES.values()))


@pytest.mark.parametrize('text', list(EXAMPLES.values()))
def test_xyz_roundtrip(text):
    molecule = read_xyz(text)
    assert read_xyz(molecule.xyz()) == molecule


@pytest.mark.parametrize(
    'text',
    [
        '',
        '1\nH 0 0 0',
        '2\ntitle\nH 0 0 0',
        '0\nempty\n',
        '1\nunknown\nXx 0 0 0',
        '1\nnan\nH nan 0 0',
        '1\ninf\nH 0 inf 0',
        '1\nextra\nH 0 0 0\nH 1 0 0',
        '2\nclash\nH 0 0 0\nH 0 0 0',
        '1\nbad\nH a 0 0',
        42,
    ],
)
def test_bad_xyz(text):
    with pytest.raises(ValueError):
        read_xyz(text)


def test_empty_comment():
    assert read_xyz('1\n\nHe 0 0 0').atoms[0].symbol == 'He'


@pytest.mark.parametrize('charge,spin', [(0, 2), (1, 1), (-1, 1), (20, 1), (0, 0)])
def test_bad_spin(charge, spin):
    with pytest.raises(ValueError):
        read_xyz(WATER).validate_state(charge, spin)


def test_doublet_ion():
    read_xyz(WATER).validate_state(1, 2)


def test_orca_golden():
    text = orca_input(read_xyz('1\nHelium\nHe 0 0 0'), Calculation(method='HF', task='Энергия', cores=1))
    assert (
        text
        == '# He_HF_def2-SVP\n! HF def2-SVP TightSCF\n%pal nprocs 1 end\n%maxcore 1000\n\n* xyz 0 1\nHe  0.00000000  0.00000000  0.00000000\n*\n'
    )


@pytest.mark.parametrize(
    'changes',
    [{'method': 'fake'}, {'basis': 'fake'}, {'cores': 0}, {'memory_mb': -1}, {'charge': True}, {'task': 'fake'}],
)
def test_invalid_calculation(changes):
    with pytest.raises(ValueError):
        orca_input(read_xyz(WATER), replace(Calculation(), **changes))


def test_project_roundtrip():
    molecule = read_xyz(WATER)
    calc = Calculation(cores=4, charge=1, multiplicity=2)
    assert read_project(project_text(molecule, calc)) == (molecule, calc)


def test_a_project_with_a_delocalized_bond_opens():
    # «Связи по порядкам Майера» put an order 1.5 into the structure and it was saved so; it opens, the bond single
    import json

    molecule = read_xyz(WATER)
    data = json.loads(project_text(molecule, Calculation()))
    data['bonds'] = [[0, 1, 1.5], [0, 2, 1.0]]
    read, _ = read_project(json.dumps(data))
    assert read.bonds == ((0, 1, 1), (0, 2, 1))
    data['bonds'] = [[0, 1, 1.3]]
    with pytest.raises(ValueError):
        read_project(json.dumps(data))


@pytest.mark.parametrize(
    'text', ['{}', '[]', 'null', 'invalid', '{"format":"qcc-studio","version":1,"xyz":42,"calculation":{}}']
)
def test_bad_project(text):
    with pytest.raises(ValueError):
        read_project(text)


def test_output_demo():
    output = read_output((Path(__file__).parents[2] / 'examples' / 'teaching-demo.out').read_text())
    assert output.demo and output.normal_exit and output.optimization_converged
    assert len(output.geometry.atoms) == 3 and len(output.frequencies) == 9
    assert output.energies[-1] == -75.95
    assert not output.imaginary


def test_truncated_job_not_success():
    output = read_output('ORCA\nFINAL SINGLE POINT ENERGY -7.5000D+01\nSCF NOT CONVERGED')
    assert not output.normal_exit and output.scf_failed
    assert output.energies == (-75.0,)
    assert 'неполным' in output.assessment


def test_last_frequency_block_only():
    output = read_output(
        'ORCA\nVIBRATIONAL FREQUENCIES\n0: 100.0 cm**-1\nNORMAL MODES\nVIBRATIONAL FREQUENCIES\n0: -23.0 cm**-1 ***imaginary mode***\nIR SPECTRUM\n0: 42.0 cm**-1'
    )
    assert output.frequencies == ((0, -23.0),)
    assert len(output.imaginary) == 1


def test_last_geometry_and_d_exponents():
    text = 'ORCA\nCARTESIAN COORDINATES (ANGSTROEM)\n-----\nH 0 0 0\nH 0 0 0.7\n\nCARTESIAN COORDINATES (ANGSTROEM)\n-----\nH 0 0 0\nH 0 0 8.0D-01\n\n'
    assert read_output(text).geometry.atoms[-1].z == 0.8


def test_multiple_jobs_rejected():
    with pytest.raises(ValueError):
        read_output('ORCA TERMINATED NORMALLY\nORCA TERMINATED NORMALLY')


def test_non_orca_rejected():
    with pytest.raises(ValueError):
        read_output('ordinary unrelated text')


def test_project_keeps_own_labels():
    # own labels of atoms in the project; an older project without them reads as {}
    from azimuth.core import Calculation, project_labels

    water = read_xyz(EXAMPLES['Вода · H₂O'])
    text = project_text(water, Calculation(), labels={0: 'O·вода', 2: 'H2', 7: 'лишний', 1: ''})
    assert project_labels(text) == {0: 'O·вода', 2: 'H2'}
    assert project_labels(project_text(water, Calculation())) == {}


def test_dummy_atom_x():
    # the dummy atom X (Chemcraft): read and written as X, no electrons, not in the formula, no bonds, left out
    # of the calculations (without_dummies renumbers the bonds); ORCA writes it as DA
    from modules.compass.chemistry.builder import connections
    from modules.compass.chemistry.geometry_tools import coordinate_text
    from azimuth.core import Molecule, without_dummies

    mol = read_xyz('4\nwater and a point\nO 0 0 0\nX 0 0 1.0\nH 0.7586 0 0.5043\nH -0.7586 0 0.5043\n')
    assert mol.formula == 'H2O' and mol.electrons(0) == 10 and 'X ' in mol.xyz()
    assert all(1 not in (i, j) for i, j, _ in connections(mol)) and len(connections(mol)) == 2
    bare = without_dummies(Molecule(mol.title, mol.atoms, ((0, 2, 1), (0, 3, 1), (0, 1, 1))))
    assert [a.symbol for a in bare.atoms] == ['O', 'H', 'H'] and bare.bonds == ((0, 1, 1), (0, 2, 1))
    assert without_dummies(bare) is bare
    orca = coordinate_text(mol, 'ORCA')
    assert '\nDA ' in orca and '\nX ' not in orca and '\nX ' in coordinate_text(mol, 'Gaussian')

