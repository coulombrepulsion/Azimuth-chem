# NWChem test data (from cclib)

Source: the cclib test data, https://github.com/cclib/cclib, commit
`493a03b1a66df927f4e289c7200bd92c01c6b234` (2026-10-25), downloaded 2026-10-26.

Whole outputs of `data/NWChem/basicNWChem7.0 (NWChem 7.0.0; dvb_ir: 7.0.2)`, unchanged, compressed with gzip (`gzip -9 -n`), saved as `<name>_nwchem-7.0.out.gz`: dvb_sp_ks, dvb_gopt_ks, dvb_ir, dvb_td, dvb_un_sp_ks, water_mp2, water_ccsd(t)
(`water_ccsd(t)` as `water_ccsdt`). Used by `tests/spectrum/test_nwchem.py` (Azimuth 0.64.0, 2026-10-26, Jane).

## NWChem 7.3.0 (Azimuth, 2026-11-22)

Run on the owner's Mac (macOS arm64, NWChem 7.3.0 of conda-forge, installed by «Установить программы для расчёта»)
with the inputs Sextant 0.222.12 writes (the MP2 one — with «mp2 freeze atomic» of 0.222.13); whole outputs,
compressed with gzip, the paths replaced with `/opt/nwchem` and `/tmp/azimuth`, the host with `azimuth`, the user with
`user` (the reader gives the same result before and after): `water_optfreq_b3lyp_d3bj` (B3LYP-D3(BJ)/def2-SVP,
«task dft optimize», «task dft freq»), `hcn_ts_b3lyp_d3bj` (HCN ⇌ HNC, «task dft saddle», «task dft freq»),
`ch2o_tddft` (10 singlets), `water_nmr` («property shielding»), `water_mp2_fc` (MP2/cc-pVDZ, frozen core),
`water_cation` (charge 1, doublet) — `<name>_nwchem-7.3.out.gz`. Used by `tests/spectrum/test_nwchem.py`; these are
the project's own files, not cclib's.

Two failures of the same day, for the messages `runner.PROBLEMS` knows: `water_scf_failed` (the SCF limited to 2
iterations by «dft iterations 2» — «Calculation failed to converge», exit code 255) and `benzene_mp2_100mb`
(MP2/def2-TZVP of benzene with «memory total 100 mb» — «mp2_grad:insufficient resources», exit code 1), and
`glycine_opt_maxiter3` (an optimization of glycine with «driver maxiter 3» — «Failed to converge in maximum number of
steps or available time», exit code 255). Used by `tests/sextant/test_runner.py`.

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
