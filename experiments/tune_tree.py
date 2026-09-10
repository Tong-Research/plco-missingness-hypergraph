"""Tuned HistGradientBoosting baseline (referee request, 2026-09-03): a small grid selected by inner 3-fold CV on
AUPRC inside each training fold, evaluated with the main-table protocol (stratified 5 folds x seeds, 40,000
subsample for PLCO). Writes one row per (cohort, seed, fold) with the default and the tuned tree's test AUPRC and
the chosen configuration.

    --cohort {colorectal,lung,ovarian,prostate}   PLCO via hgmiss.data.plco (pilot)
    --cohort mimic4                               ~/.cache/phd-matrices/mimic4_sites.npz, full n (spinner)
"""
import argparse, itertools, pathlib, sys, time
import numpy as np, pandas as pd
HERE = pathlib.Path(__file__).resolve().parent; ROOT = HERE.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / "src"))
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import average_precision_score
GRID = [dict(max_depth=d, learning_rate=lr, max_iter=it, min_samples_leaf=leaf)
        for d, lr, it, leaf in itertools.product([3, 6, None], [0.03, 0.1], [200, 500], [20, 100])]

def fit_predict(Xtr, ytr, Xte, cfg):
    return HistGradientBoostingClassifier(random_state=0, early_stopping=False, **cfg).fit(Xtr, ytr).predict_proba(Xte)[:, 1]

def tuned(Xtr, ytr, Xte, seed):
    inner = StratifiedKFold(3, shuffle=True, random_state=seed); scores = []
    for cfg in GRID:
        s = [average_precision_score(ytr[v], fit_predict(Xtr[t], ytr[t], Xtr[v], cfg)) for t, v in inner.split(Xtr, ytr)]
        scores.append(float(np.mean(s)))
    best = GRID[int(np.argmax(scores))]
    return fit_predict(Xtr, ytr, Xte, best), best, max(scores)

def load(cohort):
    if cohort == "mimic4":
        z = np.load(pathlib.Path.home() / ".cache/phd-matrices/mimic4_sites.npz", allow_pickle=True)
        return np.asarray(z["X"], float), np.asarray(z["y"]).ravel().astype(int)
    from hgmiss.data.plco import load_cohort
    from run_h1_h4 import _subsample, FULL_MAX_N, ROOT as PLCO_ROOT
    c = load_cohort(cohort, PLCO_ROOT, feature_set="baseline"); return _subsample(c, seed=0, max_n=FULL_MAX_N)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--cohort", required=True); ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--out", default=None); a = ap.parse_args()
    X, y = load(a.cohort); out = pathlib.Path(a.out or ROOT / "results" / f"tune_tree_{a.cohort}.csv"); rows = []; t0 = time.time()
    for seed in range(a.seeds):
        for fold, (tr, te) in enumerate(StratifiedKFold(5, shuffle=True, random_state=seed).split(X, y)):
            p0 = fit_predict(X[tr], y[tr], X[te], {}); p1, best, inner = tuned(X[tr], y[tr], X[te], seed)
            rows.append(dict(cohort=a.cohort, seed=seed, fold=fold, auprc_default=average_precision_score(y[te], p0),
                             auprc_tuned=average_precision_score(y[te], p1), inner_auprc=inner, **{f"cfg_{k}": v for k, v in best.items()}))
            pd.DataFrame(rows).to_csv(out, index=False)
            print(f"  {a.cohort} seed {seed} fold {fold}: default {rows[-1]['auprc_default']:.4f} tuned {rows[-1]['auprc_tuned']:.4f} {best} [{time.time()-t0:.0f}s]", flush=True)

if __name__ == "__main__":
    main()
