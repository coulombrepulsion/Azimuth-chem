"""The input of pw.x and the SSSP pseudopotentials (modules/sextant/qe_inputs.py, qe_pseudo.py).

Oracles, by hand:
  * k-points n_i = ⌈2π |a*_i| / 0.25 Å⁻¹⌉: silicon a = 5.431 Å — 2π / 5.431 = 1.157 Å⁻¹ → 5 × 5 × 5; graphite (a = 2.46,
    c = 6.70 Å, hexagonal) — |a*| = 2 / (a √3) → 2π · 0.4694 / 0.25 = 11.8 → 12, c: 2π / 6.70 / 0.25 = 3.75 → 4;
  * silicon in F d -3 m (origin 2) from its one site: the 8 atoms of the diamond cell (⅛ ⅛ ⅛, ⅞ ⅞ ⅞, ⅞ ⅜ ⅜, ⅝ ⅛ ⅝,
    ⅜ ⅞ ⅜, ⅝ ⅝ ⅛, ⅜ ⅜ ⅞, ⅛ ⅝ ⅝ — the copies by the operations, listed here), no smearing (no metal), the cutoffs of its
    pseudopotential; rock salt — an insulator (not a metal for its Na), fixed occupations; vc-relax — &IONS and &CELL;
  * the real run of that input (tests/data/qe/si_scf_pw76.out): pw.x 7.6 converged, «JOB DONE»;
  * the download of the library: the MD5 of each file checked, the archive unpacked flat — a name «../x.UPF» lands
  inside.
"""

import hashlib
import io
import json
from pathlib import Path
import tarfile

import pytest

from modules.compass.chemistry import crystal as cr
from modules.sextant import qe_inputs as qi
from modules.sextant import qe_pseudo as qp
from tests.compass.test_crystal_symmetry import rock_salt

DATA = Path(__file__).resolve().parents[1] / 'data' / 'qe'


def silicon():
    text = ('data_Si\n_cell_length_a 5.431\n_cell_length_b 5.431\n_cell_length_c 5.431\n'
            "_space_group_name_H-M_alt 'F d -3 m :2'\nloop_\n_atom_site_label\n_atom_site_fract_x\n"
            '_atom_site_fract_y\n_atom_site_fract_z\nSi1 0.125 0.125 0.125\n')
    return cr.parse_cif(text)


def test_kpoints():
    assert qi.kpoints(cr.Cell(5.431, 5.431, 5.431)) == (5, 5, 5)
    assert qi.kpoints(cr.Cell(2.46, 2.46, 6.70, 90, 90, 120)) == (12, 12, 4)


def test_silicon_input():
    text = qi.pw_input(silicon(), 'Энергия', {'Si': ('Si.upf', 30.0, 240.0)}, pseudo_dir='/p')
    assert "calculation = 'scf'" in text and 'nat = 8' in text and 'ntyp = 1' in text
    assert 'ecutwfc = 30' in text and 'ecutrho = 240' in text and 'occupations' not in text
    assert 'Si 28.0850 Si.upf' in text and "pseudo_dir = '/p'" in text
    positions = text.split('ATOMIC_POSITIONS crystal\n')[1].split('K_POINTS')[0].split('\n')
    found = {tuple(round(float(x) * 8) for x in line.split()[1:]) for line in positions if line.strip()}
    assert found == {(1, 1, 1), (7, 7, 7), (7, 3, 3), (5, 1, 5), (3, 7, 3), (5, 5, 1), (3, 3, 7), (1, 5, 5)}
    assert text.rstrip().endswith('K_POINTS automatic\n  5 5 5 0 0 0')
    assert '&IONS' not in text


