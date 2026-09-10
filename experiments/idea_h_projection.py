"""Idea H, variant C: shrunk test-time projection for unseen missingness patterns.

The published estimator (src/hgmiss/estimator.py) fits one logistic model per realised
training pattern and shrinks each toward its immediate ancestors with weight
lambda = n / (n + kappa). At prediction time a row is scored by every fitted pattern that
is a SUBSET of its observed set; a row whose observed set contains no fitted pattern falls
back to the prior. Probe 7 showed this collapses the family to the prior when a test
population stops recording a variable every training pattern contains.

This module adds the missing step: for each distinct test observed-set that is not itself
a fitted pattern, fit it on the training rows that observe it (the same `_fit_one` rule
used in training) and shrink it with the estimator's own rule toward
  (i) its immediate ancestors among the fitted patterns, when it has any; otherwise
  (ii) its nearest fitted supersets restricted to its own coordinates, intercept refit.
Case (ii) is the one the published estimator cannot handle at all. The projected pattern
then joins `patterns_` / `theta_` / `supports_`, so `predict_proba` is unchanged.

`kappa_proj` is a separate knob from the estimator's `kappa` (the CV frequently picks
kappa = 0 on abundant support, which would make the projection an unregularised refit --
probe 7b's variant B, which lost). Its value must be chosen on the dev half and frozen
in the pre-registration before the holdout is touched.
"""
from __future__ import annotations

import copy

import numpy as np
from sklearn.linear_model import LogisticRegression

from hgmiss.patterns import immediate_ancestors
from hgmiss.shrinkage import INTERCEPT, shrink


def _maximal_subsets(e: frozenset[int], patterns) -> list[frozenset[int]]:
    """Immediate ancestors of `e` among `patterns`: maximal fitted patterns strictly inside `e`.

    Equal to ``immediate_ancestors(patterns + [e])[e]`` but computed for `e` alone -- the
    library routine rebuilds the whole lattice (quadratic in the number of fitted patterns),
    which on eICU (7,164 patterns) made each projected test set cost minutes.
    """
    subs = [p for p in patterns if p < e]
    subs.sort(key=len, reverse=True)
    out: list[frozenset[int]] = []
    for p in subs:
        if not any(p < q for q in out):
            out.append(p)
    return out


def _restrict(theta: dict[int, float], keys: frozenset[int]) -> dict[int, float]:
    """A superset pattern's coefficients on `keys` only (intercept kept, refit later)."""
    return {INTERCEPT: theta[INTERCEPT], **{v: theta[v] for v in sorted(keys)}}


def _refit_intercept(theta: dict[int, float], X_scaled, y, rows, cols) -> dict[int, float]:
    """Refit the intercept alone with the slopes fixed (Result 53: calibrate locally)."""
    if rows.sum() == 0 or len(np.unique(y[rows])) < 2:
        return theta
    z = X_scaled[np.ix_(rows, cols)] @ np.array([theta[v] for v in cols])
    lr = LogisticRegression(fit_intercept=True, max_iter=500)
    # one-dimensional refit: y ~ sigmoid(a + b*z) with b pinned near 1 via a fixed offset
    # is not available in sklearn; approximate by fitting on z and rescaling the slopes.
    lr.fit(z.reshape(-1, 1), y[rows])
    b = float(lr.coef_[0, 0]); a = float(lr.intercept_[0])
    out = {v: theta[v] * b for v in cols}
    out[INTERCEPT] = a
    return out


def project_unseen(est, X_test: np.ndarray, X_train: np.ndarray, y_train: np.ndarray,
                   kappa_proj: float, min_support: int | None = None):
    """Return a copy of the fitted estimator extended with projected test patterns.

    Records which test observed-sets were projected and by which route, in
    `est.projection_log_` as {pattern: (route, support, n_anchors)}.
    """
    est = copy.deepcopy(est)
    min_support = est.min_support if min_support is None else min_support
    Xtr = np.asarray(X_train, dtype=float); ytr = np.asarray(y_train).ravel()
    mask_tr = ~np.isnan(Xtr)
    Xs = est.scaler_.transform(Xtr)
    mask_te = ~np.isnan(np.asarray(X_test, dtype=float))
    fitted = set(est.patterns_)
    test_sets = {frozenset(np.flatnonzero(m).tolist()) for m in mask_te}
    test_sets = {e for e in test_sets if e and e not in fitted}
    log = {}
    new_theta: dict[frozenset[int], dict[int, float]] = {}
    new_support: dict[frozenset[int], int] = {}
    for e in sorted(test_sets, key=len):
        cols = sorted(e)
        rows = mask_tr[:, cols].all(axis=1)
        n = int(rows.sum())
        anc = _maximal_subsets(e, est.patterns_)
        anc = [a for a in anc if a in est.theta_]
        if anc:
            route = "ancestors"
            raw = est._fit_one(Xs, ytr, mask_tr, e) if n >= min_support and len(np.unique(ytr[rows])) > 1 \
                else {INTERCEPT: 0.0, **{v: 0.0 for v in cols}}
            n_eff = n if n >= min_support else 0
            th = shrink({e: raw, **{a: est.theta_[a] for a in anc}},
                        {e: n_eff, **{a: est.supports_[a] for a in anc}},
                        {e: anc}, kappa_proj)[e]
            n_anchor = len(anc)
        else:
            sups = [p for p in est.patterns_ if e < p]
            if not sups:
                continue  # nothing to anchor on; the prior fallback stands
            route = "supersets"
            # nearest supersets: minimal ones by size, support-weighted mean of their
            # restricted coefficients
            kmin = min(len(p) for p in sups)
            near = [p for p in sups if len(p) == kmin]
            w = np.array([est.supports_[p] for p in near], dtype=float); w /= w.sum()
            anchor = {k: float(sum(wi * _restrict(est.theta_[p], e)[k] for wi, p in zip(w, near)))
                      for k in [INTERCEPT, *cols]}
            anchor = _refit_intercept(anchor, Xs, ytr, rows, cols)
            if n >= min_support and len(np.unique(ytr[rows])) > 1:
                raw = est._fit_one(Xs, ytr, mask_tr, e)
                lam = n / (n + kappa_proj) if (n + kappa_proj) > 0 else 0.0
                th = {k: lam * raw[k] + (1 - lam) * anchor[k] for k in anchor}
            else:
                th = anchor
            n_anchor = len(near)
        new_theta[e] = th
        new_support[e] = max(n, 1)
        log[e] = (route, n, n_anchor)
    est.patterns_ = est.patterns_ + list(new_theta)
    est.theta_ = {**est.theta_, **new_theta}
    est.supports_ = {**est.supports_, **new_support}
    est.projection_log_ = log
    return est
