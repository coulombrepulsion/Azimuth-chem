# Inputs of GAMESS (US) and NWChem — the oracle of Sextant's input files (0.108.39)

The inputs of the cclib test data whose outputs are in `tests/data/gamess` and `tests/data/nwchem` (the programs ran
them: GAMESS 2017, NWChem 7.0). `tests/sextant/test_inputs_more.py` compares the groups and keywords written by
`modules/sextant/inputs_more.py` with these.

Source: https://github.com/cclib/cclib, commit `38279f51cefe7ef397b0f91bbf62105939388ad9` (2026-11-08),
`data/GAMESS/basicGAMESS-US2017/*.inp` and `data/NWChem/basicNWChem7.0/*.in`, unchanged. Licence BSD-3-Clause
(`examples/LICENSE-cclib.txt`).
