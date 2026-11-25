# Outputs of CP2K (written by hand)

The computer of the tests could not run CP2K: the conda-forge build (2026.2, linux-aarch64) needs glibc 2.38 and the
virtual machine of the developer's assistant has 2.35. These files are short outputs written by hand in the format of
CP2K 2026 (the lines the reader of Azimuth looks at: «CP2K| version string», «- Atoms:», «ENERGY| Total FORCE_EVAL ( QS )
energy [hartree]», «OPTIMIZATION STEP:», «GEOMETRY OPTIMIZATION COMPLETED», «PROGRAM ENDED AT», the position file
<project>-pos-1.xyz and the cell file <project>-1.cell). They test the reader, not CP2K. Replace them by real outputs
when CP2K runs here.

- `cellopt.out`, `azimuth-pos-1.xyz`, `azimuth-1.cell`, `azimuth.inp` — a CELL_OPT of silicon (8 atoms, 2 steps), the
  numbers invented but consistent (the last frame: the diamond structure in a cubic cell of 5.47 Å).

- `cscl_energy_2026.2.out`, `cscl_energy_2026.2.inp` — a real run (2026-11-12, the owner's Mac, CP2K 2026.2 of Homebrew,
  `cp2k.psmp`): ENERGY of CsCl from examples/10-crystals (2 atoms, 16 electrons in GTH-PBE, DZVP-MOLOPT-SR, Γ point) —
  E = −35.102402520934618 hartree, the SCF converged in 16 steps. The name of the user and the folder are replaced by
  «user» and «Projects»; nothing else is changed.
- 2026-11-12: «*** SCF run converged in … steps ***» added before each energy of `cellopt.out`, as in a real output
  (the reader takes a run as converged only with it).
- `cellopt_type_abort_2026.2.out` — a real refusal (2026-11-12, the owner's Mac): CP2K 2026.2 stopped at the input of a
  CELL_OPT with `TYPE DIRECT_CELL_OPT` («MOTION/CELL_OPT/TYPE has been removed»); the name of the computer replaced by
  «computer». The reader gives the words of the box [ABORT] without its picture.
- `cscl_cellopt/` — a real CELL_OPT (2026-11-12, the owner's Mac, CP2K 2026.2): CsCl of the examples, 2 atoms at the Γ
  point with Fermi–Dirac smearing (the input of 0.139.1, which took the salt for a metal) — the cell grew from 4.123 to
  5.284 Å in 9 steps, an artefact of the Γ point and the smearing, kept as such: the files of a real optimization
  (`azimuth.inp`, `azimuth-pos-1.xyz` — frames i = 1…10, without the start, `azimuth-1.cell` — steps 1…9, `cp2k.out`; the
  name of the user, the folder and the computer replaced). The .molden, restart and Hessian files are not kept.

- `cscl_cellopt/azimuth-MOS-1_8.molden`, `azimuth-MOS-1_9.molden` — the Molden files of the last two steps of the same CELL_OPT (CP2K writes one at each step; `&MO_MOLDEN NDIGITS 9 GTO_KIND SPHERICAL`); the oracle of `readers.cp2k.for_multiwfn` (2026-11-12).

- `cscl_vibrations.mol` (2026-11-13) — written by hand in the format of `<project>-VIBRATIONS-1.mol` of CP2K
  (&VIBRATIONAL_ANALYSIS &PRINT &MOLDEN_VIB: [FREQ] cm⁻¹, [FR-COORD] bohr, [FR-NORM-COORD] «vibration k»): CsCl of 2 atoms
  (a = 4.123 Å, Cl at a√3/2 · … in bohr), three acoustic modes at 0 and the triply degenerate optical mode, Cs and Cl in
  opposite directions (amplitudes in the inverse ratio of the square roots of the masses). The numbers are invented; it
  tests the reader and the model, not CP2K. Replace by a real file when CP2K runs here.
