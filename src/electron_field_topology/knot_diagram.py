"""Independent regular-projection polygon invariants; no complete knot identifier."""
import numpy as np
from .linking import closed_curve, segment_separation

VIEWS = ((.37, .53, 1.), (1., -.41, .67), (-.71, 1., .29))


def _projection(points, normal):
    n = np.array(normal, dtype=float, copy=True)
    if n.shape != (3,) or not np.isfinite(n).all() or np.linalg.norm(n) == 0:
        raise ValueError('finite nonzero projection normal required')
    n /= np.linalg.norm(n)
    u = np.cross(n, np.eye(3)[np.argmin(abs(n))]); u /= np.linalg.norm(u)
    return np.asarray(points) @ np.stack((u, np.cross(n, u), n), axis=1)


def crossings(first, second=None, normal=VIEWS[0]):
    """Transverse segment intersections with over/under depth; reject irregular diagrams."""
    a, _ = closed_curve(first)
    same = second is None
    b = a if same else closed_curve(second)[0]
    if max(len(a), len(b)) > 513:
        raise ValueError('at most 512 segments per polygon')
    if segment_separation(a, a, True) < 1e-8 or segment_separation(b, b, True) < 1e-8:
        raise ValueError('self-intersecting/unresolved polygon')
    if not same and segment_separation(a, b) < 1e-8:
        raise ValueError('intersecting/unresolved link')
    a, b = _projection(a, normal), _projection(b, normal)
    if min(np.min(np.linalg.norm(np.diff(a[:, :2], axis=0), axis=1)),
           np.min(np.linalg.norm(np.diff(b[:, :2], axis=0), axis=1))) < 1e-12:
        raise ValueError('collapsed edge in projection')
    result = []; seen = []
    for i in range(len(a)-1):
        js = np.arange(i+1, len(b)-1) if same else np.arange(len(b)-1)
        if same: js = js[(js != i+1) & ~((i == 0) & (js == len(b)-2))]
        if not len(js): continue
        u = a[i+1, :2]-a[i, :2]; v = b[js+1, :2]-b[js, :2]; w = b[js, :2]-a[i, :2]
        det = u[0]*v[:, 1]-u[1]*v[:, 0]
        transverse = abs(det) > 1e-12*np.linalg.norm(u)*np.linalg.norm(v, axis=1)
        # Collinear projected segments whose bounding boxes overlap are not a regular diagram.
        boxes = np.all(np.maximum(np.minimum(a[i, :2], a[i+1, :2]), np.minimum(b[js, :2], b[js+1, :2])) <=
                       np.minimum(np.maximum(a[i, :2], a[i+1, :2]), np.maximum(b[js, :2], b[js+1, :2]))+1e-12, axis=1)
        if np.any(~transverse & boxes): raise ValueError('degenerate parallel projection')
        s = np.divide(w[:, 0]*v[:, 1]-w[:, 1]*v[:, 0], det, out=np.full(len(js), np.inf), where=transverse)
        t = np.divide(w[:, 0]*u[1]-w[:, 1]*u[0], det, out=np.full(len(js), np.inf), where=transverse)
        for k in np.where((s >= -1e-10) & (s <= 1+1e-10) & (t >= -1e-10) & (t <= 1+1e-10))[0]:
            if min(s[k], 1-s[k], t[k], 1-t[k]) < 1e-7:
                raise ValueError('projection crossing at/near a vertex')
            j = int(js[k]); xy = a[i, :2]+s[k]*u
            height = a[i, 2]+s[k]*(a[i+1, 2]-a[i, 2])-(b[j, 2]+t[k]*(b[j+1, 2]-b[j, 2]))
            if abs(height) < 1e-8 or any(np.linalg.norm(xy-p) < 1e-7 for p in seen):
                raise ValueError('unresolved depth or multiple projection crossing')
            seen.append(xy)
            result.append({'first': float(i+s[k]), 'second': float(j+t[k]),
                           'first_over': bool(height > 0), 'sign': int(np.sign(det[k]*height))})
            if len(result) > 64: raise ValueError('crossing budget exceeded')
    return result


def _determinant(matrix):
    """Fraction-free Bareiss elimination with exact integer divisibility controls."""
    a = [[int(x) for x in row] for row in matrix]; n = len(a)
    if not n: return 1
    previous = 1; sign = 1
    for k in range(n-1):
        pivot = next((i for i in range(k, n) if a[i][k]), None)
        if pivot is None: return 0
        if pivot != k: a[k], a[pivot] = a[pivot], a[k]; sign *= -1
        value = a[k][k]
        for i in range(k+1, n):
            for j in range(k+1, n):
                numerator = a[i][j]*value-a[i][k]*a[k][j]
                if numerator % previous: raise ValueError('non-exact integer elimination')
                a[i][j] = numerator//previous
            a[i][k] = 0
        previous = value
    return sign*a[-1][-1]


def knot_determinant(points, normal=VIEWS[0]):
    """Fox relation 2*over-under_in-under_out=0, t=-1; not a unique knot name."""
    diagram = crossings(points, normal=normal); n = len(diagram)
    if not n: return {'determinant': 1, 'crossings': 0, 'knot_type': 'not_identified'}
    under = sorted((d['second'] if d['first_over'] else d['first']) for d in diagram)
    matrix = np.zeros((n, n), dtype=int)
    for i, d in enumerate(diagram):
        low, high = (d['second'], d['first']) if d['first_over'] else (d['first'], d['second'])
        j = under.index(low); over = int(np.searchsorted(under, high, side='right') % n)
        matrix[i, over] += 2; matrix[i, j] -= 1; matrix[i, (j+1) % n] -= 1
    # Rows need not be alternating-diagram rows; compare two independent cofactors.
    first = abs(_determinant(matrix[:-1, :-1]))
    second = abs(_determinant(matrix[1:, 1:]))
    if first != second or first == 0 or first % 2 == 0:
        raise ValueError('inconsistent Fox determinant cofactors')
    return {'determinant': first, 'crossings': n, 'knot_type': 'not_identified',
            'nontrivial_polygon_detected': first > 1}


def diagram_link(first, second, normal=VIEWS[0]):
    diagram = crossings(first, second, normal)
    total = sum(d['sign'] for d in diagram)
    if total % 2: raise ValueError('odd signed link crossing sum')
    return {'linking_number': total//2, 'crossings': len(diagram)}


def invariant_gate(points):
    rows = []
    for view in VIEWS:
        try: rows.append({'normal': list(view), 'status': 'regular', **knot_determinant(points, view)})
        except ValueError as error: rows.append({'normal': list(view), 'status': 'unresolved_projection', 'reason': str(error)})
    valid = [r['determinant'] for r in rows if r['status'] == 'regular']
    agreed = len(valid) >= 2 and len(set(valid)) == 1
    return {'projections': rows, 'agreed': agreed, 'determinant': valid[0] if agreed else None,
            'knot_type': 'not_identified', 'scope': 'finite polygon invariant, not a continuum isotopy certificate'}
