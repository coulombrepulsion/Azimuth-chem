# ORCA 6.1.1 test data (Windows)

Outputs of ORCA 6.1.1 on the user's Windows PC (2026-11-02, `tools/check_programs.py --keep`), CRLF line ends:

- `ch2o_excited_opt_b3lyp.inp/.out` — the excited-state optimization (root 1) that Sextant writes for formaldehyde,
  B3LYP/def2-SVP: ORCA 6.1.1 stops at once (code 55), «Third functional derivative of a B88 exchange-containing
  functional requested … not available natively … use the LibXC version».
- `ch2o_excited_opt_libxc_b3lyp.inp/.out` — the same input with `! LibXC(B3LYP)`: 7 cycles, converged, normal end.
  The output was written by PowerShell as UTF-16 and is stored here as UTF-8 (otherwise unchanged).

Used by `tests/sextant/test_runner.py::test_diagnose_of_orca_6_1_without_a_third_derivative` (0.91.81, Sergei).