def test_salt_and_the_tasks():
    pseudo = {'Na': ('Na.upf', 40.0, 320.0), 'Cl': ('Cl.upf', 35.0, 280.0)}
    text = qi.pw_input(rock_salt(), 'Оптимизация с ячейкой', pseudo)
    assert "calculation = 'vc-relax'" in text and '&IONS' in text and '&CELL' in text
    assert 'occupations' not in text and 'smearing' not in text and 'ecutwfc = 40' in text  # fixed: the default and 'ecutrho = 320' in text and 'nat = 8' in text
    assert "calculation = 'relax'" in qi.pw_input(rock_salt(), 'Оптимизация атомов', pseudo)
    with pytest.raises(ValueError):
        qi.pw_input(rock_salt(), 'scf', {'Na': ('Na.upf', 40.0, 320.0)})


def test_the_real_run_of_the_silicon_input():
    out = (DATA / 'si_scf_pw76.out').read_text(encoding='utf-8')
    assert 'Program PWSCF v.7.6' in out and 'convergence has been achieved' in out and 'JOB DONE' in out
    assert 'number of atoms/cell      =            8' in out


def _library(tmp_path, names=('Si.upf', 'C.upf'), evil=False):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz') as tar:
        for name in names + (('../x.UPF',) if evil else ()):
            data = f'<UPF {name}>'.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    archive = buffer.getvalue()
    table = json.dumps({n.split('.')[0]: {'filename': n, 'cutoff_wfc': 30, 'cutoff_rho': 240} for n in names}).encode()
    library = {'name': 'TEST', 'functional': 'PBE', 'license': 'LICENSE.txt',
               'json': ('t.json', hashlib.md5(table).hexdigest(), len(table)),
               'archive': ('t.tar.gz', hashlib.md5(archive).hexdigest(), len(archive))}
    files = {qp.RECORD.format('t.json'): table, qp.RECORD.format('t.tar.gz'): archive,
             qp.RECORD.format('LICENSE.txt'): b'licence'}
    return library, files


def test_the_download_of_the_library(tmp_path):
    library, files = _library(tmp_path, evil=True)
    target = qp.download(tmp_path, files.__getitem__, library)
    assert qp.installed(tmp_path, library) and qp.table(tmp_path, library)['Si'] == ('Si.upf', 30.0, 240.0)
    assert (target / 'x.UPF').is_file() and not (target.parent / 'x.UPF').exists()
    assert (target / 'LICENSE.txt').read_bytes() == b'licence'
    bad = dict(files)
    bad[qp.RECORD.format('t.tar.gz')] = files[qp.RECORD.format('t.tar.gz')] + b'x'
    with pytest.raises(ValueError):
        qp.download(tmp_path / 'other', bad.__getitem__, library)
    assert qp.LIBRARY['archive'][1] == 'a58f1b3373f330179fd0832c48bb9a52'  # the record of 2026-11-11


def test_the_functional_the_dispersion_and_the_charge():
    # 0.182.0 — INPUT_PW of QE (read 2026-11-15): input_dft overrides the functional of the files; the vdW-DF names of
    # Modules/funct.f90 ('VDW-DF2', 'VDW-DF2-B86R', 'VDW-DF-CX', 'RVV10'); vdw_corr 'ts-vdw', 'mbd_vdw'; tot_charge
    pseudo = {'Si': ('Si.upf', 30.0, 240.0)}
    plain = qi.pw_input(silicon(), 'Энергия', pseudo)
    assert 'input_dft' not in plain and 'tot_charge' not in plain
    pbesol = qi.pw_input(silicon(), 'Энергия', pseudo, options=qi.Options(functional='pbesol'))
    assert 'input_dft' not in pbesol  # the functional of the PBEsol files themselves
    assert qi.library_of('pbesol') == 'PBEsol' and qi.library_of('vdw-df2') == qi.library_of('') == 'PBE'
    for name in qi.NONLOCAL:
        text = qi.pw_input(silicon(), 'Энергия', pseudo, options=qi.Options(functional=name))
        assert f"  input_dft = '{name}'" in text and 'vdw_corr' not in text
    with pytest.raises(ValueError):
        qi.pw_input(silicon(), 'Энергия', pseudo, options=qi.Options(functional='rvv10', vdw='d3bj'))
    with pytest.raises(ValueError):
        qi.pw_input(silicon(), 'Энергия', pseudo, options=qi.Options(functional='b3lyp'))
    assert "  vdw_corr = 'ts-vdw'" in qi.pw_input(silicon(), 'Энергия', pseudo, options=qi.Options(vdw='ts'))
    assert "  vdw_corr = 'mbd_vdw'" in qi.pw_input(silicon(), 'Энергия', pseudo, options=qi.Options(vdw='mbd'))
    charged = qi.pw_input(silicon(), 'Энергия', pseudo, options=qi.Options(charge=-1))
    system = charged.split('&SYSTEM')[1].split('/')[0]
    assert '  tot_charge = -1' in system


