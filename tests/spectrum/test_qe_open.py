"""An output of pw.x opened as its crystal (modules/spectrum/readers/qe.py: start_atoms, crystal_of; 0.249.1 — the
feedback of 2026-11-18: «Файл → Открыть…» of a pw.out did nothing)."""

from pathlib import Path

from modules.compass.chemistry import crystal as cr
from modules.spectrum.readers import qe

DATA = Path(__file__).resolve().parents[1] / 'data' / 'qe'


def test_the_crystal_of_an_scf_run_is_its_start():
    text = (DATA / 'graphite_scf_pw76_mpi.out').read_text(encoding='utf-8')
    assert qe.is_qe(text) and qe.read(text).done and qe.read(text).atoms == ()  # no final coordinates in an scf
    atoms = qe.start_atoms(text)
    assert [s for s, _ in atoms] == ['C'] * 4 and all(0 <= x < 1 for _, f in atoms for x in f)
    crystal = qe.crystal_of(text, 'graphite')
    assert crystal.title == 'graphite' and abs(crystal.cell.a - 2.464) < 1e-3 and abs(crystal.cell.gamma - 120) < 1e-3
    assert len(cr.unit_cell(crystal)) == 4
    # the two layers of graphite: z = 1/4 and 3/4 of c by the start (in alat units 0.681 and 2.043 of c/a = 2.724)
    assert sorted({round(f[2], 3) for _, f in atoms}) == [0.25, 0.75]


def test_a_relaxation_gives_its_final_structure():
    text = (DATA / 'si2_vcrelax_pw76.out').read_text(encoding='utf-8')
    final = qe.final_crystal(qe.read(text), 'Si')
    assert final is not None and qe.crystal_of(text, 'Si') == final
    assert qe.crystal_of('Program PWSCF v.7.6\nnothing else', 'x') is None
