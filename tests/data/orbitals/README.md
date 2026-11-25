# Orbital test data (from cclib)

Source: the cclib test data, https://github.com/cclib/cclib, commit
`76df867532961117427cb3e0877913db3233f83f` (2026-10-07), downloaded 2026-10-23.

| File here | Original | Program | Content |
|---|---|---|---|
| `dvb_sp_dft_orca6.0.out` | `data/ORCA/basicORCA6.0/dvb_sp_dft.out` (excerpt) | ORCA 6.0.0 | divinylbenzene, RKS B3LYP/STO-3G: basis, overlap matrix, orbitals, Mulliken charges |
| `dvb_sp_un_dft_orca6.0.out` | `data/ORCA/basicORCA6.0/dvb_sp_un_dft.out` (excerpt) | ORCA 6.0.0 | its cation, UKS: alpha and beta orbitals, Mulliken charges and spins |
| `water_mp2_g16.fchk` | `data/FChk/basicGaussian16/water_mp2.fchk` (whole file) | Gaussian 16 | water MP2/STO-3G: SCF orbitals, SCF and MP2 densities |
| `Mo4OCl4-sp_g16.fchk` | `data/FChk/basicGaussian16/Mo4OCl4-sp.fchk` (whole file) | Gaussian 16 | [MoOCl4]2-, B3LYP with an ECP on Mo, spherical d |
| `molden5.7_water_mp2.molden` | `test/io/data/molden5.7_water_mp2.molden` (whole file) | Molden 5.7 from GAMESS-US 2018 | water, STO-3G |
| `molden5.7_dvb_un_sp.molden` | `test/io/data/molden5.7_dvb_un_sp.molden` (whole file) | Molden 5.7 from GAMESS-US 2018 | divinylbenzene cation, UHF orbitals |

The ORCA excerpts keep, unchanged and in order, the version and termination lines and the blocks
CARTESIAN COORDINATES (ANGSTROEM), BASIS SET IN INPUT FORMAT (and the first lines of the auxiliary
basis), OVERLAP MATRIX, MOLECULAR ORBITALS and MULLIKEN ATOMIC CHARGES; omitted runs of lines are
marked `...  [lines omitted from the excerpt]`. Numbers printed by the programs and used as oracles in
`tests/spectrum/test_orbitals.py` (Azimuth, 2026-10-23, Jane): ORCA's overlap matrix and Mulliken charges (in the
excerpts), Gaussian 16's Mulliken charges of Mo4OCl4 (`data/Gaussian/basicGaussian16/Mo4OCl4-sp.log`)
and the GAMESS-US 2018 Mulliken charges of water (`data/GAMESS/basicGAMESS-US2018/water_mp2.out`),
copied by hand into the test.

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
