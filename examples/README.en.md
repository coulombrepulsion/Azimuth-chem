# Azimuth examples

Files to try the features of the program right away. The easiest way is **«File → Open an example…»** (the
dialog opens in this folder): calculation results go to Spectrum, structures and CIF files to Compass, the
fragments file to «My fragments». The usual «File → Open…» works too.

Almost all results are real program outputs from the cclib test data (BSD-3-Clause licence, see
`LICENSE-cclib.txt`; the sources are listed in `README.md`). Many are **excerpts**: the needed blocks are kept
unchanged, omissions are marked `...  [lines omitted from the excerpt]`. The molecule is mostly divinylbenzene
(C₁₀H₁₀), sometimes water. The structures in folders 0 and 8–11 were prepared for Azimuth.

| Folder | Files | What to do | What you will see |
|---|---|---|---|
| `0-molecules` | `water.xyz`, `methane.xyz`, `ammonia.xyz`, `benzene.xyz` | open (or drag into the window); the caption under the model is the point group button | simple molecules to start with: turning, zooming, measuring, editing; point groups C₂v (water), T_d (methane), C₃v (ammonia), D₆h (benzene) |
| `1-properties` | `water_mp2_orca5.out`, `divinylbenzene_cation_orca6.out`, `divinylbenzene_cation_gaussian16.log` | open; in Compass the «±» button above the model | Mulliken, Löwdin, Hirshfeld charges, the spin population of the cation, Mayer bond orders, the dipole — on the model |
| `2-optimization` | `divinylbenzene_opt_gaussian16.log`, `divinylbenzene_opt_psi4.out`, folder `xtb_divinylbenzene_opt` (open `dvb_opt.out`) | open; the ☰ steps drawer left of the model | optimization steps, the energy graph, playback, comparison with the start, a GIF of the steps |
| `3-scans` | `dihedral_scan_relaxed_orca6.out`, `dihedral_scan_relaxed_gaussian16.log`, `zmatrix_scan_rigid_orca5.out` | open; the ☰ drawer | PES scan points: the dihedral or the parameter, ΔE from the lowest point |
| `4-vibrations` | `divinylbenzene_freq_gaussian16.log`, `divinylbenzene_freq_psi4.out`, folder `xtb_divinylbenzene_freq` (`dvb_ir.out`) | Spectrum → «Vibrations and IR» | frequencies and the IR spectrum, animation, arrows (both ways), «GIF…», «XYZ frames…», «Displace +/−» |
| `5-uv-vis-nmr` | `divinylbenzene_tddft_orca6.out`, `divinylbenzene_tddft_gaussian16.log`, `divinylbenzene_nmr_orca6.out`, `divinylbenzene_nmr_gaussian16.log` | Spectrum → the «UV-Vis» and «NMR» tabs | the absorption spectrum with its envelope and transitions; shieldings and chemical shifts, equivalent atoms |
| `6-orbitals` | `water_mp2_gaussian16.fchk`, `water_gamess.molden`, `divinylbenzene_orbitals_orca6.out`, `MoOCl4_ecp_gaussian16.fchk` | open; the «Orbitals» window (for the ORCA output: the «Orbitals…» button) | the level diagram, HOMO/LUMO, the isosurface of an orbital or the density without CUBE files |
| `7-programs` | `water_ccsdt_gaussian16.log`, `water_ccsdt_psi4.out`, folder `xtb_divinylbenzene_sp` (`dvb_sp.out`) | open one after another | the same water calculation in Gaussian and Psi4 (final CCSD(T) energy); xtb charges and Wiberg bond orders |
| `8-compare` | `ethanol.xyz` and `ethanol_other_order.xyz`; `butane_anti.xyz` and `butane_gauche.xyz` | open the first file, then «Compare» → «Overlay a structure from a file…» → the second | the overlay with another atom order (RMSD ≈ 0, «numbered differently»), «Renumber the model as in the file»; how two conformers of butane differ |
| `9-torsion` | `butane.xyz`, `ethanol.xyz` | right-click the middle C–C (or the C–O) bond → «Rotate about this bond…» | the exact dihedral, turning with the mouse, the closest contact, a conformer scan into the drawer or XYZ |
| `10-crystals` | `NaCl_rock_salt.cif`, `CsCl.cif`, `graphite_P1.cif`, `Si_diamond.cif`, `benzoic_acid.cif` | open → the «Crystal» window → «Build» | the cell (NaCl: 14 Na and 13 Cl with the atoms on the faces), a block of cells, the a, b, c edges; graphite: a file without symmetry operations (P1); silicon — the diamond lattice Fd-3m, vc-relax in the primitive and in the conventional cell (a ≈ 5.47 Å); benzoic acid — a molecular crystal: «Contacts» — the O–H···O hydrogen bonds and the R²₂(8) dimer, displacement ellipsoids, a calculation of the dimer |
| `11-fragments` | `example_fragments.json` | «File → Open an example…» with this file (or «Fragment» → «Import fragments…») | three fragments in «My fragments»: —CF₃, tert-butyl, acetyl; place them on atoms or instead of hydrogens |

The root of the folder also has three teaching files opened from the menus: `teaching-demo.out`,
`optimization-demo.out`, `vibrations-demo.out`. Display schemes («View → Display scheme») can be tried on any file.

`0-molecules` (2026-11-14, after the first tester's report): the geometries are built by the program from experimental bond lengths and angles (CRC Handbook, gas phase): water r(OH) 0.9572 Å, ∠HOH 104.52°; methane r(CH) 1.087 Å, tetrahedral; ammonia r(NH) 1.012 Å, ∠HNH 106.7°; benzene r(CC) 1.397 Å, r(CH) 1.084 Å — the symmetry is exact.

`10-crystals/benzoic_acid.cif` is the COD entry 7133168 (Crystallography Open Database, public domain): benzoic acid,
P2₁/n, 296 K; Sun, Li, Chen et al., Chem. Commun. 60 (2024) 7224, doi:10.1039/d4cc01751j. Only the embedded
`_shelx_res_file` and `_shelx_hkl_file` blocks (the SHELXL input and the reflections) were removed.

`10-crystals/Si_diamond.cif` is the COD entry 9008565 (from the American Mineralogist Crystal Structure Database): silicon, Fd-3m, a = 5.4307 Å, 300 K; Wyckoff R. W. G., Crystal Structures 1 (1963) 7–83. The file is unchanged (2026-11-21, after the first tester's report).
