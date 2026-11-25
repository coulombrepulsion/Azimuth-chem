"""The program of an output is recognized and read by its own reader (modules/spectrum/readers/outputs.py)."""

from pathlib import Path

from modules.spectrum.readers.outputs import program, read_any

DATA = Path(__file__).parents[1] / 'data'


def test_each_program_goes_to_its_reader():
    cases = [
        (DATA / 'gaussian' / 'dvb_ir_g16.log', 'Gaussian', 'Gaussian 16'),
        (DATA / 'xtb' / 'dvb_ir' / 'dvb_ir.out', 'xtb', 'xtb 6.6.1'),
        (DATA / 'psi4' / 'dvb_ir_rhf_psi4-1.7.out', 'Psi4', 'Psi4 1.7'),
        (DATA / 'orca_cclib' / 'dvb_td_orca6.0.out', 'ORCA', 'ORCA'),
    ]
    for path, kind, name in cases:
        text = path.read_text(encoding='utf-8')
        assert program(text) == kind
        out = read_any(text, path)
        assert out.program == name


def test_frequency_count_rule_per_program():
    # Gaussian, xtb and Psi4 list 3N-6 frequencies; that is complete, unlike 3N-6 for ORCA
    for path in (DATA / 'gaussian' / 'dvb_ir_g16.log', DATA / 'xtb' / 'dvb_ir' / 'dvb_ir.out'):
        out = read_any(path.read_text(encoding='utf-8'), path)
        assert len(out.frequencies) == 54 and 'отличается от 3N' not in out.assessment
