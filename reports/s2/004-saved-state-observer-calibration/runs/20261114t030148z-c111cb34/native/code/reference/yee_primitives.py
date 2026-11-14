"""Unchanged Yee primitives from submitted Maxwell evidence; Apache-2.0."""
import numpy as np
def derivative(a, h, axis, forward):
    return (np.roll(a, -1, axis) - a) / h if forward else (a - np.roll(a, 1, axis)) / h

def curl(f, h, forward):
    return np.stack([derivative(f[(i + 2) % 3], h, (i + 1) % 3, forward) - derivative(f[(i + 1) % 3], h, (i + 2) % 3, forward) for i in range(3)])

def points(n, length, offset, axis, phase):
    h = length / n
    axes = [-length / 2 + (np.arange(n) + offset[i]) * h for i in range(3)]
    p = np.stack(np.meshgrid(*axes, indexing='ij'), -1)
    p[..., axis] += phase * h
    return p
