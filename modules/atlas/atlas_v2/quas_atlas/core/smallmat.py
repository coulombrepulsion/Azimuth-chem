"""Dense linear algebra for small matrices (n <= ~20) in pure Python.

HEADER
    Port of the matrix helpers shared by the Atlas v1.0 pages
    (``mat``, ``mmul``, ``tps``, ``eigSym``, ``gauss`` in ``h2.html``,
    ``scf.html``, ``density.html``).  Documentation: Wilkinson convention,
    sections 1-8.  Matrices are ``list[list[float]]`` (row-major), exactly as
    in the JavaScript original, so that the order of floating-point
    operations -- and therefore the rounding -- is preserved.

§1 THEORY
    * Product C = A B, (C)_ij = sum_k A_ik B_kj, accumulated left to right in
      k (the JavaScript ``reduce`` order).
    * Symmetric eigenproblem A V = V diag(w) by the cyclic Jacobi method:
      a sequence of plane rotations J(p,q,theta) chosen so that the rotated
      element (J^T A J)_pq vanishes.  With
          theta = (a_qq - a_pp) / (2 a_pq),
          t = sign(theta) / (|theta| + sqrt(theta^2 + 1)),   (|t| <= 1)
          c = 1 / sqrt(t^2 + 1),  s = t c,
      the rotation annihilates a_pq; choosing the smaller root |t| <= 1 keeps
      the rotation angle <= pi/4, which is what makes the cyclic method
      converge quadratically (Wilkinson & Reinsch, Handbook II/1, contribution
      by Rutishauser).  Jacobi is chosen over QR because n is tiny, the code
      is short, and it yields eigenvectors that are orthonormal to working
      precision even for clustered eigenvalues.
    * Linear system A x = b by Gauss-Jordan elimination with partial pivoting
      (used by DIIS, whose B matrix is small and possibly nearly singular).

§2 ALGORITHM
    eig_sym(A):
      V := I;  repeat at most 50 sweeps:
        off := sum_{p<q} a_pq^2;  stop if off < 1e-30;
        for p < q (row-cyclic order): if |a_pq| >= 1e-300 apply J(p,q):
          columns p,q of A, then rows p,q of A, then columns p,q of V.
      Sort eigenvalues ascending (stable), permute the columns of V alike.
    gauss(A, b):
      for each column c: pivot p = argmax_{r>=c} |a_rc| (first maximum);
      if |a_pc| < 1e-14 return None (numerically singular);
      swap rows, eliminate column c from every other row (Gauss-Jordan);
      x_i = a_i,n / a_ii.

§3 APPLICATIONS
    * Loewdin orthogonalisation X = S^{-1/2} = V diag(w^{-1/2}) V^T
      (sto3g.x_matrix) -- needs eig_sym of the overlap matrix.
    * Roothaan equations F' C' = C' eps in the orthogonal basis
      (sto3g.solve_fc).
    * DIIS extrapolation coefficients (sto3g.diis_extrap) -- gauss.

§4 SPECIFICATION
    mat(n, f)        -> n x n list, element (i,j) = f(i,j).
    mmul(A, B)       -> A B; A is m x k, B is k x n (here always square);
                        inputs not modified.
    tps(A)           -> A^T (square).
    eig_sym(A0)      -> (w, V): w list[float] ascending, V n x n with
                        eigenvectors in columns.  A0 symmetric, not
                        modified.  Reference: ``eigSym`` of the v1.0 pages.
    gauss(A0, b0)    -> list[float] solution, or None if a pivot is below
                        1e-14 in absolute value.  Inputs not modified.
    Reference implementation: Atlas v1.0 (reference/original_v1.0/
    h2.html), JavaScript run in Chromium (V8).
    Equivalence tier: ``bitwise`` for mat/mmul/tps/gauss (only +, -, *, /,
    correctly rounded in IEEE 754 in both languages, same order);
    ``bitwise`` expected for eig_sym as well (sqrt is correctly rounded in
    both; no libm transcendental is involved).  Verified in
    tests/test_smallmat.py against values computed by the original code.

§5 PROCEDURES -- below.

§6 IMPLEMENTATION NOTES
    * Row-major nested lists; no aliasing: every function returns new lists.
    * ``sign(theta or 1)``: JavaScript ``Math.sign(th||1)`` maps theta = 0
      (and -0) to +1; reproduced literally.
    * The 1e-300 guard skips exactly-zero (or subnormal-tiny) off-diagonal
      elements, avoiding 0/0 in theta.
    * The sort is stable in both languages, so equal eigenvalues keep their
      index order -- this matters for degenerate orbitals.

§7 TEST CASES (tests/test_smallmat.py)
    * eig_sym on [[2,1],[1,2]]: w = [1, 3] to 4u|w| (observed
      0.9999999999999998: the rotation uses fl(1/sqrt 2)); V V^T = I to 4u.
    * Invariants for random symmetric 6x6: ||A V - V diag(w)||_F <= bound §8.
    * gauss on a 3x3 integer system with exact rational solution
      (fractions.Fraction oracle).
    * Bitwise equality with the original JavaScript on the matrices of the
      H2 page (fixtures/js_reference/h2.json).

§8 ERROR ANALYSIS
    * mmul: |fl(C) - C| <= gamma_n |A||B|, gamma_n = n u/(1 - n u),
      u = 2^-53 (Higham, 2nd ed., §3.5).
    * Jacobi: each rotation is backward stable; after convergence
      (off < 1e-30, i.e. off-diagonal norm < 1e-15) the computed (w, V)
      satisfy ||A V - V diag(w)||_F <= c n^2 u ||A||_F with modest c
      (Demmel & Veselic 1992).  Tests use the bound 50 n^2 u ||A||_F;
      c = 50 is a generous constant (observed c < 2 for n <= 6), and
      off < 1e-30 adds at most 1e-15 to the residual.
    * gauss: Gauss-Jordan with partial pivoting is backward stable for these
      sizes; the residual ||A x - b|| <= n^2 u ||A|| ||x|| (n <= 4 in DIIS).
"""
from __future__ import annotations

