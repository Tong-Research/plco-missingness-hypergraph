"""Cross-architecture reproducibility: does a Linux number match a macOS one at this resolution?

Compares per-cell AUPRC from the same idea, cohort, seeds and folds run on different machines.
The measurement of record is SPINNER vs DUGONG, which share an identical software stack
(python 3.12.13, numpy 2.5.1, pandas 3.0.5, scikit-learn 1.9.0, scipy 1.18.0) and differ only in
architecture and BLAS -- arm64/Accelerate against x86_64/OpenBLAS. Pilot is reported for context
but confounds versions with hardware (python 3.12.14, pandas 3.0.3), so it is labelled as such.

Thresholds come from the pre-registration and are not adjustable here: the project's measured
reproducibility bound is 4.5e-05 (Result 130) and its reporting floor is 0.002.
"""
from __future__ import annotations

import itertools
import pathlib
import sys

import numpy as np
import pandas as pd
from scipy import stats

R = pathlib.Path(__file__).resolve().parent.parent / "results" / "xarch"
BOUND, FLOOR = 4.5e-5, 0.002
KEY = ["arm", "permuted", "seed", "fold"]


def load(name):
    d = pd.read_csv(R / f"{name}.csv")
    d["arm"] = d.arm.str.replace("idea_A4b_", "", regex=False)
    return d.set_index(KEY).auprc.sort_index()


def main() -> int:
    have = {n: load(n) for n in ("spinner", "dugong", "pilot") if (R / f"{n}.csv").exists()}
    print(f"  loaded: {', '.join(f'{k} ({len(v)} cells)' for k, v in have.items())}\n")

    worst = None
    for a, b in itertools.combinations(sorted(have), 2):
        s1, s2 = have[a].align(have[b], join="inner")
        d = (s1 - s2).to_numpy(float)
        med = float(np.median(d))
        mx = float(np.abs(d).max())
        nz = int((d != 0).sum())
        try:
            pv = float(stats.wilcoxon(d).pvalue) if nz else 1.0
        except ValueError:
            pv = 1.0
        record = {"spinner", "dugong"} == {a, b}
        tag = "  <-- MEASUREMENT OF RECORD (versions matched)" if record else \
              "      (versions differ; confounded)"
        print(f"  {a:8s} vs {b:8s}  n={len(d)}  median {med:+.3e}  max|d| {mx:.3e}  "
              f"cells differing {nz}/{len(d)}  p={pv:.3g}")
        print(f"  {'':8s}    {'':8s}{tag}")
        if record:
            worst = (med, mx, pv, len(d), nz)
            # per-arm, because a gap concentrated in one arm means something different
            print()
            for arm in sorted(set(i[0] for i in s1.index)):
                m = [i for i in s1.index if i[0] == arm]
                dd = (s1.loc[m] - s2.loc[m]).to_numpy(float)
                print(f"  {'':4s}{arm:26s} median {np.median(dd):+.3e}  "
                      f"max|d| {np.abs(dd).max():.3e}  differing {int((dd != 0).sum())}/{len(dd)}")
        print()

    if worst is None:
        print("  spinner and dugong not both present -- no measurement of record")
        return 1
    med, mx, pv, n, nz = worst
    print("  " + "=" * 74)
    print(f"  VERDICT  max single-cell |delta| = {mx:.3e}")
    if mx <= BOUND:
        v = (f"within the measured {BOUND:g} bound -- cross-architecture is already covered; "
             "mix freely")
    elif mx < FLOOR:
        v = (f"exceeds the {BOUND:g} bound but is below the {FLOOR:g} floor -- restate the bound "
             "to the measured value and pin whole jobs to one machine")
    else:
        v = (f"at or above the {FLOOR:g} floor -- Linux machines must not contribute numbers "
             "to this article")
    print(f"           {v}")
    print(f"  median   {med:+.3e} (p={pv:.3g}) -- "
          f"{'no systematic platform bias' if med == 0 or pv >= 0.05 else 'SYSTEMATIC BIAS, withdrawal (a)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
