"""Tuned XGBoost and LightGBM baselines (TUNEBOOST, 2026-09-14).

Paper 1 reports both at library defaults while stating that every *linear* baseline is tuned.
An untuned competitor flatters the proposed method, which is the direction that matters when the
article's result is that the proposed method loses. Result 171 tuned HistGradientBoosting the same
way; this is deliberately the same shape so the three are comparable.

A 24-point grid selected by inner 3-fold CV on AUPRC inside each training fold, evaluated with the
main-table protocol (stratified 5 folds x seeds, 40,000 subsample for PLCO, full n for MIMIC-IV).
One row per (algorithm, cohort, seed, fold) with the default and tuned test AUPRC and the chosen
configuration.

    --cohort {colorectal,lung,ovarian,prostate}   PLCO via hgmiss.data.plco (Pilot only)
    --cohort mimic4                               ~/.cache/phd-matrices/mimic4_sites.npz, full n
    --algo {xgboost,lightgbm,both}

Registered in prereg/TUNEBOOST.md before this file ran. Grid and protocol are fixed there.
"""
import argparse, itertools, pathlib, sys, time
import numpy as np, pandas as pd
HERE = pathlib.Path(__file__).resolve().parent; ROOT = HERE.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / "src"))
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import average_precision_score

# Each grid mirrors tune_tree.py's four axes in that library's own spelling. XGBoost has no
# unlimited-depth sentinel that is safe across tree methods, so 12 stands in for None; LightGBM's
# -1 is the genuine equivalent.
GRIDS = {
    "xgboost": [dict(max_depth=d, learning_rate=lr, n_estimators=n, min_child_weight=w)
                for d, lr, n, w in itertools.product([3, 6, 12], [0.03, 0.1], [200, 500], [1, 20])],
    "lightgbm": [dict(max_depth=d, learning_rate=lr, n_estimators=n, min_child_samples=s)
                 for d, lr, n, s in itertools.product([3, 6, -1], [0.03, 0.1], [200, 500], [20, 100])],
}
# The defaults the main table already reports, from src/hgmiss/baselines/native.py. Kept here as
# the fixed keyword arguments so the default arm and the tuned arm differ ONLY by the grid.
FIXED = {
    "xgboost": dict(eval_metric="logloss", tree_method="hist"),
    "lightgbm": dict(verbosity=-1),
}


def _clf(algo, seed, cfg):
    if algo == "xgboost":
        from xgboost import XGBClassifier
        return XGBClassifier(random_state=seed, **FIXED["xgboost"], **cfg)
    from lightgbm import LGBMClassifier
    return LGBMClassifier(random_state=seed, **FIXED["lightgbm"], **cfg)


def fit_predict(algo, Xtr, ytr, Xte, cfg, seed=0):
    return np.asarray(_clf(algo, seed, cfg).fit(Xtr, ytr).predict_proba(Xte))[:, 1]


def tuned(algo, Xtr, ytr, Xte, seed):
    inner = StratifiedKFold(3, shuffle=True, random_state=seed)
    splits = list(inner.split(Xtr, ytr))
    scores = []
    for cfg in GRIDS[algo]:
        s = [average_precision_score(ytr[v], fit_predict(algo, Xtr[t], ytr[t], Xtr[v], cfg, seed))
             for t, v in splits]
        scores.append(float(np.mean(s)))
    best = GRIDS[algo][int(np.argmax(scores))]
    return fit_predict(algo, Xtr, ytr, Xte, best, seed), best, max(scores)


def load(cohort):
    if cohort == "mimic4":
        z = np.load(pathlib.Path.home() / ".cache/phd-matrices/mimic4_sites.npz", allow_pickle=True)
        return np.asarray(z["X"], float), np.asarray(z["y"]).ravel().astype(int)
    from hgmiss.data.plco import load_cohort
    from run_h1_h4 import _subsample, FULL_MAX_N, ROOT as PLCO_ROOT
    c = load_cohort(cohort, PLCO_ROOT, feature_set="baseline")
    return _subsample(c, seed=0, max_n=FULL_MAX_N)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cohort", required=True)
    ap.add_argument("--algo", default="both", choices=["xgboost", "lightgbm", "both"])
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    algos = ["xgboost", "lightgbm"] if a.algo == "both" else [a.algo]
    X, y = load(a.cohort)
    out = pathlib.Path(a.out or ROOT / "results" / f"tune_boost_{a.cohort}.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    rows, t0 = [], time.time()
    print(f"{a.cohort}: X={X.shape} prevalence={y.mean():.4f} algos={algos} "
          f"grid={ {k: len(GRIDS[k]) for k in algos} }", flush=True)
    for algo in algos:
        for seed in range(a.seeds):
            for fold, (tr, te) in enumerate(
                    StratifiedKFold(a.folds, shuffle=True, random_state=seed).split(X, y)):
                p0 = fit_predict(algo, X[tr], y[tr], X[te], {}, seed)
                p1, best, inner = tuned(algo, X[tr], y[tr], X[te], seed)
                rows.append(dict(algo=algo, cohort=a.cohort, seed=seed, fold=fold,
                                 auprc_default=average_precision_score(y[te], p0),
                                 auprc_tuned=average_precision_score(y[te], p1),
                                 inner_auprc=inner,
                                 **{f"cfg_{k}": v for k, v in best.items()}))
                # Written every fold: a run this long must not lose everything to a late crash,
                # which is how results/main.csv lost 1,850 rows on 2026-08-24.
                pd.DataFrame(rows).to_csv(out, index=False)
                print(f"  {algo} s{seed} f{fold}  default {rows[-1]['auprc_default']:.4f}  "
                      f"tuned {rows[-1]['auprc_tuned']:.4f}  {time.time()-t0:.0f}s", flush=True)
    print(f"wrote {out} ({len(rows)} rows, {time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
