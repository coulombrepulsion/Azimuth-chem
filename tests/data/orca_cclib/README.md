# Real ORCA outputs for tests (from cclib)

Source: the cclib test data, https://github.com/cclib/cclib, folder `data/ORCA`, commit
`76df867532961117427cb3e0877913db3233f83f` (2026-10-07), downloaded 2026-10-23.

| File here | Original | ORCA | Content |
|---|---|---|---|
| `water_mp2_orca5.0.out` | `basicORCA5.0/water_mp2.out` (whole file) | 5.0.0 | water, MP2, polar dipole |
| `dvb_sp_un_dft_orca6.0.out` | `basicORCA6.0/dvb_sp_un_dft.out` (excerpt) | 6.0.0 | divinylbenzene cation, UKS: charges, spins, Hirshfeld, Mayer |
| `dvb_raman_orca6.0.out` | `basicORCA6.0/dvb_raman.out` (excerpt) | 6.0.0 | Cartesian gradient of the one geometry |
| `dvb_gopt_orca6.0.out` | `basicORCA6.0/dvb_gopt.out` (excerpt) | 6.0.0 | optimization: properties of the final geometry |
| `dvb_scan_relaxed_orca6.0.out` | `basicORCA6.0/dvb_scan_relaxed.out` (excerpt) | 6.0 | relaxed dihedral scan, 12 points |
| `dvb_scan_unrelaxed_orca5.0.out` | `basicORCA5.0/dvb_scan_unrelaxed.out` (excerpt) | 5.0 | rigid scan of a Z-matrix parameter |
| `dvb_td_orca6.0.out` | `basicORCA6.0/dvb_td.out` (excerpt) | 6.0.0 | TD-DFT, 5 singlets and 5 triplets: absorption table |
| `dvb_td_orca5.0.out` | `basicORCA5.0/dvb_td.out` (excerpt) | 5.0.0 | TD-DFT, the same states, ORCA 5 layout with spin-forbidden rows |
| `dvb_rocis_orca5.0.out` | `basicORCA5.0/dvb_rocis.out` (excerpt) | 5.0.0 | ROCIS, two-index absorption rows |
| `dvb_nmr_orca6.0.out` | `basicORCA6.0/dvb_nmr.out` (excerpt) | 6.0.1 | NMR shieldings of divinylbenzene |

Excerpts keep, unchanged and in order, the lines from 2 before to 30–70 after every header of a
geometry, population, Mayer, dipole and gradient block (and the version and termination lines);
omitted runs of lines are marked `...  [lines omitted from the excerpt]`.

Used by `tests/compass/test_orca_properties.py`, `tests/spectrum/test_orca_scan.py` and `tests/spectrum/test_orca_spectra.py` (Azimuth, 2026-10-23, Jane). The scan
excerpts keep the scan step headers, every coordinate block, the energy lines and the final tables; the
spectra excerpts keep the final geometry, the absorption tables and the shielding summary unchanged.

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
