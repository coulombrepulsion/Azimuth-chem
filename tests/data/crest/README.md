# CREST on macOS (Apple Silicon), conda-forge — 2026-11-07, the user's Mac

The energy window of CREGEN in CREST 3.0.2 stays 0 (crest-lab/crest#431), so every search keeps one conformer.

- `butanediol_gfnff_3.0.2_macos.out` — `crest mol.xyz --gfnff -T 4` on butane-1,4-diol (SMILES OCCCCO): 686
  structures optimized, «1 structures remain within 12.00 kcal/mol window», «sorting energy window (EWIN) : 0.0000».
- `butanediol_4_frames.xyz` — four frames of its metadynamics (crest_dynamics.trj), 0, 3.2, 8.6 and 12.6 kcal/mol
  above the lowest (GFN-FF Epot in the comment lines, unoptimized).
- `cregen_ewin20_3.0.2_macos.out`, `cregen_ewin20.0_3.0.2_macos.out` — `crest ens.xyz --cregen ens.xyz --ewin 20`
  (and `20.0`) on those frames with CREST 3.0.2: EWIN 0.0000, «number of removed by energy : 3», one left.
- `cregen_ewin20_2.12_macos.out` — the same with CREST 2.12 (conda-forge, crest-2.12-hd8c59f4_0): «conformer
  energy window /kcal : 20.0000», four conformers.
