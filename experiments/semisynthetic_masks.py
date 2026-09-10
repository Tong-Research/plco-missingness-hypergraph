"""SHOWCASE.md item D: semi-synthetic outcomes on REAL masks and values (development halves only).

For a dataset's dev half (60,000 subsample): keep X as observed (values and NaN pattern). Standardise observed
values per column. Draw a base coefficient vector beta0 ~ N(0, 1) over all columns and, for each realised pattern e
(exact observed set), a deviation u_e ~ N(0, 1) over its columns; the outcome for a record with pattern e is
Bernoulli(sigmoid(b + (beta0 + delta * u_e) . x_obs / sqrt(|e|))), with b set so that prevalence ~ 0.3.
delta in {0, 0.25, 0.5, 1}. Arms as in run_candidate (tuned imputation / indicator / interaction, published
estimator, own-rows kappa=0, exact_cv, family_cv, tree) on one 70/30 split per delta, seed 0.
Prediction (SHOWCASE.md): the own-rows gain over imputation and the indicator rises with delta and is within the
floor at delta = 0; the published support rule's gain does not rise with delta on Higgs.
"""
import argparse, pathlib, sys, time
import numpy as np, pandas as pd
HERE = pathlib.Path(__file__).resolve().parent; ROOT = HERE.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / "src"))
from scipy.special import expit
from sklearn.model_selection import train_test_split
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score
from screen_candidates import dev_mask
from run_candidate import tuned, ours_fit, exact_cv, family_cv
from idea_x_exact import ExactHypergraph

def make_y(X, delta, rng):
    Xs = (X - np.nanmean(X, 0)) / (np.nanstd(X, 0) + 1e-9); Xs = np.nan_to_num(Xs); M = ~np.isnan(X)
    beta0 = rng.normal(size=X.shape[1]); keys = [r.tobytes() for r in M]; dev = {}
    lin = np.zeros(len(X))
    for i, k in enumerate(keys):
        if k not in dev: dev[k] = rng.normal(size=X.shape[1])
        cols = M[i]; n = max(cols.sum(), 1); lin[i] = ((beta0 + delta * dev[k])[cols] @ Xs[i, cols]) / np.sqrt(n)
    lin = lin / (lin.std() + 1e-9) * 1.5; b = np.quantile(lin, 0.7); return (rng.random(len(X)) < expit(lin - b)).astype(int)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--npz", required=True); ap.add_argument("--n", type=int, default=60000); a = ap.parse_args()
    z = np.load(pathlib.Path.home() / ".cache/phd-matrices" / f"{a.npz}.npz", allow_pickle=True); X = np.asarray(z["X"], float)
    dm = dev_mask(a.npz, len(X)); X = X[dm]; idx = np.random.default_rng(0).choice(len(X), min(a.n, len(X)), replace=False); X = X[idx]
    keep = ~np.isnan(X).all(0); X = X[:, keep]; rows = []; t0 = time.time()
    for delta in [0.0, 0.25, 0.5, 1.0]:
        y = make_y(X, delta, np.random.default_rng(42)); tr, te = train_test_split(np.arange(len(y)), test_size=0.3, stratify=y, random_state=0)
        Xtr, ytr, Xte, yte = X[tr], y[tr], X[te], y[te]
        keepc = np.array([len(np.unique(Xtr[~np.isnan(Xtr[:, j]), j])) >= 2 for j in range(Xtr.shape[1])])
        p = {"mean_impute": tuned(Xtr, ytr, Xte, "mean_impute"), "mean_indicator": tuned(Xtr, ytr, Xte, "mean_indicator"), "mask_interaction": tuned(Xtr, ytr, Xte, "mask_interaction"),
             "histgb": HistGradientBoostingClassifier(random_state=0, early_stopping=False).fit(Xtr[:, keepc], ytr).predict_proba(Xte[:, keepc])[:, 1],
             "ours": ours_fit(Xtr, ytr)[0].predict_proba(Xte), "exact0": ExactHypergraph(kappa=0).fit(Xtr, ytr).predict_proba(Xte)}
        p["exact_cv"], _ = exact_cv(Xtr, ytr, Xte); p["family_cv"], ch = family_cv(Xtr, ytr, Xte)
        r = {k: float(average_precision_score(yte, v)) for k, v in p.items()}; rows.append(dict(dataset=a.npz, delta=delta, prev=float(y.mean()), family_choice=str(ch), **r))
        pd.DataFrame(rows).to_csv(ROOT / "results" / f"semisynth_{a.npz}.csv", index=False)
        print(f"  {a.npz} delta {delta}: " + " ".join(f"{k} {v:.4f}" for k, v in r.items()) + f" | family {ch} [{time.time()-t0:.0f}s]", flush=True)

if __name__ == "__main__":
    main()
