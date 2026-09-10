"""Definitive synthetic characterisation of the safe-adaptive estimator.

Protocol (the one that survived adversarial checking; see docs/):
  * baselines are inner-CV TUNED (LogisticRegressionCV over a C grid) -- an
    untuned baseline is not a baseline, and default C=1.0 under-regularises
    mask-indicator models on small n, which manufactured apparent wins;
  * kappa is selected by NESTED CV on the training fold only (never the test
    fold), so the reported number is what a user would actually obtain;
  * kappa grid includes literal np.inf, whose lambda is exactly 0, so the
    safety endpoint reproduces the pooled backbone exactly.

Factors (see synthgen.py for the generator and its calibration to real data):
  mechanism     MCAR | MAR | MNAR              (Rubin 1976; Schouten et al. 2018)
  het           pattern-specific SLOPE heterogeneity
  info          pattern-specific BASE-RATE shift
  concentration pattern-size law, calibrated to the real measured range
  n             sample size

Usage: run_synthetic_suite.py [--quick] [--out results/synthetic.csv]
"""
from __future__ import annotations

import argparse
import itertools
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, LogisticRegressionCV
from sklearn.metrics import average_precision_score
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.preprocessing import StandardScaler
from scipy.special import expit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from synthgen import make_dataset, dataset_stats  # noqa: E402

from hgmiss.estimator import HypergraphShrinkage  # noqa: E402

CS = np.logspace(-3, 2, 10)
KAPPAS = [0.0, 30.0, 100.0, 300.0, 1000.0, np.inf]


def _design(X, imp, indicators):
    Xi = imp.transform(X)
    if indicators:
        return np.column_stack([Xi, (~np.isnan(X)).astype(float)])
    return Xi


def tuned_pooled(Xtr, ytr, Xte, indicators, tune=True):
    """Pooled logistic baseline; `indicators` adds the missingness mask."""
    imp = SimpleImputer(strategy="mean", keep_empty_features=True).fit(Xtr)
    tr, te = _design(Xtr, imp, indicators), _design(Xte, imp, indicators)
    sc = StandardScaler().fit(tr)
    if tune:
        m = LogisticRegressionCV(Cs=CS, cv=3, scoring="average_precision",
                                 max_iter=2000, n_jobs=1)
    else:
        m = LogisticRegression(max_iter=2000)
    m.fit(sc.transform(tr), ytr)
    return m.predict_proba(sc.transform(te))[:, 1], (imp, sc, m)


def _backbone_logit(fitted, X):
    imp, sc, m = fitted
    return m.decision_function(sc.transform(_design(X, imp, True)))


def safe_predict(est, logit_g, X, kappa):
    """Blend each pattern's local logit toward the pooled backbone logit."""
    X = np.asarray(X, float)
    lg = np.asarray(logit_g, float)
    if not getattr(est, "raw_theta_", None):
        return np.clip(expit(lg), 1e-6, 1 - 1e-6)
    from hgmiss.shrinkage import INTERCEPT
    pats = est.patterns_
    d = X.shape[1]
    C = np.zeros((len(pats), d)); b = np.zeros(len(pats))
    s = np.zeros(len(pats)); Pf = np.zeros((len(pats), d))
    for j, e in enumerate(pats):
        th = est.raw_theta_[e]
        b[j] = th[INTERCEPT]; s[j] = est.supports_[e]
        for v in e:
            C[j, v] = th[v]; Pf[j, v] = 1.0
    Xs = np.nan_to_num(est.scaler_.transform(X), nan=0.0)
    Zraw = Xs @ C.T + b
    lam = np.zeros_like(s) if np.isinf(kappa) else s / np.maximum(s + kappa, 1e-12)
    prob = expit(lam[None, :] * Zraw + (1 - lam)[None, :] * lg[:, None])
    applic = (Pf @ (~(~np.isnan(X))).T.astype(float)) == 0
    w = applic.T * s[None, :]
    wsum = w.sum(1)
    out = np.where(wsum > 0, (w * prob).sum(1) / np.maximum(wsum, 1e-12), expit(lg))
    return np.clip(out, 1e-6, 1 - 1e-6)