def test_the_pbesol_library_of_the_record():
    # the file list of the Materials Cloud record rcyfm-68h65, read SSSP_1.3.0_PBEsol_efficiency.json
    # md5 84fbbbd8f67b551abaec2f8a9df86801, 22459 bytes; .tar.gz md5 b6cad0d97c86d3b43ae416d6e5d8b771, 60464715 bytes
    library = qp.LIBRARIES['PBEsol']
    assert library['json'] == ('SSSP_1.3.0_PBEsol_efficiency.json', '84fbbbd8f67b551abaec2f8a9df86801', 22459)
    assert library['archive'] == ('SSSP_1.3.0_PBEsol_efficiency.tar.gz', 'b6cad0d97c86d3b43ae416d6e5d8b771', 60464715)
    assert qp.LIBRARIES['PBE'] is qp.LIBRARY and qp.folder('/r', library).name == 'SSSP_1.3.0_PBEsol_efficiency'


def test_the_hybrid_functionals():
    # 0.185.0 — PW/src/setup.f90 of QE (read 2026-11-15): «forces for hybrid functionals + US/PAW not implemented» for a
    # relaxation, «stress … not implemented» for vc-relax: the energy only (SSSP is mostly US/PAW)
    pseudo = {'Si': ('Si.upf', 30.0, 240.0)}
    for name in qi.HYBRIDS:
        text = qi.pw_input(silicon(), 'Энергия', pseudo, options=qi.Options(functional=name, vdw='d3bj'))
        assert f"  input_dft = '{name}'" in text and 'dftd3_version = 4' in text  # D3 knows PBE0 and HSE06
        assert qi.library_of(name) == 'PBE'
        for task in ('Оптимизация атомов', 'Оптимизация с ячейкой'):
            with pytest.raises(ValueError):
                qi.pw_input(silicon(), task, pseudo, options=qi.Options(functional=name))


def test_the_pressure_on_the_cell():
    # press of vc-relax, kbar
    pseudo = {'Si': ('Si.upf', 30.0, 240.0)}
    text = qi.pw_input(silicon(), 'vc-relax', pseudo=pseudo, options=qi.Options(external=3.5))
    assert '  press = 35' in text
    assert 'press =' not in qi.pw_input(silicon(), 'vc-relax', pseudo=pseudo)


def test_what_of_the_cell_a_vc_relax_changes():
    # cell_dofree of pw.x (INPUT_PW: 'all' by default, '2Dxy' — the cell in its xy plane only): a layer keeps its vacuum
    pseudo = {'Si': ('Si.upf', 30.0, 240.0)}
    plain = qi.pw_input(silicon(), 'Оптимизация с ячейкой', pseudo)
    assert '&CELL\n/' in plain and 'cell_dofree' not in plain
    layer = qi.pw_input(silicon(), 'Оптимизация с ячейкой', pseudo, options=qi.Options(dofree='2Dxy', external=1.0))
    assert "&CELL\n  cell_dofree = '2Dxy'\n  press = 10\n/" in layer
    assert 'cell_dofree' not in qi.pw_input(silicon(), 'Оптимизация атомов', pseudo, options=qi.Options(dofree='2Dxy'))
    assert set(qi.DOFREE) == {'', '2Dxy', 'volume', 'shape'}
    with pytest.raises(ValueError):
        qi.pw_input(silicon(), 'Оптимизация с ячейкой', pseudo, options=qi.Options(dofree='sideways'))


