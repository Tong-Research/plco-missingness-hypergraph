"""How much could conditioning on the missingness pattern possibly gain?

``safe_oracle`` selects kappa with hindsight on the test fold, so the gain it reports
is an UPPER BOUND on what any member of this shrinkage family could deliver -- no
selection rule can beat it. Comparing that bound with what is achievable in
simulation is the cleanest statement of the project's finding.

The bound is optimistically biased, because taking a maximum over a kappa grid on a
finite test fold captures noise. The null for that bias is the same permutation used
elsewhere: shuffling the mask rows across records preserves the pattern set, the
supports and the feature distribution while destroying any association between the
pattern and the outcome. Whatever ceiling survives that permutation is selection
noise, so the quantity of interest is

    exploitable structure  =  ceiling(real)  -  ceiling(mask-permuted)

Usage: oracle_ceiling.py [--datasets a,b,c] [--seeds 3]
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import warnings

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import average_precision_score
from sklearn.model_selection import StratifiedKFold

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_synthetic_suite import KAPPAS, _backbone_logit, safe_predict, tuned_pooled  # noqa: E402
from run_real_suite import DATASETS  # noqa: E402

from hgmiss.estimator import HypergraphShrinkage  # noqa: E402

warnings.simplefilter("ignore")
MIN_SUPPORT = 15


def permute_mask(X, seed=0):
    """Same pattern set, same supports, no association with the outcome."""
    rng = np.random.default_rng(seed)
    obs = ~np.isnan(X)
    Xh = X.copy()
    col_mean = np.nanmean(X, axis=0)
    col_mean = np.where(np.isfinite(col_mean), col_mean, 0.0)
    idx = np.where(np.isnan(Xh))
    Xh[idx] = np.take(col_mean, idx[1])
    out = Xh.copy()
    out[~obs[rng.permutation(len(X))]] = np.nan
    return out


def ceiling(X, y, seeds, min_support=MIN_SUPPORT):
    """Per-fold (best-kappa-with-hindsight minus pooled) AUPRC."""
    gains = []
    for s in seeds:
        for tr, te in StratifiedKFold(5, shuffle=True, random_state=s).split(X, y):
            _, fit = tuned_pooled(X[tr], y[tr], X[te], indicators=True, tune=True)
            lg = _backbone_logit(fit, X[te])
            base = average_precision_score(y[te], 1 / (1 + np.exp(-lg)))
            est = HypergraphShrinkage(kappa=0.0, min_support=min_support).fit(X[tr], y[tr])
            best = max(average_precision_score(y[te], safe_predict(est, lg, X[te], k))
                       for k in KAPPAS)
            gains.append(best - base)
    return np.asarray(gains)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", default="")
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--out", default="results/oracle_ceiling.csv")
    a = ap.parse_args()
    want = set(a.datasets.split(",")) if a.datasets else None
    seeds = list(range(a.seeds))
    rows = []
    print(f"{'dataset':16s} {'n':>6s} {'real':>9s} {'permuted':>9s} {'excess':>9s} {'p':>8s}",
          flush=True)
    for name, load in DATASETS:
        if want and name not in want:
            continue
        try:
            X, y = load()
            if np.isnan(X).mean() < 0.01:
                continue
            t = time.time()
            g_real = ceiling(X, y, seeds)
            g_perm = ceiling(permute_mask(X), y, seeds)
            exc = g_real.mean() - g_perm.mean()
            p = stats.mannwhitneyu(g_real, g_perm, alternative="greater").pvalue
            rows.append(dict(dataset=name, n=len(y), ceiling_real=g_real.mean(),
                             ceiling_perm=g_perm.mean(), excess=exc, p=p))
            print(f"{name:16s} {len(y):6d} {g_real.mean():+9.4f} {g_perm.mean():+9.4f} "
                  f"{exc:+9.4f} {p:8.3f}  [{time.time()-t:.0f}s]", flush=True)
        except Exception as e:
            print(f"{name:16s} ERROR {type(e).__name__}: {str(e)[:50]}", flush=True)
    out = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    out.to_csv(a.out, index=False)
    if len(out):
        print(f"\nwrote {a.out}")
        print(f"  mean ceiling on real data      {out.ceiling_real.mean():+.4f}")
        print(f"  mean ceiling after permutation {out.ceiling_perm.mean():+.4f}")
        print(f"  mean EXPLOITABLE structure     {out.excess.mean():+.4f}")
        print(f"  datasets with excess significant at 0.05: "
              f"{int((out.p < 0.05).sum())}/{len(out)}")


if __name__ == "__main__":
    main()