def one_fold(Xtr, ytr, Xte, yte, min_support, rule="1se"):
    """Returns AUPRC for every method on one fold, with honest kappa selection."""
    out = {}
    p_imp, _ = tuned_pooled(Xtr, ytr, Xte, indicators=False, tune=True)
    p_ind, fit_ind = tuned_pooled(Xtr, ytr, Xte, indicators=True, tune=True)
    p_imp0, _ = tuned_pooled(Xtr, ytr, Xte, indicators=False, tune=False)
    p_ind0, _ = tuned_pooled(Xtr, ytr, Xte, indicators=True, tune=False)
    out["mean_impute"] = average_precision_score(yte, p_imp0)
    out["mean_indicator"] = average_precision_score(yte, p_ind0)
    out["tuned_impute"] = average_precision_score(yte, p_imp)
    out["tuned_indicator"] = average_precision_score(yte, p_ind)

    # nested selection of kappa: inner K-fold CV on TRAIN only. A single inner
    # split leaves too few positives at clinical prevalence (~37 at 10% of a 25%
    # split of n=1500), and the resulting selection noise costs more than the
    # method gains -- averaging over inner folds is what makes kappa selectable.
    inner_scores = {k: [] for k in KAPPAS}
    inner = StratifiedKFold(3, shuffle=True, random_state=0)
    for itr, iva in inner.split(Xtr, ytr):
        _, fin = tuned_pooled(Xtr[itr], ytr[itr], Xtr[iva], indicators=True, tune=False)
        lgi = _backbone_logit(fin, Xtr[iva])
        ei = HypergraphShrinkage(kappa=0.0, min_support=min_support).fit(Xtr[itr], ytr[itr])
        for k in KAPPAS:
            inner_scores[k].append(average_precision_score(
                ytr[iva], safe_predict(ei, lgi, Xtr[iva], k)))
    # One-standard-error rule, biased toward the SAFE end. Picking the inner-CV
    # argmax makes the deployed method genuinely able to lose: selection noise in
    # the fragmented / small-n corner picks a small kappa that does not generalise.
    # Instead take the most conservative kappa (largest, i.e. closest to the pooled
    # backbone, with np.inf reproducing it exactly) whose inner score is within one
    # standard error of the best. Deviating from the backbone then requires evidence.
    means = {k: float(np.mean(inner_scores[k])) for k in KAPPAS}
    kmax = max(means, key=means.get)
    if rule == "argmax":
        kbest = kmax
    else:
        se = float(np.std(inner_scores[kmax], ddof=1) / np.sqrt(len(inner_scores[kmax]))) \
            if len(inner_scores[kmax]) > 1 else 0.0
        thresh = means[kmax] - se
        kbest = max((k for k in KAPPAS if means[k] >= thresh),
                    key=lambda k: (np.inf if np.isinf(k) else k))

    lg = _backbone_logit(fit_ind, Xte)
    est = HypergraphShrinkage(kappa=0.0, min_support=min_support).fit(Xtr, ytr)
    out["safe_adaptive"] = average_precision_score(yte, safe_predict(est, lg, Xte, kbest))
    out["kappa"] = kbest
    # oracle kappa, reported only to quantify the selection gap
    out["safe_oracle"] = max(average_precision_score(yte, safe_predict(est, lg, Xte, k))
                             for k in KAPPAS)
    return out


def evaluate(X, y, seeds, min_support, rule="1se"):
    rows = []
    for s in seeds:
        for tr, te in StratifiedKFold(5, shuffle=True, random_state=s).split(X, y):
            rows.append(one_fold(X[tr], y[tr], X[te], y[te], min_support, rule))
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", default="results/synthetic_suite.csv")
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--min-support", type=int, default=20)
    ap.add_argument("--rule", choices=["1se", "argmax"], default="1se",
                    help="kappa selection: conservative one-standard-error, or plain inner-CV argmax")
    ap.add_argument("--mechanism", default="", help="run only this mechanism; empty runs all three")
    ap.add_argument("--outcome-from", choices=["pattern", "shared"], default="pattern",
                    help="'pattern' is the standard generator, which draws the outcome from each "
                         "row's own pattern coefficients and therefore makes coefficient divergence "
                         "predictive by construction. 'shared' is the control the oracle-bound paper "
                         "proposes and records as not run: the same per-pattern coefficients, so the "
                         "same coefficient heterogeneity, but the outcome drawn from the shared "
                         "vector, so no predictive heterogeneity.")
    a = ap.parse_args()

    if a.quick:
        grid = dict(mechanism=["MAR"], het=[0.0, 1.5], info=[0.0, 1.5],
                    concentration=[0.9], n=[2000])
    else:
        grid = dict(mechanism=["MCAR", "MAR", "MNAR"], het=[0.0, 0.5, 1.5],
                    info=[0.0, 1.5], concentration=[0.9, 0.5, 0.1], n=[1000, 4000])
    if a.mechanism: grid["mechanism"] = [a.mechanism]
    seeds = list(range(a.seeds))
    keys = list(grid)
    rows = []
    for combo in itertools.product(*(grid[k] for k in keys)):
        cfg = dict(zip(keys, combo))
        npat = {0.9: 12, 0.5: 60, 0.1: 300}.get(cfg["concentration"], 12)
        X, y, meta = make_dataset(n=cfg["n"], d=16, n_patterns=npat,
                                  concentration=cfg["concentration"],
                                  mechanism=cfg["mechanism"], het=cfg["het"],
                                  info=cfg["info"], prevalence=0.10,
                                  target_miss=0.12, seed=0,
                                  outcome_from=a.outcome_from)
        st = dataset_stats(X, y)
        t = time.time()
        df = evaluate(X, y, seeds, a.min_support, a.rule)
        rec = {**cfg, "outcome_from": a.outcome_from, "coef_spread": meta["coef_spread"],
               **{k: st[k] for k in ["miss", "n_pat", "cov30", "eff_pat", "prev"]}}
        for m in ["mean_impute", "mean_indicator", "tuned_impute", "tuned_indicator",
                  "safe_adaptive", "safe_oracle"]:
            rec[m] = df[m].mean()
        d_ = (df["safe_adaptive"] - df["tuned_indicator"]).to_numpy()
        rec["delta_vs_tuned_ind"] = d_.mean()
        rec["p_vs_tuned_ind"] = (stats.wilcoxon(d_).pvalue
                                 if not np.allclose(d_, 0) else 1.0)
        rec["wins"] = int((d_ > 0).sum()); rec["n_folds"] = len(d_)
        rec["kappa_median"] = float(np.median(df["kappa"].replace(np.inf, 1e9)))
        rows.append(rec)
        print(f"{cfg} -> safe {rec['safe_adaptive']:.4f} vs tuned_ind "
              f"{rec['tuned_indicator']:.4f} = {rec['delta_vs_tuned_ind']:+.4f} "
              f"(p={rec['p_vs_tuned_ind']:.1e}, {rec['wins']}/{rec['n_folds']}) "
              f"[{time.time()-t:.0f}s]", flush=True)
    out = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    out.to_csv(a.out, index=False)
    print(f"\nwrote {a.out} ({len(out)} configurations)")


if __name__ == "__main__":
    main()
