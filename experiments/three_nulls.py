"""Recompute the three null tests that Paper 1's discussion rests on.

Every number the paper quotes about them comes from here, not from a transcript. The three are
NOT the same test repeated -- they are three different constructions probing one proposition, and
the script prints what each one destroys so that the distinction survives into the write-up.

    1. cross-dataset ceiling   Paper 3's, over 11 public datasets. Destroys: the association
                               between pattern and outcome, by permuting mask rows. Preserves:
                               pattern set, supports, feature distribution.
    2. residual mask (A4b)     This paper's cohorts. Destroys: the mask's row-alignment inside
                               the design. Preserves: the values exactly -- verified by a
                               mask-blind arm moving by exactly zero.
    3. pattern grouping (B7)   This paper's cohorts. Destroys: which records share a group.
                               Preserves: the group size distribution exactly.

Run: experiments/three_nulls.py
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd
from scipy import stats

R = pathlib.Path(__file__).resolve().parent.parent / "results"
FLOOR = 0.002


def _paired(a, b):
    v = (a - b).dropna().to_numpy(float)
    return float(np.median(v)), float(stats.wilcoxon(v).pvalue), len(v)


def test1():
    f = R / "oracle_ceiling_b.csv"
    d = pd.read_csv(f)
    beat = int((d.ceiling_real > d.perm_mean).sum())
    print(f"\n1. CROSS-DATASET CEILING  ({f.name}, {len(d)} datasets)")
    print(f"   real ceiling  mean {d.ceiling_real.mean():+.4f}   median {d.ceiling_real.median():+.4f}")
    print(f"   permuted null mean {d.perm_mean.mean():+.4f}   median {d.perm_mean.median():+.4f}")
    print(f"   excess        mean {d.excess.mean():+.4f}   median {d.excess.median():+.4f}")
    print(f"   real exceeds its own null on {beat} of {len(d)} datasets")
    return {"n_datasets": len(d), "real": d.ceiling_real.mean(), "null": d.perm_mean.mean(),
            "excess": d.excess.mean(), "beat": beat}


def test2():
    print("\n2. RESIDUAL MASK  (results/ideas/A4b, real vs mask-permuted, arm=residual_indicator)")
    out = {}
    for f in sorted((R / "ideas" / "A4b").glob("*.csv")):
        d = pd.read_csv(f)
        d["arm"] = d.arm.str.replace("idea_A4b_", "", regex=False)
        coh = d.cohort.iloc[0]
        # the instrument check: a mask-blind arm must be unmoved by a mask permutation
        gi = d[d.arm == "mean_impute"]
        gap = float(np.abs(gi[gi.permuted == 0].set_index(["seed", "fold"]).auprc
                           - gi[gi.permuted == 1].set_index(["seed", "fold"]).auprc).max())
        g = d[d.arm == "residual_indicator"]
        m, p, n = _paired(g[g.permuted == 0].set_index(["seed", "fold"]).auprc,
                          g[g.permuted == 1].set_index(["seed", "fold"]).auprc)
        print(f"   {coh:11s} real - null {m:+.6f}  p={p:<9.3g} n={n}"
              f"   [instrument: mask-blind arm moved by {gap:.1g}]")
        assert gap == 0.0, f"{coh}: the null moved a mask-blind arm -- do not quote this"
        out[coh] = (m, p)
    return out


def test3():
    print("\n3. PATTERN GROUPING  (results/ideas/B7, oracle margin: real patterns vs random groups)")
    out = {}
    for f in sorted((R / "ideas" / "B7").glob("*.csv")):
        d = pd.read_csv(f)
        d["arm"] = d.arm.str.replace("idea_B7_", "", regex=False)
        coh = d.cohort.iloc[0]
        real = d[d.permuted == 0].pivot_table(index=["seed", "fold"], columns="arm", values="auprc")
        null = d[d.permuted == 1].pivot_table(index=["seed", "fold"], columns="arm", values="auprc")
        bad = int((real.blend_oracle < real.pooled - 1e-12).sum())
        assert bad == 0, f"{coh}: oracle below pooled in {bad} cells -- do not quote this"
        mr = (real.blend_oracle - real.pooled)
        mn = (null.blend_oracle - null.pooled)
        m, p, n = _paired(mr, mn)
        print(f"   {coh:11s} real margin {mr.median():+.6f}  null margin {mn.median():+.6f}"
              f"  excess {m:+.6f}  p={p:<9.3g} n={n}")
        out[coh] = (mr.median(), mn.median(), m, p)
    return out


def test4():
    """The decision rule against a comparison KNOWN to be null.

    A4b's `residual` and `residual_scaled` arms differ only by a per-column rescaling, which the
    estimator's StandardScaler removes before fitting. They are the same model up to
    floating-point rounding, so any difference the protocol reports between them is manufactured.
    """
    print("\n4. THE DECISION RULE vs a known-null comparison (A4b residual vs residual_scaled)")
    for f in sorted((R / "ideas" / "A4b").glob("*.csv")):
        d = pd.read_csv(f)
        d["arm"] = d.arm.str.replace("idea_A4b_", "", regex=False)
        coh = d.cohort.iloc[0]
        d = d[d.permuted == 0]
        piv = d.pivot_table(index=["seed", "fold"], columns="arm", values="auprc")
        v = (piv.residual_indicator - piv.scaled_residual_indicator).dropna()
        med, pv, n = _paired(piv.residual_indicator, piv.scaled_residual_indicator)
        mx = float(np.abs(v).max())
        passes = abs(med) >= FLOOR and pv < 0.05
        print(f"   {coh:11s} median {med:+.6f}  p={pv:<9.3g}  max|cell| {mx:.2e}  n={n}"
              f"   passes floor+p<0.05? {'YES -- ALARMING' if passes else 'no'}")
        assert not passes, f"{coh}: the protocol reported an effect between identical models"


def main() -> int:
    print("=" * 84)
    print("  THREE NULLS — three constructions, one proposition")
    print("=" * 84)
    a, b, c = test1(), test2(), test3()
    test4()
    print("\n" + "=" * 84)
    neg = [a["excess"] < 0] + [v[0] < 0 for v in b.values()] + [v[2] < 0 for v in c.values()]
    print(f"  tests where the REAL structure gained LESS than its null: {sum(neg)} of {len(neg)}")
    print("  These are different nulls destroying different things. They are consistent, which is")
    print("  the claim; they are not replications of one test, which would be a stronger and")
    print("  unsupported claim.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