import math
from typing import Callable

Matrix = list[list[float]]


def mat(n: int, f: Callable[[int, int], float]) -> Matrix:
    """n x n matrix with elements f(i, j)."""
    return [[f(i, j) for j in range(n)] for i in range(n)]


def mmul(A: Matrix, B: Matrix) -> Matrix:
    """Matrix product; (AB)_ij accumulated over k from 0 upwards."""
    n = len(A)
    m = len(B[0])
    out = []
    for i in range(n):
        row = []
        Ai = A[i]
        for j in range(m):
            s = 0.0
            for k in range(len(Ai)):
                s = s + Ai[k] * B[k][j]
            row.append(s)
        out.append(row)
    return out


def tps(A: Matrix) -> Matrix:
    """Transpose of a square matrix."""
    n = len(A)
    return [[A[j][i] for j in range(n)] for i in range(n)]


def _sign(x: float) -> float:
    """JavaScript Math.sign for finite non-zero x (zero handled by caller)."""
    return 1.0 if x > 0 else -1.0


def eig_sym(A0: Matrix) -> tuple[list[float], Matrix]:
    """Cyclic Jacobi eigen-decomposition of a symmetric matrix (see §2)."""
    n = len(A0)
    A = [list(r) for r in A0]
    V = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for _sweep in range(50):
        # off(A) = sum of squared strictly-upper elements; convergence test
        off = 0.0
        for p in range(n):
            for q in range(p + 1, n):
                off = off + A[p][q] * A[p][q]  # JS A[p][q]**2 == x*x
        if off < 1e-30:
            break
        for p in range(n):
            for q in range(p + 1, n):
                if abs(A[p][q]) < 1e-300:
                    continue
                # rotation angle that annihilates a_pq; smaller root |t| <= 1
                th = (A[q][q] - A[p][p]) / (2 * A[p][q])
                sg = _sign(th) if th != 0 else 1.0
                t = sg / (abs(th) + math.sqrt(th * th + 1))
                c = 1 / math.sqrt(t * t + 1)
                s = t * c
                # A := A J  (columns p, q)
                for k in range(n):
                    a = A[k][p]
                    b = A[k][q]
                    A[k][p] = c * a - s * b
                    A[k][q] = s * a + c * b
                # A := J^T A  (rows p, q)
                for k in range(n):
                    a = A[p][k]
                    b = A[q][k]
                    A[p][k] = c * a - s * b
                    A[q][k] = s * a + c * b
                # accumulate eigenvectors V := V J
                for k in range(n):
                    a = V[k][p]
                    b = V[k][q]
                    V[k][p] = c * a - s * b
                    V[k][q] = s * a + c * b
    # ascending eigenvalues, stable order for ties
    idx = sorted(range(n), key=lambda i: A[i][i])
    w = [A[i][i] for i in idx]
    Vs = [[V[i][idx[j]] for j in range(n)] for i in range(n)]
    return w, Vs


def gauss(A0: Matrix, b0: list[float]) -> list[float] | None:
    """Gauss-Jordan elimination with partial pivoting; None if singular."""
    n = len(b0)
    A = [list(r) + [b0[i]] for i, r in enumerate(A0)]
    for c in range(n):
        # partial pivoting: first row with the largest |a_rc|
        p = c
        for r in range(c + 1, n):
            if abs(A[r][c]) > abs(A[p][c]):
                p = r
        if abs(A[p][c]) < 1e-14:
            return None
        A[c], A[p] = A[p], A[c]
        # eliminate column c from all other rows
        for r in range(n):
            if r == c:
                continue
            f = A[r][c] / A[c][c]
            for k in range(c, n + 1):
                A[r][k] = A[r][k] - f * A[c][k]
    return [A[i][n] / A[i][i] for i in range(n)]
