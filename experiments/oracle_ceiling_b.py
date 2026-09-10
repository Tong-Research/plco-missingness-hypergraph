"""The oracle bound with a REAL permutation null: B draws, not one.

`oracle_ceiling.py` computes the permuted ceiling from a single mask permutation, then
Mann-Whitney tests its 15 fold-gains against the real 15. Those 15 permuted gains are folds
WITHIN ONE DRAW -- they share a mask, so they are not fifteen samples from the null. The
effective null sample size is one, and the test treats it as fifteen.

That matters because the entire paper turns on one number. `excess = -0.0039` is a difference
between a measured quantity and a single draw of a random one, reported without an interval.
It could be a stable property or an unlucky mask, and the current design cannot distinguish
them. Every reviewer of a bound asks how many permutations were run.

So: B independent mask permutations per dataset, each scored the same way. This gives

  * the null DISTRIBUTION of the ceiling rather than one point,
  * a permutation p-value, Pr(ceiling_perm >= ceiling_real), computed the standard way
    with the +1 correction so it can never be zero,
  * a percentile interval on the permuted ceiling, and therefore on the excess.

The real ceiling is computed once, from the real mask, exactly as before -- it is not a random
quantity under the null and re-drawing it would be a different experiment.

Cost is B times the permuted arm. These datasets are 155-3,772 rows, which is why this is
affordable at B=50 and was never a reason to run one.
"""
from __future__ import annotations

import argparse
import pathlib
import sys
import time
import warnings

import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))
warnings.simplefilter("ignore")

from oracle_ceiling import ceiling, permute_mask, MIN_SUPPORT   # noqa: E402
from run_real_suite import DATASETS, EXTRA_SETS                 # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", default="")
    ap.add_argument("--seeds", type=int, default=3, help="seeds for the REAL arm")
    ap.add_argument("--B", type=int, default=50, help="independent mask permutations")
    ap.add_argument("--perm-seeds", type=int, default=1,
                    help="seeds per permutation; 1 keeps the null arm affordable at large B")
    ap.add_argument("--out", default="results/oracle_ceiling_b.csv")
    a = ap.parse_args()

    want = set(a.datasets.split(",")) if a.datasets else None
    rows = []
    print(f"{'dataset':16s} {'n':>6s} {'real':>9s} {'perm mean':>10s} {'excess':>9s} "
          f"{'perm 2.5%':>10s} {'perm 97.5%':>11s} {'p':>7s}", flush=True)

    for name, load in DATASETS + (EXTRA_SETS if want else []):
        if want and name not in want:
            continue
        try:
            X, y = load()
            if np.isnan(X).mean() < 0.01:
                print(f"{name:16s} skipped: <1% missing, no pattern structure to bound",
                      flush=True)
                continue
            t = time.time()
            real = ceiling(X, y, list(range(a.seeds)), MIN_SUPPORT).mean()

            # Each b is an INDEPENDENT mask draw. Seeding permute_mask by b is what makes
            # them independent; reusing one mask is precisely the defect this file fixes.
            perms = np.array([
                ceiling(permute_mask(X, seed=b), y, list(range(a.perm_seeds)),
                        MIN_SUPPORT).mean()
                for b in range(a.B)])

            # Standard permutation p-value with the +1 correction: with B draws the smallest
            # reportable p is 1/(B+1), and a p of exactly zero is never honest.
            p = (1 + (perms >= real).sum()) / (a.B + 1)
            lo, hi = np.percentile(perms, [2.5, 97.5])
            rows.append(dict(dataset=name, n=len(y), B=a.B, ceiling_real=real,
                             perm_mean=perms.mean(), perm_sd=perms.std(ddof=1),
                             perm_lo=lo, perm_hi=hi, excess=real - perms.mean(), p=p))
            print(f"{name:16s} {len(y):6d} {real:+9.4f} {perms.mean():+10.4f} "
                  f"{real-perms.mean():+9.4f} {lo:+10.4f} {hi:+11.4f} {p:7.3f}"
                  f"  [{time.time()-t:.0f}s]", flush=True)
        except Exception as e:
            print(f"{name:16s} ERROR {type(e).__name__}: {str(e)[:60]}", flush=True)

    if rows:
        out = pd.DataFrame(rows)
        pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(a.out, index=False)
        print(f"\n  datasets            {len(out)}")
        print(f"  mean real ceiling   {out.ceiling_real.mean():+.4f}")
        print(f"  mean permuted       {out.perm_mean.mean():+.4f}")
        print(f"  mean excess         {out.excess.mean():+.4f}")
        print(f"  real BELOW the permuted mean on {(out.excess < 0).sum()}/{len(out)}")
        print(f"  datasets with p < 0.05          {(out.p < 0.05).sum()}/{len(out)}")
        print(f"\n  wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
