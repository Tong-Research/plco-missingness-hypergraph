"""The one place that defines the MIMIC-IV dev / holdout split for method development after M1.

M1 (prereg/MIMIC.md) used the full matrix and is closed. Any idea developed afterwards on MIMIC-IV
is explored on the DEV half only; the HOLDOUT half is reserved for that idea's pre-registered test
and must not be loaded by exploration code. The split is a deterministic hash of the record index,
so it is identical on every machine and cannot drift.
"""
from __future__ import annotations
import hashlib, numpy as np

def dev_mask(n: int) -> np.ndarray:
    return np.array([int(hashlib.sha1(f"mimic4-{i}".encode()).hexdigest(), 16) % 2 == 0 for i in range(n)])

def split(X, y):
    m = dev_mask(len(X)); return (X[m], y[m]), (X[~m], y[~m])

if __name__ == "__main__":
    m = dev_mask(66989); print(f"dev {int(m.sum()):,} / holdout {int((~m).sum()):,}; first dev indices {np.flatnonzero(m)[:6].tolist()}")
