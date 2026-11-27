# Outputs of Quantum ESPRESSO

- `si_scf_pw76.out` — pw.x 7.6 of conda-forge (linux-aarch64, serial), run on 2026-11-11 by the developer's assistant on
  the input written by `modules/sextant/qe_inputs.pw_input` for silicon (diamond, a = 5.431 Å, the conventional cell of
  8 atoms, ecutwfc 30 Ry, k 5 × 5 × 5) with `Si_r.upf` of the test pseudopotentials of Quantum ESPRESSO
  (https://github.com/QEF/q-e/tree/develop/pseudo, ONCVPSP, GPL). The paths of the run are replaced by /home/azimuth.
  Not part of the program.
- `si2_vcrelax.in`, `si2_vcrelax_pw76.out` — the same pw.x, a variable-cell relaxation (`qe_inputs.pw_input`, task
  «Оптимизация с ячейкой») of the primitive cell of silicon (2 atoms, a = 3.840 Å, 60°; k 9 × 9 × 9) with the same
  pseudopotential: 2 BFGS steps, the final cell 3.866 Å (the cubic a = 5.467 Å; PBE about 5.47, experiment 5.431).
- `si_primitive_scf_pw76.out` — the same pw.x, scf of silicon in the primitive cell made by `crystal.primitive` from the
  conventional one (2 atoms, k 9 × 9 × 9): −16.92417107 Ry, a quarter of the 8-atom cell (−67.69688399 / 4 =
  −16.92422100) within the k-point sampling; P = 18.91 kbar against 18.90.
- `si_bands.in`, `si_bands_pw76.out` — the same pw.x (0.135.0, task «Зонная структура» of `qe_inputs.steps`): scf of
  the primitive cell of silicon with `Si.pbe-n-rrkjus_psl.1.0.0.UPF` of SSSP 1.3.0 efficiency (ecutwfc 30 Ry, k 9 × 9 × 9),
  then `calculation = 'bands'` with nbnd 8 along the fcc path Γ–X–W–K–Γ–L–U–W–L–K|U–X of `qe_paths` (297 k-points):
  the highest occupied level 6.2012 eV at Γ, the lowest empty band near X (a gap of about 0.6 eV in PBE).
- `si_dos_pw76.out`, `si_dos_pw76.dos` — the same pw.x and dos.x (task «Плотность состояний»): scf, nscf on 12 × 12 × 12
  with `tetrahedra_opt` and nbnd 8, dos.x with DeltaE 0.01 eV (the file `azimuth.dos`: E, dos(E), ∫dos; EFermi in the header).
- `si_phonon_gamma_pw76.out`, `si_phonon_gamma.mold`, `si_phonon_gamma_scf.in` — pw.x, ph.x and dynmat.x 7.6 of conda-forge
  (macOS arm64, 4 MPI processes for pw.x and ph.x), run on 2026-11-21 on the owner's Mac by the developer's assistant: the
  task «Частоты (точка Γ)» of `qe_inputs.steps` for the primitive cell of silicon (2 atoms, a = 3.8403 Å, 60°; SSSP 1.3.0
  efficiency, ecutwfc 30 Ry, k by the spacing 0.25 Å⁻¹) — scf, ph.x at q = 0 with epsil (ε∞ 13.557; Z* −0.048 before
  the sum rule), dynmat.x with asr 'crystal': three zero modes and the optical triplet at 514.0 cm⁻¹ (Raman, IR 0;
  experiment 520 cm⁻¹). The file .mold is the filmol of dynmat.x. The paths are replaced by /home/azimuth. Recorded before 0.220.0, which adds `force_symmorphic` to the scf of both phonon tasks.
- `nacl_phonon_gamma_pw76.out`, `nacl_phonon_gamma.mold`, `nacl_phonon_gamma_scf.in` — the same for rock salt (2 atoms,
  a = 3.9881 Å, 60°; ecutwfc 40 Ry, k 8 × 8 × 8): ε∞ 2.511, Z*(Na) 1.099, the TO triplet at 165.37 cm⁻¹ with the IR
  activity 1.9996 (D/Å)²/amu (experiment: TO 164 cm⁻¹, ε∞ 2.34). No LO: dynmat.x without a direction of q gives the
  analytic part only.
- `nacl_dispersion.freq`, `nacl_dispersion.phdos`, `nacl_dispersion_path.json`, `nacl_dispersion_ph.in` — QE 7.6 on the
  owner's Mac (2026-11-21), the task «Фононные ветви и плотность состояний» of `qe_inputs.steps` for rock salt (the
  primitive cell of `crystal.primitive`; SSSP 1.3.0, ecutwfc 40 Ry, k 8 × 8 × 8): pw.x, ph.x on the grid q 4 × 4 × 4 with
  epsil (13 irreducible q, 34 min on 6 processes), q2r.x, matdyn.x along the fcc path of `qe_paths` (289 q — the flfrq
  file `.freq`; path.json — the x and the labels Azimuth writes beside it) and matdyn.x for the DOS on 16 × 16 × 16
  (`.phdos`). At Γ: the TO pair at 165.40 cm⁻¹ and the LO at 255.41 cm⁻¹ (the non-analytic term of ε∞ 2.510 and the
  Born charges; experiment TO 164, LO 264 cm⁻¹); the highest branch 255.4 cm⁻¹. The q lines of flfrq carry four numbers.
