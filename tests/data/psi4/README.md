# Psi4 test data (from cclib)

Source: the cclib test data, https://github.com/cclib/cclib, commit
`76df867532961117427cb3e0877913db3233f83f` (2026-10-07), downloaded 2026-10-23.

Excerpts of `data/Psi4/basicPsi4-1.7/<name>.out` (Psi4 1.7), saved as `<name>_psi4-1.7.out`
(`water_ccsd(t)` as `water_ccsdt`): dvb_gopt_rhf, dvb_ir_rhf, dvb_sp_rhf, dvb_sp_uhf, water_mp2,
water_ccsd(t). The excerpts keep, unchanged and in order, the first 12 lines, the geometry blocks (of a
finite-difference job only the first four), the SCF and correlated energy lines, the OPTKING, FINDIF and
displacement lines, the Mulliken and multipole blocks, the final optimized geometry and everything from
«Harmonic Vibrational Analysis» to the end; omitted runs of lines are marked
`...  [lines omitted from the excerpt]`. The parser gives the same result on each excerpt as on the
whole file (checked 2026-10-23). Used by `tests/spectrum/test_psi4.py` (Azimuth, 2026-10-23, Jane).

## Psi4 1.11 (Azimuth, 2026-11-22)

Run on the owner's Mac (macOS arm64, Psi4 1.11 of conda-forge, installed by «Установить программы для расчёта»;
2 processes) with the inputs Sextant 0.222.6 writes; whole outputs, the paths replaced with `/opt/psi4` and
`/tmp/azimuth`, the host with `azimuth`:

- `water_ccsdt_fc_psi4-1.11.out` — CCSD(T)/cc-pVTZ, `freeze_core true`, `scf_type pk`, water O 0 0 0.1173,
  H 0 ±0.7572 −0.4692 Å: −76.332194 Eh (ORCA 6.0.1 with its own frozen core: −76.332171).
- `ch2o_tddft_d3bj_psi4-1.11.out` — `energy('td-cam-b3lyp-d3bj')`/def2-SVP, 10 states, `symmetry c1`,
  `tdscf_r_convergence 1e-4`: the first state 3.709 eV, dark (n→π*).
- `water_optfreq_psi4-1.11.out` — B3LYP/def2-SVP from a geometry of SMILES, `symmetry c1`: 1638.6, 3792.3,
  3887.6 cm⁻¹.

Used by `tests/spectrum/test_psi4_111.py`.

## Licence of the data (cclib)

BSD 3-Clause License

Copyright (c) 2024, the cclib development team
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

* Neither the name of the copyright holder nor the names of its
  contributors may be used to endorse or promote products derived from
  this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

`hcn_ts_b3lyp_d3bj_psi4-1.11.out.gz` (2026-11-22, the input of Sextant 0.222.12, gzip, the same replacements): the
search of the transition state HCN ⇌ HNC, B3LYP-D3(BJ)/def2-SVP — `opt_type ts`, `full_hess_every 0` (a Hessian by
finite differences before the first step), then `frequency()`. Used by `tests/spectrum/test_psi4.py` (the steps and
the final geometry) and `tests/spectrum/test_nwchem.py` (the oracle of the NWChem search).

