"""Koopmans' theorem against ΔSCF and full CI for H2 and HeH+ in the STO-3G basis (Atlas).

HEADER
    Model of the panel "Орбитальные энергии и теорема Купманса" of the page "SCF" (web/<lang>/scf.html).
    Machinery in core.sto3g and core.scf. Wilkinson convention, sections 1-8.

§1 THEORY
    Koopmans: removing an electron from the occupied canonical orbital φ_i without letting the other orbitals
    change costs IP ≈ −ε_i; adding one to a virtual φ_a releases EA ≈ −ε_a. The ΔSCF ionisation energy
    E(M⁺) − E(M) lets the orbitals relax (lowers the IP); electron correlation, absent in Hartree–Fock and
    larger in the molecule with more electrons, raises it. For molecules the two errors partly cancel, so
    −ε_HOMO is often a fair estimate of the vertical IP; EA from −ε_LUMO is unreliable.
    Here: a two-electron molecule in two basis functions. The cation has one electron, so its energy is the
    lowest root of h C = S C ε (exact in the basis); the neutral is RHF (|σ1²|) or full CI over |σ1²|,
    the singly excited singlet and |σ2²| (in the MO basis, (ij|kl) chemists' notation):
        H00 = 2h11 + (11|11), H22 = 2h22 + (22|22), H11 = h11 + h22 + (11|22) + (12|12),
        H02 = (12|12), H01 = √2 (h12 + (11|12)) (= 0 at convergence, Brillouin), H12 = √2 (h12 + (12|22)).
    Vertical IPs at the given R: Koopmans −ε1, ΔSCF E(M⁺) − E_RHF, "exact in the basis" E(M⁺) − E_FCI.

§2 ALGORITHM
    RHF by plain iterations from P = 0 to rmsd < 1e-12 (as core.scf.trajectory); MO integrals by the four
    index transformation; the 3x3 CI by core.smallmat.eig_sym.

§3 APPLICATIONS
    Endpoint scf.koopmans.

§4 SPECIFICATION
    koopmans(mol, R, za, zb) -> {"eps": [ε1, ε2], "E_rhf", "E_fci", "E_cat", "ip_koop", "ip_dscf", "ip_fci",
    "ea_koop", "relax": ip_koop − ip_dscf, "corr": ip_fci − ip_dscf} (hartree).

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    1 Eh = 27.211386 eV (CODATA 2018), applied by the page.
§7 TEST CASES (tests/test_atlas_course1.py)
    H2, R = 1.4 bohr: ε1 = −0.578 Eh (Szabo–Ostlund table 3.x: −0.578), E_RHF = −1.1167, E_FCI = −1.1373
    (Szabo–Ostlund: −1.1373); ΔSCF IP < Koopmans IP < FCI IP; H01 = 0 at convergence.
§8 ERROR ANALYSIS
    2x2 and 3x3 symmetric problems, relative errors ~1e-14; the minimal basis dominates (STO-3G IP of H2
    is about 0.4 eV below experiment).
"""
from __future__ import annotations

import math

from .scf import atoms, check
from .smallmat import eig_sym
from .sto3g import build_f, density_from, energy, integrals, rmsd, solve_fc, x_matrix


def koopmans(mol: str, R: float, za: float, zb: float) -> dict:
    check(mol, R, za, zb)
    I = integrals(atoms(mol, R, za, zb))
    X = x_matrix(I["S"])
    P = [[0.0, 0.0], [0.0, 0.0]]
    for _ in range(500):
        F = build_f(I, P)["F"]
        sol = solve_fc(I, F, X)
        Pn = density_from(sol["C"], 1)
        d = rmsd(Pn, P)
        P = Pn
        if d < 1e-12:
            break
    F = build_f(I, P)["F"]
    sol = solve_fc(I, F, X)
    eps, C = sol["eps"], sol["C"]
    Vnn = I["Vnn"]
    E_rhf = energy(I, P) + Vnn
    E_cat = solve_fc(I, I["H"], X)["eps"][0] + Vnn
    n = 2
    h = [[sum(C[m][i] * I["H"][m][v] * C[v][j] for m in range(n) for v in range(n)) for j in range(n)] for i in range(n)]

    def g(i, j, k, l):  # noqa: E741
        return sum(C[a][i] * C[b][j] * C[c][k] * C[d][l] * I["ERI"][a][b][c][d]
                   for a in range(n) for b in range(n) for c in range(n) for d in range(n))

    r2 = math.sqrt(2)
    H00 = 2 * h[0][0] + g(0, 0, 0, 0)
    H22 = 2 * h[1][1] + g(1, 1, 1, 1)
    H11 = h[0][0] + h[1][1] + g(0, 0, 1, 1) + g(0, 1, 0, 1)
    H02 = g(0, 1, 0, 1)
    H01 = r2 * (h[0][1] + g(0, 0, 0, 1))
    H12 = r2 * (h[0][1] + g(0, 1, 1, 1))
    w, _ = eig_sym([[H00, H01, H02], [H01, H11, H12], [H02, H12, H22]])
    E_fci = min(w) + Vnn
    ip_k, ip_d, ip_f = -eps[0], E_cat - E_rhf, E_cat - E_fci
    return {"eps": list(eps), "E_rhf": E_rhf, "E_fci": E_fci, "E_cat": E_cat, "ip_koop": ip_k, "ip_dscf": ip_d,
            "ip_fci": ip_f, "ea_koop": -eps[1], "relax": ip_k - ip_d, "corr": ip_f - ip_d, "brillouin": H01}
