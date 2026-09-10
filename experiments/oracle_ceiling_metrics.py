"""The oracle bound under three metrics, not one.

Paper 3 §7 concedes that everything is AUPRC, chosen because several datasets are heavily
imbalanced and it is the metric most sensitive to the minority class. The concession is real:
a method could leave discrimination unchanged and improve calibration, and a bound measured
only in AUPRC would not detect it.

So the same ceiling is computed under three metrics that fail in different ways:

    auprc   ranking, weighted toward the minority class -- the published metric
    auroc   ranking, insensitive to prevalence -- catches a method that reorders the
            majority class, which AUPRC largely ignores
    brier   a proper scoring rule, so it moves with calibration as well as ranking --
            this is the one that could reveal a calibration gain AUPRC cannot see

Brier is a LOSS, so its ceiling is defined with the sign flipped (pooled minus best) to keep
"positive means the family gained something" true across all three columns. Getting that
backwards would report the family as helping precisely when it hurts, which is the kind of
error this project has already made once with a clipped lift.

The null is the same B independent mask permutations as `oracle_ceiling_b.py`, and the real
arm is computed once, for the same reasons stated there.
"""
from __future__ import annotations

import argparse
import pathlib
import sys
import time
import warnings

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))
warnings.simplefilter("ignore")

from hgmiss.estimator import HypergraphShrinkage          # noqa: E402
from hgmiss.metrics import evaluate                       # noqa: E402
from oracle_ceiling import permute_mask, KAPPAS, MIN_SUPPORT, safe_predict, tuned_pooled, \
    _backbone_logit                                       # noqa: E402
from run_real_suite import DATASETS                       # noqa: E402

# name -> (metric key, higher_is_better)
METRICS = {"auprc": ("auprc", True), "auroc": ("auroc", True), "brier": ("brier", False)}


def ceilings(X, y, seeds, min_support=MIN_SUPPORT):
    """Per-fold ceiling for every metric, from ONE set of fits per fold."""
    out = {m: [] for m in METRICS}
    for s in seeds:
        for tr, te in StratifiedKFold(5, shuffle=True, random_state=s).split(X, y):
            _, fit = tuned_pooled(X[tr], y[tr], X[te], indicators=True, tune=True)
            lg = _backbone_logit(fit, X[te])
            base = evaluate(y[te], 1 / (1 + np.exp(-lg)))
            est = HypergraphShrinkage(kappa=0.0, min_support=min_support).fit(X[tr], y[tr])
            scored = [evaluate(y[te], safe_predict(est, lg, X[te], k)) for k in KAPPAS]
            for name, (key, higher) in METRICS.items():
                vals = [sc[key] for sc in scored]
                if higher:
                    out[name].append(max(vals) - base[key])
                else:
                    # Brier is a loss: the best member MINIMISES it, and a gain is a
                    # reduction. Flip so positive means "the family gained".
                    out[name].append(base[key] - min(vals))
    return {m: np.asarray(v, float) for m, v in out.items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", default="")
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--B", type=int, default=25)
    ap.add_argument("--out", default="results/oracle_ceiling_metrics.csv")
    a = ap.parse_args()
    want = set(a.datasets.split(",")) if a.datasets else None

    rows = []
    print(f"{'dataset':16s} {'metric':7s} {'real':>9s} {'null':>9s} {'excess':>9s} {'p':>7s}",
          flush=True)
    for name, load in DATASETS:
        if want and name not in want:
            continue
        try:
            X, y = load()
            if np.isnan(X).mean() < 0.01:
                continue
            t = time.time()
            real = ceilings(X, y, list(range(a.seeds)))
            perms = {m: [] for m in METRICS}
            for b in range(a.B):
                pc = ceilings(permute_mask(X, seed=b), y, [0])
                for m in METRICS:
                    perms[m].append(np.nanmean(pc[m]))
            for m in METRICS:
                r = float(np.nanmean(real[m])); pv = np.asarray(perms[m], float)
                p = (1 + (pv >= r).sum()) / (a.B + 1)
                rows.append(dict(dataset=name, metric=m, n=len(y), B=a.B,
                                 ceiling_real=r, perm_mean=float(np.nanmean(pv)),
                                 perm_sd=float(np.nanstd(pv, ddof=1)),
                                 excess=r - float(np.nanmean(pv)), p=float(p)))
                print(f"{name:16s} {m:7s} {r:+9.4f} {np.nanmean(pv):+9.4f} "
                      f"{r-np.nanmean(pv):+9.4f} {p:7.3f}", flush=True)
            print(f"{'':16s} [{time.time()-t:.0f}s]", flush=True)
        except Exception as e:
            print(f"{name:16s} ERROR {type(e).__name__}: {str(e)[:60]}", flush=True)

    if rows:
        d = pd.DataFrame(rows)
        pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        d.to_csv(a.out, index=False)
        print("\n  mean excess by metric:")
        for m in METRICS:
            s = d[d.metric == m]
            print(f"    {m:7s} {s.excess.mean():+.5f}   negative on {(s.excess<0).sum()}/{len(s)}"
                  f"   p<0.05 on {(s.p<0.05).sum()}")
        print(f"\n  wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
