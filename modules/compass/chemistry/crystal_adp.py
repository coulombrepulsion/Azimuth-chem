"""Atomic displacement ellipsoids of a crystal.

§1 THEORY
    A CIF gives the anisotropic displacement of an atom as U^ij (A^2) in the basis of the reciprocal cell
    (_atom_site_aniso_U_11 … _U_23; B^ij = 8 pi^2 U^ij): the Cartesian tensor is
        U_cart = A N U N A^T, A = (a b c) the cell vectors as columns, N = diag(a*, b*, c*) (Grosse-Kunstleve & Adams,
    J. Appl. Cryst. 2002, 35, 477, eq. 3). A copy made by the symmetry operation W (fractional) has U'_cart = R U_cart
    R^T with R = A W A^-1, the operation in Cartesian coordinates. An isotropic atom has U_cart = U_iso I. U_eq =
    tr(U_cart) / 3 (Fischer & Tillmanns 1988) — the number CIF files print as U_iso_or_equiv. The probability that the
    atom is inside the ellipsoid x^T U^-1 x = k^2 is that of chi-square with 3 degrees of freedom below k^2: k = 1.5382
    for 50 % (the usual ORTEP drawing), 2.0004 for 70 %. On the screen the ellipsoid of a parallel projection is the
    ellipse of the 2 x 2 block of B U B^T, B the rows of the screen x, y, z in model coordinates: semi-axes k
    sqrt(lambda), along the eigenvectors.
§2 ALGORITHM
    tensors(crystal): for every site and every operation (as crystal.unit_cell) the wrapped position and U'_cart.
    for_atoms(crystal, positions): each position (A, the model of the cell at the origin) to fractional coordinates;
    the copy within MERGE (minimum image) gives its tensor, else None. ellipse(u, basis, k) -> (a, b, angle in degrees
    from the screen x towards y) in A.
§3 APPLICATIONS
    modules/compass/actions/crystal_actions.py and the viewer (viewer_drawing.draw_ellipsoids).
§4 SPECIFICATION
    u_cart(cell, u6) -> 3 x 3 list; tensors(crystal) -> [(frac, U_cart or None)]; for_atoms(crystal, positions) -> list
    of U_cart or None; ellipse(u, basis, k=P50) -> (a, b, angle); u_eq(u) -> float.
§5 PROCEDURES - below.
§6 NOTES
    Atoms with neither U^ij nor U_iso (hydrogens placed by riding models often have only U_iso) get None: drawn as
    usual. Non-positive-definite tensors (a refinement gone wrong, "NPD") give None too.
§7 TESTS
    tests/compass/test_crystal_adp.py.
§8' ROBUSTNESS / ERRORS
    None for any tensor that cannot be drawn; no exceptions for missing data.
"""

from math import atan2, degrees, sqrt

from modules.compass.chemistry import crystal as cr

P50 = 1.5382
P70 = 2.0004


def _matrices(cell):
    import numpy as np

    rows = np.array(cell.vectors(), dtype=float)  # a, b, c as rows
    a = rows.T  # as columns
    star = np.linalg.inv(rows).T  # rows a*, b*, c* (no 2 pi)
    n = np.diag(np.linalg.norm(star, axis=1))
    return a, n


def u_cart(cell, u6):
    import numpy as np

    u11, u22, u33, u12, u13, u23 = u6
    u = np.array([[u11, u12, u13], [u12, u22, u23], [u13, u23, u33]], dtype=float)
    a, n = _matrices(cell)
    return (a @ n @ u @ n @ a.T).tolist()


def _positive(u):
    import numpy as np

    try:
        return bool(np.all(np.linalg.eigvalsh(np.array(u, dtype=float)) > 1e-8))
    except np.linalg.LinAlgError:
        return False


def tensors(crystal):
    import numpy as np

    a, _ = _matrices(crystal.cell)
    inverse = np.linalg.inv(a)
    found = []
    for site in crystal.sites:
        if site.u:
            base = np.array(u_cart(crystal.cell, site.u))
        elif site.u_iso > 0:
            base = np.eye(3) * site.u_iso
        else:
            base = None
        mine = []
        for op in crystal.operations:
            f = cr._wrap(cr._apply(op, (site.x, site.y, site.z)))
            if any(cr._separation(crystal.cell, f, g) <= cr.MERGE for g in mine):
                continue
            mine.append(f)
            if base is None:
                found.append((f, None))
                continue
            r = a @ np.array(op[0], dtype=float) @ inverse
            u = r @ base @ r.T
            found.append((f, u.tolist() if _positive(u) else None))
    return found


def for_atoms(crystal, positions):
    import numpy as np

    rows = np.array(crystal.cell.vectors(), dtype=float)
    inverse = np.linalg.inv(rows)
    table = tensors(crystal)
    if not table or not len(positions):
        return [None] * len(positions)
    known = np.array([g for g, _ in table], dtype=float)
    out = []
    for p in positions:
        f = np.array(p, dtype=float) @ inverse
        d = known - f
        d -= np.round(d)  # the nearest image: exact for the short distances looked for (MERGE)
        r = np.linalg.norm(d @ rows, axis=1)
        k = int(np.argmin(r))
        out.append(table[k][1] if r[k] <= cr.MERGE else None)
    return out


def u_eq(u):
    return (u[0][0] + u[1][1] + u[2][2]) / 3


def ellipse(u, basis, k=P50):
    """(semi-axis a, semi-axis b, angle of a from the screen x towards y, degrees), A, of the projected ellipsoid."""
    import numpy as np

    b = np.array(basis, dtype=float)  # rows: screen x, y, z in model coordinates
    v = b @ np.array(u, dtype=float) @ b.T
    block = v[:2, :2]
    values, vectors = np.linalg.eigh(block)
    order = np.argsort(values)[::-1]
    values, vectors = values[order], vectors[:, order]
    major = vectors[:, 0]
    return (k * sqrt(max(values[0], 0.0)), k * sqrt(max(values[1], 0.0)), degrees(atan2(major[1], major[0])))
