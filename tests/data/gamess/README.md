# GAMESS (US) and Firefly test data (from cclib)

Source: the cclib test data, https://github.com/cclib/cclib, commit
`493a03b1a66df927f4e289c7200bd92c01c6b234` (2026-10-25), downloaded 2026-10-26.

Whole outputs of `data/GAMESS/basicGAMESS-US2017 (GAMESS (US) 20 APR 2017 R1) and GAMESS/basicFirefly8.0 (Firefly 8.0.1)`, unchanged, compressed with gzip (`gzip -9 -n`), saved as `<name>_gamess-2017.out.gz`: dvb_sp, dvb_un_sp, dvb_gopt_a, dvb_ir, dvb_td, nh3_ts_ir, water_mp2, water_ccsd(t); `<name>_firefly-8.0.out.gz`: dvb_gopt_a, dvb_ir, water_mp2; 0.64.1: `MoOCl4-sp_gamess-2017.out.gz` (test_output_orbitals.py)
(`water_ccsd(t)` as `water_ccsdt`). Used by `tests/spectrum/test_gamess.py` (Azimuth 0.64.0, 2026-10-26, Jane).

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
