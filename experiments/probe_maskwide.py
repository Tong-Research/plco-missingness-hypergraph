"""MASKWIDE (prereg/MASKWIDE.md): does the containment hierarchy pay when the mask carries signal?

LOWQ narrowed the matrix before fitting, so its hierarchy and its comparator both saw only the
retained columns' missingness -- a channel `probe_maskinc.py` measures as exactly 0.000 at every
width on 17/17 datasets. It could not have returned a positive result.

Here every column is kept, so `isnan(X)` is the FULL mask, and the withheld columns' observed
entries are overwritten with a constant. The mask is untouched; the withheld values are gone. After
mean imputation such a column is constant and contributes nothing beyond its own indicator. This is
the order-entry and claims setting: what was requested is known, what it showed is not.

The comparator is `mean_indicator` and it sees exactly what the hierarchy sees -- the same values
and the same full mask. The two differ only in whether the pattern partitions or is a feature.

One row per (dataset, q, draw, fold, arm). Writes results/maskwide/<dataset>.csv.
"""
from __future__ import annotations

import argparse
import csv
import pathlib
import sys
import time

import numpy as np
from sklearn.metrics import average_precision_score as ap_
from sklearn.model_selection import StratifiedKFold

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from probe_common import load                                   # noqa: E402
from run_candidate import family_cv, tuned, permute_mask        # noqa: E402
from hgmiss.baselines.native import histgb_native               # noqa: E402

QS = [1.0, 0.5, 0.25, 0.1]
DRAWS = {1.0: 1}          # one draw at full schema; two elsewhere
DEFAULT_DRAWS = 2


def main() -> int:
    a = argparse.ArgumentParser()
    a.add_argument("--dataset", required=True)
    a.add_argument("--slice", default="holdout")
    a.add_argument("--max-n", type=int, default=20_000)
    a.add_argument("--permute", type=int, default=-1,
                   help="permuted-mask null (prereg/MASKWIDE.md amendment): row-permute the mask with "
                        "this seed, preserving each column's marginal rate while destroying the "
                        "pattern. -1 (default) is the real mask and is unchanged.")
    a.add_argument("--out", required=True)
    a = a.parse_args()

    X, y = load(a.dataset, a.slice, a.max_n)
    if a.permute >= 0:
        X = permute_mask(X, np.random.default_rng(a.permute))
        print(f"PERMUTED MASK, seed {a.permute}: the pattern carries no information", flush=True)
    n, p = X.shape
    folds = list(StratifiedKFold(3, shuffle=True, random_state=0).split(X, y))
    prev = float(y.mean())
    print(f"{a.dataset}: n {n:,} p {p} prevalence {prev:.4f}", flush=True)

    rows = []
    # On a narrow schema several q values round to the same column count -- at p=8,
    # q=0.25 and q=0.1 both give k=2 and would be the identical draw reported twice.
    # Recording it once keeps the per-q outcomes independent, which P1 and P2 assume.
    seen_k: set[int] = set()
    for q in QS:
        k = max(2, int(np.ceil(q * p)))
        if k in seen_k:
            print(f"  q={q:.2f}: k={k} already measured at a higher q; skipped", flush=True)
            continue
        seen_k.add(k)
        for d in range(DRAWS.get(q, DEFAULT_DRAWS)):
            cols = (np.arange(p) if q == 1.0
                    else np.sort(np.random.default_rng(d).choice(p, k, replace=False)))
            # Keep every column so the full mask survives; blank the withheld columns' observed
            # values to a constant so they carry no value information. This is the whole
            # difference from LOWQ, which subsetted and so conditioned on a null channel.
            V = X.copy()
            for j in np.setdiff1d(np.arange(p), cols):
                obs = ~np.isnan(V[:, j])
                V[obs, j] = 0.0
            t0 = time.time()
            per = {}
            for fi, (tr, te) in enumerate(folds):
                Xtr, Xte, ytr, yte = V[tr], V[te], y[tr], y[te]
                if len(np.unique(ytr)) < 2 or len(np.unique(yte)) < 2:
                    print(f"  q={q} draw {d} fold {fi}: single-class fold, skipped", flush=True)
                    continue
                preds = {
                    "mean_impute": tuned(Xtr, ytr, Xte, "mean_impute"),
                    "mean_indicator": tuned(Xtr, ytr, Xte, "mean_indicator"),
                    "family_cv": family_cv(Xtr, ytr, Xte)[0],
                    "histgb_native": histgb_native(Xtr, ytr, Xte),
                }
                for arm, pr in preds.items():
                    v = float(ap_(yte, pr))
                    per.setdefault(arm, []).append(v)
                    rows.append(dict(dataset=a.dataset, slice=a.slice, q=q, draw=d, k=k,
                                     fold=fi, arm=arm, auprc=v, prevalence=prev, n=n, p=p,
                                     permuted=a.permute))
            if per:
                g = np.mean(per["family_cv"]) - np.mean(per["mean_indicator"])
                print(f"  q={q:.2f} draw {d} k={k}: "
                      f"imp {np.mean(per['mean_impute']):.4f} "
                      f"ind {np.mean(per['mean_indicator']):.4f} "
                      f"hier {np.mean(per['family_cv']):.4f} "
                      f"tree {np.mean(per['histgb_native']):.4f} "
                      f"| hier-ind {g:+.4f}  [{time.time()-t0:.0f}s]", flush=True)

    if not rows:
        print("no rows produced", file=sys.stderr)
        return 1
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
