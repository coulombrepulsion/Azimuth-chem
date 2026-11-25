# Gaussian test data (from cclib)

Source: the cclib test data, https://github.com/cclib/cclib, commit
`76df867532961117427cb3e0877913db3233f83f` (2026-10-07), downloaded 2026-10-23.

Excerpts of `data/Gaussian/basicGaussian16/<name>.(out|log)` (Gaussian 16 Rev A.03), saved as
`<name>_g16.log`: dvb_gopt, dvb_ir (freq=HPModes), dvb_td, dvb_nmr, dvb_scan_relaxed, dvb_scan_unrelaxed,
dvb_un_sp, water_mp2, water_ccsdt. The excerpts keep, unchanged and in order, the version and termination
lines, the first input orientation and every standard orientation block, «SCF Done», the optimization
and scan markers, the ModRedundant input, the scan summaries, the population, dipole, frequency (to
«Thermochemistry»), excited-state and shielding lines, the atomic masses, «EUMP2 =» and the archive
entry; omitted runs of lines are marked `...  [lines omitted from the excerpt]`. The parser gives the same
result on each excerpt as on the whole file (checked 2026-10-23). Used by `tests/spectrum/test_gaussian.py`
(Azimuth, 2026-10-23, Jane).

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
