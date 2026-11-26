# ORCA 6.0.1 — the input files of Sextant run on a Mac (0.89.24)

Written by Sextant (`tools/check_programs.py --keep`, 2026-11-01) and run by the user with ORCA 6.0.1
(macOS arm64, Open MPI 4.1.1, one process): water and formaldehyde, B3LYP/def2-SVP, `%maxcore 500`.
Each `<name>.inp` is the input as Sextant wrote it, `<name>.out` the output of ORCA. The oracles of
`tests/spectrum/test_orca601.py` are the numbers ORCA printed in these files (thermochemistry, NMR table, absorption
spectrum, Hirshfeld charges, the frozen O–H distance of the input).

| File | Task |
|---|---|
| h2o_energy | single point |
| h2o_opt | optimization |
| h2o_optfreq | optimization + frequencies, thermochemistry |
| h2o_tddft | UV-Vis, TD-DFT, 3 states |
| h2o_tda_triplets | TD-DFT, TDA, singlets and triplets |
| h2o_nmr | NMR shieldings |
| ch2o_excited_opt | excited-state optimization (root 1) |
| h2o_cpcm_water | CPCM(water) |
| h2o_d3bj, h2o_d4 | dispersion |
| h2o_verytight_hirshfeld | VeryTightSCF, Hirshfeld charges |
| h2o_opt_frozen_oh | optimization with the O–H bond 0–1 frozen (Compass constraint) |
| h2o_rijcosx | RIJCOSX |
| h2o_zora | ZORA |

`h2o_ccsdt_ccpvtz.out`, `h2o_dlpno_ccsdt_ccpvtz.out` — ORCA 6.0.1 on the owner's Mac (2026-11-21, 4 processes), the inputs
Sextant writes for «Энергия» with CCSD(T) and DLPNO-CCSD(T) (`! DLPNO-CCSD(T) cc-pVTZ AutoAux`) of water (O 0 0 0.117,
H 0 ±0.757 −0.467) in cc-pVTZ: E(CCSD(T)) −76.332171457 and −76.332003041 hartree — DLPNO within 0.17 mEh of the
canonical value; «FINAL SINGLE POINT ENERGY» is that energy. The paths are replaced (/home/azimuth, /opt/orca).

`hcn_neb_idpp_failed.out` — ORCA 6.0.1 on the owner's Mac (2026-11-22, 2 processes), the input Sextant writes for
«Путь реакции (NEB-CI)» of HCN → HNC, B3LYP-D3(BJ)/def2-SVP, 4 images, both ends exactly linear: «idpp failed to
converge», exit code 64. The whole output (it names no path of the computer). Used by
`tests/sextant/test_runner.py::test_diagnose_of_a_neb_whose_initial_path_was_not_built`.

`h2o_scf_maxiter4_parallel.out` — ORCA 6.0.1 on the owner's Mac (2026-11-22, 2 processes), water B3LYP/def2-SVP with
`%scf MaxIter 4 end`: the SCF does not converge and the parallel run ends with the lines of mpirun. The whole output,
the paths replaced (/opt/orca). Used by `tests/sextant/test_runner.py` (not an MPI failure).

`irc_hcn/` — ORCA 6.0.1 on the owner's Mac (2026-11-26, 4 processes): IRC of HCN ⇄ HNC, B3LYP-D3(BJ)/def2-SVP, from
the transition state found by «Переходное состояние + частоты» (one imaginary frequency, 1117i cm⁻¹); `%irc MaxIter
40, InitHess calc_anfreq`. Both directions converged: forward to HNC (−34.21 kcal/mol from the TS), backward to HCN
(−47.77). `hcn_irc.out` — the whole output, `hcn_irc_IRC_Full_trj.xyz` — the 61 geometries of the path (renamed after
the output, as ORCA names it). Used by `tests/sextant/test_irc_task.py`.

`xtb_neb_hcn/` — ORCA 6.0.1 with xtb 6.7.1 behind it on the owner's Mac (2026-11-26, 1 process): «Путь реакции
(NEB-CI)» of HCN → HNC with the method GFN2-xTB, the input Sextant writes (`! XTB2 NEB-CI`, 6 images), XTBEXE set by
Sextant. Converged in 20 iterations; the climbing image 72.40 kcal/mol over HCN (the ends not optimized).
`hcn_xtb_neb.out`, `hcn_xtb_neb_MEP_trj.xyz` — the output and the path; `hcn_xtb_neb_no_xtb.out` — the same task
without XTBEXE: «Please set the XTBEXE environment variable», code 52. Used by `tests/sextant/test_orca_xtb.py`.