- `si_dispersion_q222.freq`, `si_dispersion_q222_path.json`, `si_dispersion_q222_scf.in`, `si_dispersion_q222_ph.in` — the
  same task for silicon (Fd-3m :2, its primitive cell) with the grid of q set to 2 × 2 × 2 by hand (the probe of the fix;
  the task writes 4 × 4 × 4). Without `force_symmorphic` ph.x 7.6 stopped at once: «scale_sym_ops: incompatible FFT
  grid» (12 operations, 8 with fractional translations); with it — 6 q, 6 min. Γ 514.41 cm⁻¹; X: TA 141.6, LA/LO 410.1,
  TO 461.8; L: TA 109.1, LA 373.8, LO 413.9, TO 490.4 (experiment X: 150, 410, 463; L: 114, 378, 420, 490 cm⁻¹).
- `si_eos_pw76.out` — QE 7.6 on the owner's Mac (2026-11-26, 1 process), the task «Уравнение состояния (ряд объёмов)» of
  `qe_inputs.steps` for silicon (the primitive cell of `crystal.primitive`, PBE, SSSP 1.3.0, ecutwfc 30 Ry, k 9 × 9 × 9):
  seven runs of pw.x at 0.94 … 1.06 of the volume one after another (the paths replaced). «! total energy»:
  −22.83372303, −22.83649793, −22.83839394, −22.83949545, −22.83987597, −22.83961627, −22.83877497 Ry; the volumes
  pw.x prints: 254.0410 … 286.4718 a.u.³; its pressures 87.85 … −30.53 kbar (zero between the fifth and the sixth).
  The Birch–Murnaghan fit: V₀ = 40.911 Å³ (a₀ = 5.4697 Å of the cubic cell), B₀ = 88.8 GPa, B₀′ = 4.34 (PBE in the
  literature: 5.469 Å, 88–89 GPa; measured 5.431 Å, 99 GPa). Used by `tests/compass/test_equation_of_state.py`.
- `si_cutoff_pw76.out`, `si_kgrid_pw76.out` — QE 7.6 on the owner's Mac (2026-11-26, 1 process), the tasks «Сходимость по
  энергии обрезания» and «Сходимость по k-сетке» of `qe_inputs.steps` for silicon (the primitive cell, PBE, SSSP 1.3.0):
  six scf runs each, one after another (the paths replaced) — ecutwfc 20 … 70 Ry at k 9 × 9 × 9, and the grids 4, 7, 9,
  11, 14, 18 (those of `convergence.grids` for the grid 9 × 9 × 9 of the primitive cell) at 30 Ry. Used by `tests/compass/test_crystal_convergence.py`.
- `nio_magnetic_pw76.out` with `nio_magnetic_mag1.in` … `mag3.in`, `nio_hubbard_pw76.out` with `nio_hubbard_hub1.in` …
  `hub5.in` — QE 7.6 on the owner's Mac (2026-11-26, 4 processes), the tasks «Магнитный порядок (без спина, ФМ, АФМ)» and
  «Ряд по U (DFT+U)» of `qe_inputs.steps` for NiO (two formula units, the antiferromagnetic order along [111],
  a = 4.177 Å, PBE, SSSP 1.3.0, k 6 × 11 × 11; the paths replaced). Energies −769.73287092 (no spin), −769.74215935
  (ferromagnetic), −769.78059614 Ry (antiferromagnetic); with U = 0, 2, 4, 6, 8 eV the gap 0.81, 1.83, 2.65, 3.11,
  3.19 eV and the moment of Ni 1.33, 1.51, 1.61, 1.68, 1.73 μB. Used by `tests/compass/test_crystal_states.py`.
- `graphene_bands_pw76.out` with `graphene_bands_path.json`, `graphene_kpt_pw76.out` with `graphene_kpt1.in` … `kpt8.in`,
  `graphene_vac_pw76.out` with `graphene_vac1.in` … `vac6.in` — QE 7.6 on the owner's Mac (2026-11-26, 4 processes),
  graphene (a = 2.46 Å, c = 15 Å, PBE, SSSP 1.3.0; the paths replaced): «Зонная структура» on the path Γ–M–K–Γ of a
  layer (k 12 × 12 × 1; the π and π* bands touch at K at −1.6887 eV, ħv_F = 5.47 eV·Å), «Сходимость по k-сетке»
  (N = 6, 8, 9, 10, 12, 15, 18, 24) and «Сходимость по вакууму (слой)» (8 … 20 Å). Used by
  `tests/compass/test_layer.py`.
- `mgo_elastic_pw76.out` with `mgo_elastic.json` — QE 7.6 on the owner's Mac (2026-11-26, 4 processes), the task
  «Упругие постоянные (кубический кристалл)» of `qe_inputs.steps` for MgO at the cell PBE gives (a = 4.2486 Å; the
  primitive cell, SSSP 1.3.0, k 11 × 11 × 11): 19 runs — the cell as it is and 3 strains × 6 amplitudes. Of every run
  its head and its end are kept (the iterations left out; the energies «!» and «JOB DONE» are there; the paths
  replaced). C₁₁ = 276.3, C₁₂ = 92.1, C₄₄ = 143.2 GPa, B = 153.5 GPa. Used by `tests/compass/test_elastic.py`.
- `graphite_scf_pw76_mpi.out` — QE 7.6 on the Mac of a tester (2026-11-18), the task «Энергия» of graphite (P 1, 4
  atoms, PAW of pslibrary), several MPI processes: the output ends with the notes «floating-point exceptions are
  signalling» of each process after «JOB DONE». The scf run has no final coordinates — the crystal is taken from the
  table «positions (alat units)» of the start. Used by `tests/spectrum/test_qe_open.py` and
  `tests/gui/test_gui_files.py::test_an_output_of_pw_x_opens_as_its_crystal` (it was read as ORCA before 0.249.1).