def test_lda_pseudopotentials_are_fetched_by_the_element(tmp_path):
    # pslibrary on the site of Quantum ESPRESSO: the page of an element lists its files (read 2026-11-26: silicon has
    # «pz» only as psl.0.1, titanium as psl.1.0.0); the header of a file suggests its cutoffs
    page = ('<a href="/upf_files/Si.pbe-n-rrkjus_psl.1.0.0.UPF">x</a> <a href="/upf_files/Si.pz-n-kjpaw_psl.0.1.UPF">x</a>'
            '<a href="/upf_files/Si.pz-n-rrkjus_psl.0.1.UPF">x</a> <a href="/upf_files/Si.rel-pz-n-rrkjus_psl.0.1.UPF">x</a>')
    upf = ('<UPF version="2.0.1">\n Suggested minimum cutoff for wavefunctions:  44. Ry\n'
           ' Suggested minimum cutoff for charge density: 175. Ry\n').encode()
    asked = []

    def fetch(url):
        asked.append(url)
        if url.endswith('/ps-library/si'):
            return page.encode()
        if url.endswith('/ps-library/mg'):
            return b'<a href="/upf_files/Mg.pbe-spnl-rrkjus_psl.1.0.0.UPF">x</a>'
        if url.endswith('/upf_files/Si.pz-n-rrkjus_psl.0.1.UPF'):
            return upf
        raise AssertionError(url)

    names = ['/upf_files/Ti.pz-spn-rrkjus_psl.0.3.0.UPF', 'Ti.pz-spn-rrkjus_psl.1.0.0.UPF', 'Ti.pz-n-kjpaw_psl.1.0.0.UPF']
    assert qp.choose(names, 'Ti') == 'Ti.pz-spn-rrkjus_psl.1.0.0.UPF'  # ultrasoft, the newest
    assert qp.choose(['H.pz-rrkjus_psl.1.0.0.UPF', 'He.pz-rrkjus_psl.1.0.0.UPF'], 'H') == 'H.pz-rrkjus_psl.1.0.0.UPF'
    assert qp.choose(names, 'T') is None and qp.choose(['Si.rel-pz-n-rrkjus_psl.1.0.0.UPF'], 'Si') is None
    assert qp.cutoffs(upf.decode()) == (44.0, 175.0) and qp.cutoffs('<UPF>') is None
    library = qp.for_elements(qp.LDA, ['Si', 'Si'])
    assert library['elements'] == ('Si',) and qp.for_elements(qp.LIBRARY, ['Si']) is qp.LIBRARY
    assert not qp.installed(tmp_path, library)
    qp.download(tmp_path, fetch, library)
    assert qp.installed(tmp_path, library) and qp.table(tmp_path, library) == {'Si': ('Si.pz-n-rrkjus_psl.0.1.UPF', 44.0, 175.0)}
    assert (qp.folder(tmp_path, library) / 'Si.pz-n-rrkjus_psl.0.1.UPF').read_bytes() == upf
    count = len(asked)
    qp.download(tmp_path, fetch, library)  # what is there is not fetched again
    assert len(asked) == count
    both = qp.for_elements(qp.LDA, ['Si', 'Mg'])
    assert not qp.installed(tmp_path, both)
    with pytest.raises(ValueError, match='no LDA pseudopotential of Mg'):
        qp.download(tmp_path, fetch, both)
    # the input: no input_dft — the functional is that of the files
    text = qi.pw_input(silicon(), 'Энергия', qp.table(tmp_path, library), 'p', options=qi.Options(functional='lda'))
    assert 'input_dft' not in text and 'Si.pz-n-rrkjus_psl.0.1.UPF' in text and 'ecutwfc = 44' in text
    assert qi.library_of('lda') == 'LDA' and qi.library_of('') == 'PBE' and 'lda' in qi.FUNCTIONALS
