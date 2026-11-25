"""Heavy elements: relativistic effects of a hydrogen-like 1s electron and effective core potentials of def2.

HEADER
    Model of the page "Тяжёлые элементы: релятивизм и псевдопотенциалы" (web/<lang>/relativity.html),
    Atlas 2026-10-25. Wilkinson convention, sections 1-8.

§1 THEORY
    In atomic units the speed of light is c = 1/α = 137.035999084 (CODATA 2018). A hydrogen-like 1s
    electron of nuclear charge Z has the mean speed Z (Bohr model), so v/c = Zα; its mass grows by
    γ = 1/sqrt(1 − (Zα)²) and the orbital radius (∝ 1/m) shrinks by the factor sqrt(1 − (Zα)²).
    The energies (hartree):
        non-relativistic (Schrödinger) E = −Z²/2,
        Dirac, 1s1/2 E = c² (sqrt(1 − (Zα)²) − 1),
    both without the rest energy. For gold (Z = 79) the 1s electron moves at 0.58 c, the radius shrinks
    by 18 % and the 1s level is 10 % deeper. Valence s and p1/2 shells, which penetrate to the nucleus,
    contract and are stabilised too (direct effect); d and f shells, screened better, expand (indirect).
    An effective core potential (ECP) replaces the inner electrons by a potential fitted to relativistic
    atomic calculations: the valence electrons feel the scalar relativistic effects without an all-electron
    relativistic Hamiltonian (DKH2, ZORA, X2C) and its special basis sets. The def2 basis sets use the
    Stuttgart–Cologne ECPs: 28 core electrons for Rb–Xe (Z 37–54), 46 for Cs–La (55–57), 60 for Hf–Rn
    (72–86); the lighter elements up to Kr are all-electron.

§2 ALGORITHM
    Direct formulas; ECP core size by the ranges above (the lanthanides Ce–Lu are not covered: None).

§3 APPLICATIONS
    Endpoints rel.atom, rel.curve, rel.ecp.

§4 SPECIFICATION
    hydrogenic(Z) -> {"v": Zα, "gamma", "r_ratio", "E_nr", "E_dirac", "E_ratio"} (1 <= Z <= 137).
    curve() -> [[Z, r_ratio, E_ratio]] for Z = 1..118.
    ecp(Z) -> {"Z", "core": electrons in the ECP or 0, "valence": Z − core, "kind": "all-electron" | "ECP" | None}.

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    Pure Python; (Zα)² < 1 is required (Z <= 137).
§7 TEST CASES (tests/test_atlas_new_topics.py)
    Z = 1: E_dirac = −0.5000067 (fine-structure shift α²/8 relative); Z = 79: v = 0.5765, r_ratio = 0.817;
    E_dirac / E_nr → 1 for small Z; ECP of Au = 60, of I = 28, of Cs = 46, of Br = 0.
§8 ERROR ANALYSIS
    sqrt(1 − x) − 1 for small x is evaluated as −x / (1 + sqrt(1 − x)) to avoid cancellation; the
    hydrogen-like model (one electron, point nucleus) is the dominating approximation.
"""
from __future__ import annotations

import math

C = 137.035999084


def hydrogenic(Z: int) -> dict:
    if not 1 <= Z <= 137:
        raise ValueError("Z: 1..137")
    x = (Z / C) ** 2
    root = math.sqrt(1 - x)
    E_nr = -Z * Z / 2
    E_d = C * C * (-x / (1 + root))
    return {"v": Z / C, "gamma": 1 / root, "r_ratio": root, "E_nr": E_nr, "E_dirac": E_d, "E_ratio": E_d / E_nr}


def curve() -> list:
    return [[Z, hydrogenic(Z)["r_ratio"], hydrogenic(Z)["E_ratio"]] for Z in range(1, 119)]


def ecp(Z: int) -> dict:
    if not 1 <= Z <= 118:
        raise ValueError("Z: 1..118")
    if Z <= 36:
        core, kind = 0, "all-electron"
    elif Z <= 54:
        core, kind = 28, "ECP"
    elif Z <= 57:
        core, kind = 46, "ECP"
    elif 72 <= Z <= 86:
        core, kind = 60, "ECP"
    else:
        core, kind = None, None
    return {"Z": Z, "core": core, "valence": None if core is None else Z - core, "kind": kind}
